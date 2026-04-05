"""
ดึงราคาหุ้น US จาก Alpaca Market Data API → เก็บลง PriceDaily + คำนวณ Indicators

การใช้งาน:
    python manage.py fetch_us_prices                    # ดึง US ทั้งหมด 120 วัน
    python manage.py fetch_us_prices --symbol AAPL      # ดึงเฉพาะ AAPL
    python manage.py fetch_us_prices --days 365         # ย้อนหลัง 365 วัน
    python manage.py fetch_us_prices --batch 20         # batch ละ 20 symbols
    python manage.py fetch_us_prices --no-indicators    # ไม่คำนวณ indicators
"""

import logging
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from radar.models import Symbol, PriceDaily

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "ดึงราคาหุ้น US จาก Alpaca แล้วเก็บลง PriceDaily + คำนวณ Indicators"

    def add_arguments(self, parser):
        parser.add_argument("--symbol", type=str, help="ดึงเฉพาะ symbol เดียว เช่น AAPL")
        parser.add_argument("--days", type=int, default=120, help="จำนวนวันย้อนหลัง (default 120)")
        parser.add_argument("--batch", type=int, default=10, help="จำนวน symbols ต่อ batch (default 10)")
        parser.add_argument("--no-indicators", action="store_true", help="ข้ามการคำนวณ indicators")

    def handle(self, *args, **options):
        from radar import alpaca_service

        symbol_arg = options["symbol"]
        days = options["days"]
        batch_size = options["batch"]
        skip_indicators = options["no_indicators"]

        # ── ดึง symbols ──────────────────────────────────────────────────────
        if symbol_arg:
            symbols = list(Symbol.objects.filter(symbol=symbol_arg.upper()))
            if not symbols:
                self.stderr.write(f"ไม่พบ symbol '{symbol_arg}' ในระบบ")
                return
        else:
            symbols = list(
                Symbol.objects.filter(exchange__in=["NASDAQ", "NYSE"])
                .order_by("symbol")
            )

        total = len(symbols)
        self.stdout.write(f"ดึงราคา US จาก Alpaca: {total} symbols, {days} วันย้อนหลัง")

        start_date = date.today() - timedelta(days=days)
        total_saved = 0
        total_ind = 0
        errors = []

        # ── ดึงทีละ batch ────────────────────────────────────────────────────
        for i in range(0, total, batch_size):
            batch = symbols[i : i + batch_size]
            batch_symbols = [s.symbol for s in batch]
            sym_map = {s.symbol: s for s in batch}

            self.stdout.write(
                f"  batch {i // batch_size + 1}: {', '.join(batch_symbols)}"
            )

            try:
                bars_data = alpaca_service.get_bars_multi(
                    symbols=batch_symbols,
                    timeframe="1Day",
                    start=start_date,
                    limit=days + 50,  # เผื่อวันหยุด
                )
            except Exception as e:
                msg = f"Alpaca API error for batch {batch_symbols}: {e}"
                logger.error(msg)
                errors.append(msg)
                continue

            # ── บันทึกแต่ละ symbol ────────────────────────────────────────────
            for sym_str, bars in bars_data.items():
                sym_obj = sym_map.get(sym_str)
                if not sym_obj:
                    continue

                rows = self._bars_to_rows(bars)
                if not rows:
                    continue

                saved = self._save_prices(sym_obj, rows)
                total_saved += saved

                # คำนวณ indicators
                if not skip_indicators:
                    try:
                        from radar.indicator_engine import run_indicator_engine
                        result = run_indicator_engine(sym_obj)
                        total_ind += result.get("saved", 0)
                    except Exception as e:
                        logger.warning("Indicator error %s: %s", sym_str, e)

            # rate limit: Alpaca free = 200 req/min
            if i + batch_size < total:
                time.sleep(0.5)

        # ── สรุป ─────────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"\nสำเร็จ: {total_saved} price rows, {total_ind} indicator rows"
        ))
        if errors:
            self.stdout.write(self.style.WARNING(f"Errors: {len(errors)}"))
            for e in errors:
                self.stdout.write(f"  - {e}")

    def _bars_to_rows(self, bars: list[dict]) -> list[dict]:
        """แปลง Alpaca bars → list of dict สำหรับ PriceDaily"""
        rows = []
        for b in bars:
            ts = b.get("t", "")
            if not ts:
                continue
            try:
                d = date.fromisoformat(ts[:10])
                rows.append({
                    "date":   d,
                    "open":   Decimal(str(b["o"])),
                    "high":   Decimal(str(b["h"])),
                    "low":    Decimal(str(b["l"])),
                    "close":  Decimal(str(b["c"])),
                    "volume": int(b.get("v", 0)),
                })
            except (KeyError, ValueError, InvalidOperation) as e:
                logger.debug("Skip bar %s: %s", ts, e)
        return rows

    @transaction.atomic
    def _save_prices(self, sym_obj: Symbol, rows: list[dict]) -> int:
        """Bulk upsert ราคาเข้า PriceDaily"""
        existing_dates = set(
            PriceDaily.objects.filter(
                symbol=sym_obj,
                date__in=[r["date"] for r in rows],
            ).values_list("date", flat=True)
        )

        to_create = []
        to_update_rows = []

        for row in rows:
            if row["date"] in existing_dates:
                to_update_rows.append(row)
            else:
                to_create.append(PriceDaily(
                    symbol=sym_obj,
                    date=row["date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                ))

        created = 0
        if to_create:
            PriceDaily.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
            created = len(to_create)

        updated = 0
        for row in to_update_rows:
            PriceDaily.objects.filter(symbol=sym_obj, date=row["date"]).update(
                open=row["open"], high=row["high"], low=row["low"],
                close=row["close"], volume=row["volume"],
            )
            updated += 1

        return created + updated
