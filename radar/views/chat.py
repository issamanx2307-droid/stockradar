"""
Views — Chat System (Admin ↔ User) with AI Auto-Reply
"""

import logging as _log

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import ChatMessage

_logger = _log.getLogger(__name__)


def _get_admin_user():
    """คืน superuser คนแรก (ผู้ดูแลระบบ)"""
    from django.contrib.auth.models import User as AuthUser
    return AuthUser.objects.filter(is_superuser=True).order_by("id").first()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_send(request):
    """
    POST /api/chat/send/
    Body: { body: str, receiver_id?: int }
    """
    from django.contrib.auth.models import User as AuthUser
    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"error": "กรุณาพิมพ์ข้อความ"}, status=400)

    is_admin = request.user.is_staff or request.user.is_superuser

    if is_admin:
        receiver_id = request.data.get("receiver_id")
        if not receiver_id:
            return Response({"error": "ต้องระบุ receiver_id"}, status=400)
        try:
            receiver = AuthUser.objects.get(pk=receiver_id)
        except AuthUser.DoesNotExist:
            return Response({"error": "ไม่พบผู้ใช้"}, status=404)
    else:
        receiver = _get_admin_user()
        if not receiver:
            return Response({"error": "ไม่พบแอดมิน"}, status=503)

    msg = ChatMessage.objects.create(sender=request.user, receiver=receiver, body=body)

    # ── Auto-cleanup: ลบข้อความเก่าเกิน 3 วันของ user นี้ ─────────────────────
    if not is_admin:
        from django.utils import timezone as tz
        from datetime import timedelta
        from django.db.models import Q
        cutoff = tz.now() - timedelta(days=3)
        ChatMessage.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user),
            created_at__lt=cutoff,
        ).delete()

    # ── AI Auto-Reply (เฉพาะเมื่อ user ธรรมดาส่ง + AI เปิดอยู่) ──────────────
    if not is_admin:
        import threading
        threading.Thread(
            target=_try_ai_reply,
            args=(request.user, receiver, body),
            daemon=True,
        ).start()

    return Response({
        "id":             msg.id,
        "body":           msg.body,
        "sender_id":      msg.sender_id,
        "sender":         msg.sender.username,
        "is_admin_msg":   is_admin,
        "is_ai_response": False,
        "created_at":     msg.created_at.isoformat(),
    }, status=201)


def _try_ai_reply(user, admin_user, user_message: str):
    """
    เรียก Gemini 2.5 Flash (Google AI Studio) พร้อม Function Calling
    """
    from django.conf import settings
    from radar.models import SiteSetting

    setting = SiteSetting.get()
    if not setting.ai_chat_enabled:
        _logger.warning("AI reply skipped: ai_chat_enabled=False")
        return

    api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
    if not api_key:
        _logger.warning("AI reply skipped: GOOGLE_AI_API_KEY not set")
        return

    # Rate limit
    daily_limit = getattr(settings, "AI_CHAT_DAILY_LIMIT", 30)
    if daily_limit > 0:
        import datetime
        today = datetime.date.today()
        ai_today = ChatMessage.objects.filter(
            receiver=user, is_ai_response=True, created_at__date=today,
        ).count()
        _logger.info("AI daily usage: user=%s count=%d limit=%d", user.username, ai_today, daily_limit)
        if ai_today >= daily_limit:
            _logger.warning("AI reply skipped: daily limit reached (%d/%d) for user=%s", ai_today, daily_limit, user.username)
            return

    # ดึงประวัติสนทนา (10 ข้อความล่าสุด)
    from django.db.models import Q
    history_qs = ChatMessage.objects.filter(
        Q(sender=user, receiver=admin_user) |
        Q(sender=admin_user, receiver=user)
    ).order_by("-created_at")[:10]

    history = []
    for h in reversed(list(history_qs)):
        role = "user" if h.sender_id == user.id else "model"
        history.append({"role": role, "parts": [{"text": h.body}]})

    if not history or history[-1]["parts"][0]["text"] != user_message:
        history.append({"role": "user", "parts": [{"text": user_message}]})

    system_prompt = _build_system_prompt()

    try:
        from google import genai as google_genai
        from google.genai import types as genai_types
        from radar.ai_tools import get_tool_definitions, handle_tool_call

        client = google_genai.Client(api_key=api_key)
        tool_def = get_tool_definitions()
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[tool_def],
            temperature=0.7,
        )

        contents = list(history)
        MAX_ROUNDS = 3
        pending_order_info = None

        for round_idx in range(MAX_ROUNDS):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config,
                )
            except Exception as _e:
                if "429" in str(_e):
                    _logger.warning("Gemini 429 rate limit for user=%s", user.username)
                    ChatMessage.objects.create(
                        sender=admin_user, receiver=user,
                        body="⚠️ ระบบ AI ยุ่งอยู่ในขณะนี้ กรุณาลองส่งข้อความใหม่อีกครั้งใน 1 นาทีนะครับ",
                        is_ai_response=True,
                    )
                    return
                raise

            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                break

            function_calls = [
                part.function_call
                for part in (candidate.content.parts or [])
                if getattr(part, "function_call", None)
            ]

            if not function_calls:
                break

            tool_response_parts = []
            for fc in function_calls:
                _logger.info("AI tool call: %s(%s)", fc.name, dict(fc.args))
                result = handle_tool_call(fc.name, dict(fc.args), user)
                if fc.name == "propose_order" and result.get("__propose_order__"):
                    pending_order_info = {
                        "order_id":   result.get("order_id"),
                        "symbol":     result.get("symbol"),
                        "side":       result.get("side"),
                        "qty":        result.get("qty"),
                        "order_type": result.get("order_type"),
                        "limit_price": result.get("limit_price"),
                        "reasoning":  result.get("reasoning", ""),
                    }
                tool_response_parts.append(
                    genai_types.Part.from_function_response(
                        name=fc.name,
                        response={"result": result},
                    )
                )

            contents = list(contents) + [
                candidate.content,
                genai_types.Content(role="user", parts=tool_response_parts),
            ]

        ai_text = (response.text or "").strip()
        if ai_text:
            body = ai_text
            if pending_order_info:
                import json as _json
                body = ai_text + "\n|||ORDER_PROPOSAL|||" + _json.dumps(pending_order_info, ensure_ascii=False)

            ChatMessage.objects.create(
                sender=admin_user, receiver=user,
                body=body, is_ai_response=True,
            )

    except Exception as e:
        _logger.error("AI reply error: %s", e)
        try:
            ChatMessage.objects.create(
                sender=admin_user, receiver=user,
                body="⚠️ ระบบ AI เกิดข้อผิดพลาด กรุณาลองส่งข้อความใหม่อีกครั้งครับ",
                is_ai_response=True,
            )
        except Exception:
            _logger.error("Failed to send AI error message to user")
    finally:
        from django.db import connection as _db_conn
        _db_conn.close()


def _build_system_prompt():
    """สร้าง system prompt สำหรับ Gemini AI Chat"""
    return (
        "คุณคือ AI assistant ของ radarhoon.com ระบบสแกนและวิเคราะห์หุ้น\n"
        "คุณมี tools ให้ใช้เพื่อดึงข้อมูลจริงจากระบบ — ใช้ tools เสมอเมื่อ user ถามเรื่องหุ้น\n\n"
        "═══ กฎการถามจำนวนวัน (สำคัญมาก) ═══\n"
        "ก่อนเรียก get_stock_analysis ทุกครั้ง ต้องถามผู้ใช้ก่อนว่า:\n"
        "'ต้องการวิเคราะห์ข้อมูลย้อนหลังกี่วันครับ?\n"
        " • 60 วัน — มองระยะสั้น\n"
        " • 120 วัน — ระยะกลาง (แนะนำ)\n"
        " • 200 วัน — ระยะยาว'\n"
        "ยกเว้น: ถ้า user ระบุจำนวนวันมาในข้อความแล้ว ให้ใช้ค่านั้นเลย ไม่ต้องถามซ้ำ\n\n"
        "═══ กฎการตอบ ═══\n"
        "- ตอบเป็นภาษาไทย\n"
        "- แต่ละข้อมูลหรือหัวข้อต้องอยู่คนละบรรทัด ห้ามยัดข้อมูลในบรรทัดเดียว\n"
        "- ใช้ **ข้อความ** สำหรับหัวข้อสำคัญ และ ✅/❌ สำหรับ layer pass/fail\n"
        "- เว้นบรรทัดว่างระหว่างกลุ่มข้อมูล\n\n"
        "═══ กฎการอธิบาย Indicators (สำคัญมาก) ═══\n"
        "ข้อมูลที่ได้จาก tool มี 2 ส่วน:\n"
        "  indicators = ค่าดิบ (raw numbers)\n"
        "  derived    = ค่าที่คำนวณแล้วพร้อม interpretation (ใช้ส่วนนี้อธิบาย)\n\n"
        "ทุก indicator ต้องอธิบาย 3 อย่าง:\n"
        "  1. ค่าที่ได้ คืออะไร\n"
        "  2. เทียบกับเกณฑ์หรือค่าเฉลี่ย — ดีหรือไม่ดี ห่างกันแค่ไหน\n"
        "  3. ความหมายต่อหุ้นตัวนี้ตอนนี้\n\n"
        "═══ กฎเมื่อเกิด Error หรือข้อมูลไม่ครบ ═══\n"
        "- ถ้า data_available=False หรือมี error → บอกตรงๆ ว่าดึงข้อมูลไม่ได้ พร้อมสาเหตุ\n"
        "- ถ้า derived[indicator] เป็น None หรืออยู่ใน _null_fields → บอกว่า 'ไม่มีข้อมูล [indicator]'\n"
        "- ห้ามสร้างหรือเดาข้อมูลที่ไม่มีในระบบ\n\n"
        "═══ ข้อห้าม ═══\n"
        "- ห้ามแนะนำให้ซื้อหรือขายหุ้นอย่างชัดเจน\n"
        "- ไม่ใช่ที่ปรึกษาการเงิน ทุกการตัดสินใจเป็นความรับผิดชอบของผู้ใช้\n\n"
        "═══ Alpaca US Stock Trading ═══\n"
        "คุณมี tools สำหรับ US stock trading ผ่าน Alpaca Paper Trading:\n"
        "  get_alpaca_account → ดูยอดเงิน\n"
        "  get_alpaca_positions → ดู positions\n"
        "  get_us_stock_bars → ดึงราคา US\n"
        "  propose_order → เสนอ order รอ user confirm\n\n"
        "กฎการใช้ Alpaca tools:\n"
        "1. ก่อนเสนอ order ต้องเรียก get_us_stock_bars ก่อนเสมอ\n"
        "2. เสนอ order ได้ครั้งละ 1 order เท่านั้น\n"
        "3. propose_order เป็นแค่การเสนอ — ระบบจะแสดง confirm card ให้ user กดยืนยัน\n"
        "4. ห้าม execute order เองโดยไม่ผ่าน user confirm\n"
        "5. ขณะนี้เป็น Paper Trading — ไม่ใช้เงินจริง\n"
        "6. เมื่อเสนอ order ต้องอธิบาย reasoning ให้ชัดเจน\n"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_messages(request):
    """GET /api/chat/messages/?user_id=<id>"""
    from django.contrib.auth.models import User as AuthUser
    from django.db.models import Q

    is_admin = request.user.is_staff or request.user.is_superuser

    if is_admin:
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "ต้องระบุ user_id"}, status=400)
        try:
            other_user = AuthUser.objects.get(pk=user_id)
        except AuthUser.DoesNotExist:
            return Response({"error": "ไม่พบผู้ใช้"}, status=404)
    else:
        other_user = _get_admin_user()
        if not other_user:
            return Response({"messages": []})

    msgs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by("created_at")

    msgs.filter(receiver=request.user, is_read=False).update(is_read=True)

    data = [
        {
            "id":             m.id,
            "body":           m.body,
            "sender_id":      m.sender_id,
            "sender":         m.sender.username,
            "is_mine":        m.sender_id == request.user.id,
            "is_admin_msg":   m.sender.is_staff or m.sender.is_superuser,
            "is_ai_response": getattr(m, "is_ai_response", False),
            "is_read":        m.is_read,
            "created_at":     m.created_at.isoformat(),
        }
        for m in msgs
    ]
    return Response({"messages": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_conversations(request):
    """GET /api/chat/conversations/ — Admin only"""
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({"error": "ไม่มีสิทธิ์"}, status=403)

    from django.contrib.auth.models import User as AuthUser
    from django.db.models import Q

    admin_ids = list(AuthUser.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True)
    ).values_list("id", flat=True))

    user_ids = set()
    user_ids.update(
        ChatMessage.objects.filter(receiver__in=admin_ids)
        .exclude(sender__in=admin_ids)
        .values_list("sender_id", flat=True)
    )
    user_ids.update(
        ChatMessage.objects.filter(sender__in=admin_ids)
        .exclude(receiver__in=admin_ids)
        .values_list("receiver_id", flat=True)
    )

    results = []
    for uid in user_ids:
        try:
            u = AuthUser.objects.get(pk=uid)
        except AuthUser.DoesNotExist:
            continue

        msgs = ChatMessage.objects.filter(
            Q(sender_id=uid, receiver__in=admin_ids) |
            Q(receiver_id=uid, sender__in=admin_ids)
        ).order_by("-created_at")

        last_msg = msgs.first()
        unread = msgs.filter(sender_id=uid, is_read=False).count()

        results.append({
            "user_id":    u.id,
            "username":   u.username,
            "email":      u.email,
            "first_name": u.first_name,
            "last_name":  u.last_name,
            "unread":     unread,
            "last_body":  last_msg.body if last_msg else "",
            "last_at":    last_msg.created_at.isoformat() if last_msg else None,
        })

    results.sort(key=lambda x: (-x["unread"], x["last_at"] or ""), reverse=False)
    return Response({"conversations": results})
