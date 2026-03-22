"""
setup_timescaledb — Django Management Command
=============================================
คำสั่งสำหรับเปลี่ยนตาราง PriceDaily และ Indicator ให้เป็น TimescaleDB Hypertables

การใช้งาน:
    python manage.py setup_timescaledb
"""

import logging
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "เปลี่ยนตาราง Time-series ให้เป็น TimescaleDB Hypertables (ต้องการ PostgreSQL + TimescaleDB extension)"

    def handle(self, *args, **options):
        # 1. ตรวจสอบว่าใช้ PostgreSQL หรือไม่
        if connection.vendor != "postgresql":
            self.stdout.write(self.style.ERROR("⚠️  คำสั่งนี้รองรับเฉพาะ PostgreSQL เท่านั้น"))
            return

        # 2. รายชื่อตารางที่จะแปลงเป็น Hypertable
        tables = [
            ("radar_pricedaily", "date"),
            ("radar_indicator", "date"),
        ]

        self.stdout.write(self.style.MIGRATE_HEADING("=== กำลังตั้งค่า TimescaleDB Hypertables ==="))

        with connection.cursor() as cursor:
            # 3. เปิดใช้งาน TimescaleDB extension (ถ้ายังไม่มี)
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                self.stdout.write(self.style.SUCCESS("✅ Extension timescaledb พร้อมใช้งาน"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ ไม่สามารถสร้าง extension ได้: {e}"))
                return

            # 4. แปลงแต่ละตาราง
            for table_name, time_col in tables:
                try:
                    # ตรวจสอบก่อนว่าเป็น hypertable อยู่แล้วหรือไม่
                    cursor.execute(f"SELECT count(*) FROM timescaledb_information.hypertables WHERE hypertable_name = '{table_name}'")
                    is_hyper = cursor.fetchone()[0] > 0

                    if is_hyper:
                        self.stdout.write(self.style.WARNING(f"⏭️  ตาราง {table_name} เป็น Hypertable อยู่แล้ว"))
                        continue

                    # รันคำสั่งแปลง (ต้องใช้ migrate_data=True ถ้ามีข้อมูลอยู่แล้ว)
                    # ข้อควรระวัง: ตารางต้องไม่มี unique constraint ที่ไม่มี time column รวมอยู่ด้วย
                    # ในโมเดลเราใช้ unique_together = [("symbol", "date")] ซึ่งมี time column (date) อยู่แล้ว จึงทำได้
                    cursor.execute(f"SELECT create_hypertable('{table_name}', '{time_col}', migrate_data => True, if_not_exists => True);")
                    
                    self.stdout.write(self.style.SUCCESS(f"✅ แปลงตาราง {table_name} สำเร็จ"))
                    
                    # 5. เพิ่ม Data Retention Policy (ถ้าต้องการ)
                    # เช่น เก็บข้อมูลย้อนหลัง 5 ปี
                    cursor.execute(f"SELECT add_retention_policy('{table_name}', INTERVAL '5 years', if_not_exists => True);")
                    self.stdout.write(self.style.SUCCESS(f"✅ ตั้งค่า Retention Policy (5 ปี) สำหรับ {table_name}"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ เกิดข้อผิดพลาดกับตาราง {table_name}: {e}"))

        self.stdout.write(self.style.SUCCESS("\n=== ตั้งค่า TimescaleDB เสร็จสมบูรณ์ ==="))
