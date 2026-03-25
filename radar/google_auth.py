"""
google_auth.py — รับ Google id_token จาก frontend
ตรวจสอบกับ Google → สร้าง/ดึง User → คืน Token
"""
import logging
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


def _verify_google_token(id_token: str) -> dict | None:
    """ตรวจสอบ id_token กับ Google tokeninfo endpoint"""
    import requests
    try:
        r = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error("Google token verify error: %s", e)
    return None


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    """
    POST /api/auth/google/
    Body: { "id_token": "<google id_token>" }
    คืน: { token, user: {id, username, email, tier, plan} }
    """
    id_token = request.data.get("id_token", "").strip()
    if not id_token:
        return Response({"error": "กรุณาส่ง id_token"}, status=400)

    # ตรวจสอบกับ Google
    info = _verify_google_token(id_token)
    if not info or "email" not in info:
        return Response({"error": "id_token ไม่ถูกต้องหรือหมดอายุ"}, status=401)

    email    = info["email"]
    name     = info.get("name", "")
    picture  = info.get("picture", "")
    google_id= info.get("sub", "")

    # หรือสร้าง user
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email.split("@")[0][:30],
            "first_name": name.split(" ")[0] if name else "",
            "last_name":  " ".join(name.split(" ")[1:]) if " " in name else "",
        }
    )

    # ถ้า username ซ้ำ ให้ใส่ suffix
    if created:
        base_username = email.split("@")[0][:25]
        username = base_username
        counter  = 1
        while User.objects.filter(username=username).exclude(pk=user.pk).exists():
            username = f"{base_username}{counter}"
            counter += 1
        if username != user.username:
            user.username = username
            user.save(update_fields=["username"])

    # Profile tier: Free สำหรับ user ใหม่
    try:
        profile = user.profile
    except Exception:
        from radar.models import Profile
        profile = Profile.objects.create(user=user, tier="FREE")

    # บันทึกข้อมูล Google ลง Profile เสมอ (อัปเดต picture ถ้า login ซ้ำ)
    update_fields = []
    if google_id and profile.google_id != google_id:
        profile.google_id = google_id
        update_fields.append("google_id")
    if picture and profile.picture_url != picture:
        profile.picture_url = picture
        update_fields.append("picture_url")
    if not profile.login_via_google:
        profile.login_via_google = True
        update_fields.append("login_via_google")
    if update_fields:
        update_fields.append("updated_at")
        profile.save(update_fields=update_fields)

    # สร้าง/ดึง Token
    token, _ = Token.objects.get_or_create(user=user)

    # ดึงข้อมูล plan
    from radar.subscription import get_user_plan
    plan = get_user_plan(user)

    logger.info("Google login: %s (new=%s tier=%s google_id=%s)", email, created, profile.tier, google_id)

    return Response({
        "token":   token.key,
        "created": created,
        "user": {
            "id":         user.id,
            "username":   user.username,
            "email":      user.email,
            "first_name": user.first_name,
            "picture":    picture,
            "tier":       profile.tier.lower(),
            "plan":       plan,
        }
    })


@api_view(["GET"])
def me(request):
    """GET /api/auth/me/ — ข้อมูล user ปัจจุบัน"""
    if not request.user.is_authenticated:
        return Response({"authenticated": False})

    from radar.subscription import get_user_plan
    plan = get_user_plan(request.user)

    try:
        tier = request.user.profile.tier.lower()
    except Exception:
        tier = "free"

    # expires
    expires_at = None
    try:
        sub = request.user.profile.subscriptions.filter(
            is_active=True).order_by("-end_date").first()
        if sub:
            expires_at = sub.end_date.isoformat()
    except Exception:
        pass

    return Response({
        "authenticated": True,
        "id":         request.user.id,
        "username":   request.user.username,
        "email":      request.user.email,
        "first_name": request.user.first_name,
        "tier":       tier,
        "plan":       plan,
        "expires_at": expires_at,
    })


@api_view(["POST"])
def logout_api(request):
    """POST /api/auth/logout/ — ลบ Token"""
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({"message": "Logged out"})
