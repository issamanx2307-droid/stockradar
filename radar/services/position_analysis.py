from decimal import Decimal
from typing import Any

from django.utils import timezone


def _d(v: Any, places: int = 4) -> Decimal | None:
    try:
        if v is None:
            return None
        return Decimal(str(round(float(v), places)))
    except Exception:
        return None


def _pct(a: Decimal, b: Decimal) -> Decimal:
    if b == 0:
        return Decimal("0")
    return (a / b) * Decimal("100")


def analyze_position(symbol_obj, buy_price: Decimal, user=None) -> dict:
    from radar.models import PriceDaily, Indicator, PositionAnalysis

    latest_price = (PriceDaily.objects
                    .filter(symbol=symbol_obj)
                    .order_by("-date")
                    .values("date", "close")
                    .first())
    latest_ind = (Indicator.objects
                  .filter(symbol=symbol_obj)
                  .order_by("-date")
                  .values("date", "rsi", "ema20", "ema50", "ema200", "adx14")
                  .first())

    if not latest_price:
        raise ValueError("NO_MARKET_DATA")

    market_price = _d(latest_price["close"], 4) or Decimal("0")
    buy = _d(buy_price, 4) or Decimal("0")
    pnl_pct = _pct(market_price - buy, buy).quantize(Decimal("0.01")) if buy > 0 else Decimal("0.00")

    rsi14 = _d(latest_ind.get("rsi") if latest_ind else None, 2)
    ema20 = _d(latest_ind.get("ema20") if latest_ind else None, 4)
    ema50 = _d(latest_ind.get("ema50") if latest_ind else None, 4)
    ema200 = _d(latest_ind.get("ema200") if latest_ind else None, 4)
    adx14 = _d(latest_ind.get("adx14") if latest_ind else None, 2)

    score = Decimal("50.0")
    signals: dict[str, Any] = {}
    reasons: list[str] = []

    if buy <= 0:
        reasons.append("ไม่สามารถคำนวณ P/L ได้เพราะราคาเข้าซื้อไม่ถูกต้อง")
    else:
        if pnl_pct <= Decimal("-10"):
            score += Decimal("6")
            reasons.append("ขาดทุนมากกว่า 10%: เพิ่มความสำคัญด้านการบริหารความเสี่ยง")
            signals["pnl_bucket"] = "loss_gt_10"
        elif pnl_pct <= Decimal("-5"):
            score += Decimal("3")
            reasons.append("ขาดทุนมากกว่า 5%: ควรทบทวนจุดตัดขาดทุน/แผนเดิม")
            signals["pnl_bucket"] = "loss_5_10"
        elif pnl_pct >= Decimal("10"):
            score -= Decimal("4")
            reasons.append("กำไรมากกว่า 10%: พิจารณาการปกป้องกำไรและความเสี่ยงขาลง")
            signals["pnl_bucket"] = "profit_gt_10"
        elif pnl_pct >= Decimal("5"):
            score -= Decimal("2")
            reasons.append("กำไรมากกว่า 5%: โฟกัสการรักษาแนวโน้มและจุดยืนยัน")
            signals["pnl_bucket"] = "profit_5_10"

    trend_up = None
    if ema200 and market_price > 0:
        if market_price >= ema200:
            score += Decimal("6")
            reasons.append("ราคาอยู่เหนือ EMA200: แนวโน้มหลักเป็นบวก")
            trend_up = True
        else:
            score -= Decimal("6")
            reasons.append("ราคาอยู่ต่ำกว่า EMA200: แนวโน้มหลักอ่อนแรง")
            trend_up = False
    signals["trend_vs_ema200"] = trend_up

    alignment = None
    if ema20 and ema50 and ema200:
        if ema20 > ema50 > ema200:
            score += Decimal("5")
            reasons.append("EMA20 > EMA50 > EMA200: โครงสร้างแนวโน้มขาขึ้นชัด")
            alignment = "bull"
        elif ema20 < ema50 < ema200:
            score -= Decimal("5")
            reasons.append("EMA20 < EMA50 < EMA200: โครงสร้างแนวโน้มขาลงชัด")
            alignment = "bear"
        else:
            alignment = "mixed"
    signals["ema_alignment"] = alignment

    if rsi14 is not None:
        if rsi14 < Decimal("30"):
            score += Decimal("5")
            reasons.append("RSI ต่ำกว่า 30: โมเมนตัมขายมาก (อาจเกิดการเด้ง) ต้องใช้ตัวกรองเทรนด์ร่วม")
            signals["rsi_state"] = "oversold"
        elif rsi14 > Decimal("70"):
            score -= Decimal("5")
            reasons.append("RSI สูงกว่า 70: โมเมนตัมร้อนแรง/เสี่ยงพักตัว")
            signals["rsi_state"] = "overbought"
        elif rsi14 >= Decimal("50"):
            score += Decimal("2")
            reasons.append("RSI อยู่โซนแข็งแรง (>= 50): โมเมนตัมฝั่งบวกได้เปรียบ")
            signals["rsi_state"] = "bullish"
        else:
            score -= Decimal("1")
            reasons.append("RSI ต่ำกว่า 50: โมเมนตัมเริ่มอ่อนลง")
            signals["rsi_state"] = "bearish"

    if adx14 is not None:
        if adx14 >= Decimal("25"):
            score += Decimal("2")
            reasons.append("ADX >= 25: เทรนด์มีความชัดเจนมากขึ้น")
            signals["adx_trend"] = "strong"
        else:
            signals["adx_trend"] = "weak"

    score = max(Decimal("0"), min(Decimal("100"), score))

    if score >= Decimal("62"):
        decision = "BUY_MORE"
    elif score <= Decimal("38"):
        decision = "SELL"
    else:
        decision = "HOLD"

    distance = abs(score - Decimal("50"))
    confidence = min(Decimal("95"), (Decimal("50") + distance).quantize(Decimal("0.01")))

    explanation = (
        "ผลลัพธ์นี้เป็นการวิเคราะห์เชิงข้อมูลและกฎ (rule-based) เพื่อช่วยทำความเข้าใจสถานะการถือครอง "
        "ไม่ใช่คำแนะนำการลงทุน\n"
        f"- ราคาเข้าซื้อ: {buy}\n"
        f"- ราคาตลาดล่าสุด: {market_price}\n"
        f"- P/L (%): {pnl_pct}\n"
        + "\n".join([f"- {r}" for r in reasons[:8]])
    )

    analysis = PositionAnalysis.objects.create(
        user=user if (user and getattr(user, "is_authenticated", False)) else None,
        symbol=symbol_obj,
        buy_price=buy,
        market_price=market_price,
        pnl_pct=pnl_pct,
        rsi14=rsi14,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        adx14=adx14,
        decision=decision,
        confidence=confidence,
        score=score,
        explanation=explanation,
        signals=signals,
        created_at=timezone.now(),
    )

    return {
        "symbol": symbol_obj.symbol,
        "buy_price": float(buy),
        "market_price": float(market_price),
        "pnl_pct": float(pnl_pct),
        "indicators": {
            "rsi14": float(rsi14) if rsi14 is not None else None,
            "ema20": float(ema20) if ema20 is not None else None,
            "ema50": float(ema50) if ema50 is not None else None,
            "ema200": float(ema200) if ema200 is not None else None,
            "adx14": float(adx14) if adx14 is not None else None,
        },
        "decision": decision,
        "score": float(score),
        "confidence": float(confidence),
        "explanation": explanation,
        "signals": signals,
        "analysis_id": analysis.id,
    }

