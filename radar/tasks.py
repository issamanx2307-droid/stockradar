"""
Celery Tasks สำหรับ Radar หุ้น
- โหลดราคาหุ้นอัตโนมัติหลังตลาดปิด
- คำนวณ indicator
- สร้าง signal
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction

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

    def create_signal(signal_type, score):
        Signal.objects.create(
            symbol=sym_obj,
            signal_type=signal_type,
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
    if close > ema200 > 0 and rsi > 50:
        create_signal("BUY", round(55 + rsi * 0.2, 1))

    # Bearish: ราคาต่ำกว่า EMA200
    elif close < ema200 and ema200 > 0 and rsi < 50:
        create_signal("SELL", round(55 + (50 - rsi) * 0.3, 1))

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
