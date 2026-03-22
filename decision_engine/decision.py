"""
decision_engine/decision.py
แปลง score → decision + position sizing
"""


def make_decision(score: float) -> str:
    if score >= 80:
        return "STRONG BUY"
    elif score >= 60:
        return "BUY"
    elif score >= 40:
        return "HOLD"
    elif score >= 20:
        return "WATCH"
    else:
        return "SELL"


def calculate_position_size(
    capital: float,
    risk_pct: float,      # เช่น 0.01 = เสี่ยงได้ 1% ของ capital
    entry: float,
    stop_loss: float,
) -> int:
    """
    Position Sizing แบบ Fixed Fractional Risk
    size = (capital × risk_pct) / (entry − stop_loss)
    """
    if entry <= stop_loss or entry <= 0:
        return 0
    risk_per_share = entry - stop_loss
    risk_amount = capital * risk_pct
    size = int(risk_amount / risk_per_share)
    # Cap ที่ 30% ของ capital
    max_size = int((capital * 0.30) / entry)
    return min(size, max_size)


def analyze_stock(df, capital: float = 100_000) -> dict:
    """
    Pipeline เต็ม: OHLCV → signals → score → decision → size
    """
    from scanner_engine.scanner import scan_stock
    from scoring_engine.scoring import calculate_score, build_reasons

    signals   = scan_stock(df)
    if not signals:
        return {}

    score_data = calculate_score(signals)
    score      = score_data["total_score"]
    decision   = make_decision(score)
    reasons    = build_reasons(signals, score_data)

    entry      = float(df["close"].iloc[-1])
    stop_loss  = round(entry - 1.5 * float(signals.get("_atr", entry * 0.05)), 4)
    stop_loss  = max(stop_loss, entry * 0.90)  # ไม่เกิน 10%
    size       = calculate_position_size(capital, 0.01, entry, stop_loss)
    risk_pct   = round((entry - stop_loss) / entry * 100, 2)

    return {
        "score":         score,
        "breakdown":     score_data["breakdown"],
        "decision":      decision,
        "reasons":       reasons,
        "entry":         entry,
        "stop_loss":     stop_loss,
        "risk_pct":      risk_pct,
        "position_size": size,
        "cost":          round(size * entry, 2),
        "rsi":           signals.get("_rsi"),
        "adx":           signals.get("_adx"),
    }
