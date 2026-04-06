"""
Views — Subscription Status & Plans
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def subscription_plans(request):
    """GET /api/subscription/plans/ — รายการแผนทั้งหมด"""
    from radar.subscription import PLANS
    return Response({"plans": PLANS})


@api_view(["GET"])
def subscription_status(request):
    """GET /api/subscription/status/ — สถานะ plan ของ user ปัจจุบัน"""
    from radar.subscription import get_user_plan, PLANS

    if not request.user.is_authenticated:
        plan = PLANS["free"]
        return Response({
            "authenticated": False,
            "plan": plan,
            "tier": "free",
            "expires_at": None,
        })

    plan = get_user_plan(request.user)
    tier = request.user.profile.tier.lower()

    # หา expiry date
    expires_at = None
    try:
        sub = request.user.profile.subscriptions.filter(
            is_active=True
        ).order_by("-end_date").first()
        if sub:
            expires_at = sub.end_date.isoformat()
    except Exception:
        pass

    return Response({
        "authenticated": True,
        "username":  request.user.username,
        "tier":      tier,
        "plan":      plan,
        "expires_at": expires_at,
    })
