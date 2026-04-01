"""
fix_bad_symbols — แก้ไข ticker ผิด และลบหุ้น delisted ออกจาก DB

การใช้งาน:
    python manage.py fix_bad_symbols          # preview (ไม่แก้จริง)
    python manage.py fix_bad_symbols --apply  # แก้จริง
"""

from django.core.management.base import BaseCommand
from radar.models import Symbol, PriceDaily


# ── ticker ที่ต้องแก้ yahoo field ──────────────────────────────────────────
TICKER_FIXES = [
    # symbol,    new_yahoo,   reason
    ("MAKRO",    "CPAXT.BK",  "renamed to CP Axtra (CPAXT)"),
    ("INDORAMA", "IVL.BK",    "SET ticker is IVL, not INDORAMA"),
    ("PS",       "PSH.BK",    "Pruksa renamed to PSH"),
    ("SHREIT",   "SHR.BK",    "REIT renamed to SHR"),
    ("BRK.B",    "BRK-B",     "yfinance uses hyphen, not dot"),
]

# ── exchange ผิด → ต้องแก้ (เคย SET แต่จริงๆ เป็น US) ──────────────────────
EXCHANGE_FIXES = [
    # symbol, new_exchange, new_yahoo,  reason
    ("HMC",  "NYSE",       "HMC",      "Honda Motor is NYSE:HMC, not SET"),
    ("JD",   "NASDAQ",     "JD",       "JD.com is NASDAQ:JD, not SET"),
]

# ── หุ้นที่ delisted / ข้อมูลผิด → ลบ ──────────────────────────────────────
TO_DELETE = [
    # symbol,   reason
    ("DTAC",    "merged with TRUE (2023), delisted"),
    ("ESSO",    "ESSO Thailand delisted"),
    ("ROBINS",  "merged with CRC / Central, delisted"),
    ("K",       "Kellanova acquired by Mars (2024), delisted"),
    ("INTUCH",  "GULF acquired INTUCH, delisted"),
    ("KBTG",    "KBTG is private (KBank tech subsidiary), never listed on SET"),
    ("GL",      "Group Lease suspended / delisted"),
    ("OISHI",   "ThaiBev took OISHI private, delisted"),
    ("NHP",     "delisted, no data found"),
    ("KPN",     "KPN Land delisted"),
    ("PRUKSA",  "duplicate — PS is the correct SET symbol (both map to PSH)"),
]


class Command(BaseCommand):
    help = "แก้ไข yahoo ticker ผิด และลบหุ้น delisted ออกจาก DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="แก้จริง (ถ้าไม่ใส่ flag นี้จะเป็น dry-run)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        mode  = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(f"\n=== fix_bad_symbols [{mode}] ===\n")

        # ── 1. Fix yahoo ticker ──────────────────────────────────────────────
        self.stdout.write("--- Ticker fixes ---")
        for symbol, new_yahoo, reason in TICKER_FIXES:
            try:
                obj = Symbol.objects.get(symbol=symbol)
                old_yahoo = obj.yahoo
                if apply:
                    obj.yahoo = new_yahoo
                    obj.save(update_fields=["yahoo"])
                self.stdout.write(
                    f"  {'[FIXED]' if apply else '[WOULD FIX]'} "
                    f"{symbol}: yahoo {old_yahoo} -> {new_yahoo}  ({reason})"
                )
            except Symbol.DoesNotExist:
                self.stdout.write(f"  [SKIP]  {symbol}: not in DB")

        # ── 2. Fix exchange ──────────────────────────────────────────────────
        self.stdout.write("\n--- Exchange fixes ---")
        for symbol, new_exchange, new_yahoo, reason in EXCHANGE_FIXES:
            try:
                obj = Symbol.objects.get(symbol=symbol)
                old_ex, old_yah = obj.exchange, obj.yahoo
                if apply:
                    obj.exchange = new_exchange
                    obj.yahoo    = new_yahoo
                    obj.save(update_fields=["exchange", "yahoo"])
                self.stdout.write(
                    f"  {'[FIXED]' if apply else '[WOULD FIX]'} "
                    f"{symbol}: exchange {old_ex}->{new_exchange}, yahoo {old_yah}->{new_yahoo}  ({reason})"
                )
            except Symbol.DoesNotExist:
                self.stdout.write(f"  [SKIP]  {symbol}: not in DB")

        # ── 3. Delete delisted ───────────────────────────────────────────────
        self.stdout.write("\n--- Delete delisted ---")
        total_prices = 0
        for symbol, reason in TO_DELETE:
            try:
                obj = Symbol.objects.get(symbol=symbol)
                price_count = PriceDaily.objects.filter(symbol=obj).count()
                total_prices += price_count
                if apply:
                    obj.delete()  # cascade ลบ PriceDaily + Indicator + Signal ด้วย
                self.stdout.write(
                    f"  {'[DELETED]' if apply else '[WOULD DELETE]'} "
                    f"{symbol}: {price_count} price rows  ({reason})"
                )
            except Symbol.DoesNotExist:
                self.stdout.write(f"  [SKIP]  {symbol}: not in DB")

        # ── สรุป ────────────────────────────────────────────────────────────
        self.stdout.write(f"\n{'='*50}")
        if apply:
            remaining = Symbol.objects.count()
            self.stdout.write(self.style.SUCCESS(
                f"Done. {len(TICKER_FIXES)} tickers fixed, "
                f"{len(EXCHANGE_FIXES)} exchanges fixed, "
                f"{len(TO_DELETE)} symbols deleted "
                f"(~{total_prices} price rows removed)\n"
                f"Symbols remaining in DB: {remaining}"
            ))
        else:
            self.stdout.write(
                f"[DRY-RUN] No changes made. Run with --apply to execute."
            )
