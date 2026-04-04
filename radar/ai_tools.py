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
                    "ใช้เมื่อ user ถามว่าหุ้นตัวใดตัวหนึ่งเป็นอย่างไร เช่น PTT เป็นยังไง, AAPL น่าซื้อไหม"
                ),
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "symbol": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="ชื่อหุ้น เช่น PTT, KBANK, AOT, AAPL, TSLA, NVDA",
                        ),
                    },
                    required=["symbol"],
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
            result = _handle_get_stock_analysis(args.get("symbol", ""))
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
        result = {"error": str(e)}

    return _sanitize(result)


# ─── Handlers ─────────────────────────────────────────────────────────────────

def _handle_get_stock_analysis(symbol: str) -> dict:
    """วิเคราะห์หุ้น 1 ตัวด้วย Multi-Layer Engine"""
    import pandas as pd
    from datetime import date, timedelta
    from radar.models import Symbol, PriceDaily, Indicator
    from radar.indicator_cache import cached_load_latest_indicators
    from radar.multilayer_engine import analyze_symbol_multilayer

    symbol = symbol.upper().strip()
    if not symbol:
        return {"error": "กรุณาระบุชื่อหุ้น"}

    sym = Symbol.objects.filter(symbol=symbol).first()
    if not sym:
        return {"error": f"ไม่พบหุ้น '{symbol}' ในระบบ"}

    # โหลดราคา 120 วันย้อนหลัง
    since = date.today() - timedelta(days=120)
    prices = list(
        PriceDaily.objects
        .filter(symbol=sym, date__gte=since)
        .order_by("date")
        .values("date", "open", "high", "low", "close", "volume")
    )
    if len(prices) < 5:
        return {"error": f"ข้อมูลราคา {symbol} ไม่เพียงพอสำหรับวิเคราะห์"}

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
    result["name"]     = sym.name
    result["exchange"] = sym.exchange
    result["sector"]   = sym.sector or ""
    result["close"]    = round(float(last["close"]), 2)
    result["volume"]   = int(last["volume"]) if last.get("volume") else None
    result["date"]     = str(last["date"])
    result["setup_th"] = SETUP_LABEL_TH.get(result["setup"], result["setup"])

    # ── โหลด Indicators ทุกตัวจาก DB โดยตรง ──────────────────────────────────
    def _f(v, digits=2):
        """แปลง Decimal/None → float หรือ None"""
        if v is None:
            return None
        try:
            f = float(v)
            return round(f, digits) if f == f else None  # NaN check
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
        vol     = int(last["volume"]) if last.get("volume") else None
        avg20   = ind_obj["volume_avg20"]
        vol_ratio = round(vol / avg20, 2) if vol and avg20 else None

        result["indicators"] = {
            # ── Trend ─────────────────────────────
            "ema20":           _f(ind_obj["ema20"]),
            "ema50":           _f(ind_obj["ema50"]),
            "ema200":          _f(ind_obj["ema200"]),
            # ── Momentum ──────────────────────────
            "rsi":             _f(ind_obj["rsi"], 1),
            "macd":            _f(ind_obj["macd"], 4),
            "macd_signal":     _f(ind_obj["macd_signal"], 4),
            "macd_hist":       _f(ind_obj["macd_hist"], 4),
            # ── Bollinger Bands ───────────────────
            "bb_upper":        _f(ind_obj["bb_upper"]),
            "bb_middle":       _f(ind_obj["bb_middle"]),
            "bb_lower":        _f(ind_obj["bb_lower"]),
            # ── Volatility ────────────────────────
            "atr14":           _f(ind_obj["atr14"], 4),
            "atr_avg30":       _f(ind_obj["atr_avg30"], 4),
            # ── Trend Strength (ADX/DMI) ──────────
            "adx14":           _f(ind_obj["adx14"], 1),
            "di_plus":         _f(ind_obj["di_plus"], 1),
            "di_minus":        _f(ind_obj["di_minus"], 1),
            # ── Support / Resistance ──────────────
            "highest_high_20": _f(ind_obj["highest_high_20"]),
            "lowest_low_20":   _f(ind_obj["lowest_low_20"]),
            # ── Volume ───────────────────────────
            "volume":          vol,
            "volume_avg20":    int(avg20) if avg20 else None,
            "volume_ratio":    vol_ratio,
        }
    else:
        # fallback: ดึงจาก df ที่ merge ไว้
        result["indicators"] = {
            "rsi":       _f(last.get("rsi"), 1),
            "ema20":     _f(last.get("ema20")),
            "ema50":     _f(last.get("ema50")),
            "ema200":    _f(last.get("ema200")),
            "macd_hist": _f(last.get("macd_hist"), 4),
        }

    # Simplify layers — เอาเฉพาะ pass + reason
    simplified_layers = {}
    for layer_name, layer_data in result.get("layers", {}).items():
        simplified_layers[layer_name] = {
            "pass":   layer_data.get("pass", False),
            "reason": layer_data.get("reason", ""),
        }
    result["layers"] = simplified_layers

    return result


def _handle_get_scanner_results(
    setup: str = None,
    min_layers: int = 2,
    exchange: str = None,
) -> dict:
    """สแกนหุ้นทั้งตลาดและคืนรายการที่ผ่าน filter"""
    from radar.multilayer_engine import run_multilayer_scan

    min_layers = max(1, min(4, min_layers or 2))

    results = run_multilayer_scan(
        exchange=exchange or None,
        min_layers=min_layers,
        setup_filter=setup or None,
        days=120,
        limit=15,  # ส่ง AI แค่ 15 ตัวเพื่อไม่ให้ token บาน
    )

    simplified = [
        {
            "symbol":       r["symbol"],
            "name":         r["name"],
            "setup":        r["setup"],
            "setup_th":     SETUP_LABEL_TH.get(r["setup"], r["setup"]),
            "layers_passed": r["layers_passed"],
            "close":        r.get("close"),
            "exchange":     r.get("exchange", ""),
            "sector":       r.get("sector", ""),
        }
        for r in results
    ]

    return {
        "count":    len(simplified),
        "filter":   {"setup": setup, "min_layers": min_layers, "exchange": exchange},
        "stocks":   simplified,
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
        return {"count": 0, "items": []}
