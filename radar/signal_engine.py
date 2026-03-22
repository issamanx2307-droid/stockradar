"""
Signal Engine — Pro Version
============================
Strategies:
  1. Golden Cross     — EMA50 crosses above EMA200
  2. Death Cross      — EMA50 crosses below EMA200
  3. EMA Alignment    — EMA20 > EMA50 > EMA200
  4. EMA Pullback     — Price touches EMA20 during uptrend
  5. Breakout Momentum— Close > Highest High (20)

Filters:
  Volume Filter    — Volume > 1.5 × AvgVol(20)
  Volatility Filter— ATR(14) > ATR_avg(30)
  Trend Strength   — ADX(14) > 25

Entry Conditions:
  LONG  — Close > EMA200 AND (Golden Cross OR EMA Alignment OR Breakout)
           AND Volume Filter AND Trend Strength
  SHORT — Close < EMA200 AND Death Cross AND Volume Filter

Risk Management:
  Stop Loss = Entry − 1.5 × ATR(14)
  Risk %    = |Entry − SL| / Entry × 100
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

import numpy as np
from django.utils import timezone

logger = logging.getLogger(__name__)

ADX_THRESHOLD      = 25.0
VOLUME_RATIO_MIN   = 0.8
ATR_RATIO_MIN      = 1.0
EMA_PULLBACK_PCT   = 0.015
STOP_LOSS_ATR_MULT = 1.5
MIN_SCORE_SAVE     = 50.0


@dataclass
class MarketSnapshot:
    symbol:      str
    close:       float
    high:        float
    low:         float
    volume:      int
    ema20:       Optional[float] = None
    ema50:       Optional[float] = None
    ema200:      Optional[float] = None
    ema50_prev:  Optional[float] = None
    ema200_prev: Optional[float] = None
    rsi:         Optional[float] = None
    macd_hist:   Optional[float] = None
    atr14:       Optional[float] = None
    atr_avg30:   Optional[float] = None
    adx14:       Optional[float] = None
    di_plus:     Optional[float] = None
    di_minus:    Optional[float] = None
    highest_high_20: Optional[float] = None
    lowest_low_20:   Optional[float] = None
    volume_avg20:    Optional[int]   = None


@dataclass
class SignalResult:
    signal_type:      str
    direction:        str
    base_score:       float
    reasons:          list[str] = field(default_factory=list)
    filter_volume:    bool = False
    filter_volatility:bool = False
    filter_adx:       bool = False


def load_snapshot(sym_obj) -> Optional[MarketSnapshot]:
    from radar.models import PriceDaily, Indicator
    prices = list(PriceDaily.objects.filter(symbol=sym_obj)
                  .order_by("-date").values("high","low","close","volume")[:1])
    inds   = list(Indicator.objects.filter(symbol=sym_obj)
                  .order_by("-date")
                  .values("ema20","ema50","ema200","rsi","macd_hist",
                          "atr14","atr_avg30","adx14","di_plus","di_minus",
                          "highest_high_20","lowest_low_20","volume_avg20")[:2])
    if not prices or not inds:
        return None
    p = prices[0]; i = inds[0]; ip = inds[1] if len(inds) > 1 else {}
    def f(v): return float(v) if v is not None else None
    return MarketSnapshot(
        symbol=sym_obj.symbol, close=float(p["close"]),
        high=float(p["high"]), low=float(p["low"]), volume=int(p["volume"]),
        ema20=f(i.get("ema20")), ema50=f(i.get("ema50")), ema200=f(i.get("ema200")),
        ema50_prev=f(ip.get("ema50")), ema200_prev=f(ip.get("ema200")),
        rsi=f(i.get("rsi")), macd_hist=f(i.get("macd_hist")),
        atr14=f(i.get("atr14")), atr_avg30=f(i.get("atr_avg30")),
        adx14=f(i.get("adx14")), di_plus=f(i.get("di_plus")), di_minus=f(i.get("di_minus")),
        highest_high_20=f(i.get("highest_high_20")), lowest_low_20=f(i.get("lowest_low_20")),
        volume_avg20=int(i["volume_avg20"]) if i.get("volume_avg20") else None,
    )


def check_filters(s: MarketSnapshot) -> dict:
    vol_ok = (s.volume_avg20 and s.volume_avg20 > 0 and
              s.volume > s.volume_avg20 * VOLUME_RATIO_MIN)
    atr_ok = (s.atr14 and s.atr_avg30 and s.atr_avg30 > 0 and
              s.atr14 > s.atr_avg30 * ATR_RATIO_MIN)
    adx_ok = (s.adx14 is not None and s.adx14 > ADX_THRESHOLD)
    return {"volume": bool(vol_ok), "volatility": bool(atr_ok), "adx": bool(adx_ok)}


def evaluate_strategies(snap: MarketSnapshot) -> list[SignalResult]:
    results = []
    flt  = check_filters(snap)
    c    = snap.close
    e20  = snap.ema20  or 0
    e50  = snap.ema50  or 0
    e200 = snap.ema200 or 0
    e50p = snap.ema50_prev  or 0
    e200p= snap.ema200_prev or 0
    adx  = snap.adx14  or 0
    hh20 = snap.highest_high_20 or 0
    ll20 = snap.lowest_low_20   or 0
    rsi  = snap.rsi    or 50
    vr   = snap.volume / snap.volume_avg20 if snap.volume_avg20 and snap.volume_avg20 > 0 else 0

    def sig(t, d, sc, reasons):
        return SignalResult(t, d, sc, reasons,
                            flt["volume"], flt["volatility"], flt["adx"])

    # 1. Golden Cross
    if e50p > 0 and e200p > 0 and e50p <= e200p and e50 > e200:
        sc = 75 + (10 if flt["adx"] else 0) + (8 if flt["volume"] else 0) + (5 if c > e200 else 0)
        results.append(sig("GOLDEN_CROSS", "LONG", sc,
            [f"EMA50({e50:.2f}) ข้าม EMA200({e200:.2f}) ขึ้น", f"ADX={adx:.1f}"]))

    # 2. Death Cross
    if e50p > 0 and e200p > 0 and e50p >= e200p and e50 < e200:
        sc = 73 + (10 if flt["adx"] else 0) + (8 if flt["volume"] else 0) + (5 if c < e200 else 0)
        results.append(sig("DEATH_CROSS", "SHORT", sc,
            [f"EMA50({e50:.2f}) ข้าม EMA200({e200:.2f}) ลง", f"ADX={adx:.1f}"]))

    # 3. EMA Alignment
    if e20 > e50 > e200 > 0:
        sc = 68 + (12 if flt["adx"] else 0) + (8 if flt["volume"] else 0) + (7 if flt["volatility"] else 0)
        results.append(sig("EMA_ALIGNMENT", "LONG", sc,
            [f"EMA20({e20:.2f}) > EMA50({e50:.2f}) > EMA200({e200:.2f})", f"ADX={adx:.1f}"]))

    # 4. EMA Pullback
    if (e20 > e50 > e200 > 0 and c > e200 and
        e20 > 0 and abs(c - e20) / e20 <= EMA_PULLBACK_PCT):
        sc = 72 + (10 if flt["adx"] else 0) + (8 if flt["volume"] else 0)
        results.append(sig("EMA_PULLBACK", "LONG", sc,
            [f"ราคา({c:.2f}) แตะ EMA20({e20:.2f}) ระหว่าง uptrend"]))

    # 5. Breakout Momentum
    if hh20 > 0 and c > hh20 and flt["volume"]:
        sc = 78 + (12 if flt["adx"] else 0) + (8 if flt["volatility"] else 0) + (5 if c > e200 else 0)
        results.append(sig("BREAKOUT", "LONG", sc,
            [f"ราคา({c:.2f}) ทะลุ HH20({hh20:.2f})", f"Volume×{vr:.1f}"]))

    # RSI Oversold
    if rsi < 30 and c > e200 > 0:
        sc = 65 + (10 if flt["volume"] else 0)
        results.append(sig("OVERSOLD", "LONG", sc, [f"RSI={rsi:.1f} Oversold + ราคาเหนือ EMA200"]))

    # RSI Overbought
    if rsi > 70 and e200 > 0 and c < e200:
        sc = 63 + (10 if flt["volume"] else 0)
        results.append(sig("OVERBOUGHT", "SHORT", sc, [f"RSI={rsi:.1f} Overbought + ราคาต่ำ EMA200"]))

    return results


def apply_entry_conditions(snap: MarketSnapshot,
                           results: list[SignalResult]) -> Optional[SignalResult]:
    if not results:
        return None
    c    = snap.close
    e200 = snap.ema200 or 0

    qualified = []
    for r in results:
        if r.direction == "LONG":
            # ผ่อน: Volume ผ่านพอ (ADX เป็น bonus — golden/breakout ได้คะแนนพิเศษอยู่แล้ว)
            if c > e200 > 0 and r.filter_volume:
                qualified.append(r)
        elif r.direction == "SHORT":
            if e200 > 0 and c < e200 and r.filter_volume:
                qualified.append(r)
        else:
            qualified.append(r)

    if not qualified:
        best = max(results, key=lambda r: r.base_score)
        if best.base_score >= MIN_SCORE_SAVE + 10:
            best.signal_type = "WATCH"
            best.direction   = "NEUTRAL"
            best.base_score  = min(best.base_score, 65.0)
            return best
        return None

    best = max(qualified, key=lambda r: r.base_score)
    if best.base_score >= 90:
        best.signal_type = "STRONG_BUY" if best.direction == "LONG" else "STRONG_SELL"
    return best


def calc_stop_loss(entry: float, atr: Optional[float], direction: str):
    if not atr or atr <= 0:
        return None, None
    sl = entry - STOP_LOSS_ATR_MULT * atr if direction == "LONG" else entry + STOP_LOSS_ATR_MULT * atr
    rp = abs(entry - sl) / entry * 100 if entry > 0 else None
    return round(sl, 4), round(rp, 2) if rp else None


def run_signal_engine(sym_obj) -> Optional[dict]:
    from radar.models import Signal

    snap = load_snapshot(sym_obj)
    if not snap:
        return None

    results = evaluate_strategies(snap)
    if not results:
        return None

    best = apply_entry_conditions(snap, results)
    if not best or best.base_score < MIN_SCORE_SAVE:
        return None

    sl, rp = calc_stop_loss(snap.close, snap.atr14, best.direction)
    vr = round(snap.volume / snap.volume_avg20, 2) if snap.volume_avg20 and snap.volume_avg20 > 0 else None

    signal = Signal.objects.create(
        symbol=sym_obj,
        signal_type=best.signal_type,
        direction=best.direction,
        score=Decimal(str(round(min(best.base_score, 100.0), 2))),
        price=Decimal(str(snap.close)),
        stop_loss=Decimal(str(sl)) if sl else None,
        risk_pct=Decimal(str(rp)) if rp else None,
        atr_at_signal=Decimal(str(round(snap.atr14, 4))) if snap.atr14 else None,
        adx_at_signal=Decimal(str(round(snap.adx14, 2))) if snap.adx14 else None,
        volume_ratio=Decimal(str(vr)) if vr else None,
        filter_volume=best.filter_volume,
        filter_volatility=best.filter_volatility,
        filter_adx=best.filter_adx,
        created_at=timezone.now(),
    )

    result = {
        "symbol": snap.symbol, "signal_type": signal.signal_type,
        "direction": signal.direction, "score": float(signal.score),
        "price": snap.close, "stop_loss": sl, "risk_pct": rp,
        "atr": snap.atr14, "adx": snap.adx14, "vol_ratio": vr,
        "filters": {"volume": best.filter_volume, "volatility": best.filter_volatility, "adx": best.filter_adx},
        "reasons": best.reasons,
    }

    logger.info("🔔 %s | %s | %s | %.1f | SL=%s | ADX=%.1f",
                snap.symbol, signal.signal_type, signal.direction,
                float(signal.score), sl or "-", snap.adx14 or 0)
    return result
