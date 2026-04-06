"""
Views — VI Screener & Multi-Layer Scanner
"""

from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


@api_view(["GET"])
@permission_classes([AllowAny])
def vi_screen_api(request):
    """GET /api/vi-screen/"""
    from ..models import FundamentalSnapshot
    from ..tasks import fetch_set_fundamentals

    total = FundamentalSnapshot.objects.count()
    if total == 0:
        try:
            fetch_set_fundamentals.delay()
        except Exception:
            import threading
            threading.Thread(target=fetch_set_fundamentals, daemon=True).start()

    qs = FundamentalSnapshot.objects.select_related("symbol").filter(vi_score__isnull=False)

    grade = request.query_params.get("grade", "")
    if grade in ("A", "B", "C", "D"):
        qs = qs.filter(vi_grade=grade)

    for param, field, op in [
        ("min_score", "vi_score__gte", None),
        ("max_pe", "pe_ratio__lte", "pe_ratio__gt"),
        ("max_pb", "pb_ratio__lte", "pb_ratio__gt"),
        ("min_roe", "roe__gte", None),
        ("min_div", "dividend_yield__gte", None),
    ]:
        val = request.query_params.get(param, "")
        if val:
            try:
                qs = qs.filter(**{field: float(val)})
                if op:
                    qs = qs.filter(**{op: 0})
            except ValueError:
                pass

    SORT_MAP = {
        "vi_score": "-vi_score", "pe_ratio": "pe_ratio", "pb_ratio": "pb_ratio",
        "roe": "-roe", "dividend_yield": "-dividend_yield",
    }
    sort_param = request.query_params.get("sort", "vi_score")
    qs = qs.order_by(SORT_MAP.get(sort_param, "-vi_score"))

    try:
        page_size = min(int(request.query_params.get("page_size", 50)), 200)
    except ValueError:
        page_size = 50
    qs = qs[:page_size]

    results = []
    for snap in qs:
        sym = snap.symbol
        row = {"symbol": sym.symbol, "name": sym.name, "exchange": sym.exchange,
               "sector": getattr(sym, "sector", None), "market_cap": snap.market_cap,
               "fetched_at": snap.fetched_at.isoformat() if snap.fetched_at else None}
        for f in ["vi_score","vi_grade","pe_ratio","pb_ratio","roe","roa","net_margin",
                   "revenue_growth","debt_to_equity","current_ratio","dividend_yield"]:
            v = getattr(snap, f)
            row[f] = float(v) if v is not None and f != "vi_grade" else v
        results.append(row)

    from django.db.models import Count
    grade_counts = dict(
        FundamentalSnapshot.objects.filter(vi_grade__isnull=False)
        .values("vi_grade").annotate(n=Count("id")).values_list("vi_grade", "n")
    )

    return Response({"count": total, "grade_counts": grade_counts,
                     "results": results, "fetching": total == 0})


@api_view(["GET"])
def multi_layer_scan(request):
    """GET /api/multi-layer/"""
    from radar.multilayer_engine import run_multilayer_scan

    p = request.query_params
    exchange = p.get("exchange", "")
    setup = p.get("setup", "")
    try: min_layers = max(1, min(4, int(p.get("min_layers", 2))))
    except ValueError: min_layers = 2
    try: days = max(60, min(365, int(p.get("days", 120))))
    except ValueError: days = 120
    try: page_size = max(1, min(300, int(p.get("page_size", 100))))
    except ValueError: page_size = 100

    cache_key = f"multilayer:{exchange}:{min_layers}:{setup}:{days}"
    cached = cache.get(cache_key)
    if cached and cached.get("count", 0) > 0:
        return Response(cached)

    results = run_multilayer_scan(
        exchange=exchange or None, min_layers=min_layers,
        setup_filter=setup or None, days=days, limit=page_size,
    )
    resp = {"count": len(results), "results": results}
    cache.set(cache_key, resp, 300)
    return Response(resp)
