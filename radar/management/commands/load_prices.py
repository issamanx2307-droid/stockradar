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


_YF_SESSION = None   # shared session + crumb cache


def _get_yf_session():
    """
    สร้าง session พร้อม cookie + crumb จาก Yahoo Finance จริงๆ
    ทำให้ request ผ่านได้แม้อยู่บน VPS
    """
    global _YF_SESSION
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://finance.yahoo.com/",
    })

    # ขอ cookie จาก Yahoo Finance homepage
    try:
        session.get("https://finance.yahoo.com", timeout=10)
    except Exception:
        pass

    # ขอ crumb
    crumb = None
    try:
        r = session.get(
            "https://query2.finance.yahoo.com/v1/test/getcrumb",
            timeout=10,
        )
        if r.status_code == 200 and r.text and "<" not in r.text:
            crumb = r.text.strip()
    except Exception:
        pass

    _YF_SESSION = (session, crumb)
    return session, crumb


def _fetch_yahoo_direct(ticker: str, start: date, end: date) -> "pd.DataFrame | None":
    """ดึงข้อมูลจาก Yahoo Finance Chart API โดยตรง (ไม่ผ่าน yfinance library)"""
    import requests

    session, crumb = _get_yf_session()
    start_ts = int(time.mktime(start.timetuple()))
    end_ts   = int(time.mktime(end.timetuple())) + 86400

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={start_ts}&period2={end_ts}&interval=1d&events=history"
    )
    if crumb:
        url += f"&crumb={crumb}"

    for attempt in range(3):
        try:
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue
            data = r.json()
            result = data.get("chart", {}).get("result")
            if not result:
                break
            result = result[0]
            timestamps = result.get("timestamp", [])
            ohlcv = result.get("indicators", {}).get("quote", [{}])[0]
            adjclose = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])

            rows = []
            for i, ts in enumerate(timestamps):
                try:
                    close = adjclose[i] if adjclose else ohlcv.get("close", [])[i]
                    if close is None:
                        continue
                    rows.append({
                        "date":   date.fromtimestamp(ts),
                        "open":   Decimal(str(round(float(ohlcv.get("open",  [])[i] or close), 4))),
                        "high":   Decimal(str(round(float(ohlcv.get("high",  [])[i] or close), 4))),
                        "low":    Decimal(str(round(float(ohlcv.get("low",   [])[i] or close), 4))),
                        "close":  Decimal(str(round(float(close), 4))),
                        "volume": int(ohlcv.get("volume", [])[i] or 0),
                    })
                except (IndexError, TypeError):
                    continue
            return rows
        except Exception:
            time.sleep(2 ** attempt)

    return None


def _fetch_stooq(ticker: str, start: date, end: date) -> list | None:
    """
    Fallback: ดึงข้อมูลจาก Stooq.com (ฟรี ไม่ต้องการ API key ไม่บล็อก VPS)
    Ticker format: AAPL.US, MSFT.US, PTT.BK
    """
    try:
        import pandas_datareader.data as web
        # แปลง ticker format: AAPL → AAPL.US, PTT.BK → PTT.BK
        stooq_ticker = ticker if "." in ticker else f"{ticker}.US"
        df = web.DataReader(stooq_ticker, "stooq", start=start, end=end)
        if df is None or df.empty:
            return None
        df = df.sort_index()
        rows = []
        for idx, row in df.iterrows():
            close = row.get("Close")
            if close is None or float(close) == 0:
                continue
            rows.append({
                "date":   idx.date() if hasattr(idx, "date") else idx,
                "open":   Decimal(str(round(float(row.get("Open",  close)), 4))),
                "high":   Decimal(str(round(float(row.get("High",  close)), 4))),
                "low":    Decimal(str(round(float(row.get("Low",   close)), 4))),
                "close":  Decimal(str(round(float(close), 4))),
                "volume": int(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 0,
            })
        return rows if rows else None
    except Exception:
        return None


def fetch_prices_batch(tickers: list[str], start: date, end: date) -> dict:
    """
    ดึงราคาหุ้นทีละตัว
    1. ลอง Yahoo Finance Chart API โดยตรง (cookie + crumb)
    2. ถ้าล้มเหลว → fallback ไป Stooq
    """
    if not tickers:
        return {}

    results = {}
    for ticker in tickers:
        rows = _fetch_yahoo_direct(ticker, start, end)
        if not rows:
            rows = _fetch_stooq(ticker, start, end)
        if rows:
            results[ticker] = rows
        time.sleep(0.3)   # ป้องกัน rate limit

    return results

def _process_df_rows(df) -> list[dict]:
    """Helper แปลง DF เป็น list of dict (รองรับทั้ง download และ history)"""
    # normalize column names (ticker.history คืน 'Close', download คืน ('Close','AAPL'))
    if hasattr(df.columns, "levels"):
        df = df.droplevel(1, axis=1) if df.columns.nlevels > 1 else df
    df.columns = [str(c).split(",")[0].strip().title() for c in df.columns]

    rows = []
    for idx, row in df.iterrows():
        close = row.get("Close")
        if close is None or pd.isna(close) or float(close) == 0:
            continue
        rows.append({
            "date":   idx.date() if hasattr(idx, "date") else idx,
            "open":   Decimal(str(round(float(row.get("Open",  close)), 4))),
            "high":   Decimal(str(round(float(row.get("High",  close)), 4))),
            "low":    Decimal(str(round(float(row.get("Low",   close)), 4))),
            "close":  Decimal(str(round(float(close), 4))),
            "volume": int(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 0,
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
            default=getattr(settings, "PRICE_LOAD_BATCH_SIZE", 10),
            help="จำนวนหุ้นที่โหลดพร้อมกัน (default: 10)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="หน่วงเวลาระหว่าง batch (วินาที) เพื่อไม่ให้ถูก rate-limit",
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
