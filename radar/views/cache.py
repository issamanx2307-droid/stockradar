"""
Views — Cache Management API
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def cache_stats(request):
    """GET /api/cache/stats/ — ดูสถานะ Redis cache"""
    try:
        from radar.indicator_cache import indicator_cache
        from radar.models import Symbol, Indicator

        stats = indicator_cache.stats()
        stats["total_symbols"] = Symbol.objects.count()
        stats["total_indicators"] = Indicator.objects.count()

        # ทดสอบ cache hit
        sym = Symbol.objects.first()
        if sym:
            cached = indicator_cache.get_latest_indicator(sym.id)
            stats["sample_symbol"] = sym.symbol
            stats["sample_cached"] = cached is not None

        return Response(stats)
    except Exception as e:
        return Response({"error": str(e), "available": False})


@api_view(["POST"])
def cache_warmup(request):
    """POST /api/cache/warmup/ — warm-up Redis cache"""
    try:
        from radar.indicator_cache import warm_up_cache
        exchange = request.data.get("exchange")
        result   = warm_up_cache(exchange)
        return Response({"status": "สำเร็จ", **result})
    except Exception as e:
        return Response({"status": "ล้มเหลว", "error": str(e)}, status=500)


@api_view(["POST"])
def cache_invalidate(request):
    """POST /api/cache/invalidate/ — ล้าง cache"""
    try:
        from radar.indicator_cache import indicator_cache
        exchange = request.data.get("exchange", "ALL")
        if exchange != "ALL":
            indicator_cache.invalidate_exchange(exchange)
        else:
            from django.core.cache import cache
            cache.clear()
        return Response({"status": "สำเร็จ", "cleared": exchange})
    except Exception as e:
        return Response({"status": "ล้มเหลว", "error": str(e)}, status=500)
