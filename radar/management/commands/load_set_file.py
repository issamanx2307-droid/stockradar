"""
load_set_file — โหลดหุ้น SET จากไฟล์ listedCompanies_th_TH.xls ของ SET

การใช้งาน:
    python manage.py load_set_file --file listedCompanies_th_TH.xls
"""

import io
import os
from django.core.management.base import BaseCommand, CommandError
from radar.models import Symbol


class Command(BaseCommand):
    help = "โหลดหุ้น SET ทั้งตลาดจากไฟล์ XLS ของ SET (listedCompanies_th_TH.xls)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="listedCompanies_th_TH.xls",
            help="path ของไฟล์ XLS จาก SET (default: listedCompanies_th_TH.xls)",
        )
        parser.add_argument(
            "--include-mai",
            action="store_true",
            default=True,
            help="รวมหุ้น mai ด้วย (default: True)",
        )

    def handle(self, *args, **options):
        import pandas as pd

        filepath = options["file"]

        # หาไฟล์ในหลายที่
        search_paths = [
            filepath,
            os.path.join(os.getcwd(), filepath),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))), filepath),
        ]

        found = None
        for p in search_paths:
            if os.path.exists(p):
                found = p
                break

        if not found:
            raise CommandError(
                f"ไม่พบไฟล์ '{filepath}'\n"
                f"กรุณาวางไฟล์ listedCompanies_th_TH.xls ใน D:\\stockradar\\"
            )

        self.stdout.write(f"📂 อ่านไฟล์: {found}")

        # อ่านไฟล์ด้วย encoding tis-620
        with open(found, 'rb') as f:
            content = f.read().decode('tis-620', errors='replace')

        df = pd.read_html(io.StringIO(content))[0]
        df = df.iloc[2:].reset_index(drop=True)
        df.columns = ['symbol','name','exchange','industry','sector','address','zipcode','tel','fax','website']

        # กรองตลาด
        exchanges = ['SET']
        if options["include_mai"]:
            exchanges.append('mai')

        df = df[df['exchange'].isin(exchanges)].copy()
        df['symbol'] = df['symbol'].astype(str).str.strip().str.upper()
        df = df[df['symbol'].str.len() <= 8]
        df = df[df['symbol'] != 'NAN']
        df = df[df['symbol'].str.match(r'^[A-Z0-9-]+$')]

        created = updated = 0

        self.stdout.write(f"📋 พบหุ้น: {len(df)} ตัว (SET: {len(df[df.exchange=='SET'])}, mai: {len(df[df.exchange=='mai'])})")

        for _, row in df.iterrows():
            sym      = str(row['symbol']).strip()
            exchange = str(row['exchange']).strip()
            # ใช้ symbol เป็น name ชั่วคราว เพราะ encoding ภาษาไทยผิด
            name     = sym
            sector   = "อื่นๆ"

            obj, was_created = Symbol.objects.update_or_create(
                symbol=sym,
                defaults={
                    "name":     name,
                    "exchange": exchange.upper() if exchange == "SET" else "SET",
                    "sector":   sector,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ เพิ่มใหม่: {created}  อัปเดต: {updated}  รวม: {Symbol.objects.filter(exchange='SET').count()} ตัว"
        ))
