"""
scoring_engine/scoring.py
คำนวณคะแนน 0-100 จาก signals
Trend(40) + Momentum(25) + Volume(15) + Volatility(10) − Risk(10)
"""


def calculate_score(signals: dict) -> dict:
    score = 0
    detail = {}

    # ═══════════════════════════════
    # 1. TREND (0–40)
    # ═══════════════════════════════
    trend_score = 0
    if signals.get("ema_alignment"):       trend_score += 20   # EMA20>50>200
    if signals.get("price_above_ema50"):   trend_score += 10
    if signals.get("higher_high"):         trend_score += 10
    score += trend_score
    detail["trend"] = trend_score

    # ═══════════════════════════════
    # 2. MOMENTUM (0–25)
    # ═══════════════════════════════
    momentum_score = 0
    if signals.get("breakout_20d"):        momentum_score += 10
    if signals.get("rsi_strength"):        momentum_score += 5   # RSI 50–70
    if signals.get("relative_strength"):   momentum_score += 10
    score += momentum_score
    detail["momentum"] = momentum_score

    # ═══════════════════════════════
    # 3. VOLUME (0–15)
    # ═══════════════════════════════
    volume_score = 0
    if signals.get("volume_spike"):        volume_score += 10   # >1.5x avg
    if signals.get("accumulation"):        volume_score += 5
    score += volume_score
    detail["volume"] = volume_score

    # ═══════════════════════════════
    # 4. VOLATILITY (0–10)
    # ═══════════════════════════════
    vol_score = 0
    if signals.get("atr_expansion"):       vol_score += 5
    if signals.get("tight_range_breakout"):vol_score += 5
    score += vol_score
    detail["volatility"] = vol_score

    # ═══════════════════════════════
    # 5. RISK PENALTY (0–10)
    # ═══════════════════════════════
    risk_penalty = 0
    if signals.get("overbought"):          risk_penalty += 5   # RSI > 75
    if signals.get("near_resistance"):     risk_penalty += 5
    score -= risk_penalty
    detail["risk_penalty"] = risk_penalty

    # ═══════════════════════════════
    # Normalize 0–100
    # ═══════════════════════════════
    score = max(0, min(100, score))

    return {
        "total_score": score,
        "breakdown":   detail,
    }


def build_reasons(signals: dict, score_data: dict) -> list[str]:
    """สร้าง reason list สำหรับ display"""
    reasons = []
    bd = score_data.get("breakdown", {})

    if signals.get("ema_alignment"):
        reasons.append("📈 EMA20 > EMA50 > EMA200 (แนวโน้มขาขึ้น)")
    if signals.get("price_above_ema50"):
        reasons.append("✅ ราคาอยู่เหนือ EMA50")
    if signals.get("higher_high"):
        reasons.append("🔼 Higher High Pattern")
    if signals.get("breakout_20d"):
        reasons.append("🚀 Breakout จาก High 20 วัน")
    if signals.get("rsi_strength"):
        rsi = signals.get("_rsi", 0)
        reasons.append(f"💪 RSI อยู่ในโซนแข็งแกร่ง ({rsi:.1f})")
    if signals.get("relative_strength"):
        reasons.append("📊 MACD Histogram เป็นบวกและเพิ่มขึ้น")
    if signals.get("volume_spike"):
        reasons.append("📢 Volume สูงผิดปกติ (>1.5x เฉลี่ย)")
    if signals.get("accumulation"):
        reasons.append("🏦 สัญญาณ Accumulation (Volume ขึ้น ราคาไม่ลง)")
    if signals.get("atr_expansion"):
        reasons.append("⚡ ATR ขยายตัว — ความผันผวนเพิ่ม")
    if signals.get("tight_range_breakout"):
        reasons.append("💥 Tight Range Breakout")
    if signals.get("overbought"):
        reasons.append("⚠️ RSI Overbought (>75) — ระวัง")
    if signals.get("near_resistance"):
        reasons.append("⚠️ ราคาใกล้ Resistance (BB Upper)")

    return reasons
