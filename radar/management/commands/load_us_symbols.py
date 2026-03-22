"""
load_us_symbols — โหลดหุ้น US ทั้งตลาดจาก Wikipedia
ครอบคลุม: S&P 500 (~503), NASDAQ 100 (~101), Dow Jones 30
รวมประมาณ 500-600+ ตัวที่ไม่ซ้ำกัน

การใช้งาน:
    python manage.py load_us_symbols
    python manage.py load_us_symbols --update   # อัปเดตข้อมูลที่มีอยู่
"""

import time
import logging
import requests
import pandas as pd
from django.core.management.base import BaseCommand
from radar.models import Symbol

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 StockRadar/1.0 (educational project)"}


def fetch_sp500() -> list[tuple]:
    """ดึง S&P 500 จาก Wikipedia"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url, attrs={"id": "constituents"})
        df = tables[0]
        # คอลัมน์: Symbol, Security, GICS Sector, GICS Sub-Industry, ...
        results = []
        for _, row in df.iterrows():
            sym = str(row["Symbol"]).strip().replace(".", "-")  # BRK.B → BRK-B (Yahoo format)
            name = str(row.get("Security", sym)).strip()
            sector = str(row.get("GICS Sector", "อื่นๆ")).strip()
            results.append((sym, name, "NYSE", sector))
        return results
    except Exception as e:
        logger.error(f"fetch_sp500 error: {e}")
        return []


def fetch_nasdaq100() -> list[tuple]:
    """ดึง NASDAQ 100 จาก Wikipedia"""
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    try:
        tables = pd.read_html(url)
        # หา table ที่มีคอลัมน์ Ticker
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            if "ticker" in cols or "symbol" in cols:
                sym_col = "Ticker" if "Ticker" in df.columns else "Symbol"
                name_col = None
                for c in df.columns:
                    if "company" in str(c).lower() or "name" in str(c).lower():
                        name_col = c
                        break
                results = []
                for _, row in df.iterrows():
                    sym = str(row[sym_col]).strip()
                    name = str(row[name_col]).strip() if name_col else sym
                    if sym and sym != "nan" and len(sym) <= 10:
                        results.append((sym, name, "NASDAQ", "เทคโนโลยี"))
                if results:
                    return results
        return []
    except Exception as e:
        logger.error(f"fetch_nasdaq100 error: {e}")
        return []


def fetch_dowjones() -> list[tuple]:
    """ดึง Dow Jones 30 จาก Wikipedia"""
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    try:
        tables = pd.read_html(url)
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            if "symbol" in cols or "ticker" in cols:
                sym_col = next((c for c in df.columns if str(c).lower() in ["symbol", "ticker"]), None)
                name_col = next((c for c in df.columns if "company" in str(c).lower()), None)
                if sym_col:
                    results = []
                    for _, row in df.iterrows():
                        sym = str(row[sym_col]).strip()
                        name = str(row[name_col]).strip() if name_col else sym
                        if sym and sym != "nan" and len(sym) <= 10:
                            results.append((sym, name, "NYSE", "อุตสาหกรรม"))
                    if len(results) >= 20:
                        return results
        return []
    except Exception as e:
        logger.error(f"fetch_dowjones error: {e}")
        return []

# ── GICS Sector → ภาษาไทย ────────────────────────────────────────────────────
SECTOR_MAP = {
    "Information Technology": "เทคโนโลยี",
    "Health Care": "สุขภาพ",
    "Financials": "การเงิน",
    "Consumer Discretionary": "สินค้าผู้บริโภค",
    "Consumer Staples": "สินค้าอุปโภค",
    "Communication Services": "สื่อสาร",
    "Industrials": "อุตสาหกรรม",
    "Energy": "พลังงาน",
    "Utilities": "สาธารณูปโภค",
    "Real Estate": "อสังหาริมทรัพย์",
    "Materials": "วัสดุ",
    "Technology": "เทคโนโลยี",
    "Financial Services": "การเงิน",
    "Healthcare": "สุขภาพ",
    "Basic Materials": "วัสดุ",
    "nan": "อื่นๆ",
}


def map_sector(raw: str) -> str:
    return SECTOR_MAP.get(raw.strip(), raw.strip() or "อื่นๆ")


def detect_exchange(symbol: str, name: str = "") -> str:
    """เดา exchange จากรหัสหุ้น — ใช้เป็น fallback"""
    nasdaq_known = {
        "AAPL","MSFT","GOOGL","GOOG","AMZN","META","NVDA","TSLA","AVGO",
        "ADBE","CSCO","INTC","CMCSA","NFLX","AMD","QCOM","TXN","AMGN","SBUX",
        "ISRG","MU","LRCX","KLAC","AMAT","MRVL","PANW","CRWD","SNPS","CDNS",
        "MELI","ASML","TEAM","ZS","DDOG","FTNT","FAST","PAYX","ROST","ODFL",
        "BIIB","GILD","VRTX","REGN","ILMN","IDXX","ALGN","DXCM","MRNA","EXAS",
        "PCAR","CTAS","CPRT","VRSK","ANSS","SGEN","MTCH","LCID","RIVN","ABNB",
        "PYPL","EBAY","BIDU","JD","NTES","BKNG","EXPE","CSGP","TCOM","SIRI",
        "WBA","COST","DLTR","KHC","MDLZ","MNST","PEPSICO","PEP",
    }
    if symbol in nasdaq_known:
        return "NASDAQ"
    return "NYSE"


class Command(BaseCommand):
    help = "โหลดหุ้น US ทั้งตลาดจาก Wikipedia (S&P500 + NASDAQ100 + DowJones30)"

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true",
                            help="อัปเดต name/sector ของหุ้นที่มีอยู่แล้ว")
        parser.add_argument("--sp500-only", action="store_true",
                            help="โหลดเฉพาะ S&P 500")

    def handle(self, *args, **options):
        do_update = options["update"]
        sp500_only = options["sp500_only"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== โหลดหุ้น US ทั้งตลาดจาก Wikipedia ===\n"
        ))

        all_symbols: dict[str, tuple] = {}  # sym → (sym, name, exchange, sector)

        # ── 1. S&P 500 ──
        self.stdout.write("⏳ ดึง S&P 500...")
        sp500 = fetch_sp500()
        time.sleep(1)
        for sym, name, exchange, sector in sp500:
            exchange = detect_exchange(sym)
            all_symbols[sym] = (sym, name, exchange, map_sector(sector))
        self.stdout.write(f"   ✅ S&P 500: {len(sp500)} ตัว")

        if not sp500_only:
            # ── 2. NASDAQ 100 ──
            self.stdout.write("⏳ ดึง NASDAQ 100...")
            nq100 = fetch_nasdaq100()
            time.sleep(1)
            for sym, name, exchange, sector in nq100:
                if sym not in all_symbols:
                    all_symbols[sym] = (sym, name, exchange, sector)
            self.stdout.write(f"   ✅ NASDAQ 100: {len(nq100)} ตัว")

            # ── 3. Dow Jones 30 ──
            self.stdout.write("⏳ ดึง Dow Jones 30...")
            dj30 = fetch_dowjones()
            time.sleep(1)
            for sym, name, exchange, sector in dj30:
                if sym not in all_symbols:
                    all_symbols[sym] = (sym, name, exchange, sector)
            self.stdout.write(f"   ✅ Dow Jones 30: {len(dj30)} ตัว")

        # กรองรหัสที่ไม่ valid ออก
        valid = {
            k: v for k, v in all_symbols.items()
            if k and k != "nan" and len(k) <= 12
            and k.replace("-", "").replace(".", "").isalnum()
        }

        self.stdout.write(f"\n📊 รวมหุ้น US ไม่ซ้ำ: {len(valid)} ตัว")
        self.stdout.write("⏳ บันทึกลง database...\n")

        created = updated = skipped = 0
        for sym, name, exchange, sector in valid.values():
            obj, was_created = Symbol.objects.get_or_create(
                symbol=sym,
                defaults={"name": name, "exchange": exchange, "sector": sector},
            )
            if was_created:
                created += 1
            elif do_update:
                obj.name = name
                obj.exchange = exchange
                obj.sector = sector
                obj.save()
                updated += 1
            else:
                skipped += 1

        total_us = Symbol.objects.filter(
            exchange__in=["NYSE", "NASDAQ"]
        ).count()

        self.stdout.write(self.style.SUCCESS(
            f"✅ เพิ่มใหม่: {created}  อัปเดต: {updated}  ข้าม: {skipped}\n"
            f"📈 หุ้น US ในระบบตอนนี้: {total_us} ตัว\n"
            f"📌 รวมทุกตลาดในระบบ: {Symbol.objects.count()} ตัว"
        ))

        if created == 0 and skipped > 0:
            self.stdout.write(self.style.WARNING(
                "\n💡 Tip: ถ้าต้องการอัปเดต name/sector ให้ใช้ --update flag"
            ))
