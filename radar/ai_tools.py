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
    from radar.models import Symbol, PriceDaily
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

    # โหลด indicators ล่าสุด
    ind_df = cached_load_latest_indicators([sym.id])
    if not ind_df.empty:
        row = ind_df.iloc[0]
        for col in ["ema20", "ema50", "ema200", "rsi", "macd_hist"]:
            val = row.get(col)
            df.loc[df.index[-1], col] = float(val) if val is not None else np.nan
    else:
        for col in ["ema20", "ema50", "ema200", "rsi", "macd_hist"]:
            df[col] = np.nan

    result = analyze_symbol_multilayer(df, symbol)

    # เพิ่มข้อมูลเสริม
    last = df.iloc[-1]
    result["name"]     = sym.name
    result["exchange"] = sym.exchange
    result["sector"]   = sym.sector or ""
    result["close"]    = round(float(last["close"]), 2)
    result["date"]     = str(last["date"])
    result["setup_th"] = SETUP_LABEL_TH.get(result["setup"], result["setup"])

    # Indicators สำหรับ AI อ่าน
    result["indicators"] = {
        "rsi":       round(float(last.get("rsi", 0) or 0), 1),
        "ema20":     round(float(last.get("ema20", 0) or 0), 2),
        "ema50":     round(float(last.get("ema50", 0) or 0), 2),
        "ema200":    round(float(last.get("ema200", 0) or 0), 2),
        "macd_hist": round(float(last.get("macd_hist", 0) or 0), 4),
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
