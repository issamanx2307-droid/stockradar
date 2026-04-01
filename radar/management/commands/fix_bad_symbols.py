"""
fix_bad_symbols — แก้ไข symbol/exchange ผิด และลบหุ้น delisted ออกจาก DB

การใช้งาน:
    python manage.py fix_bad_symbols          # preview (ไม่แก้จริง)
    python manage.py fix_bad_symbols --apply  # แก้จริง

หมายเหตุ: yahoo ticker ถูก compute อัตโนมัติใน symbols_export view:
    - SET exchange  → yahoo = symbol + ".BK"
    - ไม่ใช่ SET    → yahoo = symbol
  ดังนั้นต้องแก้ที่ symbol/exchange โดยตรง
"""

from django.core.management.base import BaseCommand
from radar.models import Symbol, PriceDaily


# ── เปลี่ยนชื่อ symbol (SET: yahoo=symbol.BK จะตามไปเอง) ──────────────────
# (old_symbol, new_symbol, reason)
# หมายเหตุ: MAKRO และ INDORAMA ไม่อยู่ที่นี่ เพราะ CPAXT/IVL มีอยู่ใน DB แล้ว
#           → ย้ายไปอยู่ใน TO_DELETE แทน
SYMBOL_RENAMES = [
    ("PS",    "PSH",   "Pruksa renamed to PSH on SET"),
    ("SHREIT","SHR",   "REIT renamed to SHR on SET"),
    ("BRK.B", "BRK-B", "yfinance uses BRK-B (hyphen); exchange stays NYSE"),
]

# ── แก้ exchange ผิด (yahoo จะ compute ใหม่อัตโนมัติ) ──────────────────────
# (symbol, new_exchange, reason)
EXCHANGE_FIXES = [
    ("HMC", "NYSE",   "Honda Motor is NYSE:HMC, was wrongly set to SET"),
    ("JD",  "NASDAQ", "JD.com is NASDAQ:JD, was wrongly set to SET"),
]

# ── ลบหุ้น delisted / ข้อมูลผิด ────────────────────────────────────────────
# (symbol, reason)
TO_DELETE = [
    ("MAKRO",  "CPAXT already exists in DB; MAKRO = old name, delete duplicate"),
    ("INDORAMA","IVL already exists in DB; INDORAMA = wrong symbol, delete duplicate"),
    ("DTAC",   "merged with TRUE (2023), delisted"),
    ("ESSO",   "ESSO Thailand delisted"),
    ("ROBINS", "merged with CRC/Central, delisted"),
    ("K",      "Kellanova acquired by Mars (2024), delisted"),
    ("INTUCH", "GULF acquired INTUCH, delisted"),
    ("KBTG",   "KBTG is private (KBank tech subsidiary), never listed on SET"),
    ("GL",     "Group Lease suspended/delisted"),
    ("OISHI",  "ThaiBev took OISHI private, delisted"),
    ("NHP",    "delisted, no data found"),
    ("KPN",    "KPN Land delisted"),
    ("PRUKSA", "duplicate — PS is the correct SET symbol (both = PSH now)"),
]


class Command(BaseCommand):
    help = "แก้ไข symbol/exchange ผิด และลบหุ้น delisted ออกจาก DB"

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

        # ── 1. Rename symbol ────────────────────────────────────────────────
        self.stdout.write("--- Symbol renames ---")
        for old_sym, new_sym, reason in SYMBOL_RENAMES:
            try:
                obj = Symbol.objects.get(symbol=old_sym)
                price_count = PriceDaily.objects.filter(symbol=obj).count()
                if apply:
                    obj.symbol = new_sym
                    obj.save(update_fields=["symbol"])
                self.stdout.write(
                    f"  {'[RENAMED]' if apply else '[WOULD RENAME]'} "
                    f"{old_sym} -> {new_sym}  ({price_count} price rows preserved)  ({reason})"
                )
            except Symbol.DoesNotExist:
                self.stdout.write(f"  [SKIP]  {old_sym}: not in DB")

        # ── 2. Fix exchange ─────────────────────────────────────────────────
        self.stdout.write("\n--- Exchange fixes ---")
        for sym, new_exchange, reason in EXCHANGE_FIXES:
            try:
                obj = Symbol.objects.get(symbol=sym)
                old_exchange = obj.exchange
                if apply:
                    obj.exchange = new_exchange
                    obj.save(update_fields=["exchange"])
                self.stdout.write(
                    f"  {'[FIXED]' if apply else '[WOULD FIX]'} "
                    f"{sym}: exchange {old_exchange} -> {new_exchange}  ({reason})"
                )
            except Symbol.DoesNotExist:
                self.stdout.write(f"  [SKIP]  {sym}: not in DB")

        # ── 3. Delete delisted ──────────────────────────────────────────────
        self.stdout.write("\n--- Delete delisted ---")
        total_prices = 0
        deleted_count = 0
        for sym, reason in TO_DELETE:
            try:
                obj = Symbol.objects.get(symbol=sym)
                price_count = PriceDaily.objects.filter(symbol=obj).count()
                total_prices += price_count
                if apply:
                    obj.delete()  # cascade ลบ PriceDaily + Indicator + Signal ด้วย
                    deleted_count += 1
                self.stdout.write(
                    f"  {'[DELETED]' if apply else '[WOULD DELETE]'} "
                    f"{sym}: {price_count} price rows  ({reason})"
                )
            except Symbol.DoesNotExist:
                self.stdout.write(f"  [SKIP]  {sym}: not in DB")

        # ── สรุป ────────────────────────────────────────────────────────────
        self.stdout.write(f"\n{'='*55}")
        if apply:
            remaining = Symbol.objects.count()
            self.stdout.write(self.style.SUCCESS(
                f"Done.\n"
                f"  Renamed : {len(SYMBOL_RENAMES)} symbols\n"
                f"  Exchange: {len(EXCHANGE_FIXES)} fixed\n"
                f"  Deleted : {deleted_count} symbols (~{total_prices} price rows removed)\n"
                f"  Remaining in DB: {remaining} symbols"
            ))
        else:
            self.stdout.write(
                "No changes made. Run with --apply to execute."
            )
