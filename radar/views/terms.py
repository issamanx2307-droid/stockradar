"""
Views — Terms / Business Profile / Position Analyze
"""

import re

from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.cache import cache

from ..models import (
    Symbol,
    BusinessProfile,
    StockTerm,
)
from ..serializers import (
    BusinessProfileSerializer,
    StockTermSerializer,
    PositionAnalyzeRequestSerializer,
)


# ─── Business Profile ─────────────────────────────────────────────────────────

@api_view(["GET"])
def business_profile_api(request):
    """ดึงข้อมูลธุรกิจสำหรับหน้าติดต่อเรา (สาธารณะ)"""
    profile = BusinessProfile.objects.first()
    if not profile:
        return Response({"error": "ไม่พบข้อมูลโพรไฟล์ธุรกิจ"}, status=404)
    return Response(BusinessProfileSerializer(profile).data)


def _normalize_term(value: str) -> str:
    return (value or "").strip().upper()


@api_view(["GET"])
def term_lookup(request):
    q = _normalize_term(request.query_params.get("q", ""))
    if not q:
        return Response({"error": "กรุณาระบุ q"}, status=400)

    cache_key = f"term:{q}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    obj = StockTerm.objects.filter(term=q).first()
    if not obj:
        return Response({"error": "ไม่พบคำศัพท์"}, status=404)

    data = StockTermSerializer(obj).data
    cache.set(cache_key, data, 60 * 60 * 24 * 30)
    return Response(data)


@api_view(["GET"])
def term_search(request):
    q_raw = (request.query_params.get("q", "") or "").strip()
    if not q_raw:
        return Response({"results": []})

    q = q_raw.upper()
    qs = (StockTerm.objects
          .filter(models.Q(term__icontains=q_raw) | models.Q(short_definition__icontains=q_raw))
          .order_by("-is_featured", "-priority", "term")[:20])

    return Response({"results": StockTermSerializer(qs, many=True).data})


@api_view(["GET"])
def featured_terms(request):
    qs = StockTerm.objects.filter(is_featured=True).order_by("-priority", "term")[:50]
    return Response({"results": StockTermSerializer(qs, many=True).data})


_TERM_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\_/]{1,20}")


def _extract_candidate_terms(text: str) -> list[str]:
    tokens = [t.upper() for t in _TERM_TOKEN_RE.findall(text or "")]
    seen = set()
    out = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:10]


@api_view(["POST"])
def position_analyze_api(request):
    serializer = PositionAnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    symbol_code = (serializer.validated_data["symbol"] or "").strip().upper()
    buy_price = serializer.validated_data["buy_price"]

    sym = Symbol.objects.filter(symbol=symbol_code).first()
    if not sym:
        return Response({"error": "ไม่พบสัญลักษณ์หุ้น"}, status=404)

    from radar.services.position_analysis import analyze_position

    try:
        result = analyze_position(sym, buy_price=buy_price, user=request.user)
        return Response(result)
    except ValueError as e:
        if str(e) == "NO_MARKET_DATA":
            return Response({"error": "ยังไม่มีข้อมูลราคาตลาดสำหรับหุ้นนี้"}, status=404)
        return Response({"error": "วิเคราะห์ไม่สำเร็จ"}, status=400)
    except Exception:
        return Response({"error": "ระบบขัดข้องชั่วคราว"}, status=500)
