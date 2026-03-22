"""
setup_system — ดึงหุ้นจากตลาดจริงทั้งหมด คำนวณทุกตัว

ขั้นตอน:
  1. ดึงรายชื่อจากตลาดจริง (SET + S&P500 + NASDAQ100 + NYSE)
  2. โหลดราคา 3 ปีทุกตัว
  3. คำนวณ Indicator ทุกตัว
  4. สร้าง Signal ทุกตัว (เก็บทุก score)
  → Scanner กรองที่คะแนน ≥ 70 หรือ ≥ 80 ได้เอง
"""

import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Setup ระบบ — ดึงหุ้นทั้งตลาดจริง คำนวณทุกตัว"

    def add_arguments(self, parser):
        parser.add_argument("--force",  action="store_true", help="รีเซ็ตและโหลดใหม่ทั้งหมด")
        parser.add_argument("--update", action="store_true", help="อัปเดตหุ้นใหม่ + ราคาล่าสุด")
        parser.add_argument("--days",   type=int, default=1825, help="วันย้อนหลัง (default: 1825 = 5 ปี)")

    def handle(self, *args, **options):
        from radar.models import Symbol, PriceDaily, Indicator, Signal

        force  = options["force"]
        update = options["update"]
        days   = options["days"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n╔══════════════════════════════════════════╗\n"
            "║  📡 Radar หุ้น — Setup ระบบอัตโนมัติ    ║\n"
            "╚══════════════════════════════════════════╝\n"
        ))

        sym_count = Symbol.objects.count()

        # ── Step 1: ดึงรายชื่อหุ้นจากตลาดจริง ──
        if sym_count < 500 or force or update:
            self.stdout.write("📋 Step 1 — ดึงรายชื่อหุ้นจากตลาดจริง")
            self.stdout.write("   SET + S&P500 + NASDAQ100 + NYSE\n")
            created = self._fetch_and_save_symbols(force)
            self.stdout.write(self.style.SUCCESS(
                f"   ✅ หุ้นในระบบ: {Symbol.objects.count():,} ตัว (เพิ่มใหม่: {created})\n"
            ))
        else:
            self.stdout.write(f"✅ Step 1 — มีหุ้น {sym_count:,} ตัวแล้ว (ข้าม)\n")

        # ── Step 2: โหลดราคา ──
        price_count = PriceDaily.objects.count()
        if price_count < 10000 or force or update:
            self.stdout.write(f"📥 Step 2 — โหลดราคา {days} วัน ทุกหุ้น")
            self.stdout.write("   อาจใช้เวลา 30-90 นาที\n")
            self.stdout.write("   🇹🇭 โหลดราคาหุ้นไทย SET...")
            call_command("load_prices", exchange="SET", days=days)
            self.stdout.write("   🇺🇸 โหลดราคาหุ้น US...")
            call_command("load_prices", exchange="US", days=days)
            self.stdout.write(self.style.SUCCESS(
                f"   ✅ ราคา: {PriceDaily.objects.count():,} แถว\n"
            ))
        else:
            self.stdout.write(f"✅ Step 2 — มีราคา {price_count:,} แถวแล้ว (ข้าม)\n")

        # ── Step 3: คำนวณ Indicator ──
        ind_count = Indicator.objects.count()
        if ind_count < 1000 or force or update:
            self.stdout.write("📊 Step 3 — คำนวณ Indicator ทุกหุ้น...")
            call_command("run_engine", mode="indicators")
            self.stdout.write(self.style.SUCCESS(
                f"   ✅ Indicator: {Indicator.objects.count():,} แถว\n"
            ))
        else:
            self.stdout.write(f"✅ Step 3 — มี Indicator {ind_count:,} แถวแล้ว (ข้าม)\n")

        # ── Step 4: สร้าง Signal ทุกตัว ──
        self.stdout.write("🔔 Step 4 — สร้าง Signal ทุกหุ้น...")
        call_command("run_engine", mode="signals")
        self.stdout.write(self.style.SUCCESS(
            f"   ✅ Signal: {Signal.objects.count():,} รายการ\n"
        ))

        # ── สรุป ──
        self.stdout.write(self.style.SUCCESS(
            "╔══════════════════════════════════════════╗\n"
            "║   ✅ Setup เสร็จสมบูรณ์!                 ║\n"
            f"║   หุ้น:      {Symbol.objects.count():>7,} ตัว                ║\n"
            f"║   ราคา:      {PriceDaily.objects.count():>7,} แถว               ║\n"
            f"║   Indicator: {Indicator.objects.count():>7,} แถว               ║\n"
            f"║   Signal:    {Signal.objects.count():>7,} รายการ            ║\n"
            "╠══════════════════════════════════════════╣\n"
            "║   Scanner: กรองคะแนน ≥ 70 หรือ ≥ 80    ║\n"
            "╚══════════════════════════════════════════╝\n"
        ))

    def _fetch_and_save_symbols(self, force: bool) -> int:
        from radar.models import Symbol
        from radar.market_fetcher import fetch_all_markets, _read_set_xls
        import os

        if force:
            Symbol.objects.all().delete()

        all_symbols = []
        seen = set()

        # ── 1. SET จากไฟล์ XLS (ครบทั้งตลาด ~800 ตัว) ──
        xls_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))),
            "stockradar", "listedCompanies_th_TH.xls"
        )
        if os.path.exists(xls_path):
            self.stdout.write(f"   📂 พบไฟล์ SET XLS: {xls_path}")
            set_symbols = _read_set_xls(xls_path)
            for s in set_symbols:
                sym = s["symbol"]
                if sym not in seen:
                    seen.add(sym)
                    all_symbols.append(s)
            self.stdout.write(f"   ✅ SET จากไฟล์: {len(set_symbols)} ตัว")
        else:
            self.stdout.write("   ⚠️  ไม่พบไฟล์ XLS — ดึง SET จาก Wikipedia แทน")

        # ── 2. US + SET เพิ่มเติมจาก Wikipedia (S&P500, NASDAQ100, NYSE) ──
        market_symbols = fetch_all_markets()
        added_from_web = 0
        for s in market_symbols:
            sym = s["symbol"].strip().upper()
            if sym and sym not in seen and len(sym) <= 10:
                seen.add(sym)
                all_symbols.append(s)
                added_from_web += 1
        self.stdout.write(f"   ✅ เพิ่มจาก Wikipedia: {added_from_web} ตัว")

        # ── บันทึกลง DB ──
        created = 0
        for data in all_symbols:
            _, was_created = Symbol.objects.get_or_create(
                symbol=data["symbol"],
                defaults={
                    "name":     data.get("name",     data["symbol"]),
                    "exchange": data.get("exchange", "OTHER"),
                    "sector":   data.get("sector",   "อื่นๆ"),
                },
            )
            if was_created:
                created += 1
        return created
