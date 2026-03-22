import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from radar.models import Symbol

class Command(BaseCommand):
    help = "โหลดรายชื่อหุ้นเข้าฐานข้อมูล (หุ้นไทย SET + หุ้น US)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--exchange",
            type=str,
            choices=["SET", "NASDAQ", "NYSE", "US", "ALL"],
            default="ALL",
            help="เลือกตลาดที่ต้องการโหลด (default: ALL)",
        )
        parser.add_argument(
            "--csv",
            type=str,
            default="symbols.csv", # ตั้งค่า default เป็น symbols.csv ตามที่คุณใช้งาน
            help="path ของไฟล์ CSV",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="อัปเดตข้อมูลหุ้นที่มีอยู่แล้ว",
        )

    def handle(self, *args, **options):
        exchange = options["exchange"]
        csv_path = options["csv"]
        do_update = options["update"]

        self.stdout.write(self.style.MIGRATE_HEADING("===เริ่มโหลดรายชื่อหุ้น ==="))

        # ตรวจสอบว่ามีไฟล์ CSV หรือไม่ ถ้ามีให้โหลดจาก CSV ถ้าไม่มีให้ใช้ค่าเริ่มต้น
        path = Path(csv_path)
        if path.exists():
            self._load_from_csv(csv_path, do_update)
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ ไม่พบไฟล์ {csv_path} ระบบจะใช้ข้อมูลหุ้นตัวอย่างแทน"))
            self._load_defaults(exchange, do_update)

    def _load_defaults(self, exchange: str, do_update: bool):
        # ข้อมูลหุ้นตัวอย่างจากไฟล์ที่คุณส่งมา
        DEFAULT_SET_SYMBOLS = [
            ("PTT", "ปตท. จำกัด (มหาชน)", "พลังงาน"),
            ("PTTEP", "ปตท. สำรวจและผลิตปิโตรเลียม", "พลังงาน"),
            ("ADVANC", "แอดวานซ์ อินโฟร์ เซอร์วิส", "เทคโนโลยี"),
            ("KBANK", "ธนาคารกสิกรไทย", "การเงิน"),
            # ... เพิ่มเติมได้ตามไฟล์เดิมของคุณ ...
        ]
        
        created_count = updated_count = skipped_count = 0
        symbols_to_load = []

        if exchange in ("SET", "ALL"):
            for sym, name, sector in DEFAULT_SET_SYMBOLS:
                symbols_to_load.append({"symbol": sym, "name": name, "exchange": "SET", "sector": sector})

        for data in symbols_to_load:
            obj, created = Symbol.objects.get_or_create(symbol=data["symbol"], defaults=data)
            if created:
                created_count += 1
            elif do_update:
                for field, value in data.items(): setattr(obj, field, value)
                obj.save()
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ เพิ่มใหม่: {created_count}  🔄 อัปเดต: {updated_count}  ⏭️ ข้าม: {skipped_count}"))

    def _load_from_csv(self, csv_path: str, do_update: bool):
        created = updated = skipped = 0
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data = {
                    "symbol": row["symbol"].strip().upper(),
                    "name": row["name"].strip(),
                    "exchange": row["exchange"].strip().upper(),
                    "sector": row["sector"].strip(),
                }
                obj, was_created = Symbol.objects.get_or_create(symbol=data["symbol"], defaults=data)
                if was_created:
                    created += 1
                elif do_update:
                    for field, value in data.items(): setattr(obj, field, value)
                    obj.save()
                    updated += 1
                else:
                    skipped += 1
        self.stdout.write(self.style.SUCCESS(f"✅ โหลดจาก CSV สำเร็จ - เพิ่มใหม่: {created}  อัปเดต: {updated}"))