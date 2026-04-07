"""
GitHub Actions — ดึงราคาหุ้น
  Thai stocks  : Stooq (หลัก) → Yahoo Finance batch (fallback)
  US stocks    : Alpaca Data API (ใช้ credentials เดิมที่มีอยู่แล้ว)

Environment variables (GitHub Secrets):
    VPS_API_URL       = https://radarhoon.com
    VPS_API_TOKEN     = <IMPORT_API_TOKEN ใน .env ของ VPS>
    ALPACA_API_KEY    = <Alpaca API Key>
    ALPACA_SECRET_KEY = <Alpaca Secret Key>

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

VPS_API_URL       = os.environ.get("VPS_API_URL", "").strip().rstrip("/")
VPS_API_TOKEN     = os.environ.get("VPS_API_TOKEN", "").strip()
ALPACA_API_KEY    = os.environ.get("ALPACA_API_KEY", "").strip()
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "").strip()
ALPACA_DATA_URL   = "https://data.alpaca.markets"

BATCH_SIZE        = 200
SLEEP_TICKER      = 0.3   # delay หลังแต่ละ ticker (Stooq)
MAX_RETRIES       = 3
YAHOO_BATCH_SIZE  = 50    # จำนวน ticker ต่อ batch ใน yf.download()


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


def parse_ticker_df(df: pd.DataFrame, ticker: str) -> list[dict]:
    """แปลง DataFrame (single-level) ของ ticker หนึ่งตัวเป็น list[dict]"""
    if df is None or df.empty:
        return []
    rows = []
    for idx, row in df.iterrows():
        try:
            close = float(row["Close"])
        except (ValueError, TypeError, KeyError):
            continue
        if close == 0 or pd.isna(close):
            continue
        try:
            vol = int(row["Volume"]) if not pd.isna(row.get("Volume", float("nan"))) else 0
        except (ValueError, TypeError):
            vol = 0
        rows.append({
            "date":   idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10],
            "open":   round(float(row.get("Open",  close)), 4),
            "high":   round(float(row.get("High",  close)), 4),
            "low":    round(float(row.get("Low",   close)), 4),
            "close":  round(close, 4),
            "volume": vol,
        })
    return rows


def fetch_batch_yahoo(sym_map: dict[str, str], start: date, end: date) -> dict[str, list[dict]]:
    """
    ดึงราคาจาก Yahoo Finance แบบ batch ด้วย yf.download()
    sym_map: {symbol: yahoo_ticker}  เช่น {"PTT": "PTT.BK", "AAPL": "AAPL"}
    คืน:     {symbol: list[dict]}
    """
    import yfinance as yf

    result: dict[str, list[dict]] = {}
    symbols_list = list(sym_map.keys())

    # แบ่งเป็น batch ย่อย เพื่อลด request size
    for batch_start in range(0, len(symbols_list), YAHOO_BATCH_SIZE):
        batch_syms = symbols_list[batch_start : batch_start + YAHOO_BATCH_SIZE]
        batch_tickers = [sym_map[s] for s in batch_syms]

        for attempt in range(MAX_RETRIES):
            try:
                if len(batch_tickers) == 1:
                    # Single ticker → ใช้ Ticker().history() (ไม่มี MultiIndex)
                    ticker = batch_tickers[0]
                    df = yf.Ticker(ticker).history(
                        start=start.isoformat(), end=end.isoformat()
                    )
                    sym = batch_syms[0]
                    result[sym] = parse_ticker_df(df, ticker)
                else:
                    # Multiple tickers → yf.download() ให้ MultiIndex columns
                    df_all = yf.download(
                        batch_tickers,
                        start=start.isoformat(),
                        end=end.isoformat(),
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=True,
                    )
                    for sym, ticker in zip(batch_syms, batch_tickers):
                        try:
                            # MultiIndex: ระดับ 0 = ticker, ระดับ 1 = column
                            if ticker in df_all.columns.get_level_values(0):
                                ticker_df = df_all[ticker].copy()
                            else:
                                ticker_df = pd.DataFrame()
                            result[sym] = parse_ticker_df(ticker_df, ticker)
                        except Exception as ex:
                            print(f"  ✗ parse {sym} ({ticker}): {ex}")
                            result[sym] = []
                break  # batch สำเร็จ → ออก retry loop

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = 10 * (attempt + 1)
                    print(f"  ⚠ Yahoo batch retry {attempt+1} (wait {wait}s): {e}")
                    time.sleep(wait)
                else:
                    print(f"  ✗ Yahoo batch failed: {e}")
                    for sym in batch_syms:
                        result.setdefault(sym, [])

        # หน่วงระหว่าง batch เพื่อไม่โดน rate limit
        if batch_start + YAHOO_BATCH_SIZE < len(symbols_list):
            time.sleep(3)

    return result


def fetch_us_stocks_alpaca(symbols: list[str], start: date, end: date) -> dict[str, list[dict]]:
    """
    ดึง OHLCV bars ของ US stocks จาก Alpaca Data API (multi-symbol, pagination)
    คืน dict: { "AAPL": [rows], "TSLA": [rows], ... }
    แต่ละ row มี keys: date, open, high, low, close, volume, symbol
    """
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        print("  ⚠ ไม่พบ ALPACA_API_KEY / ALPACA_SECRET_KEY — ข้าม US stocks")
        return {}

    headers = {
        "APCA-API-KEY-ID":     ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    }
    ALPACA_BATCH = 100  # symbols per request (Alpaca แนะนำ ≤ 100)
    result: dict[str, list[dict]] = {}

    for batch_start in range(0, len(symbols), ALPACA_BATCH):
        batch = symbols[batch_start : batch_start + ALPACA_BATCH]
        params = {
            "symbols":   ",".join(batch),
            "timeframe": "1Day",
            "start":     start.isoformat(),
            "end":       end.isoformat(),
            "limit":     1000,
            "feed":      "iex",   # iex = ฟรี, sip = ต้องจ่ายแต่ครบกว่า
            "sort":      "asc",
        }
        page_token = None

        for attempt in range(MAX_RETRIES):
            try:
                while True:
                    if page_token:
                        params["page_token"] = page_token
                    r = requests.get(
                        f"{ALPACA_DATA_URL}/v2/stocks/bars",
                        headers=headers,
                        params=params,
                        timeout=30,
                    )
                    r.raise_for_status()
                    data = r.json()

                    for sym, bars in data.get("bars", {}).items():
                        if sym not in result:
                            result[sym] = []
                        for b in bars:
                            ts = b.get("t", "")[:10]  # "2024-01-02T00:00:00Z" → "2024-01-02"
                            result[sym].append({
                                "date":   ts,
                                "open":   round(float(b.get("o", 0)), 4),
                                "high":   round(float(b.get("h", 0)), 4),
                                "low":    round(float(b.get("l", 0)), 4),
                                "close":  round(float(b.get("c", 0)), 4),
                                "volume": int(b.get("v", 0)),
                            })

                    page_token = data.get("next_page_token")
                    if not page_token:
                        break
                break  # batch สำเร็จ
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = 5 * (attempt + 1)
                    print(f"  ⚠ Alpaca retry {attempt+1} (wait {wait}s): {e}")
                    time.sleep(wait)
                else:
                    print(f"  ✗ Alpaca batch ล้มเหลว: {e}")

        if batch_start + ALPACA_BATCH < len(symbols):
            time.sleep(1)  # หน่วงระหว่าง batch เพื่อไม่โดน rate limit

    return result


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

    print(f"📡 ดึงข้อมูลจาก {start} ถึง {end}")

    # ── ดึง symbols จาก VPS ──
    print("🔍 กำลังโหลดรายชื่อหุ้น...")
    try:
        symbols = get_symbols()
    except Exception as e:
        print(f"❌ โหลดรายชื่อหุ้นไม่ได้: {e}")
        sys.exit(1)

    print(f"✅ พบ {len(symbols)} หุ้น")

    # แบ่ง Thai vs US
    thai_syms = []  # [(symbol, yahoo, stooq_ticker), ...]
    us_syms   = []  # [(symbol, yahoo), ...]

    for sym in symbols:
        symbol   = sym["symbol"]
        yahoo    = sym.get("yahoo", symbol)
        exchange = sym.get("exchange", "")
        is_us    = exchange in ("NASDAQ", "NYSE")

        if is_us:
            us_syms.append((symbol, yahoo))
        else:
            stooq_ticker = to_stooq_ticker(symbol, yahoo)
            thai_syms.append((symbol, yahoo, stooq_ticker))

    print(f"  Thai: {len(thai_syms)} ตัว  |  US: {len(us_syms)} ตัว")

    all_records = []

    # ══════════════════════════════════════════
    # Phase 1: Stooq → Thai stocks
    # ══════════════════════════════════════════
    print("\n📥 Phase 1: Stooq (Thai stocks)...")
    stooq_ok   = 0
    stooq_fail = []  # list of (symbol, yahoo) ที่ต้อง fallback

    for i, (symbol, yahoo, stooq_ticker) in enumerate(thai_syms, 1):
        rows = fetch_ticker_stooq(stooq_ticker, start, end)
        if rows:
            for row in rows:
                row["symbol"] = symbol
            all_records.extend(rows)
            stooq_ok += 1
        else:
            stooq_fail.append((symbol, yahoo))

        if i % 50 == 0:
            print(f"  [{i}/{len(thai_syms)}] Stooq ✅{stooq_ok} / ❌{len(stooq_fail)} (ต้อง fallback)")

        time.sleep(SLEEP_TICKER)

    print(f"  Stooq: ✅{stooq_ok} สำเร็จ  |  ❌{len(stooq_fail)} ต้อง fallback → Yahoo")

    # ══════════════════════════════════════════
    # Phase 2: Yahoo batch → Thai stocks ที่ Stooq ไม่ได้
    # ══════════════════════════════════════════
    if stooq_fail:
        print(f"\n📥 Phase 2: Yahoo batch (Thai fallback {len(stooq_fail)} ตัว)...")
        sym_map = {sym: yah for sym, yah in stooq_fail}
        batch_result = fetch_batch_yahoo(sym_map, start, end)

        yahoo_thai_ok   = 0
        yahoo_thai_fail = 0
        for symbol, rows in batch_result.items():
            if rows:
                for row in rows:
                    row["symbol"] = symbol
                all_records.extend(rows)
                yahoo_thai_ok += 1
            else:
                yahoo_thai_fail += 1
                print(f"  ✗ ไม่ได้ข้อมูล: {symbol}")

        print(f"  Yahoo Thai: ✅{yahoo_thai_ok}  ❌{yahoo_thai_fail}")
    else:
        yahoo_thai_ok = yahoo_thai_fail = 0

    # ══════════════════════════════════════════
    # Phase 3: Alpaca → US stocks (ทั้งหมด)
    # ══════════════════════════════════════════
    us_ok = us_fail = 0
    if us_syms:
        us_symbol_list = [sym for sym, _yahoo in us_syms]
        print(f"\n📥 Phase 3: Alpaca Data API (US {len(us_symbol_list)} ตัว)...")
        alpaca_result = fetch_us_stocks_alpaca(us_symbol_list, start, end)

        for symbol, rows in alpaca_result.items():
            if rows:
                for row in rows:
                    row["symbol"] = symbol
                all_records.extend(rows)
                us_ok += 1
            else:
                us_fail += 1

        # แจ้ง symbol ที่ไม่มีข้อมูล (Alpaca อาจไม่รองรับ OTC หรือ delisted)
        missing_us = [sym for sym, _ in us_syms if sym not in alpaca_result or not alpaca_result.get(sym)]
        if missing_us:
            print(f"  ⚠ ไม่มีข้อมูลจาก Alpaca ({len(missing_us)} ตัว): {', '.join(missing_us[:10])}{'...' if len(missing_us) > 10 else ''}")

        print(f"  Alpaca US: ✅{us_ok}  ❌{us_fail}")

    # ── สรุป ──
    total_ok   = stooq_ok + yahoo_thai_ok + us_ok
    total_fail = yahoo_thai_fail + us_fail
    print(f"\n📊 สรุป: ✅{total_ok} ตัวได้ข้อมูล  ❌{total_fail} ตัวไม่ได้")
    print(f"   Stooq: {stooq_ok}  |  Yahoo Thai fallback: {yahoo_thai_ok}  |  Yahoo US: {us_ok}")
    print(f"   รวม {len(all_records)} แถว")

    # ── ส่งไป VPS ──
    if not all_records:
        print("⚠️ ไม่มีข้อมูลที่จะส่ง")
        sys.exit(0)

    print(f"\n📤 กำลังส่งข้อมูลไปยัง VPS ({len(all_records)} แถว)...")
    imported, skipped = send_to_vps(all_records)
    print(f"✅ import: {imported} แถว  |  skip: {skipped} แถว")


if __name__ == "__main__":
    main()
