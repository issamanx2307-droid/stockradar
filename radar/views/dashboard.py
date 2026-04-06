"""
Views — Dashboard + User Profile
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Symbol, Signal
from ..serializers import SignalSerializer, UserSerializer


# ─── Profile & User ───────────────────────────────────────────────────────────

@api_view(["GET", "PUT"])
def user_profile(request):
    """
    ดูข้อมูลโปรไฟล์และแก้ไขการตั้งค่า (Token แจ้งเตือน)
    """
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    profile = request.user.profile

    if request.method == "GET":
        return Response(UserSerializer(request.user).data)

    elif request.method == "PUT":
        # อนุญาตให้แก้ไขเฉพาะ Line/Telegram token
        profile.line_notify_token = request.data.get("line_notify_token", profile.line_notify_token)
        profile.telegram_chat_id = request.data.get("telegram_chat_id", profile.telegram_chat_id)
        profile.save()
        return Response(UserSerializer(request.user).data)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@api_view(["GET"])
def dashboard_summary(request):
    week_ago = timezone.now() - timedelta(days=7)

    base = Signal.objects.select_related("symbol").filter(created_at__gte=week_ago)

    # แยกตาม category
    buy_signals  = (base.filter(direction="LONG",
                                signal_type__in=["BUY","STRONG_BUY","GOLDEN_CROSS","EMA_ALIGNMENT","EMA_PULLBACK","OVERSOLD"])
                        .order_by("-score")[:50])
    sell_signals = (base.filter(direction="SHORT",
                                signal_type__in=["SELL","STRONG_SELL","DEATH_CROSS","BREAKDOWN","OVERBOUGHT"])
                        .order_by("-score")[:50])
    breakout_signals = (base.filter(signal_type="BREAKOUT")
                            .order_by("-score")[:50])
    watch_signals    = (base.filter(signal_type__in=["WATCH","ALERT"])
                            .order_by("-score")[:50])

    latest_signals = (Signal.objects.select_related("symbol")
                      .order_by("-created_at", "-score")[:20])
    top_bullish    = (base.filter(direction="LONG").order_by("-score")[:10])

    stats = {
        "total_symbols":  Symbol.objects.count(),
        "total_signals":  Signal.objects.count(),
        "buy_signals":    buy_signals.count(),
        "sell_signals":   sell_signals.count(),
        "breakout_count": breakout_signals.count(),
        "watch_count":    watch_signals.count(),
        "strong_signals": Signal.objects.filter(score__gte=80).count(),
    }

    return Response({
        "stats":            stats,
        "latest_signals":   SignalSerializer(latest_signals,    many=True).data,
        "top_bullish":      SignalSerializer(top_bullish,       many=True).data,
        "buy_signals":      SignalSerializer(buy_signals,       many=True).data,
        "sell_signals":     SignalSerializer(sell_signals,      many=True).data,
        "breakout_signals": SignalSerializer(breakout_signals,  many=True).data,
        "watch_signals":    SignalSerializer(watch_signals,     many=True).data,
    })
