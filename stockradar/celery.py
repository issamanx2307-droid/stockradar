"""
การตั้งค่า Celery สำหรับ background tasks
เช่น โหลดราคาหุ้น, คำนวณ indicator
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockradar.settings")

app = Celery("stockradar")
app.config_from_object("django.conf:settings", namespace="CELERY")

# โหลด tasks จากทุก Django app อัตโนมัติ
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Celery Beat — ตั้งเวลา tasks อัตโนมัติ
# ---------------------------------------------------------------------------

from celery.schedules import crontab  # noqa: E402

app.conf.beat_schedule = {
    # โหลดราคาหุ้นหลังตลาดปิด (จ-ศ 18:00 น. เวลาไทย)
    "โหลดราคาหุ้นรายวัน": {
        "task": "radar.tasks.load_all_prices",
        "schedule": crontab(hour=18, minute=0, day_of_week="1-5"),
    },
    # คำนวณ indicator หลังโหลดราคาเสร็จ (18:30 น.)
    "คำนวณ-indicator-รายวัน": {
        "task": "radar.tasks.calculate_all_indicators",
        "schedule": crontab(hour=18, minute=30, day_of_week="1-5"),
    },
    # สร้าง signal (19:00 น.)
    "สร้าง-signal-รายวัน": {
        "task": "radar.tasks.generate_all_signals",
        "schedule": crontab(hour=19, minute=0, day_of_week="1-5"),
    },
    # Refresh Materialized View หลัง signal เสร็จ (19:15 น.)
    "refresh-snapshot-รายวัน": {
        "task": "radar.tasks.refresh_latest_snapshot",
        "schedule": crontab(hour=19, minute=15, day_of_week="1-5"),
    },
}
