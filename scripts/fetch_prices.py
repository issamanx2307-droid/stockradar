"""
GitHub Actions — ดึงราคาหุ้นจาก Stooq (หลัก) และ Yahoo Finance (fallback)
แล้วส่งไปยัง VPS

Environment variables (GitHub Secrets):
    VPS_API_URL   = https://radarhoon.com
    VPS_API_TOKEN = <IMPORT_API_TOKEN ใน .env ของ VPS>

Usage:
    python scripts/fetch_prices.py          # ดึง 7 วันล่าสุด
    python scripts/fetch_prices.py --days 1825  # ดึงย้อนหลัง 5 ปี
    python scripts/fetch_prices.py --days 3650  # ดึงย้อนหลัง 10 ปี
"""

import argparse
import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests

VPS_API_URL   = os.environ.get("VPS_API_URL", "").strip().rstrip("/")
VPS_API_TOKEN = os.environ.get("VPS_API_TOKEN", "").strip()

BATCH_SIZE   = 200
SLEEP_TICKER = 0.3
MAX_RETRIES  = 3


def get_symbols() -> list[dict]:
    """ดึงรายชื่อหุ้นทั้งหมดจาก VPS"""
    url = f"{VPS_API_URL}/api/symbols-export/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def to_stooq_ticker(symbol: str, yahoo: str) -> str:
    """แปลง symbol เป็น Stooq format
    หุ้นไทย: PTT.BK  → PTT.TH
    หุ้น US: AAPL    → AAPL.US
    """
    if yahoo.upper().endswith(".BK"):
        return f"{symbol.upper()}.TH"
    return f"{symbol.upper()}.US"


def fetch_ticker_stooq(stooq_ticker: str, start: date, end: date) -> list[dict]:
    """ดึงราคาจาก Stooq"""
    url = (
        f"https://stooq.com/q/d/l/"
        f"?s={stooq_ticker.lower()}&d1={start.strftime('%Y%m%d')}"
        f"&d2={end.strftime('%Y%m%d')}&i=d"
    )
    for attempt in range(MAX_RETRIES):
        try:
            df = pd.read_csv(url)
            if df.empty or "Close" not in df.columns:
                return []
            df.columns = [c.strip().title() for c in df.columns]
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")
            rows = []
            for _, row in df.iterrows():
                close = row.get("Close")
                if pd.isna(close) or float(close) == 0:
                    continue
                rows.append({
                    "date":   row["Date"].date().isoformat(),
                    "open":   round(float(row.get("Open",  close)), 4),
                    "high":   round(float(row.get("High",  close)), 4),
                    "low":    round(float(row.get("Low",   close)), 4),
                    "close":  round(float(close), 4),
                    "volume": int(row["Volume"]) if not pd.isna(row.get("Volume", 0)) else 0,
                })
            return rows
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  ✗ {stooq_ticker}: {e}")
    return []


def fetch_ticker_yahoo(symbol: str, yahoo_ticker: str, start: date, end: date) -> list[dict]:
    """Fallback: ดึงราคาจาก Yahoo Finance ผ่าน yf.Ticker().history()
    ใช้ Ticker API แทน yf.download() เพื่อหลีกเลี่ยง multi-level DataFrame"""
    try:
        import yfinance as yf
        ticker = yahoo_ticker if yahoo_ticker else symbol
        df = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat())
        if df.empty:
            return []
        rows = []
        for idx, row in df.iterrows():
            try:
                close = float(row["Close"])
            except (ValueError, TypeError):
                continue
            if close == 0:
                continue
            rows.append({
                "date":   idx.date().isoformat(),
                "open":   round(float(row.get("Open",  close)), 4),
                "high":   round(float(row.get("High",  close)), 4),
                "low":    round(float(row.get("Low",   close)), 4),
                "close":  round(close, 4),
                "volume": int(row["Volume"]) if row.get("Volume") and not pd.isna(row["Volume"]) else 0,
            })
        return rows
    except Exception as e:
        print(f"  ✗ Yahoo fallback {symbol}: {e}")
        return []


def send_to_vps(records: list[dict]) -> tuple[int, int]:
    """ส่งข้อมูลราคาเข้า VPS เป็น batch"""
    imported = skipped = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.post(
                    f"{VPS_API_URL}/api/import-prices/",
                    json=batch,
                    headers={"X-Import-Token": VPS_API_TOKEN},
                    timeout=60,
                )
                r.raise_for_status()
                result = r.json()
                imported += result.get("imported", 0)
                skipped  += result.get("skipped",  0)
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3)
                else:
                    print(f"  ✗ ส่งข้อมูลไม่สำเร็จ: {e}")
                    skipped += len(batch)
    return imported, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7,
                        help="จำนวนวันย้อนหลัง (default=7, ใช้ 1825 สำหรับ 5 ปี)")
    args = parser.parse_args()

    if not VPS_API_URL or not VPS_API_TOKEN:
        print("❌ ไม่พบ VPS_API_URL หรือ VPS_API_TOKEN")
        sys.exit(1)

    end   = date.today() + timedelta(days=1)
    start = date.today() - timedelta(days=args.days)

    print(f"📡 ดึงข้อมูลจาก {start} ถึง {end} (Stooq=Thai, Yahoo=US)")

    # ── ดึง symbols จาก VPS ──
    print("🔍 กำลังโหลดรายชื่อหุ้น...")
    try:
        symbols = get_symbols()
    except Exception as e:
        print(f"❌ โหลดรายชื่อหุ้นไม่ได้: {e}")
        sys.exit(1)

    print(f"✅ พบ {len(symbols)} หุ้น (Thai + US)")

    # ── ดึงราคาทีละตัว ──
    all_records = []
    ok = fail = yahoo_direct = yahoo_fallback = 0

    for i, sym in enumerate(symbols, 1):
        symbol       = sym["symbol"]
        yahoo        = sym.get("yahoo", symbol)
        exchange     = sym.get("exchange", "")
        is_us        = exchange in ("NASDAQ", "NYSE")
        stooq_ticker = to_stooq_ticker(symbol, yahoo)

        if is_us:
            # US stocks: ใช้ Yahoo Finance ตรงๆ (Stooq มักบล็อก GitHub Actions)
            rows = fetch_ticker_yahoo(symbol, yahoo, start, end)
            if rows:
                yahoo_direct += 1
            else:
                # fallback ไป Stooq ถ้า Yahoo ไม่ได้
                rows = fetch_ticker_stooq(stooq_ticker, start, end)
        else:
            # Thai stocks: ใช้ Stooq ก่อน → fallback Yahoo
            rows = fetch_ticker_stooq(stooq_ticker, start, end)
            if not rows:
                rows = fetch_ticker_yahoo(symbol, yahoo, start, end)
                if rows:
                    yahoo_fallback += 1

        if rows:
            for row in rows:
                row["symbol"] = symbol
            all_records.extend(rows)
            ok += 1
        else:
            fail += 1

        if i % 20 == 0:
            print(f"  [{i}/{len(symbols)}] ✅{ok} ❌{fail} (Yahoo fallback: {yahoo_fallback})")

        time.sleep(SLEEP_TICKER)

    print(f"\n📊 ดึงได้ {ok} หุ้น / ไม่ได้ {fail} หุ้น / Yahoo direct {yahoo_direct} ตัว / Yahoo fallback {yahoo_fallback} ตัว / รวม {len(all_records)} แถว")

    # ── ส่งไป VPS ──
    if not all_records:
        print("⚠️ ไม่มีข้อมูลที่จะส่ง")
        sys.exit(0)

    print(f"📤 กำลังส่งข้อมูลไปยัง VPS ({len(all_records)} แถว)...")
    imported, skipped = send_to_vps(all_records)
    print(f"✅ import: {imported} แถว  |  skip: {skipped} แถว")


if __name__ == "__main__":
    main()
