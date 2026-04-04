"""
Django Admin สำหรับระบบ Radar หุ้น (ภาษาไทย)
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from .models import Profile, BusinessProfile, StockTerm, SubscriptionPlan, Subscription, ChatMessage, SiteSetting

# ---------------------------------------------------------------------------
# Business Profile
# ---------------------------------------------------------------------------

@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "email", "phone", "updated_at")
    
    fieldsets = (
        ("ข้อมูลธุรกิจ", {
            "fields": ("company_name", "description"),
        }),
        ("ช่องทางการติดต่อ", {
            "fields": ("address", "phone", "email", "line_id", "facebook_url", "website_url"),
        }),
        ("ข้อมูลอื่นๆ", {
            "fields": ("footer_text",),
        }),
    )

    def has_add_permission(self, request):
        # จำกัดให้มีได้เพียง 1 record
        if BusinessProfile.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        # ไม่อนุญาตให้ลบ
        return False

# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "max_strategies", "created_at")
    list_filter = ("tier", "created_at")
    search_fields = ("user__username", "user__email")
    ordering = ("-created_at",)

    fieldsets = (
        ("ข้อมูลผู้ใช้", {
            "fields": ("user", "tier", "max_strategies"),
        }),
        ("การแจ้งเตือน", {
            "fields": ("line_notify_token", "telegram_chat_id"),
        }),
    )


# ---------------------------------------------------------------------------
# Subscription System
# ---------------------------------------------------------------------------

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display  = ("name", "tier", "price_thb", "duration_days", "is_active", "created_at")
    list_filter   = ("tier", "is_active")
    list_editable = ("is_active", "price_thb")
    ordering      = ("price_thb",)

    fieldsets = (
        ("ข้อมูลแผน", {
            "fields": ("name", "tier", "price_thb", "duration_days", "is_active"),
        }),
        ("รายละเอียด", {
            "fields": ("description", "features"),
            "classes": ("collapse",),
        }),
    )


class SubscriptionInline(admin.TabularInline):
    model  = Subscription
    extra  = 1
    fields = ("plan", "status", "start_date", "end_date", "is_active", "payment_ref", "note")
    readonly_fields = ("created_at",)
    show_change_link = True
    ordering = ("-start_date",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ("user_link", "plan", "tier_badge", "status_badge",
                     "start_date", "end_date", "days_left", "payment_ref", "created_at")
    list_filter   = ("status", "plan__tier", "plan", "start_date")
    search_fields = ("profile__user__username", "profile__user__email", "payment_ref")
    ordering      = ("-start_date",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields   = ("profile", "created_by")
    date_hierarchy  = "start_date"
    save_on_top     = True

    fieldsets = (
        ("ข้อมูลสมาชิก", {
            "fields": ("profile", "plan", "status", "is_active"),
        }),
        ("ช่วงเวลา", {
            "fields": ("start_date", "end_date"),
        }),
        ("การชำระเงิน", {
            "fields": ("payment_ref", "note", "created_by"),
        }),
        ("ระบบ", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["activate_subscriptions", "expire_subscriptions"]

    def user_link(self, obj):
        url = f"/admin/auth/user/{obj.profile.user.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.profile.user.username)
    user_link.short_description = "ผู้ใช้"
    user_link.admin_order_field = "profile__user__username"

    def tier_badge(self, obj):
        colors = {"FREE": "#6b7280", "PRO": "#3b82f6", "PREMIUM": "#8b5cf6"}
        color  = colors.get(obj.plan.tier, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.plan.tier
        )
    tier_badge.short_description = "Tier"

    def status_badge(self, obj):
        colors = {"ACTIVE": "#22c55e", "EXPIRED": "#ef4444", "CANCELLED": "#6b7280", "TRIAL": "#f59e0b"}
        color  = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "สถานะ"

    def days_left(self, obj):
        from datetime import date
        remaining = (obj.end_date - date.today()).days
        if remaining < 0:
            return format_html('<span style="color:#ef4444">หมดอายุ {}</span>', f"{abs(remaining)} วันที่แล้ว")
        elif remaining <= 7:
            return format_html('<span style="color:#f59e0b">⚠️ {}</span>', f"{remaining} วัน")
        return format_html('<span style="color:#22c55e">{}</span>', f"{remaining} วัน")
    days_left.short_description = "เหลือ"

    def activate_subscriptions(self, request, queryset):
        for sub in queryset:
            sub.is_active = True
            sub.status    = "ACTIVE"
            sub.save()
        self.message_user(request, f"Activated {queryset.count()} subscriptions")
    activate_subscriptions.short_description = "✅ Activate ที่เลือก"

    def expire_subscriptions(self, request, queryset):
        for sub in queryset:
            sub.is_active = False
            sub.status    = "EXPIRED"
            sub.save()
        self.message_user(request, f"Expired {queryset.count()} subscriptions")
    expire_subscriptions.short_description = "❌ Expire ที่เลือก"


# Profile admin อัปเกรด (เพิ่ม inline subscriptions + Google info)
admin.site.unregister(Profile)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "tier_badge", "google_badge", "sub_status", "sub_end_date",
                     "portfolio_badge", "max_strategies", "created_at")
    list_filter   = ("tier", "login_via_google", "can_use_portfolio", "created_at")
    search_fields = ("user__username", "user__email", "google_id")
    ordering      = ("-created_at",)
    inlines       = [SubscriptionInline]
    readonly_fields = ("tier", "google_id", "login_via_google", "google_picture_preview")

    fieldsets = (
        ("ข้อมูลผู้ใช้", {
            "fields": ("user", "tier", "max_strategies"),
        }),
        ("สิทธิ์การใช้งาน", {
            "fields": ("can_use_portfolio",),
        }),
        ("บัญชี Google", {
            "fields": ("login_via_google", "google_id", "picture_url", "google_picture_preview"),
            "classes": ("collapse",),
        }),
        ("การแจ้งเตือน", {
            "fields": ("line_notify_token", "telegram_chat_id"),
        }),
    )

    def tier_badge(self, obj):
        colors = {"FREE":"#6b7280","PRO":"#3b82f6","PREMIUM":"#8b5cf6"}
        color  = colors.get(obj.tier, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:4px;">{}</span>',
            color, obj.tier
        )
    tier_badge.short_description = "Tier"

    def google_badge(self, obj):
        if obj.login_via_google:
            if obj.picture_url:
                return format_html(
                    '<span title="{}" style="display:inline-flex;align-items:center;gap:6px;">'
                    '<img src="{}" width="24" height="24" style="border-radius:50%;vertical-align:middle;"/>'
                    '<span style="color:#4285F4;font-weight:bold;">● Google</span></span>',
                    obj.google_id or "", obj.picture_url
                )
            return format_html('<span style="color:#4285F4;font-weight:bold;">● Google</span>')
        return format_html('<span style="color:#9ca3af;">—</span>')
    google_badge.short_description = "Google"

    def google_picture_preview(self, obj):
        if obj.picture_url:
            return format_html(
                '<img src="{}" width="64" height="64" style="border-radius:50%;border:2px solid #4285F4;" />',
                obj.picture_url
            )
        return "—"
    google_picture_preview.short_description = "รูปโปรไฟล์"

    def sub_status(self, obj):
        sub = obj.active_subscription
        if sub:
            return format_html('<span style="color:#22c55e">✅ {}</span>', sub.plan.name)
        return format_html('<span style="color:#6b7280">—</span>')
    sub_status.short_description = "Subscription"

    def sub_end_date(self, obj):
        sub = obj.active_subscription
        return sub.end_date if sub else "—"
    sub_end_date.short_description = "หมดอายุ"

    def portfolio_badge(self, obj):
        if obj.can_use_portfolio:
            return format_html('<span style="color:#22c55e;font-weight:bold;">✅ เปิด</span>')
        return format_html('<span style="color:#9ca3af;">—</span>')
    portfolio_badge.short_description = "Portfolio"


# ---------------------------------------------------------------------------
# Chat Message (กล่องข้อความ User ↔ Admin)
# ---------------------------------------------------------------------------

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    หน้า list → แสดงเป็น user inbox (1 แถว / 1 user)
    หน้า detail / filter by sender → แสดงทุกข้อความของ user นั้น
    """
    list_display   = ("user_inbox", "last_msg_preview", "unread_count_badge", "last_active", "action_btns")
    list_filter    = ("is_read",)
    search_fields  = ("sender__username", "sender__email", "body")
    ordering       = ("-created_at",)
    readonly_fields = ("sender", "receiver", "body", "is_read", "created_at")

    fieldsets = (
        ("ข้อความ", {"fields": ("sender", "receiver", "body", "is_read", "created_at")}),
    )
    actions = ["mark_read"]

    def get_queryset(self, request):
        from django.db.models import Max
        qs = super().get_queryset(request)
        # กรองเฉพาะข้อความของ user ธรรมดา
        qs = qs.filter(sender__is_staff=False, sender__is_superuser=False)
        # ถ้ามี filter sender (admin กดดู inbox ของ user คนใดคนหนึ่ง) → แสดงทั้งหมด
        if "sender__id__exact" in request.GET or "sender__username" in request.GET:
            return qs
        # ปกติ → แสดงเฉพาะข้อความล่าสุดต่อ user (inbox view)
        latest_ids = (
            qs.values("sender")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )
        return qs.filter(id__in=latest_ids)

    def user_inbox(self, obj):
        url = f"/mantapa/radar/chatmessage/?sender__id__exact={obj.sender.id}"
        return format_html(
            '👤 <a href="{}" style="font-weight:bold;color:#1565c0;">{}</a><br>'
            '<small style="color:#6b7280;">{}</small>',
            url, obj.sender.username, obj.sender.email,
        )
    user_inbox.short_description = "ผู้ใช้"
    user_inbox.allow_tags = True

    def last_msg_preview(self, obj):
        text = (obj.body or "").strip()
        return text[:80] + ("…" if len(text) > 80 else "")
    last_msg_preview.short_description = "ข้อความล่าสุด"

    def unread_count_badge(self, obj):
        count = ChatMessage.objects.filter(
            sender=obj.sender, is_read=False,
            sender__is_staff=False, sender__is_superuser=False,
        ).count()
        if count:
            return format_html(
                '<span style="background:#ef4444;color:#fff;padding:2px 10px;'
                'border-radius:10px;font-weight:bold;">{} ใหม่</span>', count
            )
        return format_html('<span style="color:#6b7280;font-size:11px;">อ่านแล้ว</span>')
    unread_count_badge.short_description = "สถานะ"

    def last_active(self, obj):
        return obj.created_at
    last_active.short_description = "ล่าสุด"
    last_active.admin_order_field = "created_at"

    def action_btns(self, obj):
        view_url  = f"/mantapa/radar/chatmessage/?sender__id__exact={obj.sender.id}"
        reply_url = f"/mantapa/radar/chatmessage/add/?receiver={obj.sender.id}&sender={obj.receiver.id}"
        return format_html(
            '<a href="{}" style="background:#374151;color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;text-decoration:none;margin-right:4px;">📋 ดูทั้งหมด</a>'
            '<a href="{}" style="background:#1565c0;color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;text-decoration:none;">↩ ตอบ</a>',
            view_url, reply_url,
        )
    action_btns.short_description = ""

    def mark_read(self, request, queryset):
        from django.db.models import Q as _Q
        # mark read ทุกข้อความของ user เหล่านั้น
        sender_ids = queryset.values_list("sender_id", flat=True)
        updated = ChatMessage.objects.filter(sender_id__in=sender_ids).update(is_read=True)
        self.message_user(request, f"Mark read {updated} ข้อความ")
    mark_read.short_description = "✅ Mark อ่านแล้วทั้งหมด"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.sender = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("sender", "receiver", "body", "is_read", "created_at")
        return ("created_at",)

    add_fieldsets = (
        ("ตอบกลับ User", {"fields": ("receiver", "body")}),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return (
                ("ตอบกลับ User", {
                    "fields": ("receiver", "body"),
                }),
            )
        return self.fieldsets


# ---------------------------------------------------------------------------
# Site Setting (admin toggle: AI Chat on/off)
# ---------------------------------------------------------------------------

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display  = ("__str__", "ai_chat_enabled")
    fields        = ("ai_chat_enabled",)

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
