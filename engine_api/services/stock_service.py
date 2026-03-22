"""
engine_api/services/stock_service.py
Service layer — ประสาน pipeline ทั้งหมด พร้อม Django cache
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from data_pipeline.storage import load_data
from scanner_engine.scanner import scan_stock
from scoring_engine.scoring import calculate_score, build_reasons
from decision_engine.decision import make_decision, calculate_position_size

CACHE_TTL = 60  # วินาที


def _get_cache():
    try:
        from django.core.cache import cache
        return cache
    except Exception:
        return None


def analyze(symbol: str, capital: float = 100_000, days: int = 365) -> dict:
    """
    Pipeline เต็ม: load → scan → score → decide
    Cache 60 วินาทีด้วย Django cache (Redis)
    """
    cache = _get_cache()
    cache_key = f"engine:analyze:{symbol}"

    if cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    df = load_data(symbol, days=days)
    if df is None or df.empty or len(df) < 30:
        return {"error": f"ไม่มีข้อมูลราคาสำหรับ {symbol}"}

    signals    = scan_stock(df)
    score_data = calculate_score(signals)
    score      = score_data["total_score"]
    decision   = make_decision(score)
    reasons    = build_reasons(signals, score_data)

    entry     = float(df["close"].iloc[-1])
    atr_val   = float(signals.get("_atr", entry * 0.05))
    stop_loss = max(round(entry - 1.5 * atr_val, 4), entry * 0.90)
    size      = calculate_position_size(capital, 0.01, entry, stop_loss)
    risk_pct  = round((entry - stop_loss) / entry * 100, 2)

    result = {
        "symbol":        symbol,
        "decision":      decision,
        "reasons":       reasons,
        "score":         score_data,
        "entry":         entry,
        "stop_loss":     stop_loss,
        "risk_pct":      risk_pct,
        "position_size": size,
        "cost":          round(size * entry, 2),
        "rsi":           signals.get("_rsi"),
        "adx":           signals.get("_adx"),
    }

    if cache:
        cache.set(cache_key, result, timeout=CACHE_TTL)

    return result


def scan_top(
    exchange: str = None,
    top_n: int = 20,
    min_score: float = 0,
    capital: float = 100_000,
) -> list[dict]:
    """
    Scan ทุกหุ้น — ใช้ข้อมูลจาก DB โดยตรง (เร็ว)
    """
    import pandas as pd
    from radar.models import Symbol, PriceDaily, Indicator

    try:
        qs = Symbol.objects.all()
        if exchange:
            qs = qs.filter(exchange=exchange.upper())
        symbols = list(qs.values("id", "symbol", "name", "exchange", "sector"))
    except Exception:
        return []

    if not symbols:
        return []

    results = []
    for sym in symbols:
        try:
            result = analyze(sym["symbol"], capital=capital, days=365)
            if not result or result.get("error"):
                continue
            score = result.get("score", {})
            total = score.get("total_score", 0) if isinstance(score, dict) else score
            if total >= min_score:
                results.append(result)
        except Exception:
            continue

    results.sort(key=lambda x: (
        x.get("score", {}).get("total_score", 0) if isinstance(x.get("score"), dict)
        else x.get("score", 0)
    ), reverse=True)

    return results[:top_n]


def _analyze_worker(symbol: str, capital: float = 100_000) -> dict:
    """Worker function สำหรับ multiprocessing"""
    try:
        result = analyze(symbol, capital=capital)
        return result
    except Exception:
        return {}
