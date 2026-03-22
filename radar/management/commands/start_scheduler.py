"""
Auto Scheduler — รันอัตโนมัติทุกวัน ไม่ต้องสั่งเอง
=================================================
ทำงาน:
  18:00 น. — โหลดราคาหุ้นไทย (SET หลังตลาดปิด 17:00)
  18:30 น. — โหลดราคาหุ้น US (ตลาด US ยังเปิด แต่อัปข้อมูลล่าสุด)
  21:30 น. — โหลดราคาหุ้น US อีกครั้ง (ตลาด US ปิด 04:00 ไทย)
  22:00 น. — คำนวณ Indicator ทั้งหมด
  22:30 น. — สร้าง Signal ทั้งหมด

วิธีเริ่ม:
  python manage.py start_scheduler
"""

import logging
import threading
import time
from datetime import datetime, date, timedelta

import pytz
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

BANGKOK_TZ = pytz.timezone("Asia/Bangkok")


def _now_bkk() -> datetime:
    return datetime.now(BANGKOK_TZ)


def _is_weekday() -> bool:
    """จันทร์–ศุกร์เท่านั้น"""
    return _now_bkk().weekday() < 5


def _run_load_prices(exchange: str, days: int = 3):
    """โหลดราคาย้อนหลัง N วัน (default 3 วัน เพื่อแก้ missing data)"""
    try:
        from django.core.management import call_command
        logger.info("📥 โหลดราคา %s...", exchange)
        call_command("load_prices", exchange=exchange, days=days)
        logger.info("✅ โหลดราคา %s เสร็จ", exchange)
    except Exception as e:
        logger.error("❌ โหลดราคา %s ล้มเหลว: %s", exchange, e)


def _run_indicators():
    try:
        from django.core.management import call_command
        logger.info("📊 คำนวณ Indicator...")
        call_command("run_engine", mode="indicators")
        logger.info("✅ คำนวณ Indicator เสร็จ")
    except Exception as e:
        logger.error("❌ คำนวณ Indicator ล้มเหลว: %s", e)


def _run_signals():
    try:
        from django.core.management import call_command
        logger.info("🔔 สร้าง Signal...")
        call_command("run_engine", mode="signals")
        logger.info("✅ สร้าง Signal เสร็จ")
    except Exception as e:
        logger.error("❌ สร้าง Signal ล้มเหลว: %s", e)


def _run_fetch_news():
    try:
        from radar.news_fetcher import fetch_and_save_news
        logger.info("📰 ดึงข่าว RSS...")
        stats = fetch_and_save_news(max_per_feed=50)
        logger.info("✅ ข่าว: บันทึก %d รายการ", stats.get("saved", 0))
    except Exception as e:
        logger.error("❌ ดึงข่าวล้มเหลว: %s", e)


# ── ตารางเวลา Tasks ──────────────────────────────────────────────────────────

SCHEDULE = [
    # (ชั่วโมง, นาที, ฟังก์ชัน, args, kwargs, ชื่อ)
    (8,   0, _run_fetch_news,  [],        {},           "ดึงข่าวเช้า"),
    (10,  0, _run_fetch_news,  [],        {},           "ดึงข่าวสาย"),
    (12,  0, _run_fetch_news,  [],        {},           "ดึงข่าวเที่ยง"),
    (15,  0, _run_fetch_news,  [],        {},           "ดึงข่าวบ่าย"),
    (18,  0, _run_load_prices, ["SET"],   {"days": 3},  "โหลดราคาหุ้นไทย"),
    (18, 30, _run_load_prices, ["US"],    {"days": 3},  "โหลดราคาหุ้น US (ระหว่างวัน)"),
    (18, 30, _run_fetch_news,  [],        {},           "ดึงข่าวเย็น"),
    (22,  0, _run_load_prices, ["SET"],   {"days": 3},  "โหลดราคาหุ้นไทย (รอบ 2)"),
    (22, 30, _run_load_prices, ["US"],    {"days": 3},  "โหลดราคาหุ้น US (ปิดตลาด)"),
    (22, 30, _run_fetch_news,  [],        {},           "ดึงข่าวดึก"),
    (23,  0, _run_indicators,  [],        {},           "คำนวณ Indicator"),
    (23, 30, _run_signals,     [],        {},           "สร้าง Signal"),
]


def scheduler_loop():
    """
    Loop หลัก — ตรวจสอบทุก 60 วินาที ว่าถึงเวลารัน task ไหนหรือยัง
    """
    last_run: dict[str, date] = {}   # ป้องกันรัน task ซ้ำในวันเดียวกัน

    logger.info("🚀 Auto Scheduler เริ่มทำงาน")

    while True:
        now  = _now_bkk()
        today = now.date()

        if _is_weekday():
            for hour, minute, func, args, kwargs, name in SCHEDULE:
                key = f"{name}_{today}"

                # ถึงเวลาแล้ว และยังไม่ได้รันวันนี้
                if now.hour == hour and now.minute >= minute and key not in last_run:
                    last_run[key] = today
                    logger.info("⏰ ถึงเวลา: %s", name)

                    # รันใน thread แยก ไม่บล็อก scheduler
                    t = threading.Thread(
                        target=func,
                        args=args,
                        kwargs=kwargs,
                        name=name,
                        daemon=True,
                    )
                    t.start()

        # ล้าง last_run ของวันเก่า
        old_keys = [k for k, v in last_run.items() if v < today]
        for k in old_keys:
            del last_run[k]

        time.sleep(60)  # ตรวจทุก 1 นาที


class Command(BaseCommand):
    help = "เปิด Auto Scheduler — โหลดราคา/คำนวณ indicator/สร้าง signal อัตโนมัติทุกวัน"

    def add_arguments(self, parser):
        parser.add_argument(
            "--background",
            action="store_true",
            help="รันใน background thread (ใช้กับ runserver)",
        )
        parser.add_argument(
            "--run-now",
            action="store_true",
            help="รัน pipeline ทันทีโดยไม่รอเวลา",
        )

    def handle(self, *args, **options):
        if options["run_now"]:
            self._run_full_pipeline()
            return

        if options["background"]:
            t = threading.Thread(target=scheduler_loop, daemon=True, name="AutoScheduler")
            t.start()
            self.stdout.write(self.style.SUCCESS(
                "✅ Auto Scheduler รันใน background แล้ว"
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            "=== Auto Scheduler เริ่มทำงาน (กด Ctrl+C เพื่อหยุด) ==="
        ))
        self.stdout.write("\nตารางเวลา:")
        for h, m, _, _, _, name in SCHEDULE:
            self.stdout.write(f"  {h:02d}:{m:02d} น. — {name}")
        self.stdout.write("")

        try:
            scheduler_loop()
        except KeyboardInterrupt:
            self.stdout.write("\n🛑 หยุด Scheduler แล้ว")

    def _run_full_pipeline(self):
        """รัน pipeline ทั้งหมดทันที"""
        self.stdout.write(self.style.MIGRATE_HEADING("=== รัน Full Pipeline ทันที ==="))

        self.stdout.write("📥 โหลดราคาหุ้นไทย...")
        _run_load_prices("SET", days=1095)  # 3 ปี

        self.stdout.write("📥 โหลดราคาหุ้น US...")
        _run_load_prices("US", days=1095)   # 3 ปี

        self.stdout.write("📊 คำนวณ Indicator...")
        _run_indicators()

        self.stdout.write("🔔 สร้าง Signal...")
        _run_signals()

        self.stdout.write(self.style.SUCCESS("✅ Pipeline เสร็จสมบูรณ์"))
