"""
price_poller.py — ดึงราคาล่าสุดทุก 60 วินาที → broadcast WebSocket
ทำงานระหว่างเวลาตลาดเปิด:
  SET:  09:30–16:35 (UTC+7)
  NYSE: 21:30–04:00 (UTC+7 next day)
"""
import logging
import threading
import time
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
BKK = pytz.timezone("Asia/Bangkok")

# หุ้นที่ monitor แบบ real-time (top liquid)
SET_WATCHLIST  = ["PTT","PTTEP","KBANK","SCB","AOT","DELTA","ADVANC","BBL","CPF","SCC"]
US_WATCHLIST   = ["AAPL","MSFT","NVDA","TSLA","AMZN","META","GOOGL","SPY","QQQ","BRK-B"]

_poller_thread = None
_stop_event    = threading.Event()


def _is_market_open() -> str | None:
    """คืน 'SET', 'US' หรือ None"""
    now = datetime.now(BKK)
    h, m = now.hour, now.minute
    t = h * 60 + m
    if now.weekday() < 5:
        if 9*60+30 <= t <= 16*60+35:
            return "SET"
        if t >= 21*60+30 or t <= 4*60:
            return "US"
    return None


def _fetch_latest(symbols: list[str], suffix: str = "") -> list[dict]:
    """ดึงราคาล่าสุดจาก yfinance (1d interval 1m)"""
    import yfinance as yf
    results = []
    tickers = [f"{s}{suffix}" if suffix and not s.endswith(suffix) else s
               for s in symbols]
    try:
        data = yf.download(
            tickers, period="1d", interval="1m",
            progress=False, group_by="ticker",
            auto_adjust=True, threads=True
        )
        for sym, ticker in zip(symbols, tickers):
            try:
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker] if ticker in data.columns.get_level_values(0) else None
                if df is None or df.empty:
                    continue
                row = df.dropna().iloc[-1]
                results.append({
                    "symbol":  sym,
                    "price":   round(float(row["Close"]), 4),
                    "open":    round(float(row["Open"]), 4),
                    "high":    round(float(row["High"]), 4),
                    "low":     round(float(row["Low"]), 4),
                    "volume":  int(row["Volume"]),
                    "time":    df.index[-1].isoformat()[:19],
                    "delayed": True,
                })
            except Exception:
                continue
    except Exception as e:
        logger.error("fetch_latest error: %s", e)
    return results


def _poll_once():
    """ดึงราคาและ broadcast"""
    from radar.broadcaster import broadcast_prices
    market = _is_market_open()
    if not market:
        return

    if market == "SET":
        prices = _fetch_latest(SET_WATCHLIST, suffix=".BK")
    else:
        prices = _fetch_latest(US_WATCHLIST, suffix="")

    if prices:
        broadcast_prices(prices)
        logger.debug("Broadcast %d prices (%s)", len(prices), market)


def _poller_loop(interval: int = 60):
    logger.info("Price poller started (interval=%ds)", interval)
    while not _stop_event.is_set():
        try:
            _poll_once()
        except Exception as e:
            logger.error("Poller error: %s", e)
        _stop_event.wait(interval)
    logger.info("Price poller stopped")


def start_poller(interval: int = 60):
    global _poller_thread
    if _poller_thread and _poller_thread.is_alive():
        return
    _stop_event.clear()
    _poller_thread = threading.Thread(
        target=_poller_loop, args=(interval,),
        name="PricePoller", daemon=True
    )
    _poller_thread.start()


def stop_poller():
    _stop_event.set()
