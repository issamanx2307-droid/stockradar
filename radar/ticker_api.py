"""
ticker_api.py — ดึงราคาดัชนีและสินทรัพย์สำคัญสำหรับ Ticker Tape
Cache 5 นาที
"""
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

TICKER_SYMBOLS = [
    # ดัชนีไทย
    {"symbol": "^SET.BK",  "label": "SET",       "type": "index"},
    {"symbol": "^mai.BK",  "label": "mai",        "type": "index"},
    # ดัชนีสหรัฐ
    {"symbol": "^GSPC",    "label": "S&P 500",    "type": "index"},
    {"symbol": "^DJI",     "label": "Dow Jones",  "type": "index"},
    {"symbol": "^IXIC",    "label": "NASDAQ",     "type": "index"},
    {"symbol": "^VIX",     "label": "VIX",        "type": "index"},
    # เอเชีย
    {"symbol": "^N225",    "label": "Nikkei",     "type": "index"},
    {"symbol": "^HSI",     "label": "Hang Seng",  "type": "index"},
    {"symbol": "000001.SS","label": "Shanghai",   "type": "index"},
    # สินค้าโภคภัณฑ์
    {"symbol": "GC=F",     "label": "Gold",       "type": "commodity"},
    {"symbol": "CL=F",     "label": "Oil (WTI)",  "type": "commodity"},
    {"symbol": "SI=F",     "label": "Silver",     "type": "commodity"},
    # FX
    {"symbol": "THB=X",    "label": "USD/THB",    "type": "fx"},
    {"symbol": "EURUSD=X", "label": "EUR/USD",    "type": "fx"},
    {"symbol": "JPY=X",    "label": "USD/JPY",    "type": "fx"},
    # Crypto
    {"symbol": "BTC-USD",  "label": "Bitcoin",    "type": "crypto"},
    {"symbol": "ETH-USD",  "label": "Ethereum",   "type": "crypto"},
]


def _fetch_single(sym: str, meta: dict) -> dict | None:
    """ดึงข้อมูลดัชนี/สินทรัพย์เดี่ยว ด้วย Ticker().history() (single-level DataFrame)"""
    import yfinance as yf
    try:
        df = yf.Ticker(sym).history(period="5d", interval="1d")
        if df is None or df.empty:
            return None
        closes = df["Close"].dropna()
        if len(closes) < 2:
            return None
        price = float(closes.iloc[-1])
        prev  = float(closes.iloc[-2])
        if prev == 0:
            return None
        change     = price - prev
        change_pct = (change / prev) * 100
        return {
            "symbol":     sym,
            "label":      meta["label"],
            "type":       meta["type"],
            "price":      round(price, 4),
            "change":     round(change, 4),
            "change_pct": round(change_pct, 2),
            "up":         change >= 0,
        }
    except Exception:
        return None


def fetch_ticker_data() -> list[dict]:
    """ดึงราคาดัชนีทั้งหมด คืน list พร้อมแสดงผล"""
    cache_key = "ticker_tape_data"
    cached = cache.get(cache_key)
    if cached:
        return cached

    from concurrent.futures import ThreadPoolExecutor, as_completed

    label_map = {t["symbol"]: t for t in TICKER_SYMBOLS}
    results = []

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_fetch_single, t["symbol"], t): t["symbol"]
                for t in TICKER_SYMBOLS}
        for fut in as_completed(futs, timeout=25):
            item = fut.result()
            if item:
                results.append(item)

    # เรียงตามลำดับเดิม
    order = {t["symbol"]: i for i, t in enumerate(TICKER_SYMBOLS)}
    results.sort(key=lambda x: order.get(x["symbol"], 99))

    if results:
        cache.set(cache_key, results, timeout=300)
    else:
        logger.warning("ticker_tape: ไม่ได้ข้อมูลเลย — คืน fallback")

    return results
