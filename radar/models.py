"""
Models สำหรับระบบ Radar หุ้น — Pro Version
==========================================
Phase Pro: เพิ่ม ATR, ADX, Highest High 20, Lowest Low 20,
           Volume Avg 20, Stop Loss, Direction, Filters
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ─────────────────────────────────────────────────────────────────────────────
# User Profile & Subscription
# ─────────────────────────────────────────────────────────────────────────────

class Profile(models.Model):
    TIER_CHOICES = [
        ("FREE",    "Free — ทดลองใช้"),
        ("PRO",     "Pro — ฟีเจอร์เต็ม"),
        ("PREMIUM", "Premium — ไม่จำกัด"),
    ]

    TIER_LIMITS = {
        "FREE":    {"watchlist": 3,  "backtest_years": 1, "scanner_top": 20,  "fundamental": False},
        "PRO":     {"watchlist": 10, "backtest_years": 3, "scanner_top": 100, "fundamental": True},
        "PREMIUM": {"watchlist": 20, "backtest_years": 5, "scanner_top": 500, "fundamental": True},
    }

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default="FREE",
                            db_index=True, verbose_name="ระดับสมาชิก")
    line_notify_token = models.CharField(max_length=100, blank=True, null=True)
    telegram_chat_id  = models.CharField(max_length=50,  blank=True, null=True)
    max_strategies    = models.IntegerField(default=3)

    # ── Google OAuth ──────────────────────────────────────────────────────────
    google_id        = models.CharField(max_length=128, blank=True, null=True,
                                        unique=True, verbose_name="Google ID")
    picture_url      = models.URLField(max_length=512, blank=True, null=True,
                                       verbose_name="รูปโปรไฟล์ Google")
    login_via_google = models.BooleanField(default=False, db_index=True,
                                           verbose_name="สมัครด้วย Google")
    can_use_portfolio = models.BooleanField(default=False, verbose_name="เข้าใช้ Portfolio ได้")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "โปรไฟล์ผู้ใช้"
        verbose_name_plural = "โปรไฟล์ผู้ใช้"

    def __str__(self):
        return f"{self.user.username} ({self.tier})"

    @property
    def is_pro(self):
        return self.tier in ("PRO", "PREMIUM")

    @property
    def is_premium(self):
        return self.tier == "PREMIUM"

    @property
    def limits(self):
        return self.TIER_LIMITS.get(self.tier, self.TIER_LIMITS["FREE"])

    # ── Active subscription ──
    @property
    def active_subscription(self):
        return self.subscriptions.filter(is_active=True).order_by("-end_date").first()

    def sync_tier_from_subscription(self):
        """อัปเดต tier จาก subscription ที่ active"""
        sub = self.active_subscription
        if sub:
            self.tier = sub.plan.tier
        else:
            # superuser ไม่จำกัด
            if self.user.is_superuser:
                self.tier = "PREMIUM"
            else:
                self.tier = "FREE"
        self.save(update_fields=["tier", "updated_at"])


class SubscriptionPlan(models.Model):
    """แผนสมาชิกที่ admin สร้างและจัดการได้"""
    TIER_CHOICES = [
        ("FREE",    "Free"),
        ("PRO",     "Pro"),
        ("PREMIUM", "Premium"),
    ]

    name        = models.CharField(max_length=50, unique=True, verbose_name="ชื่อแผน")
    tier        = models.CharField(max_length=10, choices=TIER_CHOICES, verbose_name="ระดับ")
    price_thb   = models.DecimalField(max_digits=10, decimal_places=2,
                                      default=0, verbose_name="ราคา (บาท/เดือน)")
    duration_days = models.IntegerField(default=30, verbose_name="ระยะเวลา (วัน)")
    is_active   = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    description = models.TextField(blank=True, verbose_name="รายละเอียด")
    features    = models.JSONField(default=list, blank=True,
                                   verbose_name="ฟีเจอร์ (JSON list)")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "แผนสมาชิก"
        verbose_name_plural = "แผนสมาชิก"
        ordering            = ["price_thb"]

    def __str__(self):
        return f"{self.name} ({self.tier}) ฿{self.price_thb}/เดือน"


class Subscription(models.Model):
    """ประวัติการสมัครสมาชิกของ user"""
    STATUS_CHOICES = [
        ("ACTIVE",   "กำลังใช้งาน"),
        ("EXPIRED",  "หมดอายุ"),
        ("CANCELLED","ยกเลิก"),
        ("TRIAL",    "ทดลองใช้"),
    ]

    profile     = models.ForeignKey(Profile, on_delete=models.CASCADE,
                                    related_name="subscriptions")
    plan        = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT,
                                    verbose_name="แผน")
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES,
                                   default="ACTIVE", db_index=True, verbose_name="สถานะ")
    start_date  = models.DateField(verbose_name="วันเริ่ม")
    end_date    = models.DateField(verbose_name="วันสิ้นสุด", db_index=True)
    is_active   = models.BooleanField(default=True, db_index=True, verbose_name="Active")
    payment_ref = models.CharField(max_length=255, blank=True,
                                   verbose_name="หมายเลขอ้างอิงการชำระ")
    note        = models.TextField(blank=True, verbose_name="หมายเหตุ (admin)")
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="created_subscriptions",
                                    verbose_name="สร้างโดย admin")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "ประวัติสมาชิก"
        verbose_name_plural = "ประวัติสมาชิก"
        ordering            = ["-start_date"]

    def __str__(self):
        return f"{self.profile.user.username} | {self.plan.name} | {self.start_date}→{self.end_date}"

    def save(self, *args, **kwargs):
        from datetime import date
        # auto-update is_active
        if self.end_date < date.today():
            self.is_active = False
            self.status    = "EXPIRED"
        super().save(*args, **kwargs)
        # sync tier กลับไปที่ profile
        self.profile.sync_tier_from_subscription()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            tier="PREMIUM" if instance.is_superuser else "FREE",
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()


# ─────────────────────────────────────────────────────────────────────────────
# Symbol
# ─────────────────────────────────────────────────────────────────────────────

class Symbol(models.Model):
    EXCHANGE_CHOICES = [
        ("SET",    "ตลาดหลักทรัพย์แห่งประเทศไทย"),
        ("NASDAQ", "NASDAQ"),
        ("NYSE",   "New York Stock Exchange"),
        ("OTHER",  "อื่นๆ"),
    ]

    symbol   = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="รหัสหุ้น")
    name     = models.CharField(max_length=255, verbose_name="ชื่อบริษัท")
    exchange = models.CharField(max_length=20, choices=EXCHANGE_CHOICES, db_index=True, verbose_name="ตลาด")
    sector   = models.CharField(max_length=100, blank=True, db_index=True, verbose_name="หมวดอุตสาหกรรม")

    class Meta:
        verbose_name        = "หุ้น"
        verbose_name_plural = "รายชื่อหุ้น"
        ordering            = ["symbol"]
        indexes = [
            models.Index(fields=["exchange", "sector"], name="idx_symbol_exchange_sector"),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.exchange})"


# ─────────────────────────────────────────────────────────────────────────────
# PriceDaily
# ─────────────────────────────────────────────────────────────────────────────

class PriceDaily(models.Model):
    """ราคาหุ้นรายวัน OHLCV"""

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE,
                               related_name="prices", db_index=True, verbose_name="หุ้น")
    date   = models.DateField(db_index=True, verbose_name="วันที่")
    open   = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="เปิด")
    high   = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="สูงสุด")
    low    = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="ต่ำสุด")
    close  = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="ปิด")
    volume = models.BigIntegerField(verbose_name="ปริมาณ")

    class Meta:
        verbose_name        = "ราคารายวัน"
        verbose_name_plural = "ราคารายวัน"
        unique_together     = [("symbol", "date")]
        ordering            = ["-date"]
        indexes = [
            models.Index(fields=["symbol", "-date"], name="idx_price_symbol_date_desc"),
            models.Index(fields=["date"],             name="idx_price_date"),
        ]

    def __str__(self):
        return f"{self.symbol.symbol} | {self.date} | close={self.close}"


# ─────────────────────────────────────────────────────────────────────────────
# Indicator  — Pro Version
# ─────────────────────────────────────────────────────────────────────────────

class Indicator(models.Model):
    """
    Technical Indicators รายวัน — Pro Version

    สูตรคำนวณ:
      EMA(n)     = Price × k + EMAp × (1-k),  k = 2/(n+1)
      ATR(14)    = Wilder EMA14 ของ True Range
                   TR = max(H-L, |H-Cp|, |L-Cp|)
      +DM        = High - Prev High  (ถ้า > 0 และ > |-DM|)
      -DM        = Prev Low - Low    (ถ้า > 0 และ > |+DM|)
      +DI        = 100 × EMA14(+DM) / ATR14
      -DI        = 100 × EMA14(-DM) / ATR14
      DX         = 100 × |+DI - -DI| / (+DI + -DI)
      ADX(14)    = EMA14(DX)
      HH20       = rolling_max(High, 20)
      LL20       = rolling_min(Low,  20)
      AvgVol(20) = rolling_mean(Volume, 20)
    """

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE,
                               related_name="indicators", db_index=True, verbose_name="หุ้น")
    date   = models.DateField(db_index=True, verbose_name="วันที่")

    # ── EMA ──────────────────────────────────────────────────────────────────
    ema20  = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="EMA 20")
    ema50  = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="EMA 50")
    ema200 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="EMA 200")

    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                              verbose_name="RSI 14", help_text="0–100")

    # ── MACD ──────────────────────────────────────────────────────────────────
    macd        = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="MACD")
    macd_signal = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="MACD Signal")
    macd_hist   = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="MACD Hist")

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_upper  = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="BB Upper")
    bb_middle = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="BB Middle")
    bb_lower  = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, verbose_name="BB Lower")

    # ── ATR — Average True Range ──────────────────────────────────────────────
    atr14     = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True,
                                    verbose_name="ATR 14",
                                    help_text="Wilder ATR 14 วัน — วัดความผันผวน")
    atr_avg30 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True,
                                    verbose_name="ATR Avg 30",
                                    help_text="ค่าเฉลี่ย ATR 30 วัน — Volatility Filter")

    # ── ADX — Average Directional Index ───────────────────────────────────────
    adx14    = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                   verbose_name="ADX 14",
                                   help_text="Trend Strength 0–100 (>25 = แนวโน้มชัด)")
    di_plus  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                   verbose_name="+DI 14",
                                   help_text="Positive Directional Indicator")
    di_minus = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                   verbose_name="-DI 14",
                                   help_text="Negative Directional Indicator")

    # ── Highest High / Lowest Low ─────────────────────────────────────────────
    highest_high_20 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True,
                                          verbose_name="Highest High 20",
                                          help_text="ราคาสูงสุดใน 20 วัน — Breakout signal")
    lowest_low_20   = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True,
                                          verbose_name="Lowest Low 20",
                                          help_text="ราคาต่ำสุดใน 20 วัน — Breakdown signal")

    # ── Volume ────────────────────────────────────────────────────────────────
    volume_avg20 = models.BigIntegerField(null=True, blank=True,
                                          verbose_name="Volume Avg 20",
                                          help_text="Volume เฉลี่ย 20 วัน — Volume Filter (>1.5×)")
    volume_avg30 = models.BigIntegerField(null=True, blank=True,
                                          verbose_name="Volume Avg 30")

    class Meta:
        verbose_name        = "Indicator"
        verbose_name_plural = "Indicators"
        unique_together     = [("symbol", "date")]
        ordering            = ["-date"]
        indexes = [
            models.Index(fields=["symbol", "-date"],       name="idx_ind_symbol_date"),
            models.Index(fields=["date", "adx14"],         name="idx_ind_date_adx"),
            models.Index(fields=["date", "atr14"],         name="idx_ind_date_atr"),
            models.Index(fields=["date", "rsi"],           name="idx_ind_date_rsi"),
            models.Index(fields=["date", "ema20", "ema50"],name="idx_ind_date_ema_cross"),
            models.Index(fields=["date", "macd_hist"],     name="idx_ind_date_macd"),
            models.Index(fields=["date", "highest_high_20"],name="idx_ind_date_hh20"),
        ]

    def __str__(self):
        return f"{self.symbol.symbol} | {self.date} | ADX={self.adx14} RSI={self.rsi}"


# ─────────────────────────────────────────────────────────────────────────────
# Signal  — Pro Version
# ─────────────────────────────────────────────────────────────────────────────

class Signal(models.Model):
    """
    สัญญาณซื้อขาย — Pro Version
    เพิ่ม: direction, stop_loss, risk_pct, atr/adx ณ วันสัญญาณ, filter flags
    """

    SIGNAL_TYPE_CHOICES = [
        # Bullish
        ("GOLDEN_CROSS",  "Golden Cross EMA50/200"),
        ("EMA_ALIGNMENT", "EMA Alignment 20>50>200"),
        ("EMA_PULLBACK",  "EMA Pullback แตะ EMA20"),
        ("BREAKOUT",      "Breakout เหนือ High 20"),
        ("BUY",           "ซื้อ"),
        ("STRONG_BUY",    "ซื้อแข็งแกร่ง"),
        ("OVERSOLD",      "Oversold RSI<30"),
        # Bearish
        ("DEATH_CROSS",   "Death Cross EMA50/200"),
        ("BREAKDOWN",     "Breakdown ต่ำกว่า Low 20"),
        ("SELL",          "ขาย"),
        ("STRONG_SELL",   "ขายแข็งแกร่ง"),
        ("OVERBOUGHT",    "Overbought RSI>70"),
        # Neutral
        ("WATCH",         "เฝ้าดู"),
        ("ALERT",         "แจ้งเตือน"),
    ]

    DIRECTION_CHOICES = [
        ("LONG",    "Long / ซื้อ"),
        ("SHORT",   "Short / ขาย"),
        ("NEUTRAL", "Neutral"),
    ]

    symbol      = models.ForeignKey(Symbol, on_delete=models.CASCADE,
                                    related_name="signals", db_index=True, verbose_name="หุ้น")
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPE_CHOICES,
                                   db_index=True, verbose_name="ประเภทสัญญาณ")
    direction   = models.CharField(max_length=10, choices=DIRECTION_CHOICES,
                                   default="NEUTRAL", db_index=True, verbose_name="ทิศทาง")
    score       = models.DecimalField(max_digits=6, decimal_places=2,
                                      db_index=True, verbose_name="คะแนน 0–100")

    # ── Entry & Risk Management ────────────────────────────────────────────────
    price       = models.DecimalField(max_digits=18, decimal_places=4,
                                      verbose_name="ราคาเข้า")
    stop_loss   = models.DecimalField(max_digits=18, decimal_places=4,
                                      null=True, blank=True,
                                      verbose_name="Stop Loss",
                                      help_text="Entry − 1.5 × ATR(14)")
    risk_pct    = models.DecimalField(max_digits=6, decimal_places=2,
                                      null=True, blank=True,
                                      verbose_name="ความเสี่ยง %",
                                      help_text="(Entry − SL) / Entry × 100")

    # ── Indicator ณ วันสัญญาณ ──────────────────────────────────────────────────
    atr_at_signal  = models.DecimalField(max_digits=18, decimal_places=4,
                                         null=True, blank=True, verbose_name="ATR")
    adx_at_signal  = models.DecimalField(max_digits=6, decimal_places=2,
                                         null=True, blank=True, verbose_name="ADX")
    volume_ratio   = models.DecimalField(max_digits=6, decimal_places=2,
                                         null=True, blank=True,
                                         verbose_name="Volume Ratio",
                                         help_text="Volume ÷ AvgVol20")

    # ── Filter flags ──────────────────────────────────────────────────────────
    filter_volume     = models.BooleanField(default=False, verbose_name="Volume Filter ✓")
    filter_volatility = models.BooleanField(default=False, verbose_name="Volatility Filter ✓")
    filter_adx        = models.BooleanField(default=False, verbose_name="ADX Filter ✓ (>25)")

    created_at  = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="เวลาที่สร้าง")

    class Meta:
        verbose_name        = "สัญญาณ"
        verbose_name_plural = "สัญญาณซื้อขาย"
        ordering            = ["-created_at", "-score"]
        indexes = [
            models.Index(fields=["symbol", "-created_at", "-score"], name="idx_sig_symbol_recent"),
            models.Index(fields=["signal_type", "-created_at", "-score"], name="idx_sig_type_recent"),
            models.Index(fields=["-score", "-created_at"],               name="idx_sig_score_recent"),
            models.Index(fields=["direction", "-score", "-created_at"],  name="idx_sig_direction"),
        ]

    def __str__(self):
        sl = f" SL={self.stop_loss}" if self.stop_loss else ""
        return f"{self.symbol.symbol} | {self.signal_type} | {self.direction} | {self.score}{sl}"


# ─────────────────────────────────────────────────────────────────────────────
# Business Profile (สำหรับหน้าติดต่อเรา)
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProfile(models.Model):
    """
    เก็บข้อมูลธุรกิจและช่องทางการติดต่อ (Singleton Model)
    """
    company_name = models.CharField(max_length=255, verbose_name="ชื่อบริษัท/แบรนด์")
    description = models.TextField(blank=True, verbose_name="รายละเอียดธุรกิจ")
    
    # ช่องทางติดต่อ
    address = models.TextField(blank=True, verbose_name="ที่อยู่")
    phone = models.CharField(max_length=50, blank=True, verbose_name="เบอร์โทรศัพท์")
    email = models.EmailField(blank=True, verbose_name="อีเมลติดต่อ")
    line_id = models.CharField(max_length=100, blank=True, verbose_name="Line ID")
    facebook_url = models.URLField(blank=True, verbose_name="Facebook URL")
    website_url = models.URLField(blank=True, verbose_name="Website URL")
    
    # สำหรับ SEO หรือข้อความส่วนตัว
    footer_text = models.CharField(max_length=255, blank=True, verbose_name="ข้อความท้ายเว็บ")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "บันทึกโพรไฟล์ธุรกิจ"
        verbose_name_plural = "บันทึกโพรไฟล์ธุรกิจ"

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        # จำกัดให้มีได้เพียง 1 record เท่านั้น (Singleton)
        if not self.pk and BusinessProfile.objects.exists():
            return
        return super().save(*args, **kwargs)


class StockTerm(models.Model):
    CATEGORY_CHOICES = [
        ("indicator", "Indicator"),
        ("pattern", "Pattern"),
        ("concept", "Concept"),
        ("faq", "FAQ"),
        ("other", "Other"),
    ]

    term = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="คำศัพท์/หัวข้อ")
    short_definition = models.TextField(blank=True, verbose_name="คำอธิบายสั้น")
    full_definition = models.TextField(blank=True, verbose_name="คำอธิบายเต็ม")
    category = models.CharField(max_length=24, choices=CATEGORY_CHOICES, default="other", db_index=True, verbose_name="หมวดหมู่")
    keywords = models.JSONField(default=list, blank=True, verbose_name="คีย์เวิร์ด")
    is_featured = models.BooleanField(default=False, db_index=True, verbose_name="แนะนำ (Featured)")
    priority = models.IntegerField(default=0, db_index=True, verbose_name="ลำดับความสำคัญ")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "คลังคำศัพท์/คำแนะนำ"
        verbose_name_plural = "คลังคำศัพท์/คำแนะนำ"
        ordering = ["-is_featured", "-priority", "term"]
        indexes = [
            models.Index(fields=["category", "-is_featured", "-priority"], name="idx_term_cat_feat_pri"),
            models.Index(fields=["term"], name="idx_term_term"),
        ]

    def __str__(self):
        return self.term


class TermQuestion(models.Model):
    STATUS_CHOICES = [
        ("NEW", "รอคำตอบ"),
        ("ANSWERED", "ตอบแล้ว"),
    ]

    asked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="term_questions", verbose_name="ผู้ถาม")
    question = models.TextField(verbose_name="คำถาม")
    normalized_term = models.CharField(max_length=64, blank=True, db_index=True, verbose_name="คำศัพท์ที่เกี่ยวข้อง")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="NEW", db_index=True, verbose_name="สถานะ")
    answer_short = models.TextField(blank=True, verbose_name="คำตอบสั้น")
    answer_full = models.TextField(blank=True, verbose_name="คำตอบเต็ม")
    answered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="answered_term_questions", verbose_name="ผู้ตอบ")
    answered_at = models.DateTimeField(null=True, blank=True, verbose_name="เวลาที่ตอบ")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "คำถามคำศัพท์"
        verbose_name_plural = "คำถามคำศัพท์"
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="idx_termq_status_recent"),
            models.Index(fields=["normalized_term", "-created_at"], name="idx_termq_term_recent"),
        ]

    def __str__(self):
        return self.question[:80]

    def save(self, *args, **kwargs):
        is_answered = self.status == "ANSWERED"
        has_term = bool((self.normalized_term or "").strip())
        has_answer = bool((self.answer_short or "").strip() or (self.answer_full or "").strip())

        if is_answered and has_term and has_answer and self.answered_at is None:
            self.answered_at = timezone.now()

        super().save(*args, **kwargs)

        if is_answered and has_term and has_answer:
            term_key = (self.normalized_term or "").strip().upper()
            StockTerm.objects.update_or_create(
                term=term_key,
                defaults={
                    "short_definition": self.answer_short or "",
                    "full_definition": self.answer_full or "",
                    "category": "faq",
                    "keywords": [],
                    "is_featured": True,
                    "priority": 50,
                },
            )


class PositionAnalysis(models.Model):
    DECISION_CHOICES = [
        ("BUY_MORE", "Buy More"),
        ("HOLD", "Hold"),
        ("SELL", "Sell"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="position_analyses")
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name="position_analyses")

    buy_price = models.DecimalField(max_digits=18, decimal_places=4)
    market_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    pnl_pct = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)

    rsi14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ema20 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ema50 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ema200 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    adx14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    decision = models.CharField(max_length=16, choices=DECISION_CHOICES)
    confidence = models.DecimalField(max_digits=5, decimal_places=2)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    explanation = models.TextField()
    signals = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "วิเคราะห์สถานะถือหุ้น"
        verbose_name_plural = "วิเคราะห์สถานะถือหุ้น"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["symbol", "-created_at"], name="idx_pos_symbol_recent"),
            models.Index(fields=["user", "-created_at"], name="idx_pos_user_recent"),
        ]

    def __str__(self):
        return f"{self.symbol.symbol} | {self.decision} | score={self.score} | {self.created_at:%Y-%m-%d %H:%M}"

# ─────────────────────────────────────────────────────────────────────────────
# NewsItem — ข่าวหุ้นพร้อม Sentiment Score
# ─────────────────────────────────────────────────────────────────────────────

class NewsItem(models.Model):
    """ข่าวหุ้นจาก RSS/API พร้อม Sentiment วิเคราะห์"""

    SENTIMENT_CHOICES = [
        ("BULLISH",  "🟢 Bullish"),
        ("BEARISH",  "🔴 Bearish"),
        ("NEUTRAL",  "⚪ Neutral"),
    ]

    SOURCE_CHOICES = [
        ("SET",         "SET (ตลาดหลักทรัพย์)"),
        ("REUTERS",     "Reuters"),
        ("YAHOO",       "Yahoo Finance"),
        ("GOOGLE",      "Google News"),
        ("THANSETTAKIJ","ฐานเศรษฐกิจ"),
        ("MANAGER",     "ผู้จัดการออนไลน์"),
        ("BANGKOKPOST",  "Bangkok Post"),
        ("OTHER",       "อื่นๆ"),
    ]

    # ── เนื้อหาข่าว ──
    title       = models.CharField(max_length=512, verbose_name="หัวข้อ")
    summary     = models.TextField(blank=True, verbose_name="สรุปข่าว")
    url         = models.URLField(max_length=2048, unique=True, verbose_name="ลิงก์ข่าว")
    source      = models.CharField(max_length=20, choices=SOURCE_CHOICES,
                                   default="OTHER", db_index=True, verbose_name="แหล่งข่าว")
    published_at = models.DateTimeField(db_index=True, verbose_name="เวลาเผยแพร่")

    # ── Sentiment ──
    sentiment       = models.CharField(max_length=10, choices=SENTIMENT_CHOICES,
                                       default="NEUTRAL", db_index=True, verbose_name="Sentiment")
    sentiment_score = models.FloatField(default=0.0,
                                        help_text="-1.0 (Bearish) ถึง +1.0 (Bullish)",
                                        verbose_name="คะแนน Sentiment")

    # ── Symbol ที่เกี่ยวข้อง (M2M) ──
    symbols = models.ManyToManyField(
        "Symbol", blank=True,
        related_name="news",
        verbose_name="หุ้นที่เกี่ยวข้อง"
    )

    # ── Metadata ──
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "ข่าวหุ้น"
        verbose_name_plural = "ข่าวหุ้น"
        ordering            = ["-published_at"]
        indexes = [
            models.Index(fields=["-published_at"],              name="idx_news_pub"),
            models.Index(fields=["source", "-published_at"],    name="idx_news_src_pub"),
            models.Index(fields=["sentiment", "-published_at"], name="idx_news_sent_pub"),
        ]

    def __str__(self):
        return f"[{self.source}] {self.title[:60]}"

# ─────────────────────────────────────────────────────────────────────────────
# Watchlist — ติดตามหุ้นส่วนตัว + บันทึกการซื้อ
# ─────────────────────────────────────────────────────────────────────────────

class Watchlist(models.Model):
    """Watchlist ของ user แต่ละคน (1 user = 1 watchlist)"""
    user       = models.OneToOneField(User, on_delete=models.CASCADE,
                                      related_name="watchlist")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Watchlist"
        verbose_name_plural = "Watchlists"

    def __str__(self):
        return f"Watchlist of {self.user.username}"


class WatchlistItem(models.Model):
    """หุ้นแต่ละตัวใน Watchlist (max 10 ตัวต่อ user)"""
    watchlist  = models.ForeignKey(Watchlist, on_delete=models.CASCADE,
                                   related_name="items")
    symbol     = models.ForeignKey(Symbol, on_delete=models.CASCADE,
                                   related_name="watchlist_items")
    note       = models.CharField(max_length=255, blank=True,
                                  verbose_name="หมายเหตุ")
    alert_price_high = models.DecimalField(max_digits=18, decimal_places=4,
                                           null=True, blank=True,
                                           verbose_name="Alert ราคาสูงกว่า")
    alert_price_low  = models.DecimalField(max_digits=18, decimal_places=4,
                                           null=True, blank=True,
                                           verbose_name="Alert ราคาต่ำกว่า")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Watchlist Item"
        verbose_name_plural = "Watchlist Items"
        unique_together     = [("watchlist", "symbol")]
        ordering            = ["created_at"]

    def __str__(self):
        return f"{self.watchlist.user.username} → {self.symbol.symbol}"


class WatchlistTrade(models.Model):
    """บันทึกการซื้อ (ได้ไม่จำกัดครั้ง) สำหรับคำนวณต้นทุนเฉลี่ย"""
    ACTION_CHOICES = [
        ("BUY",  "ซื้อ"),
        ("SELL", "ขาย"),
    ]

    item       = models.ForeignKey(WatchlistItem, on_delete=models.CASCADE,
                                   related_name="trades")
    action     = models.CharField(max_length=4, choices=ACTION_CHOICES,
                                  default="BUY", verbose_name="ซื้อ/ขาย")
    price      = models.DecimalField(max_digits=18, decimal_places=4,
                                     verbose_name="ราคาต่อหน่วย")
    quantity   = models.IntegerField(verbose_name="จำนวนหุ้น")
    trade_date = models.DateField(default=timezone.now,
                                  verbose_name="วันที่ทำรายการ")
    note       = models.CharField(max_length=255, blank=True,
                                  verbose_name="หมายเหตุ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "รายการซื้อขาย"
        verbose_name_plural = "รายการซื้อขาย"
        ordering            = ["trade_date", "created_at"]

    def __str__(self):
        sym = self.item.symbol.symbol
        return f"{self.action} {sym} {self.quantity}@{self.price}"


# ─────────────────────────────────────────────────────────────────────────────
# LatestSnapshot — Materialized View (managed = False)
# ─────────────────────────────────────────────────────────────────────────────

class LatestSnapshot(models.Model):
    """
    Materialized View ที่ join ข้อมูลล่าสุดจาก Symbol + PriceDaily + Indicator + Signal
    ไว้ใน 1 แถวต่อหุ้น — query เร็วมาก ไม่ต้อง join หลายตาราง

    Refresh: python manage.py refresh_snapshot
    สร้างจาก: migration 0012_latest_snapshot_view.py
    """

    # ── Symbol ────────────────────────────────────────────────────────────────
    symbol_id = models.IntegerField(primary_key=True)
    symbol    = models.CharField(max_length=20)
    name      = models.CharField(max_length=255)
    exchange  = models.CharField(max_length=20)
    sector    = models.CharField(max_length=100, blank=True)

    # ── Price (ล่าสุด) ────────────────────────────────────────────────────────
    price_date = models.DateField(null=True)
    close      = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    open       = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    high       = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    low        = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    volume     = models.BigIntegerField(null=True)

    # ── Indicator (ล่าสุด) ───────────────────────────────────────────────────
    ema20           = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    ema50           = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    ema200          = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    rsi             = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    macd            = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    macd_signal     = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    macd_hist       = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    adx14           = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    atr14           = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    bb_upper        = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    bb_lower        = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    highest_high_20 = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    lowest_low_20   = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    volume_avg20    = models.BigIntegerField(null=True)

    # ── Signal (ล่าสุด) ──────────────────────────────────────────────────────
    signal_type  = models.CharField(max_length=20, null=True)
    direction    = models.CharField(max_length=10, null=True)
    signal_score = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    stop_loss    = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    risk_pct     = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    signal_date  = models.DateTimeField(null=True)

    class Meta:
        managed  = False          # Django ไม่สร้าง/ลบตาราง — จัดการโดย migration SQL
        db_table = "radar_latest_snapshot"
        ordering = ["-signal_score"]
        verbose_name        = "Latest Snapshot"
        verbose_name_plural = "Latest Snapshots"

    def __str__(self):
        return f"{self.symbol} | {self.close} | {self.direction} {self.signal_score}"


# ─────────────────────────────────────────────────────────────────────────────
# FundamentalSnapshot — VI Screener (หุ้นดีราคาต่ำ)
# ดึงจาก Yahoo Finance (.BK) วันละ 50 บริษัท / cache 7 วัน
# ─────────────────────────────────────────────────────────────────────────────

class FundamentalSnapshot(models.Model):
    symbol          = models.OneToOneField(Symbol, on_delete=models.CASCADE,
                                           related_name="fundamental_snapshot")
    # ── Valuation ────────────────────────────────────────────────────────────
    pe_ratio        = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    pb_ratio        = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    market_cap      = models.BigIntegerField(null=True)            # THB
    # ── Profitability ────────────────────────────────────────────────────────
    roe             = models.DecimalField(max_digits=8,  decimal_places=2, null=True)   # %
    roa             = models.DecimalField(max_digits=8,  decimal_places=2, null=True)   # %
    net_margin      = models.DecimalField(max_digits=8,  decimal_places=2, null=True)   # %
    # ── Growth ───────────────────────────────────────────────────────────────
    revenue_growth  = models.DecimalField(max_digits=8,  decimal_places=2, null=True)   # % YoY
    earnings_growth = models.DecimalField(max_digits=8,  decimal_places=2, null=True)   # % YoY
    # ── Health ───────────────────────────────────────────────────────────────
    debt_to_equity  = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    current_ratio   = models.DecimalField(max_digits=8,  decimal_places=2, null=True)
    # ── Dividend ─────────────────────────────────────────────────────────────
    dividend_yield  = models.DecimalField(max_digits=8,  decimal_places=2, null=True)   # %
    # ── VI Score ─────────────────────────────────────────────────────────────
    vi_score        = models.DecimalField(max_digits=6,  decimal_places=2, null=True)
    vi_grade        = models.CharField(max_length=2, null=True)    # A/B/C/D
    # ── Meta ─────────────────────────────────────────────────────────────────
    fetched_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Fundamental Snapshot"
        verbose_name_plural = "Fundamental Snapshots"

    def __str__(self):
        return f"{self.symbol} | VI={self.vi_score} ({self.vi_grade})"


# ─────────────────────────────────────────────────────────────────────────────
# Chat System (Admin ↔ User)
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(models.Model):
    sender   = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name="sent_chat_msgs",
                                 verbose_name="ผู้ส่ง")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name="recv_chat_msgs",
                                 verbose_name="ผู้รับ")
    body     = models.TextField(verbose_name="ข้อความ")
    is_read  = models.BooleanField(default=False, db_index=True,
                                   verbose_name="อ่านแล้ว")
    is_ai_response = models.BooleanField(default=False, verbose_name="ตอบโดย AI")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering            = ["created_at"]
        verbose_name        = "ข้อความแชท"
        verbose_name_plural = "ข้อความแชท"
        indexes = [
            models.Index(fields=["sender", "receiver", "created_at"],
                         name="idx_chat_convo"),
        ]

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.body[:40]}"


# ─────────────────────────────────────────────────────────────────────────────
# Site Settings
# ─────────────────────────────────────────────────────────────────────────────

class SiteSetting(models.Model):
    ai_chat_enabled = models.BooleanField(
        default=False,
        verbose_name="เปิดใช้ AI ในแชท",
        help_text="เมื่อเปิด ระบบจะตอบแชทผู้ใช้โดยอัตโนมัติด้วย Claude AI",
    )

    class Meta:
        verbose_name        = "ตั้งค่าระบบ"
        verbose_name_plural = "ตั้งค่าระบบ"

    def __str__(self):
        return f"SiteSetting (AI Chat: {'เปิด' if self.ai_chat_enabled else 'ปิด'})"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ── Alpaca US Stock Trading ──────────────────────────────────────────────────

class AlpacaOrder(models.Model):
    SIDE_CHOICES = [("buy", "Buy"), ("sell", "Sell")]
    TYPE_CHOICES = [("market", "Market"), ("limit", "Limit")]
    STATUS_CHOICES = [
        ("pending_confirm", "รอยืนยัน"),
        ("submitted",       "ส่งแล้ว"),
        ("filled",          "สำเร็จ"),
        ("cancelled",       "ยกเลิก"),
        ("rejected",        "ถูกปฏิเสธ"),
    ]

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alpaca_orders", verbose_name="ผู้ใช้")
    symbol          = models.CharField(max_length=20, verbose_name="หุ้น")
    side            = models.CharField(max_length=4, choices=SIDE_CHOICES, verbose_name="ทิศทาง")
    qty             = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="จำนวนหุ้น")
    order_type      = models.CharField(max_length=10, choices=TYPE_CHOICES, default="market", verbose_name="ประเภท Order")
    limit_price     = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, verbose_name="ราคา Limit")
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_confirm", verbose_name="สถานะ")
    alpaca_order_id = models.CharField(max_length=100, blank=True, verbose_name="Alpaca Order ID")
    ai_reasoning    = models.TextField(blank=True, verbose_name="เหตุผลที่ AI เสนอ")
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")
    confirmed_at    = models.DateTimeField(null=True, blank=True, verbose_name="ยืนยันเมื่อ")

    class Meta:
        verbose_name        = "Alpaca Order"
        verbose_name_plural = "Alpaca Orders"
        ordering            = ["-created_at"]
        indexes             = [models.Index(fields=["user", "status"]), models.Index(fields=["alpaca_order_id"])]

    def __str__(self):
        return f"{self.side.upper()} {self.qty} {self.symbol} [{self.get_status_display()}]"
