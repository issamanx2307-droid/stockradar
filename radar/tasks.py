"""
Celery Tasks สำหรับ Radar หุ้น
- โหลดราคาหุ้นอัตโนมัติหลังตลาดปิด
- คำนวณ indicator
- สร้าง signal
"""

import logging
import time
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task: โหลดราคาหุ้นทั้งหมด
# ---------------------------------------------------------------------------

@shared_task(name="radar.tasks.load_all_prices", bind=True, max_retries=3)
def load_all_prices(self, days: int = 1):
    """
    โหลดราคาหุ้นรายวันจาก Yahoo Finance แบบ Batch
    """
    from radar.models import Symbol
    from radar.management.commands.load_prices import (
        fetch_prices_batch,
        get_yahoo_ticker,
    )
    import time

    end_date = date.today()
    start_date = end_date - timedelta(days=days + 5)

    qs = Symbol.objects.all()
    symbols = list(qs)
    total = len(symbols)
    batch_size = 50
    success = failed = 0

    logger.info("เริ่มโหลดราคาหุ้น %d ตัว (Batch mode)", total)

    for i in range(0, total, batch_size):
        batch = symbols[i:i + batch_size]
        ticker_map = {get_yahoo_ticker(s.symbol, s.exchange): s for s in batch}
        tickers = list(ticker_map.keys())
        
        try:
            batch_data = fetch_prices_batch(tickers, start_date, end_date)
            for ticker, rows in batch_data.items():
                sym_obj = ticker_map.get(ticker)
                if sym_obj and rows:
                    _bulk_upsert_prices(sym_obj, rows)
                    success += 1
            
            # หน่วงเล็กน้อย
            if i + batch_size < total:
                time.sleep(0.5)
        except Exception as exc:
            logger.error("Batch load ล้มเหลว: %s", exc)
            failed += len(batch)

    logger.info("โหลดราคาเสร็จ ✅ %d ❌ %d", success, failed)
    return {"success": success, "failed": failed}


# ---------------------------------------------------------------------------
# Task: คำนวณ Indicator ทั้งหมด
# ---------------------------------------------------------------------------

@shared_task(name="radar.tasks.calculate_all_indicators", bind=True)
def calculate_all_indicators(self):
    """
    คำนวณ EMA, RSI, Volume Avg สำหรับทุกหุ้น
    เรียกใช้หลัง load_all_prices เสร็จ
    """
    from radar.models import Symbol

    symbols = Symbol.objects.all()
    success = failed = 0

    for sym_obj in symbols:
        try:
            calculate_indicators_for_symbol.delay(sym_obj.id)
            success += 1
        except Exception as exc:
            logger.error("สั่งคำนวณ indicator %s ล้มเหลว: %s", sym_obj.symbol, exc)
            failed += 1

    return {"queued": success, "failed": failed}


@shared_task(name="radar.tasks.calculate_indicators_for_symbol")
def calculate_indicators_for_symbol(symbol_id: int):
    """ใช้ Indicator Engine แบบ Pro ที่ปรับปรุงแล้ว"""
    from radar.models import Symbol
    from radar.indicator_engine import run_indicator_engine
    
    try:
        sym_obj = Symbol.objects.get(id=symbol_id)
        run_indicator_engine(sym_obj)
    except Exception as e:
        logger.error("คำนวณ indicator %s ล้มเหลว: %s", symbol_id, e)


# ---------------------------------------------------------------------------
# Task: สร้าง Signal
# ---------------------------------------------------------------------------

@shared_task(name="radar.tasks.generate_all_signals")
def generate_all_signals():
    """
    ตรวจ strategy ทุกตัว แล้วสร้าง signal
    เรียกใช้หลัง calculate_all_indicators เสร็จ
    """
    from radar.models import Symbol

    symbols = Symbol.objects.all()
    total_signals = 0

    for sym_obj in symbols:
        count = _generate_signals_for_symbol(sym_obj)
        total_signals += count

    logger.info("สร้าง signal ทั้งหมด %d รายการ", total_signals)
    return {"total_signals": total_signals}


def _generate_signals_for_symbol(sym_obj) -> int:
    """
    ตรวจ indicator ล่าสุดของหุ้น แล้วสร้าง signal
    คืนจำนวน signal ที่สร้าง
    """
    from radar.models import Indicator, Signal, PriceDaily
    from django.utils import timezone

    # ดึง indicator ล่าสุด
    indicator = (
        Indicator.objects
        .filter(symbol=sym_obj)
        .order_by("-date")
        .first()
    )
    if not indicator:
        return 0

    # ดึงราคาปัจจุบัน
    price_obj = (
        PriceDaily.objects
        .filter(symbol=sym_obj)
        .order_by("-date")
        .first()
    )
    if not price_obj:
        return 0

    signals_created = 0
    now = timezone.now()

    # mapping signal_type → direction
    SIGNAL_DIRECTION = {
        "OVERSOLD":     "LONG",
        "GOLDEN_CROSS": "LONG",
        "BREAKOUT":     "LONG",
        "BUY":          "LONG",
        "STRONG_BUY":   "LONG",
        "OVERBOUGHT":   "SHORT",
        "DEATH_CROSS":  "SHORT",
        "SELL":         "SHORT",
        "WEAK_SELL":    "SHORT",
        "STRONG_SELL":  "SHORT",
    }

    def create_signal(signal_type, score):
        direction = SIGNAL_DIRECTION.get(signal_type, "NEUTRAL")
        Signal.objects.create(
            symbol=sym_obj,
            signal_type=signal_type,
            direction=direction,
            score=Decimal(str(score)),
            price=price_obj.close,
            created_at=now,
        )
        nonlocal signals_created
        signals_created += 1

    rsi    = float(indicator.rsi   or 50)
    ema20  = float(indicator.ema20  or 0)
    ema50  = float(indicator.ema50  or 0)
    ema200 = float(indicator.ema200 or 0)
    close  = float(price_obj.close)
    vol    = price_obj.volume
    vol30  = indicator.volume_avg30 or 0

    # ---- กฎ Strategy ----

    # RSI Oversold
    if rsi < 30:
        score = round(60 + (30 - rsi) * 1.5, 1)
        create_signal("OVERSOLD", min(score, 95))

    # RSI Overbought
    elif rsi > 70:
        score = round(60 + (rsi - 70) * 1.5, 1)
        create_signal("OVERBOUGHT", min(score, 95))

    # Golden Cross: EMA20 ข้าม EMA50 ขึ้น
    if ema20 > ema50 > ema200 > 0:
        create_signal("GOLDEN_CROSS", 80)

    # Death Cross: EMA20 ข้าม EMA50 ลง
    elif ema20 < ema50 and ema50 < ema200 and ema200 > 0:
        create_signal("DEATH_CROSS", 78)

    # Volume Spike: ปริมาณซื้อขายสูงกว่าค่าเฉลี่ย 2 เท่า
    if vol30 > 0 and vol > vol30 * 2:
        create_signal("BREAKOUT", round(65 + min((vol / vol30 - 2) * 5, 25), 1))

    # Bullish: ราคาอยู่เหนือ EMA200
    # score = 60 (base) + trend bonus (close/ema200) + momentum bonus (rsi)
    # ตัวอย่าง: close/ema200=1.05, rsi=60 → 60 + 10 + 6 = 76
    if close > ema200 > 0 and rsi > 50:
        trend_bonus    = min((close / ema200 - 1) * 200, 20)   # 0-20 (cap 10% above EMA200)
        momentum_bonus = (rsi - 50) * 0.3                       # 0-6 (for rsi 50-70)
        create_signal("BUY", round(60 + trend_bonus + momentum_bonus, 1))

    # Bearish: ราคาต่ำกว่า EMA200
    # score = 60 + trend penalty + RSI weakness
    elif close < ema200 and ema200 > 0 and rsi < 50:
        trend_bonus    = min((1 - close / ema200) * 200, 20)   # 0-20
        momentum_bonus = (50 - rsi) * 0.3                       # 0-6
        create_signal("SELL", round(60 + trend_bonus + momentum_bonus, 1))

    return signals_created


# ---------------------------------------------------------------------------
# Task: Refresh Materialized View
# ---------------------------------------------------------------------------

@shared_task(name="radar.tasks.refresh_latest_snapshot")
def refresh_latest_snapshot():
    """
    REFRESH MATERIALIZED VIEW CONCURRENTLY radar_latest_snapshot
    รันหลัง generate_all_signals เสร็จ (19:15 น.)
    """
    from django.db import connection
    import time
    t0 = time.time()
    with connection.cursor() as cur:
        cur.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY radar_latest_snapshot;"
        )
    elapsed = round(time.time() - t0, 2)
    logger.info("✅ Refreshed radar_latest_snapshot in %ss", elapsed)
    return {"elapsed": elapsed}


# ---------------------------------------------------------------------------
# ฟังก์ชันช่วย
# ---------------------------------------------------------------------------

def _calc_rsi(series, period: int = 14):
    """คำนวณ Relative Strength Index"""
    import pandas as pd
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _bulk_upsert_prices(sym_obj, rows: list[dict]):
    """Bulk Upsert ราคาหุ้นเพื่อลดจำนวน query"""
    from radar.models import PriceDaily
    
    dates = [r["date"] for r in rows]
    existing = {p.date: p for p in PriceDaily.objects.filter(symbol=sym_obj, date__in=dates)}
    
    to_create = []
    to_update = []
    
    for row in rows:
        dt = row["date"]
        if dt in existing:
            obj = existing[dt]
            for k, v in row.items():
                if k != "date":
                    setattr(obj, k, v)
            to_update.append(obj)
        else:
            to_create.append(PriceDaily(symbol=sym_obj, **row))
            
    with transaction.atomic():
        if to_create:
            PriceDaily.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            PriceDaily.objects.bulk_update(to_update, ["open", "high", "low", "close", "volume"], batch_size=500)


# ─────────────────────────────────────────────────────────────────────────────
# VI Screener: fetch fundamentals + compute VI score
# รัน 1 ครั้ง/วัน  โหลด 50 หุ้น/ครั้ง (rolling 3 วัน = ~150 บริษัทใน SET)
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val) -> float | None:
    """แปลง yfinance value เป็น float ปลอดภัย (None / inf → None)"""
    try:
        v = float(val)
        return None if (v != v or abs(v) == float("inf")) else v
    except (TypeError, ValueError):
        return None


def compute_vi_score(snap) -> tuple[float, str]:
    """
    คำนวณ VI Score 0–100 จาก FundamentalSnapshot instance

    คะแนน:
      P/E       25 pt   ≤10→25, ≤15→20, ≤20→15, ≤25→8, >25→0
      P/B       20 pt   ≤1→20,  ≤2→15,  ≤3→8,   >3→0
      ROE       20 pt   ≥20→20, ≥15→15, ≥10→8,  <10→0
      DivYield  15 pt   ≥5→15,  ≥3→10,  ≥1→5,   <1→0
      D/E       10 pt   ≤0.5→10,≤1→7,  ≤2→3,   >2→0
      RevGrowth 10 pt   ≥20→10, ≥10→7,  ≥0→4,   <0→0

    Grade: A≥80 / B≥60 / C≥40 / D<40
    """
    score = 0.0

    # P/E
    pe = _safe_float(snap.pe_ratio)
    if pe is not None and pe > 0:
        if pe <= 10:   score += 25
        elif pe <= 15: score += 20
        elif pe <= 20: score += 15
        elif pe <= 25: score += 8

    # P/B
    pb = _safe_float(snap.pb_ratio)
    if pb is not None and pb > 0:
        if pb <= 1:   score += 20
        elif pb <= 2: score += 15
        elif pb <= 3: score += 8

    # ROE
    roe = _safe_float(snap.roe)
    if roe is not None:
        if roe >= 20:   score += 20
        elif roe >= 15: score += 15
        elif roe >= 10: score += 8

    # Dividend Yield
    dy = _safe_float(snap.dividend_yield)
    if dy is not None and dy >= 0:
        if dy >= 5:   score += 15
        elif dy >= 3: score += 10
        elif dy >= 1: score += 5

    # D/E
    de = _safe_float(snap.debt_to_equity)
    if de is not None and de >= 0:
        if de <= 0.5: score += 10
        elif de <= 1: score += 7
        elif de <= 2: score += 3

    # Revenue Growth
    rg = _safe_float(snap.revenue_growth)
    if rg is not None:
        if rg >= 20:  score += 10
        elif rg >= 10: score += 7
        elif rg >= 0:  score += 4

    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
    return round(score, 2), grade


@shared_task(name="radar.fetch_set_fundamentals")
def fetch_set_fundamentals():
    """
    ดึงข้อมูล fundamental จาก Yahoo Finance สำหรับ SET
    - คัด top 150 หุ้นตาม volume_avg20 จาก LatestSnapshot
    - แบ่ง batch 50 หุ้น/วัน (rotating โดยใช้ day-of-year % 3)
    - skip ถ้า fetched_at < 7 วัน (cache)
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return

    from .models import Symbol, FundamentalSnapshot

    # ดึง SET symbols ทั้งหมดจาก Symbol model โดยตรง
    symbol_list = list(
        Symbol.objects.filter(exchange="SET").values_list("symbol", flat=True)
    )
    if not symbol_list:
        logger.warning("fetch_set_fundamentals: no SET symbols found")
        return

    # ถ้า DB ว่างเปล่า (first run) ดึงทุกตัวเลย
    # ถ้ามีข้อมูลแล้ว ใช้ rotating batch 50 ตัว/วัน เพื่อ refresh
    from .models import FundamentalSnapshot as _FS
    if _FS.objects.count() == 0:
        batch = symbol_list          # fetch ทั้งหมดครั้งแรก
    else:
        batch_size = 50
        day_offset = timezone.now().toordinal() % max(1, len(symbol_list) // batch_size)
        batch = symbol_list[day_offset * batch_size : day_offset * batch_size + batch_size]

    stale_cutoff = timezone.now() - timedelta(days=7)
    updated = skipped = errors = 0

    for sym_code in batch:
        # skip ถ้ายังไม่ stale
        try:
            existing = FundamentalSnapshot.objects.get(symbol__symbol=sym_code)
            if existing.fetched_at >= stale_cutoff:
                skipped += 1
                continue
        except FundamentalSnapshot.DoesNotExist:
            existing = None

        ticker_code = f"{sym_code}.BK"
        try:
            info = yf.Ticker(ticker_code).info

            pe  = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
            pb  = _safe_float(info.get("priceToBook"))
            roe = _safe_float(info.get("returnOnEquity"))
            if roe is not None: roe *= 100          # yfinance → ratio → %
            roa = _safe_float(info.get("returnOnAssets"))
            if roa is not None: roa *= 100
            nm  = _safe_float(info.get("profitMargins"))
            if nm is not None: nm *= 100
            rg  = _safe_float(info.get("revenueGrowth"))
            if rg is not None: rg *= 100
            eg  = _safe_float(info.get("earningsGrowth"))
            if eg is not None: eg *= 100
            de  = _safe_float(info.get("debtToEquity"))
            cr  = _safe_float(info.get("currentRatio"))
            dy  = _safe_float(info.get("dividendYield"))
            if dy is not None: dy *= 100
            mc  = info.get("marketCap")
            mc  = int(mc) if mc else None

            # pre-filter: skip rubbish data
            net_income = info.get("netIncomeToCommon")
            if net_income is not None and float(net_income) < 0:
                logger.info("skip %s: negative net income", sym_code)
                skipped += 1
                time.sleep(1)
                continue
            if pb is not None and pb < 0:
                logger.info("skip %s: negative book value", sym_code)
                skipped += 1
                time.sleep(1)
                continue

            sym_obj = Symbol.objects.get(symbol=sym_code)
            snap, _ = FundamentalSnapshot.objects.get_or_create(symbol=sym_obj)
            snap.pe_ratio       = pe
            snap.pb_ratio       = pb
            snap.market_cap     = mc
            snap.roe            = roe
            snap.roa            = roa
            snap.net_margin     = nm
            snap.revenue_growth = rg
            snap.earnings_growth = eg
            snap.debt_to_equity = de
            snap.current_ratio  = cr
            snap.dividend_yield = dy

            vi_score, vi_grade = compute_vi_score(snap)
            snap.vi_score = vi_score
            snap.vi_grade = vi_grade
            snap.save()
            updated += 1

        except Exception as e:
            logger.warning("fetch_set_fundamentals error %s: %s", sym_code, e)
            errors += 1

        time.sleep(1.5)   # ป้องกัน rate limit

    logger.info(
        "fetch_set_fundamentals done: updated=%d skipped=%d errors=%d",
        updated, skipped, errors
    )
    return {"updated": updated, "skipped": skipped, "errors": errors}
