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


def fetch_ohlcv(symbol: str, days: int = 365) -> pd.DataFrame:
    """ดึงข้อมูล OHLCV จาก yfinance"""
    ticker = symbol if symbol.endswith(".BK") else symbol
    end = date.today()
    start = end - timedelta(days=days)
    try:
        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True)
        if df.empty:
            # ลอง .BK suffix สำหรับหุ้น SET
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
