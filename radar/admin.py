"""
Django Admin สำหรับระบบ Radar หุ้น (ภาษาไทย)
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Symbol, PriceDaily, Indicator, Signal, Profile, BusinessProfile, StockTerm, TermQuestion, PositionAnalysis, SubscriptionPlan, Subscription

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


@admin.register(StockTerm)
class StockTermAdmin(admin.ModelAdmin):
    list_display = ("term", "category", "is_featured", "priority", "updated_at")
    list_filter = ("category", "is_featured", "updated_at")
    search_fields = ("term", "short_definition", "full_definition")
    ordering = ("-is_featured", "-priority", "term")


@admin.register(TermQuestion)
class TermQuestionAdmin(admin.ModelAdmin):
    list_display = ("status", "normalized_term", "short_question", "asked_by", "created_at", "answered_at")
    list_filter = ("status", "created_at", "answered_at")
    search_fields = ("question", "normalized_term", "answer_short", "answer_full")
    ordering = ("status", "-created_at")
    readonly_fields = ("created_at", "updated_at", "answered_at")

    fieldsets = (
        ("คำถาม", {
            "fields": ("status", "normalized_term", "asked_by", "question"),
        }),
        ("คำตอบ", {
            "fields": ("answered_by", "answer_short", "answer_full", "answered_at"),
        }),
        ("ระบบ", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def short_question(self, obj):
        s = (obj.question or "").strip()
        return s[:80] + ("..." if len(s) > 80 else "")

    short_question.short_description = "คำถาม"


@admin.register(PositionAnalysis)
class PositionAnalysisAdmin(admin.ModelAdmin):
    list_display = ("created_at", "symbol", "decision", "score", "confidence", "pnl_pct", "buy_price", "market_price")
    list_filter = ("decision", "created_at")
    search_fields = ("symbol__symbol", "symbol__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


# ---------------------------------------------------------------------------
# Symbol
# ---------------------------------------------------------------------------

@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "exchange", "sector")
    list_filter = ("exchange", "sector")
    search_fields = ("symbol", "name")
    ordering = ("symbol",)

    fieldsets = (
        ("ข้อมูลหลัก", {
            "fields": ("symbol", "name"),
        }),
        ("จัดหมวดหมู่", {
            "fields": ("exchange", "sector"),
        }),
    )

    class Meta:
        verbose_name = "หุ้น"


# ---------------------------------------------------------------------------
# PriceDaily
# ---------------------------------------------------------------------------

@admin.register(PriceDaily)
class PriceDailyAdmin(admin.ModelAdmin):
    list_display = ("symbol", "date", "open", "high", "low", "close", "volume", "change_pct")
    list_filter = ("symbol__exchange", "date")
    search_fields = ("symbol__symbol",)
    ordering = ("-date",)
    date_hierarchy = "date"
    raw_id_fields = ("symbol",)

    def change_pct(self, obj):
        """แสดง % เปลี่ยนแปลงราคา"""
        if obj.open and obj.open != 0:
            pct = float((obj.close - obj.open) / obj.open) * 100
            color = "green" if pct >= 0 else "red"
            # ใช้ format() กับค่าตัวเลขก่อนส่งให้ format_html
            pct_text = "{:+.2f}%".format(pct)
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, pct_text
            )
        return "-"

    change_pct.short_description = "เปลี่ยนแปลง"


# ---------------------------------------------------------------------------
# Indicator
# ---------------------------------------------------------------------------

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("symbol", "date", "rsi", "ema20", "ema50", "ema200", "volume_avg30")
    list_filter = ("date",)
    search_fields = ("symbol__symbol",)
    ordering = ("-date",)
    date_hierarchy = "date"
    raw_id_fields = ("symbol",)

    def rsi_badge(self, obj):
        """แสดง RSI พร้อมสีตามระดับ"""
        if obj.rsi is None:
            return "-"
        rsi = float(obj.rsi)
        if rsi < 30:
            color, label = "#ef4444", "Oversold"
        elif rsi > 70:
            color, label = "#f59e0b", "Overbought"
        else:
            color, label = "#22c55e", "Normal"
        
        rsi_text = "{:.1f} ({})".format(rsi, label)
        return format_html(
            '<span style="background:{}; color:white; padding:2px 6px; border-radius:4px;">'
            '{}</span>',
            color, rsi_text
        )

    rsi_badge.short_description = "RSI"


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

SIGNAL_COLORS = {
    "BUY": "#22c55e",
    "STRONG_BUY": "#16a34a",
    "BREAKOUT": "#3b82f6",
    "GOLDEN_CROSS": "#8b5cf6",
    "OVERSOLD": "#06b6d4",
    "SELL": "#ef4444",
    "STRONG_SELL": "#dc2626",
    "BREAKDOWN": "#f97316",
    "DEATH_CROSS": "#9333ea",
    "OVERBOUGHT": "#f59e0b",
    "WATCH": "#6b7280",
    "ALERT": "#fbbf24",
}

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ("symbol", "signal_badge", "score", "price", "created_at")
    list_filter = ("signal_type", "created_at")
    search_fields = ("symbol__symbol",)
    ordering = ("-created_at", "-score")
    raw_id_fields = ("symbol",)

    def signal_badge(self, obj):
        color = SIGNAL_COLORS.get(obj.signal_type, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:4px; font-size:12px;">{}</span>',
            color, obj.get_signal_type_display()
        )

    signal_badge.short_description = "สัญญาณ"


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
                     "max_strategies", "created_at")
    list_filter   = ("tier", "login_via_google", "created_at")
    search_fields = ("user__username", "user__email", "google_id")
    ordering      = ("-created_at",)
    inlines       = [SubscriptionInline]
    readonly_fields = ("tier", "google_id", "login_via_google", "google_picture_preview")

    fieldsets = (
        ("ข้อมูลผู้ใช้", {
            "fields": ("user", "tier", "max_strategies"),
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

