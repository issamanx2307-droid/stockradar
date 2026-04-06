"""
Views — News & Sentiment API
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated


@api_view(["GET"])
@permission_classes([AllowAny])
def news_list(request):
    """
    GET /api/news/
    Params: symbol, source, sentiment, days (default 7), limit (default 50)
    """
    from radar.models import NewsItem

    from django.db.models import Q
    p     = request.query_params
    days  = int(p.get("days", 7))
    limit = min(int(p.get("limit", 50)), 200)
    since = timezone.now() - timedelta(days=days)

    qs = NewsItem.objects.filter(
        Q(published_at__gte=since) | Q(published_at__isnull=True)
    ).order_by("-id")

    if p.get("symbol"):
        qs = qs.filter(symbols__symbol=p["symbol"].upper())
    if p.get("source"):
        qs = qs.filter(source=p["source"].upper())
    if p.get("sentiment"):
        qs = qs.filter(sentiment=p["sentiment"].upper())

    qs = qs.prefetch_related("symbols")[:limit]

    results = []
    for n in qs:
        results.append({
            "id":              n.id,
            "title":           n.title,
            "summary":         n.summary[:200] if n.summary else "",
            "url":             n.url,
            "source":          n.source,
            "published_at":    n.published_at.isoformat(),
            "sentiment":       n.sentiment,
            "sentiment_score": n.sentiment_score,
            "symbols":         [s.symbol for s in n.symbols.all()],
        })

    # Sentiment Summary
    from django.db.models import Count, Avg
    summary = NewsItem.objects.filter(published_at__gte=since).aggregate(
        total=Count("id"),
        bullish=Count("id", filter=models.Q(sentiment="BULLISH")),
        bearish=Count("id", filter=models.Q(sentiment="BEARISH")),
        neutral=Count("id", filter=models.Q(sentiment="NEUTRAL")),
        avg_score=Avg("sentiment_score"),
    )

    return Response({
        "summary": summary,
        "results": results,
        "count":   len(results),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def news_fetch(request):
    """POST /api/news/fetch/ — ดึงข่าวใหม่จาก RSS feeds ทันที (ต้อง login)"""
    if not request.user.is_staff:
        return Response({"error": "Staff only"}, status=403)
    try:
        from radar.news_fetcher import fetch_and_save_news
        stats = fetch_and_save_news(max_per_feed=30)
        return Response({"status": "สำเร็จ", **stats})
    except Exception as e:
        return Response({"status": "ล้มเหลว", "error": str(e)}, status=500)


@api_view(["GET"])
def news_sentiment_summary(request):
    """
    GET /api/news/sentiment/
    ภาพรวม sentiment ตลาดรายวัน + per-symbol
    """
    from radar.models import NewsItem, Symbol
    from django.db.models import Count, Avg, Q

    days = int(request.query_params.get("days", 7))
    since = timezone.now() - timedelta(days=days)

    # Overall market sentiment
    overall = NewsItem.objects.filter(published_at__gte=since).aggregate(
        total=Count("id"),
        bullish=Count("id", filter=Q(sentiment="BULLISH")),
        bearish=Count("id", filter=Q(sentiment="BEARISH")),
        neutral=Count("id", filter=Q(sentiment="NEUTRAL")),
        avg_score=Avg("sentiment_score"),
    )

    # Sentiment ต่อ source
    by_source = list(
        NewsItem.objects.filter(published_at__gte=since)
        .values("source")
        .annotate(
            count=Count("id"),
            avg_score=Avg("sentiment_score"),
            bullish=Count("id", filter=Q(sentiment="BULLISH")),
            bearish=Count("id", filter=Q(sentiment="BEARISH")),
        )
        .order_by("-count")
    )

    # Top bullish/bearish symbols from news
    top_bullish = list(
        Symbol.objects.filter(
            news__sentiment="BULLISH",
            news__published_at__gte=since
        ).annotate(news_count=Count("news"))
        .order_by("-news_count")
        .values("symbol", "name", "news_count")[:10]
    )
    top_bearish = list(
        Symbol.objects.filter(
            news__sentiment="BEARISH",
            news__published_at__gte=since
        ).annotate(news_count=Count("news"))
        .order_by("-news_count")
        .values("symbol", "name", "news_count")[:10]
    )

    return Response({
        "overall":     overall,
        "by_source":   by_source,
        "top_bullish": top_bullish,
        "top_bearish": top_bearish,
    })
