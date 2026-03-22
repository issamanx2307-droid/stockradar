"""
Indicator Cache — Redis Layer
==============================
เก็บ indicator ล่าสุดของทุกหุ้นใน Redis
ทำให้ Scanner ไม่ต้อง query DB ทุกครั้ง

Flow:
  Scanner → Cache.get() → hit  → return DataFrame (~1ms)
                         → miss → query DB → compute → cache.set() → return

Cache Keys:
  ind:latest:{symbol_id}     — indicator ล่าสุด 1 แถว (JSON)
  ind:batch:{exchange}       — indicator ทุกหุ้นในตลาด (Parquet bytes)
  price:latest:{symbol_id}   — ราคาล่าสุด 1 แถว (JSON)
  price:history:{symbol_id}  — ราคาย้อนหลัง (Parquet bytes)

TTL:
  indicator latest  = 4 ชั่วโมง (อัปเดตหลังตลาดปิด)
  price latest      = 30 นาที   (อัปเดตถี่กว่า)
  batch             = 4 ชั่วโมง
"""

import json
import logging
import pickle
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── TTL (วินาที) ──────────────────────────────────────────────────────────────
TTL_IND_LATEST   = 4 * 3600   # 4 ชั่วโมง
TTL_PRICE_LATEST = 30 * 60    # 30 นาที
TTL_BATCH        = 4 * 3600   # 4 ชั่วโมง
TTL_PRICE_HIST   = 2 * 3600   # 2 ชั่วโมง

# ── Cache Key Builders ────────────────────────────────────────────────────────

def _key_ind_latest(symbol_id: int) -> str:
    return f"ind:latest:{symbol_id}"

def _key_price_latest(symbol_id: int) -> str:
    return f"price:latest:{symbol_id}"

def _key_ind_batch(exchange: str) -> str:
    return f"ind:batch:{exchange.upper()}"

def _key_price_hist(symbol_id: int) -> str:
    return f"price:hist:{symbol_id}"

def _key_ind_prev(symbol_id: int) -> str:
    return f"ind:prev:{symbol_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# Redis Connection Helper
# ═══════════════════════════════════════════════════════════════════════════════

def _get_redis():
    """คืน Redis client จาก Django cache backend"""
    try:
        from django.core.cache import cache
        # ดึง redis client โดยตรง
        client = cache._cache.get_client()
        return client
    except Exception:
        try:
            import redis as redis_lib
            from django.conf import settings
            url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            return redis_lib.from_url(url, decode_responses=False)
        except Exception as e:
            logger.warning("ไม่สามารถเชื่อมต่อ Redis: %s", e)
            return None


def _redis_available() -> bool:
    """ตรวจว่า Redis พร้อมใช้งาน"""
    try:
        from django.core.cache import cache
        cache.set("_ping", "1", timeout=5)
        return cache.get("_ping") == "1"
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Serialization Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _df_to_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame → bytes (pickle — เร็วกว่า parquet สำหรับ small data)"""
    return pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)


def _bytes_to_df(data: bytes) -> pd.DataFrame:
    """bytes → DataFrame"""
    return pickle.loads(data)


def _dict_to_bytes(d: dict) -> bytes:
    return pickle.dumps(d, protocol=pickle.HIGHEST_PROTOCOL)


def _bytes_to_dict(data: bytes) -> dict:
    return pickle.loads(data)


# ═══════════════════════════════════════════════════════════════════════════════
# Individual Indicator Cache
# ═══════════════════════════════════════════════════════════════════════════════

class IndicatorCache:
    """
    Cache layer สำหรับ indicators
    Fallback to DB ถ้า Redis ไม่พร้อม
    """

    def __init__(self):
        self._available = None  # lazy check

    def _is_available(self) -> bool:
        if self._available is None:
            self._available = _redis_available()
        return self._available

    # ── Django Cache API (ง่าย reliable) ──────────────────────────────────────

    def get_latest_indicator(self, symbol_id: int) -> Optional[dict]:
        """ดึง indicator ล่าสุดของ symbol จาก cache"""
        if not self._is_available():
            return None
        try:
            from django.core.cache import cache
            data = cache.get(_key_ind_latest(symbol_id))
            return data
        except Exception as e:
            logger.debug("cache get ind error: %s", e)
            return None

    def set_latest_indicator(self, symbol_id: int, ind_dict: dict) -> bool:
        """บันทึก indicator ล่าสุดเข้า cache"""
        if not self._is_available():
            return False
        try:
            from django.core.cache import cache
            cache.set(_key_ind_latest(symbol_id), ind_dict, timeout=TTL_IND_LATEST)
            return True
        except Exception as e:
            logger.debug("cache set ind error: %s", e)
            return False

    def get_prev_indicator(self, symbol_id: int) -> Optional[dict]:
        """ดึง indicator วันก่อนหน้า (สำหรับตรวจ EMA cross)"""
        if not self._is_available():
            return None
        try:
            from django.core.cache import cache
            return cache.get(_key_ind_prev(symbol_id))
        except Exception:
            return None

    def set_prev_indicator(self, symbol_id: int, ind_dict: dict) -> bool:
        if not self._is_available():
            return False
        try:
            from django.core.cache import cache
            cache.set(_key_ind_prev(symbol_id), ind_dict, timeout=TTL_IND_LATEST)
            return True
        except Exception:
            return False

    def get_latest_price(self, symbol_id: int) -> Optional[dict]:
        """ดึงราคาล่าสุดจาก cache"""
        if not self._is_available():
            return None
        try:
            from django.core.cache import cache
            return cache.get(_key_price_latest(symbol_id))
        except Exception:
            return None

    def set_latest_price(self, symbol_id: int, price_dict: dict) -> bool:
        if not self._is_available():
            return False
        try:
            from django.core.cache import cache
            cache.set(_key_price_latest(symbol_id), price_dict, timeout=TTL_PRICE_LATEST)
            return True
        except Exception:
            return False

    # ── Batch Cache (DataFrame ทั้งตลาด) ──────────────────────────────────────

    def get_batch_indicators(self, exchange: str) -> Optional[pd.DataFrame]:
        """ดึง indicator DataFrame ทั้งตลาดจาก cache"""
        if not self._is_available():
            return None
        try:
            from django.core.cache import cache
            data = cache.get(_key_ind_batch(exchange))
            if data is None:
                return None
            return _bytes_to_df(data)
        except Exception as e:
            logger.debug("cache get batch error: %s", e)
            return None

    def set_batch_indicators(self, exchange: str, df: pd.DataFrame) -> bool:
        """บันทึก indicator DataFrame ทั้งตลาดเข้า cache"""
        if not self._is_available():
            return False
        try:
            from django.core.cache import cache
            cache.set(_key_ind_batch(exchange), _df_to_bytes(df), timeout=TTL_BATCH)
            logger.info("💾 Cached %d indicators for %s", len(df), exchange)
            return True
        except Exception as e:
            logger.debug("cache set batch error: %s", e)
            return False

    def get_price_history(self, symbol_id: int) -> Optional[pd.DataFrame]:
        """ดึงราคาย้อนหลังจาก cache"""
        if not self._is_available():
            return None
        try:
            from django.core.cache import cache
            data = cache.get(_key_price_hist(symbol_id))
            if data is None:
                return None
            return _bytes_to_df(data)
        except Exception:
            return None

    def set_price_history(self, symbol_id: int, df: pd.DataFrame) -> bool:
        if not self._is_available():
            return False
        try:
            from django.core.cache import cache
            cache.set(_key_price_hist(symbol_id), _df_to_bytes(df), timeout=TTL_PRICE_HIST)
            return True
        except Exception:
            return False

    def invalidate_symbol(self, symbol_id: int):
        """ล้าง cache ของหุ้น 1 ตัว (เรียกหลัง load_prices)"""
        if not self._is_available():
            return
        try:
            from django.core.cache import cache
            cache.delete_many([
                _key_ind_latest(symbol_id),
                _key_ind_prev(symbol_id),
                _key_price_latest(symbol_id),
                _key_price_hist(symbol_id),
            ])
        except Exception:
            pass

    def invalidate_exchange(self, exchange: str):
        """ล้าง batch cache ของตลาด (เรียกหลัง run_engine)"""
        if not self._is_available():
            return
        try:
            from django.core.cache import cache
            cache.delete(_key_ind_batch(exchange))
            logger.info("🗑️  Invalidated batch cache: %s", exchange)
        except Exception:
            pass

    def stats(self) -> dict:
        """สถิติ cache"""
        if not self._is_available():
            return {"available": False}
        try:
            from django.core.cache import cache
            return {
                "available": True,
                "backend":   str(type(cache).__name__),
            }
        except Exception:
            return {"available": False}


# Singleton
indicator_cache = IndicatorCache()


# ═══════════════════════════════════════════════════════════════════════════════
# Cache-Aware Bulk Load (ใช้ใน scanner_engine)
# ═══════════════════════════════════════════════════════════════════════════════

def cached_load_latest_indicators(symbol_ids: list[int]) -> pd.DataFrame:
    """
    โหลด indicator ล่าสุด — ตรวจ cache ก่อน ค่อย fallback DB

    Strategy:
      1. ตรวจ batch cache ก่อน (ถ้ามี return ทันที)
      2. ตรวจ per-symbol cache
      3. Query DB สำหรับที่ไม่มีใน cache
      4. เก็บผลลัพธ์ใน cache
    """
    from radar.models import Indicator
    from django.db.models import OuterRef, Subquery

    results = {}
    miss_ids = []

    # ── ตรวจ per-symbol cache ─────────────────────────────────────────────────
    for sid in symbol_ids:
        cached = indicator_cache.get_latest_indicator(sid)
        if cached is not None:
            results[sid] = cached
        else:
            miss_ids.append(sid)

    cache_hit  = len(symbol_ids) - len(miss_ids)
    cache_miss = len(miss_ids)

    if cache_hit > 0:
        logger.debug("Cache hit: %d/%d indicators", cache_hit, len(symbol_ids))

    # ── Query DB สำหรับ miss ──────────────────────────────────────────────────
    if miss_ids:
        # 1. หาคู่ (symbol_id, max_date) ล่าสุด
        # SQLite ทำงานได้ดีกับ Subquery แบบพื้นฐาน
        from django.db.models import Max
        
        # แบ่ง miss_ids เป็นชุดละ 100 เพื่อกันเหนียวสำหรับ SQLite
        def chunk(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        
        for batch_ids in chunk(miss_ids, 100):
            sq = Indicator.objects.filter(
                symbol_id=OuterRef("symbol_id")
            ).order_by("-date").values("date")[:1]

            qs = (Indicator.objects
                  .filter(symbol_id__in=batch_ids)
                  .filter(date=Subquery(sq))
                  .values("symbol_id","date","ema20","ema50","ema200",
                          "rsi","macd_hist","atr14","atr_avg30","adx14",
                          "di_plus","di_minus","highest_high_20","lowest_low_20",
                          "volume_avg20"))

            for row in qs:
                sid = row["symbol_id"]
                d = {}
                for k, v in row.items():
                    if k == "symbol_id": continue
                    elif v is None: d[k] = None
                    elif hasattr(v, 'isoformat'): d[k] = str(v)
                    else:
                        try: d[k] = float(v)
                        except: d[k] = str(v)
                results[sid] = d
                indicator_cache.set_latest_indicator(sid, d)

    if not results:
        return pd.DataFrame()

    # ── แปลงเป็น DataFrame ───────────────────────────────────────────────────
    rows = [{"symbol_id": sid, **d} for sid, d in results.items()]
    df   = pd.DataFrame(rows)

    float_cols = ["ema20","ema50","ema200","rsi","macd_hist","atr14","atr_avg30",
                  "adx14","di_plus","di_minus","highest_high_20","lowest_low_20"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def cached_load_latest_prices(symbol_ids: list[int]) -> pd.DataFrame:
    """โหลดราคาล่าสุด — cache-aware"""
    from radar.models import PriceDaily
    from django.db.models import OuterRef, Subquery

    results = {}
    miss_ids = []

    for sid in symbol_ids:
        cached = indicator_cache.get_latest_price(sid)
        if cached is not None:
            results[sid] = cached
        else:
            miss_ids.append(sid)

    if miss_ids:
        from django.db.models import Max
        
        def chunk(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
                
        for batch_ids in chunk(miss_ids, 100):
            sq = PriceDaily.objects.filter(
                symbol_id=OuterRef("symbol_id")
            ).order_by("-date").values("date")[:1]

            qs = (PriceDaily.objects
                  .filter(symbol_id__in=batch_ids)
                  .filter(date=Subquery(sq))
                  .values("symbol_id","date","high","low","close","volume"))

            for row in qs:
                sid = row["symbol_id"]
                d   = {
                    "date":   str(row["date"]),
                    "high":   float(row["high"]),
                    "low":    float(row["low"]),
                    "close":  float(row["close"]),
                    "volume": float(row["volume"]),
                }
                results[sid] = d
                indicator_cache.set_latest_price(sid, d)

    if not results:
        return pd.DataFrame()

    rows = [{"symbol_id": sid, **d} for sid, d in results.items()]
    df   = pd.DataFrame(rows)
    for col in ["high","low","close","volume"]:
        df[col] = df[col].astype(float)
    return df


def cached_load_prev_indicators(symbol_ids: list[int]) -> pd.DataFrame:
    """โหลด indicator วันก่อนหน้า — cache-aware (สำหรับ EMA cross)"""
    from radar.models import Indicator
    from django.db.models import OuterRef, Subquery

    results = {}
    miss_ids = []

    for sid in symbol_ids:
        cached = indicator_cache.get_prev_indicator(sid)
        if cached is not None:
            results[sid] = cached
        else:
            miss_ids.append(sid)

    if miss_ids:
        sq = Indicator.objects.filter(
            symbol_id=OuterRef("symbol_id")
        ).order_by("-date").values("date")[1:2]

        qs = (Indicator.objects
              .filter(symbol_id__in=miss_ids)
              .filter(date=Subquery(sq))
              .values("symbol_id","ema50","ema200"))

        for row in qs:
            sid = row["symbol_id"]
            d   = {
                "ema50_prev":  float(row["ema50"])  if row["ema50"]  else None,
                "ema200_prev": float(row["ema200"]) if row["ema200"] else None,
            }
            results[sid] = d
            indicator_cache.set_prev_indicator(sid, d)

    if not results:
        return pd.DataFrame(columns=["symbol_id","ema50_prev","ema200_prev"])

    rows = [{"symbol_id": sid, **d} for sid, d in results.items()]
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# Cache Warm-up — เรียกหลัง run_engine เพื่อ pre-populate cache
# ═══════════════════════════════════════════════════════════════════════════════

def warm_up_cache(exchange: Optional[str] = None) -> dict:
    """
    Pre-populate indicator cache หลัง run_engine เสร็จ
    ทำให้ Scanner request ต่อไปเร็วขึ้นทันที

    เรียกใช้:
        from radar.indicator_cache import warm_up_cache
        warm_up_cache("SET")
        warm_up_cache("US")
    """
    from radar.models import Symbol, Indicator, PriceDaily
    from django.db.models import OuterRef, Subquery
    import time

    t0 = time.perf_counter()

    qs = Symbol.objects.all()
    if exchange:
        qs = qs.filter(exchange__in=["NASDAQ","NYSE"]) if exchange.upper()=="US" \
             else qs.filter(exchange=exchange.upper())

    symbol_ids = list(qs.values_list("id", flat=True))
    if not symbol_ids:
        return {"warmed": 0, "elapsed": 0}

    # Bulk load indicators
    sq_ind = Indicator.objects.filter(
        symbol_id=OuterRef("symbol_id")
    ).order_by("-date").values("date")[:1]

    inds = list(Indicator.objects
                .filter(symbol_id__in=symbol_ids)
                .filter(date=Subquery(sq_ind))
                .values("symbol_id","date","ema20","ema50","ema200",
                        "rsi","macd_hist","atr14","atr_avg30","adx14",
                        "di_plus","di_minus","highest_high_20","lowest_low_20",
                        "volume_avg20"))

    # Bulk load prices
    sq_pr = PriceDaily.objects.filter(
        symbol_id=OuterRef("symbol_id")
    ).order_by("-date").values("date")[:1]

    prices = list(PriceDaily.objects
                  .filter(symbol_id__in=symbol_ids)
                  .filter(date=Subquery(sq_pr))
                  .values("symbol_id","date","high","low","close","volume"))

    # เก็บใน cache
    warmed = 0
    for row in inds:
        sid = row["symbol_id"]
        d = {}
        for k, v in row.items():
            if k == "symbol_id":
                continue
            elif v is None:
                d[k] = None
            elif hasattr(v, 'isoformat'):   # date / datetime
                d[k] = str(v)
            else:
                try:
                    d[k] = float(v)
                except (TypeError, ValueError):
                    d[k] = str(v)
        if indicator_cache.set_latest_indicator(sid, d):
            warmed += 1

    for row in prices:
        sid = row["symbol_id"]
        d   = {
            "date":   str(row["date"]),
            "high":   float(row["high"]),
            "low":    float(row["low"]),
            "close":  float(row["close"]),
            "volume": float(row["volume"]),
        }
        indicator_cache.set_latest_price(sid, d)

    elapsed = time.perf_counter() - t0
    logger.info("🔥 Cache warm-up: %d symbols | %.2fs", warmed, elapsed)

    return {
        "warmed":      warmed,
        "elapsed_sec": round(elapsed, 3),
        "exchange":    exchange or "ALL",
    }


from typing import Optional
