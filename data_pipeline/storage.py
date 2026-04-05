"""
data_pipeline/storage.py
ดึงและจัดเก็บข้อมูล OHLCV จาก yfinance → DB
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


def _is_us_symbol(symbol: str) -> bool:
    """ตรวจว่าเป็นหุ้น US หรือไม่ (ดูจาก DB exchange)"""
    try:
        from radar.models import Symbol as SymbolModel
        sym = SymbolModel.objects.filter(symbol=symbol.upper()).first()
        return sym and sym.exchange in ("NASDAQ", "NYSE")
    except Exception:
        return False


def _fetch_ohlcv_alpaca(symbol: str, days: int = 365) -> pd.DataFrame:
    """ดึง OHLCV จาก Alpaca Data API สำหรับหุ้น US"""
    try:
        from radar.alpaca_service import get_bars
        bars = get_bars(symbol.upper(), timeframe="1Day", limit=days)
        if not bars:
            return pd.DataFrame()
        rows = []
        for b in bars:
            ts = b.get("t", "")
            if not ts:
                continue
            rows.append({
                "date":   date.fromisoformat(ts[:10]),
                "open":   float(b["o"]),
                "high":   float(b["h"]),
                "low":    float(b["l"]),
                "close":  float(b["c"]),
                "volume": int(b.get("v", 0)),
            })
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).set_index("date").sort_index()
        return df[["open", "high", "low", "close", "volume"]].dropna()
    except Exception as e:
        logger.error("fetch_ohlcv_alpaca %s: %s", symbol, e)
        return pd.DataFrame()


def fetch_ohlcv(symbol: str, days: int = 365) -> pd.DataFrame:
    """ดึงข้อมูล OHLCV — US ใช้ Alpaca, SET ใช้ yfinance"""
    # US stocks → Alpaca
    if _is_us_symbol(symbol):
        return _fetch_ohlcv_alpaca(symbol, days)

    # SET stocks → yfinance (เหมือนเดิม)
    ticker = symbol if symbol.endswith(".BK") else symbol
    end = date.today()
    start = end - timedelta(days=days)
    try:
        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True)
        if df.empty:
            df = yf.download(f"{symbol}.BK", start=start, end=end,
                             progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df = df.rename(columns=str.lower)
        df.index = pd.to_datetime(df.index).date
        df.index.name = "date"
        return df[["open", "high", "low", "close", "volume"]].dropna()
    except Exception as e:
        logger.error("fetch_ohlcv %s: %s", symbol, e)
        return pd.DataFrame()


def load_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    โหลดข้อมูลจาก DB ก่อน ถ้าไม่มีค่อย fetch จาก yfinance
    คืน DataFrame พร้อมใช้งาน (date index, OHLCV columns)
    """
    try:
        import django
        from radar.models import PriceDaily, Symbol as SymbolModel
        sym = SymbolModel.objects.filter(symbol=symbol.upper()).first()
        if sym:
            start = date.today() - timedelta(days=days)
            qs = (PriceDaily.objects
                  .filter(symbol=sym, date__gte=start)
                  .order_by("date")
                  .values("date", "open", "high", "low", "close", "volume"))
            if qs.exists():
                df = pd.DataFrame(list(qs))
                df = df.set_index("date")
                for col in ["open", "high", "low", "close"]:
                    df[col] = df[col].astype(float)
                return df
    except Exception:
        pass
    # Fallback: ดึงจาก yfinance
    return fetch_ohlcv(symbol, days)


def to_market_data_list(symbol: str, df: pd.DataFrame) -> list[MarketData]:
    """แปลง DataFrame → list[MarketData]"""
    result = []
    for idx, row in df.iterrows():
        result.append(MarketData(
            symbol=symbol,
            date=idx,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        ))
    return result
