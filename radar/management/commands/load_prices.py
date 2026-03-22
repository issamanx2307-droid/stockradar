"""
คำสั่ง Django สำหรับโหลดราคาหุ้นจาก Yahoo Finance

การใช้งาน:
    python manage.py load_prices                        # โหลดทุกหุ้น
    python manage.py load_prices --symbol PTT           # โหลดเฉพาะ PTT
    python manage.py load_prices --exchange SET         # โหลดเฉพาะหุ้นไทย
    python manage.py load_prices --days 90              # โหลดย้อนหลัง 90 วัน
    python manage.py load_prices --full                 # โหลดย้อนหลัง 5 ปี
"""

import logging
import time
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from radar.models import Symbol, PriceDaily

logger = logging.getLogger(__name__)


def get_yahoo_ticker(symbol: str, exchange: str) -> str:
    """แปลง symbol เป็น Yahoo Finance ticker format"""
    if exchange == "SET":
        return f"{symbol}.BK"       # หุ้นไทย: PTT.BK
    return symbol                   # US: AAPL, MSFT ฯลฯ


def fetch_prices_batch(tickers: list[str], start: date, end: date) -> dict:
    """
    ดึงราคาหุ้นหลายตัวพร้อมกันผ่าน yfinance.download
    คืนค่า dict {ticker: rows_list}
    """
    try:
        import yfinance as yf
    except ImportError:
        raise CommandError("ต้องติดตั้ง yfinance ก่อน: pip install yfinance")

    if not tickers:
        return {}

    # yfinance download คืนค่าเป็น MultiIndex DataFrame ถ้ามีหลาย ticker
    df = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        group_by='ticker',
        auto_adjust=True,
        threads=True, # ใช้ multi-threading
    )

    if df.empty:
        return {}

    results = {}
    
    # กรณี ticker เดียว df จะไม่มี MultiIndex ระดับบนสุดเป็น ticker
    if len(tickers) == 1:
        t = tickers[0]
        results[t] = _process_df_rows(df)
        return results

    for ticker in tickers:
        if ticker not in df.columns.levels[0]:
            continue
        ticker_df = df[ticker]
        results[ticker] = _process_df_rows(ticker_df)
        
    return results

def _process_df_rows(df) -> list[dict]:
    """Helper แปลง DF เป็น list of dict"""
    rows = []
    for idx, row in df.iterrows():
        if pd.isna(row["Close"]) or row["Close"] == 0:
            continue
        rows.append({
            "date": idx.date() if hasattr(idx, "date") else idx,
            "open": Decimal(str(round(float(row["Open"]), 4))),
            "high": Decimal(str(round(float(row["High"]), 4))),
            "low": Decimal(str(round(float(row["Low"]), 4))),
            "close": Decimal(str(round(float(row["Close"]), 4))),
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
        })
    return rows

import pandas as pd


class Command(BaseCommand):
    help = "โหลดราคาหุ้นรายวันจาก Yahoo Finance เข้าฐานข้อมูล"

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            default=None,
            help="โหลดเฉพาะหุ้นที่ระบุ เช่น PTT หรือ AAPL",
        )
        parser.add_argument(
            "--exchange",
            type=str,
            choices=["SET", "NASDAQ", "NYSE", "US"],
            default=None,
            help="โหลดเฉพาะตลาดที่ระบุ",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "PRICE_HISTORY_DAYS", 365),
            help="จำนวนวันย้อนหลังที่จะโหลด (default: 365)",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="โหลดข้อมูลย้อนหลัง 5 ปี",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=getattr(settings, "PRICE_LOAD_BATCH_SIZE", 50),
            help="จำนวนหุ้นที่โหลดพร้อมกัน (default: 50)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.3,
            help="หน่วงเวลาระหว่างแต่ละหุ้น (วินาที) เพื่อไม่ให้ถูก rate-limit",
        )

    def handle(self, *args, **options):
        # คำนวณช่วงวันที่
        end_date = date.today()
        if options["full"]:
            start_date = end_date - timedelta(days=365 * 5)
        else:
            start_date = end_date - timedelta(days=options["days"])

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== โหลดราคาหุ้น {start_date} ถึง {end_date} ==="
        ))

        # เลือกหุ้นที่จะโหลด
        qs = Symbol.objects.all()

        if options["symbol"]:
            sym = options["symbol"].upper()
            qs = qs.filter(symbol=sym)
            if not qs.exists():
                raise CommandError(f"ไม่พบหุ้น '{sym}' ในฐานข้อมูล")

        if options["exchange"]:
            exch = options["exchange"].upper()
            if exch == "US":
                qs = qs.filter(exchange__in=["NASDAQ", "NYSE"])
            else:
                qs = qs.filter(exchange=exch)

        symbols = list(qs.order_by("symbol"))
        total = len(symbols)

        if total == 0:
            self.stdout.write(self.style.WARNING("⚠️  ไม่พบหุ้นที่ตรงเงื่อนไข"))
            return

        self.stdout.write(f"จะโหลดราคาหุ้นทั้งหมด {total} ตัว (Batch size: {options['batch']})\n")

        success = 0
        failed = 0
        skipped = 0
        
        # แบ่งเป็น batches
        batch_size = options["batch"]
        for i in range(0, total, batch_size):
            batch_syms = symbols[i:i + batch_size]
            ticker_map = {get_yahoo_ticker(s.symbol, s.exchange): s for s in batch_syms}
            tickers = list(ticker_map.keys())
            
            progress = f"[{i+len(batch_syms)}/{total}]"
            
            try:
                batch_data = fetch_prices_batch(tickers, start_date, end_date)
                
                for ticker, rows in batch_data.items():
                    sym_obj = ticker_map.get(ticker)
                    if not sym_obj: continue
                    
                    if not rows:
                        skipped += 1
                        continue
                        
                    saved = self._save_prices(sym_obj, rows)
                    self.stdout.write(f"  ✅ {sym_obj.symbol} — {saved} วัน")
                    success += 1
                
                # ตัวที่ไม่มีข้อมูลใน batch_data
                for ticker, sym_obj in ticker_map.items():
                    if ticker not in batch_data:
                        self.stdout.write(self.style.WARNING(f"  ⏭️ {sym_obj.symbol} — ไม่มีข้อมูล"))
                        skipped += 1

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ❌ Batch {progress} ล้มเหลว: {exc}"))
                failed += len(batch_syms)

            if i + batch_size < total:
                time.sleep(options["delay"])

        # สรุปผล
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✅ สำเร็จ: {success}  ❌ ล้มเหลว: {failed}  ⏭️  ข้าม: {skipped}"
        ))

    # ------------------------------------------------------------------
    # บันทึกราคาเข้าฐานข้อมูล
    # ------------------------------------------------------------------

    @transaction.atomic
    def _save_prices(self, sym_obj: Symbol, rows: list[dict]) -> int:
        """
        บันทึกราคาหุ้นเข้าฐานข้อมูลแบบ upsert
        คืนจำนวนแถวที่บันทึก
        """
        saved = 0

        for row in rows:
            _, created = PriceDaily.objects.update_or_create(
                symbol=sym_obj,
                date=row["date"],
                defaults={
                    "open":   row["open"],
                    "high":   row["high"],
                    "low":    row["low"],
                    "close":  row["close"],
                    "volume": row["volume"],
                },
            )
            saved += 1

        return saved
