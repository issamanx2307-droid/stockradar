"""
Multi-Layer Scanner Engine
===========================
วิเคราะห์หุ้นผ่าน 4 Layer เรียงตามลำดับ:

  Layer 1 — Trend     : EMA20/50/200 alignment
  Layer 2 — Structure : Pivot Points + Dynamic S/R Cluster
  Layer 3 — Pattern   : Candlestick Patterns (Hammer, Engulfing, Doji, Pin Bar)
  Layer 4 — Momentum  : RSI zone + MACD histogram direction

ผลลัพธ์ต่อหุ้น:
  - pass/fail แต่ละ layer
  - detail อธิบายว่าทำไม
  - setup = BUY | SELL | NEUTRAL
  - layers_passed = 0-4
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _sf(val, default: float = 0.0) -> float:
    """Safe float: แปลง None / NaN / invalid เป็น default (0 by default)"""
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f   # f != f is True only for NaN
    except (TypeError, ValueError):
        return default


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1 — Trend (EMA Alignment)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_trend(df: pd.DataFrame) -> dict:
    """
    ตรวจแนวโน้มจาก EMA20/50/200
    Strong Up  : EMA20 > EMA50 > EMA200 + ราคาเหนือ EMA50
    Weak Up    : EMA20 > EMA50 แต่ยังต่ำกว่า EMA200
    Sideways   : EMA20 ≈ EMA50 (ห่างกัน < 1%)
    Strong Down: EMA20 < EMA50 < EMA200
    """
    if len(df) < 5:
        return {"pass": False, "signal": "NO_DATA", "detail": "ข้อมูลไม่เพียงพอ", "direction": "NEUTRAL"}

    row   = df.iloc[-1]
    close = _sf(row.get("close"))
    ema20 = _sf(row.get("ema20"))
    ema50 = _sf(row.get("ema50"))
    ema200= _sf(row.get("ema200"))

    if ema20 <= 0 or ema50 <= 0:
        return {"pass": False, "signal": "NO_DATA", "detail": "ยังไม่มีข้อมูล EMA20/EMA50", "direction": "NEUTRAL"}
    # EMA200 อาจไม่มีสำหรับหุ้นใหม่ — ใช้เป็น optional

    above_ema200 = close > ema200
    above_ema50  = close > ema50
    ema20_above50 = ema20 > ema50
    ema50_above200= ema50 > ema200
    spread_pct   = abs(ema20 - ema50) / ema50 * 100

    if ema20_above50 and ema50_above200 and above_ema50:
        signal    = "STRONG_UP"
        passed    = True
        direction = "BUY"
        detail    = f"EMA20({ema20:.2f}) > EMA50({ema50:.2f}) > EMA200({ema200:.2f}) — แนวโน้มขาขึ้นแข็งแกร่ง"
    elif ema20_above50 and above_ema50 and not ema50_above200:
        signal    = "WEAK_UP"
        passed    = True
        direction = "BUY"
        detail    = f"EMA20 > EMA50 แต่ยังต่ำกว่า EMA200({ema200:.2f}) — ฟื้นตัวระยะสั้น"
    elif not ema20_above50 and not ema50_above200 and not above_ema50:
        signal    = "STRONG_DOWN"
        passed    = True
        direction = "SELL"
        detail    = f"EMA20({ema20:.2f}) < EMA50({ema50:.2f}) < EMA200({ema200:.2f}) — แนวโน้มขาลงแข็งแกร่ง"
    elif not ema20_above50 and not above_ema50:
        signal    = "WEAK_DOWN"
        passed    = True
        direction = "SELL"
        detail    = f"EMA20 < EMA50 — แนวโน้มขาลงระยะสั้น"
    elif spread_pct < 1.0:
        signal    = "SIDEWAYS"
        passed    = False
        direction = "NEUTRAL"
        detail    = f"EMA20 ≈ EMA50 (ห่างกัน {spread_pct:.1f}%) — ไม่มีทิศทางชัดเจน"
    else:
        signal    = "MIXED"
        passed    = False
        direction = "NEUTRAL"
        detail    = "EMA alignment ไม่สอดคล้องกัน — รอสัญญาณชัดขึ้น"

    return {
        "pass":      passed,
        "signal":    signal,
        "direction": direction,
        "detail":    detail,
        "values":    {"ema20": round(ema20,2), "ema50": round(ema50,2), "ema200": round(ema200,2), "close": round(close,2)},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2 — Structure (Support / Resistance)
# ═══════════════════════════════════════════════════════════════════════════════

def _find_dynamic_sr(df: pd.DataFrame, lookback: int = 60, tolerance: float = 0.015) -> list[dict]:
    """
    หา S/R levels จาก local high/low ที่ราคาแตะซ้ำ ≥ 2 ครั้ง
    Returns list ของ {"type": "S"|"R", "price": float, "strength": int}
    เรียงจาก strength มากไปน้อย (top 6)
    """
    recent = df.tail(lookback).copy()
    if len(recent) < 10:
        return []

    highs = recent["high"].astype(float).values
    lows  = recent["low"].astype(float).values
    levels: list[dict] = []

    for i in range(2, len(highs) - 2):
        # Local High → Resistance
        if highs[i] == max(highs[max(0,i-2):i+3]):
            price   = highs[i]
            touches = int(sum(abs(h - price) / price < tolerance for h in highs))
            if touches >= 2:
                levels.append({"type": "R", "price": round(float(price), 2), "strength": touches})

        # Local Low → Support
        if lows[i] == min(lows[max(0,i-2):i+3]):
            price   = lows[i]
            touches = int(sum(abs(l - price) / price < tolerance for l in lows))
            if touches >= 2:
                levels.append({"type": "S", "price": round(float(price), 2), "strength": touches})

    # กรองออก level ที่ใกล้กันเกินไป (merge zones ภายใน tolerance เดียวกัน)
    merged: list[dict] = []
    for lv in sorted(levels, key=lambda x: -x["strength"]):
        is_dup = any(abs(lv["price"] - m["price"]) / lv["price"] < tolerance for m in merged)
        if not is_dup:
            merged.append(lv)
        if len(merged) >= 6:
            break

    return merged


def _pivot_points(df: pd.DataFrame) -> dict:
    """Classic Pivot Points จากแท่งวันก่อน"""
    if len(df) < 2:
        return {}
    prev = df.iloc[-2]
    h = float(prev["high"]); l = float(prev["low"]); c = float(prev["close"])
    pp = (h + l + c) / 3
    return {
        "pp": round(pp, 2),
        "r1": round(2*pp - l, 2),
        "r2": round(pp + (h - l), 2),
        "s1": round(2*pp - h, 2),
        "s2": round(pp - (h - l), 2),
    }


def analyze_structure(df: pd.DataFrame, trend_direction: str = "NEUTRAL") -> dict:
    """
    ตรวจว่าราคาอยู่ในตำแหน่งที่ดีบน S/R Map ไหม:
      BUY setup  → ราคาใกล้แนวรับ (ห่าง < 3%) และไม่ชนแนวต้าน
      SELL setup → ราคาใกล้แนวต้าน (ห่าง < 3%) และไม่อยู่เหนือแนวรับ
    """
    if len(df) < 5:
        return {"pass": False, "signal": "NO_DATA", "detail": "ข้อมูลไม่เพียงพอ", "levels": [], "pivots": {}}

    close   = _sf(df.iloc[-1].get("close"))
    pivots  = _pivot_points(df)
    dyn_sr  = _find_dynamic_sr(df)
    all_levels = list(dyn_sr)

    # เพิ่ม Pivot Points เข้า level list
    if pivots:
        for k, price in [("s1", pivots.get("s1")), ("s2", pivots.get("s2")),
                          ("r1", pivots.get("r1")), ("r2", pivots.get("r2"))]:
            if price:
                all_levels.append({
                    "type": "S" if k.startswith("s") else "R",
                    "price": price,
                    "strength": 1,
                    "label": k.upper(),
                })

    if not all_levels:
        return {
            "pass": False, "signal": "NO_LEVELS",
            "detail": "ไม่พบแนวรับ/แนวต้านที่ชัดเจนในช่วง 60 วัน",
            "levels": [], "pivots": pivots,
        }

    # หาแนวรับ/ต้านที่ใกล้ที่สุด
    supports    = sorted([l for l in all_levels if l["type"] == "S" and l["price"] < close], key=lambda x: -x["price"])
    resistances = sorted([l for l in all_levels if l["type"] == "R" and l["price"] > close], key=lambda x: x["price"])

    nearest_s = supports[0]    if supports    else None
    nearest_r = resistances[0] if resistances else None

    dist_to_s = (close - nearest_s["price"]) / close * 100 if nearest_s else 999
    dist_to_r = (nearest_r["price"] - close) / close * 100 if nearest_r else 999

    NEAR_THRESHOLD  = 5.0   # ห่างแนวรับ/ต้าน ≤ 5% ถือว่า "ใกล้"
    DANGER_THRESHOLD= 2.0   # ชนแนวต้านภายใน 2% ถือว่า "เสี่ยง"

    if trend_direction in ("BUY", "NEUTRAL"):
        if nearest_s and dist_to_s <= NEAR_THRESHOLD:
            if nearest_r and dist_to_r <= DANGER_THRESHOLD:
                signal = "NEAR_RESISTANCE"
                passed = False
                detail = f"ใกล้แนวต้าน {nearest_r['price']} (ห่าง {dist_to_r:.1f}%) — พื้นที่เสี่ยง"
            else:
                signal = "NEAR_SUPPORT"
                passed = True
                detail = f"ใกล้แนวรับ {nearest_s['price']} (ห่าง {dist_to_s:.1f}%) — จุดเข้าที่ดี"
        elif nearest_r and dist_to_r <= DANGER_THRESHOLD:
            signal = "AT_RESISTANCE"
            passed = False
            detail = f"ชนแนวต้าน {nearest_r['price']} (ห่าง {dist_to_r:.1f}%) — ความเสี่ยงสูง"
        else:
            signal = "MID_ZONE"
            passed = False
            detail = f"อยู่กลางระหว่าง S({nearest_s['price'] if nearest_s else '?'}) และ R({nearest_r['price'] if nearest_r else '?'})"
    else:  # SELL
        if nearest_r and dist_to_r <= NEAR_THRESHOLD:
            if nearest_s and dist_to_s <= DANGER_THRESHOLD:
                signal = "NEAR_SUPPORT"
                passed = False
                detail = f"ใกล้แนวรับ {nearest_s['price']} (ห่าง {dist_to_s:.1f}%) — อาจเด้งกลับ"
            else:
                signal = "NEAR_RESISTANCE"
                passed = True
                detail = f"ใกล้แนวต้าน {nearest_r['price']} (ห่าง {dist_to_r:.1f}%) — จุด Short ที่ดี"
        else:
            signal = "MID_ZONE"
            passed = False
            detail = f"อยู่กลางระหว่าง S({nearest_s['price'] if nearest_s else '?'}) และ R({nearest_r['price'] if nearest_r else '?'})"

    return {
        "pass":    passed,
        "signal":  signal,
        "detail":  detail,
        "levels":  all_levels[:8],
        "pivots":  pivots,
        "nearest_support":    nearest_s,
        "nearest_resistance": nearest_r,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3 — Price Action (Candlestick Patterns)
# ═══════════════════════════════════════════════════════════════════════════════

def _body(o, c):
    return abs(c - o)

def _range(h, l):
    return h - l if h > l else 0.0001

def analyze_pattern(df: pd.DataFrame, trend_direction: str = "NEUTRAL") -> dict:
    """
    ตรวจ 5 candlestick patterns จาก OHLC ล้วนๆ:
      Bullish: Hammer, Bullish Engulfing, Morning Doji Star
      Bearish: Shooting Star, Bearish Engulfing
      Neutral: Doji
    """
    if len(df) < 3:
        return {"pass": False, "signal": "NO_DATA", "detail": "ข้อมูลไม่เพียงพอ", "patterns": []}

    patterns_found: list[str] = []
    df = df.tail(5).copy()
    rows = df.reset_index(drop=True)

    # ── แท่งปัจจุบัน (today) ──
    t   = rows.iloc[-1]
    o0  = float(t["open"]); h0 = float(t["high"]); l0 = float(t["low"]); c0 = float(t["close"])
    b0  = _body(o0, c0); r0 = _range(h0, l0)
    upper_wick0 = h0 - max(o0, c0)
    lower_wick0 = min(o0, c0) - l0
    is_bull0 = c0 > o0; is_bear0 = c0 < o0

    # ── แท่งก่อนหน้า (yesterday) ──
    t1  = rows.iloc[-2]
    o1  = float(t1["open"]); h1 = float(t1["high"]); l1 = float(t1["low"]); c1 = float(t1["close"])
    b1  = _body(o1, c1); r1 = _range(h1, l1)
    is_bull1 = c1 > o1; is_bear1 = c1 < o1

    # 1. Hammer (แท่งค้อน) — Bullish reversal
    if (lower_wick0 >= 2.0 * b0 and upper_wick0 <= 0.3 * b0
            and r0 > 0 and b0 / r0 < 0.35):
        patterns_found.append("HAMMER")

    # 2. Shooting Star (ดาวตก) — Bearish reversal
    if (upper_wick0 >= 2.0 * b0 and lower_wick0 <= 0.3 * b0
            and r0 > 0 and b0 / r0 < 0.35):
        patterns_found.append("SHOOTING_STAR")

    # 3. Bullish Engulfing (แท่งกลืนขาขึ้น)
    if (is_bear1 and is_bull0
            and o0 <= c1 and c0 >= o1
            and b0 >= b1 * 1.1):
        patterns_found.append("BULL_ENGULFING")

    # 4. Bearish Engulfing (แท่งกลืนขาลง)
    if (is_bull1 and is_bear0
            and o0 >= c1 and c0 <= o1
            and b0 >= b1 * 1.1):
        patterns_found.append("BEAR_ENGULFING")

    # 5. Doji (ลังเล)
    if r0 > 0 and b0 / r0 < 0.1:
        patterns_found.append("DOJI")

    # 6. Pin Bar (ไส้ยาวผิดปกติ)
    if r0 > 0:
        if lower_wick0 >= 0.6 * r0 and b0 / r0 < 0.25:
            patterns_found.append("BULLISH_PIN_BAR")
        elif upper_wick0 >= 0.6 * r0 and b0 / r0 < 0.25:
            patterns_found.append("BEARISH_PIN_BAR")

    # ── ตัดสิน pass/fail ตาม trend direction ──
    BULLISH_PATTERNS = {"HAMMER", "BULL_ENGULFING", "BULLISH_PIN_BAR"}
    BEARISH_PATTERNS = {"SHOOTING_STAR", "BEAR_ENGULFING", "BEARISH_PIN_BAR"}
    NEUTRAL_PATTERNS = {"DOJI"}

    LABEL_MAP = {
        "HAMMER":           "🔨 Hammer — ไส้ล่างยาว กลับตัวขาขึ้น",
        "SHOOTING_STAR":    "⭐ Shooting Star — ไส้บนยาว กลับตัวขาลง",
        "BULL_ENGULFING":   "🟢 Bullish Engulfing — แท่งกลืนขาขึ้น",
        "BEAR_ENGULFING":   "🔴 Bearish Engulfing — แท่งกลืนขาลง",
        "DOJI":             "➕ Doji — ลังเล จุดพลิก",
        "BULLISH_PIN_BAR":  "📌 Bullish Pin Bar — rejection ขาลง",
        "BEARISH_PIN_BAR":  "📌 Bearish Pin Bar — rejection ขาขึ้น",
    }

    found_bullish = [p for p in patterns_found if p in BULLISH_PATTERNS]
    found_bearish = [p for p in patterns_found if p in BEARISH_PATTERNS]
    found_neutral = [p for p in patterns_found if p in NEUTRAL_PATTERNS]

    if trend_direction in ("BUY", "NEUTRAL"):
        if found_bullish:
            passed = True
            primary = found_bullish[0]
            detail = LABEL_MAP.get(primary, primary)
        elif found_neutral:
            passed = False
            primary = "DOJI"
            detail = "Doji — ลังเล รอ confirm อีก 1 แท่ง"
        elif not patterns_found:
            passed = False
            primary = "NONE"
            detail = "ไม่พบ candlestick pattern ที่ชัดเจน"
        else:
            passed = False
            primary = found_bearish[0]
            detail = f"{LABEL_MAP.get(primary, primary)} — ขัดแย้งกับ trend"
    else:  # SELL
        if found_bearish:
            passed = True
            primary = found_bearish[0]
            detail = LABEL_MAP.get(primary, primary)
        elif found_neutral:
            passed = False
            primary = "DOJI"
            detail = "Doji — ลังเล รอ confirm อีก 1 แท่ง"
        elif not patterns_found:
            passed = False
            primary = "NONE"
            detail = "ไม่พบ candlestick pattern ที่ชัดเจน"
        else:
            passed = False
            primary = found_bullish[0]
            detail = f"{LABEL_MAP.get(primary, primary)} — ขัดแย้งกับ trend"

    return {
        "pass":     passed,
        "signal":   primary if patterns_found else "NONE",
        "detail":   detail,
        "patterns": [{"name": p, "label": LABEL_MAP.get(p, p)} for p in patterns_found],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4 — Momentum (RSI + MACD)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_momentum(df: pd.DataFrame, trend_direction: str = "NEUTRAL") -> dict:
    """
    RSI zone + MACD histogram direction
    BUY  pass: RSI 40-65 (มีที่ไป) + MACD hist > 0 หรือกำลังขึ้น
    SELL pass: RSI 35-60 + MACD hist < 0 หรือกำลังลง
    """
    if len(df) < 3:
        return {"pass": False, "signal": "NO_DATA", "detail": "ข้อมูลไม่เพียงพอ"}

    row  = df.iloc[-1]
    prev = df.iloc[-2]
    rsi            = _sf(row.get("rsi"))
    macd_hist      = _sf(row.get("macd_hist"))
    # prev row ไม่มี indicator — ใช้ 0 เป็น baseline (ดีกว่า NaN ที่ทำให้ comparison ล้ม)
    macd_hist_prev_raw = _sf(prev.get("macd_hist"))
    macd_hist_prev = macd_hist_prev_raw  # 0 ถ้าไม่มีข้อมูล

    if rsi <= 0:
        return {"pass": False, "signal": "NO_DATA", "detail": "ยังไม่มีข้อมูล RSI"}

    macd_rising  = macd_hist > macd_hist_prev
    macd_falling = macd_hist < macd_hist_prev
    macd_pos     = macd_hist > 0
    macd_neg     = macd_hist < 0

    rsi_oversold   = rsi < 35
    rsi_overbought = rsi > 70
    rsi_healthy_up = 40 <= rsi <= 65
    rsi_healthy_dn = 35 <= rsi <= 60

    if trend_direction in ("BUY", "NEUTRAL"):
        if rsi_overbought:
            passed = False
            signal = "OVERBOUGHT"
            detail = f"RSI={rsi:.1f} Overbought — ความเสี่ยงปรับฐานสูง"
        elif rsi_healthy_up and (macd_pos or macd_rising):
            passed = True
            signal = "BULLISH"
            macd_desc = "MACD Hist > 0" if macd_pos else "MACD กำลังขึ้น"
            detail = f"RSI={rsi:.1f} มีที่ไป + {macd_desc} — momentum บวก"
        elif rsi_oversold and macd_rising:
            passed = True
            signal = "OVERSOLD_RECOVERY"
            detail = f"RSI={rsi:.1f} Oversold + MACD กำลังเด้ง — โอกาสกลับตัว"
        elif rsi_oversold:
            passed = False
            signal = "OVERSOLD_FALLING"
            detail = f"RSI={rsi:.1f} Oversold แต่ MACD ยังลง — รอสัญญาณเด้ง"
        else:
            passed = False
            signal = "WEAK"
            detail = f"RSI={rsi:.1f} + MACD ไม่สนับสนุน — momentum ไม่ชัดเจน"
    else:  # SELL
        if rsi_oversold:
            passed = False
            signal = "OVERSOLD"
            detail = f"RSI={rsi:.1f} Oversold — อาจเด้งกลับ เสี่ยงต่อ Short"
        elif rsi_healthy_dn and (macd_neg or macd_falling):
            passed = True
            signal = "BEARISH"
            macd_desc = "MACD Hist < 0" if macd_neg else "MACD กำลังลง"
            detail = f"RSI={rsi:.1f} + {macd_desc} — momentum ลบ"
        elif rsi_overbought and macd_falling:
            passed = True
            signal = "OVERBOUGHT_REVERSAL"
            detail = f"RSI={rsi:.1f} Overbought + MACD กำลังหมุน — โอกาส Short"
        else:
            passed = False
            signal = "WEAK"
            detail = f"RSI={rsi:.1f} + MACD ไม่สนับสนุน — momentum ไม่ชัดเจน"

    return {
        "pass":   passed,
        "signal": signal,
        "detail": detail,
        "values": {
            "rsi":        round(rsi, 1),
            "macd_hist":  round(macd_hist, 4),
            "macd_rising": macd_rising,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Master — วิเคราะห์ 1 หุ้ว
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_symbol_multilayer(df: pd.DataFrame, symbol: str = "") -> dict:
    """
    รับ DataFrame OHLCV + indicators ของหุ้น 1 ตัว
    คืนผลวิเคราะห์ทั้ง 4 layers

    df ต้องมี columns:
      open, high, low, close, volume,
      ema20, ema50, ema200, rsi, macd_hist
    เรียงตาม date จากเก่าไปใหม่
    """
    if df.empty or len(df) < 5:
        return {
            "symbol": symbol, "layers_passed": 0, "setup": "NEUTRAL",
            "confidence": "NONE", "error": "ข้อมูลไม่เพียงพอ",
        }

    # Layer 1
    trend = analyze_trend(df)
    direction = trend.get("direction", "NEUTRAL")

    # Layer 2
    structure = analyze_structure(df, direction)

    # Layer 3
    pattern = analyze_pattern(df, direction)

    # Layer 4
    momentum = analyze_momentum(df, direction)

    passed = sum([
        trend["pass"], structure["pass"],
        pattern["pass"], momentum["pass"]
    ])

    # Setup
    if direction in ("BUY",) and passed >= 3:
        setup = "BUY"
    elif direction in ("SELL",) and passed >= 3:
        setup = "SELL"
    elif direction in ("BUY",) and passed == 2:
        setup = "WATCH_BUY"
    elif direction in ("SELL",) and passed == 2:
        setup = "WATCH_SELL"
    else:
        setup = "NEUTRAL"

    # Confidence
    if passed == 4:
        confidence = "HIGH"
    elif passed == 3:
        confidence = "MEDIUM"
    elif passed == 2:
        confidence = "LOW"
    else:
        confidence = "NONE"

    return {
        "symbol":        symbol,
        "layers_passed": passed,
        "setup":         setup,
        "confidence":    confidence,
        "direction":     direction,
        "layers": {
            "trend":     trend,
            "structure": structure,
            "pattern":   pattern,
            "momentum":  momentum,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Batch Scanner — ใช้ใน API view
# ═══════════════════════════════════════════════════════════════════════════════

def run_multilayer_scan(
    exchange: Optional[str] = None,
    min_layers: int = 2,
    setup_filter: Optional[str] = None,
    days: int = 120,
    limit: int = 200,
) -> list[dict]:
    """
    สแกนหุ้นทั้งตลาดด้วย 4-layer filter
    คืน list ของหุ้นที่ผ่าน ≥ min_layers เรียงจาก layers_passed มากไปน้อย
    """
    from radar.models import Symbol, PriceDaily, Indicator
    from django.db.models import OuterRef, Subquery
    from datetime import date, timedelta

    # โหลด symbols
    sym_qs = Symbol.objects.all()
    if exchange:
        ex = exchange.upper()
        if ex == "US":
            sym_qs = sym_qs.filter(exchange__in=["NASDAQ", "NYSE"])
        else:
            sym_qs = sym_qs.filter(exchange=ex)

    symbols = list(sym_qs.values("id", "symbol", "name", "exchange", "sector"))
    if not symbols:
        return []

    sym_ids = [s["id"] for s in symbols]
    sym_map = {s["id"]: s for s in symbols}

    # Bulk load price history
    since = date.today() - timedelta(days=days)
    prices_qs = (PriceDaily.objects
                 .filter(symbol_id__in=sym_ids, date__gte=since)
                 .order_by("symbol_id", "date")
                 .values("symbol_id", "date", "open", "high", "low", "close", "volume"))
    price_df = pd.DataFrame(list(prices_qs))
    if price_df.empty:
        return []
    for col in ["open", "high", "low", "close", "volume"]:
        price_df[col] = pd.to_numeric(price_df[col], errors="coerce")

    # Bulk load latest indicators (ใช้ indicator_cache)
    from radar.indicator_cache import cached_load_latest_indicators
    ind_df = cached_load_latest_indicators(sym_ids)
    ind_map: dict[int, dict] = {}
    if not ind_df.empty:
        for _, row in ind_df.iterrows():
            ind_map[int(row["symbol_id"])] = row.to_dict()

    results: list[dict] = []

    for sid in sym_ids:
        sym_info = sym_map.get(sid)
        if not sym_info:
            continue

        # Price history สำหรับ symbol นี้
        pf = price_df[price_df["symbol_id"] == sid].copy()
        if len(pf) < 5:
            continue

        # Merge indicators เข้าแถวสุดท้าย
        ind = ind_map.get(sid, {})
        if ind:
            for col in ["ema20", "ema50", "ema200", "rsi", "macd_hist"]:
                val = ind.get(col)
                pf.loc[pf.index[-1], col] = float(val) if val is not None else np.nan
        else:
            for col in ["ema20", "ema50", "ema200", "rsi", "macd_hist"]:
                pf[col] = np.nan

        try:
            result = analyze_symbol_multilayer(pf, sym_info["symbol"])
        except Exception as e:
            logger.warning("multilayer error %s: %s", sym_info["symbol"], e)
            continue

        # กรอง
        if result["layers_passed"] < min_layers:
            continue
        if setup_filter and result["setup"] != setup_filter:
            continue

        result["name"]     = sym_info.get("name", "")
        result["exchange"] = sym_info.get("exchange", "")
        result["sector"]   = sym_info.get("sector", "")
        close_val = float(pf.iloc[-1]["close"]) if not pf.empty else 0
        result["close"] = round(close_val, 2)

        results.append(result)
        if len(results) >= limit:
            break

    results.sort(key=lambda x: (-x["layers_passed"], x["symbol"]))

    # Safety filter — กันกรณี sym_map มี exchange ปนกัน
    if exchange:
        ex = exchange.upper()
        if ex == "US":
            results = [r for r in results if r.get("exchange") in ("NASDAQ", "NYSE")]
        else:
            results = [r for r in results if r.get("exchange") == ex]

    return results
