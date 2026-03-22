"""
Django Admin สำหรับระบบ Radar หุ้น (ภาษาไทย)
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Symbol, PriceDaily, Indicator, Signal, Profile, BusinessProfile, StockTerm, TermQuestion, PositionAnalysis

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
