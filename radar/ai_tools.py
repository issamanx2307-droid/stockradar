"""
AI Function Calling Tools สำหรับ Gemini Chat
แต่ละ tool ให้ Gemini เรียกได้เองเพื่อดึงข้อมูลจากระบบ StockRadar
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _sanitize(obj):
    """แปลง NaN/Inf → None เพื่อให้ serialize เป็น JSON ได้"""
    import math
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


# ─── Label ภาษาไทย ────────────────────────────────────────────────────────────

SETUP_LABEL_TH = {
    "STRONG_BUY":  "คะแนนดีมาก",
    "BUY":         "คะแนนดี",
    "WATCH_BUY":   "เฝ้าดู (โน้มเอียงขึ้น)",
    "WATCH_SELL":  "เฝ้าดู (โน้มเอียงลง)",
    "NEUTRAL":     "เฝ้าดู",
    "SELL":        "คะแนนต่ำ",
    "STRONG_SELL": "คะแนนต่ำมาก",
}

# ─── Layer Metadata — อธิบายให้ Gemini รู้ว่าแต่ละ Layer วัดอะไร ──────────────

LAYER_DESCRIPTIONS = {
    "layer1_trend": {
        "name": "Layer 1 — Trend (แนวโน้ม)",
        "what_it_measures": "การเรียงตัวของ EMA20/50/200 และตำแหน่งราคาสัมพันธ์กับ EMA",
        "pass_condition": "EMA20 > EMA50 > EMA200 และราคาปิดเหนือ EMA50 (แนวโน้มขาขึ้น) หรือ EMA20 < EMA50 < EMA200 และราคาต่ำกว่า EMA50 (แนวโน้มขาลง)",
        "fail_condition": "EMA20 ≈ EMA50 (ห่างกัน < 1%) = Sideways, หรือ EMA alignment ขัดแย้งกัน",
        "weight": "เป็น Layer หลัก — กำหนดทิศทาง (BUY/SELL) สำหรับ Layer 2-4",
        "key_indicators": ["EMA20", "EMA50", "EMA200", "Close price"],
    },
    "layer2_structure": {
        "name": "Layer 2 — Structure (แนวรับ/แนวต้าน)",
        "what_it_measures": "ตำแหน่งราคาสัมพันธ์กับ Pivot Points และ Dynamic S/R Cluster (60 วันย้อนหลัง)",
        "pass_condition": "BUY: ราคาใกล้แนวรับ ≤5% และไม่ชนแนวต้าน ≤2% | SELL: ราคาใกล้แนวต้าน ≤5%",
        "fail_condition": "ราคาอยู่กลางระหว่าง S/R หรือชนแนวต้านภายใน 2%",
        "weight": "ยืนยัน entry point — หุ้นผ่าน Layer 1 แต่ไม่ผ่าน Layer 2 หมายถึงยังไม่ใช่จุดเข้าที่ดี",
        "key_indicators": ["Pivot Point (PP, S1, S2, R1, R2)", "Dynamic S/R จาก local high/low ที่แตะซ้ำ ≥2 ครั้ง", "Highest High 20", "Lowest Low 20"],
    },
    "layer3_pattern": {
        "name": "Layer 3 — Pattern (Candlestick)",
        "what_it_measures": "รูปแบบแท่งเทียน 6 แบบจาก OHLC ล้วนๆ (ไม่ใช้ indicator)",
        "pass_condition": "BUY: พบ Hammer / Bullish Engulfing / Bullish Pin Bar | SELL: พบ Shooting Star / Bearish Engulfing / Bearish Pin Bar",
        "fail_condition": "ไม่พบ pattern หรือพบ pattern ที่ขัดแย้งกับ trend | Doji = ลังเล รอ confirm",
        "weight": "ยืนยัน timing — หุ้นผ่าน Layer 1+2 แต่ไม่ผ่าน Layer 3 หมายถึงยังไม่มีสัญญาณ price action",
        "key_indicators": ["Hammer", "Shooting Star", "Bullish/Bearish Engulfing", "Doji", "Bullish/Bearish Pin Bar"],
    },
    "layer4_momentum": {
        "name": "Layer 4 — Momentum (RSI + MACD)",
        "what_it_measures": "กำลังของโมเมนตัมปัจจุบัน",
        "pass_condition": "BUY: RSI อยู่ 40-65 (มีที่ไป) + MACD Hist > 0 หรือกำลังขึ้น | SELL: RSI 35-60 + MACD Hist < 0 หรือกำลังลง",
        "fail_condition": "BUY: RSI > 70 (Overbought ซื้อแล้วแพง) หรือ RSI < 35 แต่ MACD ยังลง | SELL: RSI < 35 (เสี่ยงเด้ง)",
        "weight": "กรองสัญญาณอ่อน — ถ้าผ่านทั้ง 4 Layer = setup แข็งแกร่งมาก",
        "key_indicators": ["RSI 14", "MACD Histogram", "MACD direction (rising/falling)"],
    },
}


# ─── Tool Definitions (google-genai format) ───────────────────────────────────

def get_tool_definitions():
    """คืน genai_types.Tool ที่ใช้ส่งให้ Gemini"""
    from google.genai import types as genai_types

    return genai_types.Tool(
        function_declarations=[
            genai_types.FunctionDeclaration(
                name="get_stock_analysis",
                description=(
                    "วิเคราะห์หุ้นด้วย Multi-Layer System (4 layers: Trend, Structure, Pattern, Momentum) "
                    "ใช้เมื่อ user ถามว่าหุ้นตัวใดตัวหนึ่งเป็นอย่างไร เช่น PTT เป็นยังไง, AAPL น่าซื้อไหม "
                    "ต้องถามผู้ใช้ก่อนว่าต้องการใช้ข้อมูลย้อนหลังกี่วัน แล้วค่อยเรียก tool นี้"
                ),
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "symbol": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="ชื่อหุ้น เช่น PTT, KBANK, AOT, AAPL, TSLA, NVDA",
                        ),
                        "days": genai_types.Schema(
                            type=genai_types.Type.INTEGER,
                            description="จำนวนวันย้อนหลังที่ใช้วิเคราะห์ (30-365) ค่าแนะนำ: 60=ระยะสั้น, 120=ระยะกลาง, 200=ระยะยาว",
                        ),
                    },
                    required=["symbol", "days"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="get_scanner_results",
                description=(
                    "ดึงรายการหุ้นที่ผ่านการสแกน Multi-Layer Scanner "
                    "ใช้เมื่อ user ถามว่า 'หุ้นอะไรน่าสนใจ', 'มีหุ้นคะแนนดีไหม', 'หาหุ้นให้หน่อย'"
                ),
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "setup": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="กรองตาม setup: STRONG_BUY, BUY, SELL, STRONG_SELL (ไม่ระบุ = ทั้งหมด)",
                        ),
                        "min_layers": genai_types.Schema(
                            type=genai_types.Type.INTEGER,
                            description="ผ่านขั้นต่ำกี่ layer 1-4 (default 2)",
                        ),
                        "exchange": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="ตลาด: SET, US, NASDAQ, NYSE (ไม่ระบุ = ทุกตลาด)",
                        ),
                    },
                    required=[],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="get_user_watchlist",
                description="ดู Watchlist ของ user ว่าติดตามหุ้นอะไรไว้บ้าง",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={},
                    required=[],
                ),
            ),
        ]
    )


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def handle_tool_call(name: str, args: dict, user) -> dict:
    """รับ tool call จาก Gemini แล้วส่งไปยัง handler ที่ถูกต้อง"""
    try:
        if name == "get_stock_analysis":
            result = _handle_get_stock_analysis(
                symbol=args.get("symbol", ""),
                days=int(args.get("days", 120)),
            )
        elif name == "get_scanner_results":
            result = _handle_get_scanner_results(
                setup=args.get("setup"),
                min_layers=int(args.get("min_layers", 2)),
                exchange=args.get("exchange"),
            )
        elif name == "get_user_watchlist":
            result = _handle_get_user_watchlist(user)
        else:
            result = {"error": f"ไม่รู้จัก tool: {name}"}
    except Exception as e:
        logger.error("Tool %s error: %s", name, e)
        result = {"error": f"เกิดข้อผิดพลาดภายในระบบ: {str(e)}"}

    return _sanitize(result)


# ─── Handlers ─────────────────────────────────────────────────────────────────

def _handle_get_stock_analysis(symbol: str, days: int = 120) -> dict:
    """วิเคราะห์หุ้น 1 ตัวด้วย Multi-Layer Engine"""
    import pandas as pd
    from datetime import date, timedelta
    from radar.models import Symbol, PriceDaily, Indicator
    from radar.indicator_cache import cached_load_latest_indicators
    from radar.multilayer_engine import analyze_symbol_multilayer

    symbol = symbol.upper().strip()
    if not symbol:
        return {"data_available": False, "error": "กรุณาระบุชื่อหุ้น"}

    # จำกัด days ให้อยู่ในช่วงที่สมเหตุสมผล
    days = max(30, min(365, days))

    sym = Symbol.objects.filter(symbol=symbol).first()
    if not sym:
        return {
            "data_available": False,
            "error": f"ไม่พบหุ้น '{symbol}' ในระบบ กรุณาตรวจสอบชื่อหุ้นอีกครั้ง",
        }

    since = date.today() - timedelta(days=days)
    prices = list(
        PriceDaily.objects
        .filter(symbol=sym, date__gte=since)
        .order_by("date")
        .values("date", "open", "high", "low", "close", "volume")
    )
    actual_days = len(prices)
    if actual_days < 5:
        return {
            "data_available": False,
            "error": (
                f"ข้อมูลราคา {symbol} มีเพียง {actual_days} วัน ไม่เพียงพอสำหรับวิเคราะห์ "
                f"(ต้องการอย่างน้อย 5 วัน)"
            ),
        }

    df = pd.DataFrame(prices)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # โหลด indicators ล่าสุด (สำหรับ multilayer engine)
    ind_df = cached_load_latest_indicators([sym.id])
    ema_cols = ["ema20", "ema50", "ema200", "rsi", "macd_hist"]
    if not ind_df.empty:
        row = ind_df.iloc[0]
        for col in ema_cols:
            val = row.get(col)
            df.loc[df.index[-1], col] = float(val) if val is not None else np.nan
    else:
        for col in ema_cols:
            df[col] = np.nan

    result = analyze_symbol_multilayer(df, symbol)

    # เพิ่มข้อมูลเสริม
    last = df.iloc[-1]
    result["data_available"] = True
    result["name"]        = sym.name
    result["exchange"]    = sym.exchange
    result["sector"]      = sym.sector or ""
    result["close"]       = round(float(last["close"]), 2)
    result["volume"]      = int(last["volume"]) if last.get("volume") else None
    result["date"]        = str(last["date"])
    result["days_used"]   = actual_days
    result["days_requested"] = days
    result["setup_th"]    = SETUP_LABEL_TH.get(result["setup"], result["setup"])

    # ── โหลด Indicators ทุกตัวจาก DB โดยตรง ──────────────────────────────────
    def _f(v, digits=2):
        if v is None:
            return None
        try:
            f = float(v)
            return round(f, digits) if f == f else None
        except Exception:
            return None

    ind_obj = (
        Indicator.objects
        .filter(symbol=sym)
        .order_by("-date")
        .values(
            "date",
            "ema20", "ema50", "ema200",
            "rsi",
            "macd", "macd_signal", "macd_hist",
            "bb_upper", "bb_middle", "bb_lower",
            "atr14", "atr_avg30",
            "adx14", "di_plus", "di_minus",
            "highest_high_20", "lowest_low_20",
            "volume_avg20", "volume_avg30",
        )
        .first()
    )

    if ind_obj:
        vol       = int(last["volume"]) if last.get("volume") else None
        avg20     = ind_obj["volume_avg20"]
        vol_ratio = round(vol / avg20, 2) if vol and avg20 else None

        result["indicators"] = {
            "ema20":           _f(ind_obj["ema20"]),
            "ema50":           _f(ind_obj["ema50"]),
            "ema200":          _f(ind_obj["ema200"]),
            "rsi":             _f(ind_obj["rsi"], 1),
            "macd":            _f(ind_obj["macd"], 4),
            "macd_signal":     _f(ind_obj["macd_signal"], 4),
            "macd_hist":       _f(ind_obj["macd_hist"], 4),
            "bb_upper":        _f(ind_obj["bb_upper"]),
            "bb_middle":       _f(ind_obj["bb_middle"]),
            "bb_lower":        _f(ind_obj["bb_lower"]),
            "atr14":           _f(ind_obj["atr14"], 4),
            "atr_avg30":       _f(ind_obj["atr_avg30"], 4),
            "adx14":           _f(ind_obj["adx14"], 1),
            "di_plus":         _f(ind_obj["di_plus"], 1),
            "di_minus":        _f(ind_obj["di_minus"], 1),
            "highest_high_20": _f(ind_obj["highest_high_20"]),
            "lowest_low_20":   _f(ind_obj["lowest_low_20"]),
            "volume":          vol,
            "volume_avg20":    int(avg20) if avg20 else None,
            "volume_ratio":    vol_ratio,
        }
        # บอก Gemini ว่า field ไหน null เพื่อไม่ให้เดา
        result["indicators"]["_null_fields"] = [
            k for k, v in result["indicators"].items()
            if v is None and not k.startswith("_")
        ]
    else:
        result["indicators"] = {
            "rsi":       _f(last.get("rsi"), 1),
            "ema20":     _f(last.get("ema20")),
            "ema50":     _f(last.get("ema50")),
            "ema200":    _f(last.get("ema200")),
            "macd_hist": _f(last.get("macd_hist"), 4),
            "_null_fields": ["bb_upper", "bb_middle", "bb_lower", "atr14", "adx14",
                             "di_plus", "di_minus", "volume_avg20"],
        }

    # ── Layer details (pass + detail จาก engine) ──────────────────────────────
    simplified_layers = {}
    for layer_name, layer_data in result.get("layers", {}).items():
        simplified_layers[layer_name] = {
            "pass":   layer_data.get("pass", False),
            "detail": layer_data.get("detail", layer_data.get("reason", "")),
            "signal": layer_data.get("signal", ""),
        }
    result["layers"] = simplified_layers

    # ── Layer Metadata — อธิบายระบบให้ Gemini เข้าใจน้ำหนักแต่ละ layer ─────────
    result["layer_system"] = LAYER_DESCRIPTIONS

    return result


def _handle_get_scanner_results(
    setup: str = None,
    min_layers: int = 2,
    exchange: str = None,
) -> dict:
    """สแกนหุ้นทั้งตลาดและคืนรายการที่ผ่าน filter"""
    from radar.multilayer_engine import run_multilayer_scan

    min_layers = max(1, min(4, min_layers or 2))

    try:
        results = run_multilayer_scan(
            exchange=exchange or None,
            min_layers=min_layers,
            setup_filter=setup or None,
            days=120,
            limit=15,
        )
    except Exception as e:
        return {"data_available": False, "error": f"สแกนไม่สำเร็จ: {str(e)}"}

    if not results:
        return {
            "data_available": True,
            "count": 0,
            "stocks": [],
            "filter": {"setup": setup, "min_layers": min_layers, "exchange": exchange},
            "note": "ไม่พบหุ้นที่ตรงเงื่อนไข ลองลด min_layers หรือเปลี่ยน setup",
        }

    simplified = [
        {
            "symbol":        r["symbol"],
            "name":          r["name"],
            "setup":         r["setup"],
            "setup_th":      SETUP_LABEL_TH.get(r["setup"], r["setup"]),
            "layers_passed": r["layers_passed"],
            "close":         r.get("close"),
            "exchange":      r.get("exchange", ""),
            "sector":        r.get("sector", ""),
        }
        for r in results
    ]

    return {
        "data_available": True,
        "count":  len(simplified),
        "filter": {"setup": setup, "min_layers": min_layers, "exchange": exchange},
        "stocks": simplified,
    }


def _handle_get_user_watchlist(user) -> dict:
    """ดู Watchlist ของ user"""
    from radar.models import Watchlist

    try:
        wl = Watchlist.objects.get(user=user)
        items = list(
            wl.items.select_related("symbol")
            .values("symbol__symbol", "symbol__name", "symbol__exchange")
        )
        return {
            "data_available": True,
            "count": len(items),
            "items": [
                {
                    "symbol":   i["symbol__symbol"],
                    "name":     i["symbol__name"],
                    "exchange": i["symbol__exchange"],
                }
                for i in items
            ],
        }
    except Watchlist.DoesNotExist:
        return {"data_available": True, "count": 0, "items": []}
