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
    {"symbol": "THBUSD=X", "label": "USD/THB",    "type": "fx"},
    {"symbol": "EURUSD=X", "label": "EUR/USD",    "type": "fx"},
    {"symbol": "JPY=X",    "label": "USD/JPY",    "type": "fx"},
    # Crypto
    {"symbol": "BTC-USD",  "label": "Bitcoin",    "type": "crypto"},
    {"symbol": "ETH-USD",  "label": "Ethereum",   "type": "crypto"},
]


def fetch_ticker_data() -> list[dict]:
    """ดึงราคาดัชนีทั้งหมด คืน list พร้อมแสดงผล"""
    cache_key = "ticker_tape_data"
    cached = cache.get(cache_key)
    if cached:
        return cached

    import yfinance as yf

    symbols = [t["symbol"] for t in TICKER_SYMBOLS]
    label_map = {t["symbol"]: t for t in TICKER_SYMBOLS}

    results = []
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                info = tickers.tickers[sym].fast_info
                price     = getattr(info, "last_price", None)
                prev      = getattr(info, "previous_close", None)
                if price is None or prev is None or prev == 0:
                    continue

                change     = price - prev
                change_pct = (change / prev) * 100
                meta       = label_map[sym]

                results.append({
                    "symbol":     sym,
                    "label":      meta["label"],
                    "type":       meta["type"],
                    "price":      round(price, 4),
                    "change":     round(change, 4),
                    "change_pct": round(change_pct, 2),
                    "up":         change >= 0,
                })
            except Exception:
                continue
    except Exception as e:
        logger.error("ticker fetch error: %s", e)

    if results:
        cache.set(cache_key, results, timeout=300)  # 5 นาที
    return results
