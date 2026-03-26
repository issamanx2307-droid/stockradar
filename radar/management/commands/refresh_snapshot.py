"""
Management Command: refresh_snapshot
ใช้ REFRESH MATERIALIZED VIEW CONCURRENTLY เพื่ออัปเดต radar_latest_snapshot
โดยไม่ lock ตาราง (ผู้ใช้ยังอ่านได้ระหว่าง refresh)

Usage:
    python manage.py refresh_snapshot
"""
import time
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Refresh Materialized View: radar_latest_snapshot"

    def handle(self, *args, **options):
        self.stdout.write("🔄 Refreshing radar_latest_snapshot ...")
        t0 = time.time()
        with connection.cursor() as cur:
            # CONCURRENTLY = ไม่ lock ขณะ refresh (ต้องมี UNIQUE INDEX)
            cur.execute(
                "REFRESH MATERIALIZED VIEW CONCURRENTLY radar_latest_snapshot;"
            )
        elapsed = round(time.time() - t0, 2)
        self.stdout.write(
            self.style.SUCCESS(f"✅ Refreshed in {elapsed}s")
        )
