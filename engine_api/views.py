"""
engine_api/views.py
REST API endpoints สำหรับ Engine ใหม่
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rest_framework.decorators import api_view
from rest_framework.response import Response


# ─── GET /engine/scan/ ──────────────────────────────────────────────────────
@api_view(["GET"])
def scan_stocks(request):
    """
    GET /engine/scan/ — ดึง top signals จาก DB (เร็ว ไม่ต้อง scan real-time)
    Params: exchange, top, min_score
    """
    from radar.models import Signal, Symbol
    from django.utils import timezone
    from datetime import timedelta

    exchange  = request.query_params.get("exchange")
    top_n     = int(request.query_params.get("top", 20))
    min_score = float(request.query_params.get("min_score", 0))
    capital   = float(request.query_params.get("capital", 100_000))
    days      = int(request.query_params.get("days", 7))

    since = timezone.now() - timedelta(days=days)
    qs = (Signal.objects
          .select_related("symbol")
          .filter(direction="LONG", created_at__gte=since, score__gte=min_score)
          .order_by("-score", "-created_at"))

    if exchange:
        qs = qs.filter(symbol__exchange=exchange.upper())

    qs = qs[:top_n]

    out = []
    for s in qs:
        from decision_engine.decision import calculate_position_size
        entry     = float(s.price)
        stop_loss = float(s.stop_loss) if s.stop_loss else entry * 0.95
        size      = calculate_position_size(capital, 0.01, entry, stop_loss)
        out.append({
            "symbol":    s.symbol.symbol,
            "score":     float(s.score),
            "breakdown": {},
            "decision":  s.signal_type,
            "reasons":   [s.get_signal_type_display()],
            "entry":     entry,
            "stop_loss": stop_loss,
            "risk_pct":  float(s.risk_pct) if s.risk_pct else round((entry-stop_loss)/entry*100,2),
            "size":      size,
            "rsi":       float(s.atr_at_signal) if s.atr_at_signal else None,
            "adx":       float(s.adx_at_signal) if s.adx_at_signal else None,
        })

    return Response({"count": len(out), "results": out})


# ─── GET /engine/analyze/<symbol>/ ──────────────────────────────────────────
@api_view(["GET"])
def analyze_stock(request, symbol: str):
    """
    วิเคราะห์หุ้นเดียว คืน full analysis พร้อม reasons
    """
    from engine_api.services.stock_service import analyze

    capital = float(request.query_params.get("capital", 100_000))
    days    = int(request.query_params.get("days", 365))

    result = analyze(symbol.upper(), capital=capital, days=days)

    if result.get("error"):
        return Response(result, status=404)

    return Response({
        "symbol":        result["symbol"],
        "decision":      result["decision"],
        "reasons":       result["reasons"],
        "score":         result["score"]["total_score"],
        "breakdown":     result["score"]["breakdown"],
        "entry":         result["entry"],
        "stop_loss":     result["stop_loss"],
        "risk_pct":      result["risk_pct"],
        "position_size": result["position_size"],
        "cost":          result["cost"],
        "rsi":           result.get("rsi"),
        "adx":           result.get("adx"),
    })


# ─── POST /engine/backtest/ ─────────────────────────────────────────────────
@api_view(["POST"])
def run_backtest(request):
    """
    Backtest หุ้นเดียว
    Body: { symbol, capital, stop_loss_pct, take_profit_pct }
    """
    from data_pipeline.storage import load_data
    from backtesting_engine.report import run_backtest as _run, calculate_metrics, generate_report

    symbol        = request.data.get("symbol", "").upper()
    capital       = float(request.data.get("capital", 100_000))
    sl_pct        = float(request.data.get("stop_loss_pct", 5.0))
    tp_pct        = float(request.data.get("take_profit_pct", 10.0))
    days          = int(request.data.get("days", 730))

    if not symbol:
        return Response({"error": "กรุณาระบุ symbol"}, status=400)

    df = load_data(symbol, days=days)
    if df is None or df.empty:
        return Response({"error": f"ไม่มีข้อมูลราคาสำหรับ {symbol}"}, status=404)

    equity  = _run(df, capital, sl_pct, tp_pct)
    metrics = calculate_metrics(equity)
    report  = generate_report(metrics)

    return Response({
        "symbol":       symbol,
        "equity_curve": equity[-50:],   # 50 จุดล่าสุด
        "metrics":      metrics,
        "report":       report,
    })


# ─── POST /engine/portfolio/run/ ────────────────────────────────────────────
@api_view(["POST"])
def run_portfolio(request):
    """
    วิเคราะห์ทุกหุ้นแล้วสร้าง portfolio allocation
    Body: { capital, exchange, min_score }
    """
    from engine_api.services.stock_service import scan_top
    from portfolio_engine.portfolio_manager import PortfolioManager, run_portfolio_system

    capital   = float(request.data.get("capital", 100_000))
    exchange  = request.data.get("exchange")
    min_score = float(request.data.get("min_score", 60))

    analysis = scan_top(exchange=exchange, top_n=50,
                        min_score=min_score, capital=capital)

    # แปล format ให้ run_portfolio_system ใช้ได้
    flat = [{
        "symbol":    r["symbol"],
        "score":     r["score"]["total_score"],
        "decision":  r["decision"],
        "entry":     r["entry"],
        "stop_loss": r["stop_loss"],
    } for r in analysis]

    portfolio = PortfolioManager(capital)
    decisions = run_portfolio_system(flat, portfolio, min_score=min_score)
    summary   = portfolio.summary({d["symbol"]: d["entry"] for d in decisions})

    return Response({
        "summary":   summary,
        "decisions": decisions,
    })
