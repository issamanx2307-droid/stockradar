"""
indicator_engine/indicators.py
คำนวณ Technical Indicators ทั้งหมด
"""
import pandas as pd
import numpy as np


def ema(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].ewm(span=period, adjust=False).mean()


def sma(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].rolling(period).mean()


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    fast_ema = df["close"].ewm(span=fast, adjust=False).mean()
    slow_ema = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "hist": macd_line - signal_line,
    })


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close).abs(),
        (low - close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    atr14 = atr(df, period)
    plus_dm = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    # ถ้า +DM < -DM → +DM = 0
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr14
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr14
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1/period, adjust=False).mean()
    return pd.DataFrame({"adx": adx_val, "di_plus": plus_di, "di_minus": minus_di})


def bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    mid = df["close"].rolling(period).mean()
    sigma = df["close"].rolling(period).std()
    return pd.DataFrame({
        "bb_upper": mid + std * sigma,
        "bb_mid":   mid,
        "bb_lower": mid - std * sigma,
    })


def volume_avg(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["volume"].rolling(period).mean()


def highest_high(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["high"].rolling(period).max()


def lowest_low(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["low"].rolling(period).min()


def compute_all(df: pd.DataFrame) -> dict:
    """คำนวณ indicators ทั้งหมดพร้อมกัน คืน dict ของ Series"""
    result = {
        "ema20":  ema(df, 20),
        "ema50":  ema(df, 50),
        "ema200": ema(df, 200),
        "rsi14":  rsi(df, 14),
        "atr14":  atr(df, 14),
        "vol_avg20": volume_avg(df, 20),
        "hh20":   highest_high(df, 20),
        "ll20":   lowest_low(df, 20),
    }
    macd_df = macd(df)
    result["macd"] = macd_df["macd"]
    result["macd_signal"] = macd_df["signal"]
    result["macd_hist"] = macd_df["hist"]
    adx_df = adx(df)
    result["adx14"] = adx_df["adx"]
    result["di_plus"] = adx_df["di_plus"]
    result["di_minus"] = adx_df["di_minus"]
    bb_df = bollinger_bands(df)
    result["bb_upper"] = bb_df["bb_upper"]
    result["bb_mid"]   = bb_df["bb_mid"]
    result["bb_lower"] = bb_df["bb_lower"]
    return result
