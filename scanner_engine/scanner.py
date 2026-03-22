"""
scanner_engine/scanner.py
แปลง indicators → signals dict พร้อมใช้ใน scoring engine
"""
import pandas as pd
from indicator_engine.indicators import compute_all


def scan_stock(df: pd.DataFrame) -> dict:
    """
    รับ OHLCV DataFrame คืน signals dict ทุก key
    ที่ scoring engine ต้องการ
    """
    if len(df) < 30:
        return {}

    ind = compute_all(df)
    close  = df["close"]
    volume = df["volume"]

    # ── ดึงค่าล่าสุด ──
    c   = close.iloc[-1]
    c1  = close.iloc[-2]       # วันก่อนหน้า
    e20 = ind["ema20"].iloc[-1]
    e50 = ind["ema50"].iloc[-1]
    e200= ind["ema200"].iloc[-1]
    rsi = ind["rsi14"].iloc[-1]
    atr = ind["atr14"].iloc[-1]
    vol = volume.iloc[-1]
    vavg= ind["vol_avg20"].iloc[-1]
    hh20= ind["hh20"].iloc[-2]      # High 20 วัน (ยกเว้นวันนี้)
    adx = ind["adx14"].iloc[-1]
    macd_h = ind["macd_hist"].iloc[-1]
    macd_h1= ind["macd_hist"].iloc[-2]
    bb_upper = ind["bb_upper"].iloc[-1]
    bb_lower = ind["bb_lower"].iloc[-1]

    # ── 1. TREND ──
    ema_alignment    = e20 > e50 > e200
    price_above_ema50 = c > e50
    higher_high      = c > c1 and close.iloc[-3] < c1  # HH pattern

    # ── 2. MOMENTUM ──
    breakout_20d     = c > hh20
    rsi_strength     = 50 <= rsi <= 70
    relative_strength = macd_h > 0 and macd_h > macd_h1  # MACD cross up

    # ── 3. VOLUME ──
    volume_spike     = vol > 1.5 * vavg
    accumulation     = volume_spike and c >= c1  # volume up + price not drop

    # ── 4. VOLATILITY ──
    atr_expansion    = atr > ind["atr14"].rolling(10).mean().iloc[-1] if hasattr(ind["atr14"], "rolling") else False
    # Tight range: ATR ต่ำกว่าค่าเฉลี่ย 20 วัน แล้วแตก
    atr_series = ind["atr14"]
    atr_mean20 = atr_series.rolling(20).mean().iloc[-2] if len(atr_series) >= 20 else atr
    tight_range_breakout = atr_series.iloc[-2] < atr_mean20 * 0.8 and breakout_20d

    # ── 5. RISK ──
    overbought       = rsi > 75
    near_resistance  = c > bb_upper * 0.98  # ราคาใกล้ BB Upper

    return {
        # Trend
        "ema_alignment":      bool(ema_alignment),
        "price_above_ema50":  bool(price_above_ema50),
        "higher_high":        bool(higher_high),
        # Momentum
        "breakout_20d":       bool(breakout_20d),
        "rsi_strength":       bool(rsi_strength),
        "relative_strength":  bool(relative_strength),
        # Volume
        "volume_spike":       bool(volume_spike),
        "accumulation":       bool(accumulation),
        # Volatility
        "atr_expansion":      bool(atr_expansion),
        "tight_range_breakout": bool(tight_range_breakout),
        # Risk
        "overbought":         bool(overbought),
        "near_resistance":    bool(near_resistance),
        # Raw values (ใช้ใน display)
        "_rsi":   round(float(rsi), 2),
        "_adx":   round(float(adx), 2),
        "_atr":   round(float(atr), 4),
        "_close": round(float(c), 4),
    }


def scan_many(symbol_df_pairs: list[tuple]) -> list[dict]:
    """
    scan หลายหุ้นพร้อมกัน (single thread version)
    คืน list ของ {symbol, signals}
    """
    results = []
    for symbol, df in symbol_df_pairs:
        try:
            signals = scan_stock(df)
            results.append({"symbol": symbol, "signals": signals})
        except Exception:
            continue
    return results
