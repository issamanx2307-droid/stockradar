"""
Scanner Engine — Pro Version (Batch Vectorized)
================================================
Architecture:
  1. Bulk Load    — 1 SQL query ต่อ table (ไม่ใช้ loop)
  2. Vectorized   — pandas groupby compute indicators
  3. Boolean Mask — scan signals ทุกหุ้นพร้อมกัน
  4. Bulk Create  — 1 INSERT สำหรับ signals ทั้งหมด
  5. Celery Chord — parallel chunks สำหรับ 10,000+ หุ้น

Performance:
  600 หุ้น   → <5s  (single process)
  10,000 หุ้น → <60s (4 Celery workers)
"""

import logging
import time
from decimal import Decimal
from typing import Optional
from django.contrib.auth.models import User

import numpy as np
import pandas as pd
# Celery optional — ใช้งานได้แม้ไม่มี celery (ใช้ sync mode แทน)
try:
    from celery import chord, group, shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Stub decorators สำหรับกรณีที่ไม่มี celery
    def shared_task(*args, **kwargs):
        def decorator(fn):
            fn.delay = fn
            fn.s = fn
            return fn
        return decorator if args and callable(args[0]) else decorator
    chord = group = None
from django.db import transaction
from django.utils import timezone

from radar.indicator_engine import (
    calc_ema, calc_rsi, calc_macd, calc_atr, calc_adx, calc_hh_ll,
)
from radar.strategies import run_strategy_scan, Strategy
from radar.alerts import alert_service

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
ADX_MIN          = 25.0
VOL_RATIO_MIN    = 0.8
ATR_RATIO_MIN    = 1.0
EMA_PULLBACK_PCT = 0.015
SL_ATR_MULT      = 1.5
MIN_SCORE        = 50.0
CHUNK_SIZE       = 200


# ═══════════════════════════════════════════════════════════════════════════════
# Bulk Load — 1 SQL query ต่อ table
# ═══════════════════════════════════════════════════════════════════════════════

def _bulk_load_prices(symbol_ids: list[int], days: int = 300) -> pd.DataFrame:
    from radar.models import PriceDaily
    from datetime import date, timedelta
    since = date.today() - timedelta(days=days)
    qs = (PriceDaily.objects
          .filter(symbol_id__in=symbol_ids, date__gte=since)
          .order_by("symbol_id","date")
          .values("symbol_id","date","open","high","low","close","volume"))
    df = pd.DataFrame(list(qs))
    if df.empty: return df
    for c in ["open","high","low","close"]: df[c] = df[c].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df


def _bulk_load_latest_ind(symbol_ids: list[int]) -> pd.DataFrame:
    from radar.models import Indicator
    from django.db.models import OuterRef, Subquery
    sq = Indicator.objects.filter(symbol_id=OuterRef("symbol_id")).order_by("-date").values("date")[:1]
    qs = (Indicator.objects.filter(symbol_id__in=symbol_ids)
          .filter(date=Subquery(sq))
          .values("symbol_id","ema20","ema50","ema200","rsi","macd_hist",
                  "atr14","atr_avg30","adx14","di_plus","di_minus",
                  "highest_high_20","lowest_low_20","volume_avg20"))
    df = pd.DataFrame(list(qs))
    if df.empty: return df
    for c in ["ema20","ema50","ema200","rsi","macd_hist","atr14","atr_avg30",
              "adx14","di_plus","di_minus","highest_high_20","lowest_low_20"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _bulk_load_prev_ind(symbol_ids: list[int]) -> pd.DataFrame:
    from radar.models import Indicator
    from django.db.models import OuterRef, Subquery
    sq = Indicator.objects.filter(symbol_id=OuterRef("symbol_id")).order_by("-date").values("date")[1:2]
    qs = (Indicator.objects.filter(symbol_id__in=symbol_ids)
          .filter(date=Subquery(sq))
          .values("symbol_id","ema50","ema200"))
    df = pd.DataFrame(list(qs))
    if df.empty: return pd.DataFrame(columns=["symbol_id","ema50_prev","ema200_prev"])
    df = df.rename(columns={"ema50":"ema50_prev","ema200":"ema200_prev"})
    for c in ["ema50_prev","ema200_prev"]: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[["symbol_id","ema50_prev","ema200_prev"]]


def _bulk_load_latest_price(symbol_ids: list[int]) -> pd.DataFrame:
    from radar.models import PriceDaily
    from django.db.models import OuterRef, Subquery
    sq = PriceDaily.objects.filter(symbol_id=OuterRef("symbol_id")).order_by("-date").values("date")[:1]
    qs = (PriceDaily.objects.filter(symbol_id__in=symbol_ids)
          .filter(date=Subquery(sq))
          .values("symbol_id","date","high","low","close","volume"))
    df = pd.DataFrame(list(qs))
    if df.empty: return df
    for c in ["high","low","close"]: df[c] = df[c].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Vectorized Indicator Compute
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_batch(price_df: pd.DataFrame) -> pd.DataFrame:
    """groupby vectorized — คืนแถวล่าสุดของแต่ละหุ้นพร้อม indicators"""
    def _apply(grp):
        grp = grp.sort_values("date").copy()
        c, h, lo, v = grp["close"], grp["high"], grp["low"], grp["volume"]
        grp["ema20"]  = calc_ema(c,20)
        grp["ema50"]  = calc_ema(c,50)
        grp["ema200"] = calc_ema(c,200)
        grp["rsi"]    = calc_rsi(c)
        grp["macd"], grp["macd_signal"], grp["macd_hist"] = calc_macd(c)
        grp["atr14"]  = calc_atr(h,lo,c)
        grp["atr_avg30"] = grp["atr14"].rolling(30,min_periods=30).mean()
        grp["adx14"], grp["di_plus"], grp["di_minus"] = calc_adx(h,lo,c)
        grp["highest_high_20"], grp["lowest_low_20"] = calc_hh_ll(h,lo)
        grp["volume_avg20"] = v.rolling(20,min_periods=20).mean()
        return grp.iloc[[-1]]

    return (price_df.sort_values(["symbol_id","date"])
            .groupby("symbol_id", group_keys=False)
            .apply(_apply, include_groups=False)
            .reset_index(drop=True))


# ═══════════════════════════════════════════════════════════════════════════════
# Vectorized Signal Scan — Zero Python Loops
# ═══════════════════════════════════════════════════════════════════════════════

def scan_signals_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    สร้าง signals ทุกหุ้นพร้อมกันด้วย boolean masks
    Zero Python loops
    """
    if df.empty: return pd.DataFrame()

    c     = df["close"]
    e20   = df["ema20"].fillna(0)
    e50   = df["ema50"].fillna(0)
    e200  = df["ema200"].fillna(0)
    e50p  = df.get("ema50_prev",  pd.Series(0.0, index=df.index)).fillna(0)
    e200p = df.get("ema200_prev", pd.Series(0.0, index=df.index)).fillna(0)
    adx   = df["adx14"].fillna(0)
    rsi   = df["rsi"].fillna(50)
    atr   = df["atr14"].fillna(0)
    atr30 = df["atr_avg30"].fillna(0)
    hh20  = df["highest_high_20"].fillna(0)
    vol   = df["volume"].fillna(0)
    va20  = df["volume_avg20"].fillna(0)

    # ── Filters ───────────────────────────────────────────────────────────────
    f_vol = (va20 > 0) & (vol > va20 * VOL_RATIO_MIN)
    f_atr = (atr30 > 0) & (atr > atr30 * ATR_RATIO_MIN)
    f_adx = adx > ADX_MIN

    # ── Strategy Masks ────────────────────────────────────────────────────────
    golden   = (e50p > 0) & (e200p > 0) & (e50p <= e200p) & (e50 > e200)
    death    = (e50p > 0) & (e200p > 0) & (e50p >= e200p) & (e50 < e200)
    align    = (e20 > e50) & (e50 > e200) & (e200 > 0)
    pullback = align & (c > e200) & (e20 > 0) & ((c - e20).abs() / e20.replace(0,np.nan) <= EMA_PULLBACK_PCT)
    breakout = (hh20 > 0) & (c > hh20) & f_vol
    oversold   = (rsi < 30) & (c > e200) & (e200 > 0)
    overbought = (rsi > 70) & (c < e200) & (e200 > 0)

    # ── Entry Conditions ──────────────────────────────────────────────────────
    long_ok     = (c > e200) & (e200 > 0) & f_vol        # ไม่บังคับ ADX
    long_strong = (c > e200) & (e200 > 0) & f_vol & f_adx # บังคับ ADX
    short_ok    = (c < e200) & (e200 > 0) & f_vol

    # ── Active Signals ────────────────────────────────────────────────────────
    sig_golden   = golden   & long_strong          # ต้องผ่าน ADX
    sig_death    = death    & short_ok
    sig_align    = align    & long_ok  & ~sig_golden        # ไม่บังคับ ADX
    sig_pullback = pullback & long_ok  & ~sig_golden & ~sig_align
    sig_breakout = breakout & (c > e200) & f_adx   # ต้องผ่าน ADX
    sig_oversold   = oversold   & f_vol & ~sig_golden
    sig_overbought = overbought & f_vol & ~sig_death

    # ── Score (vectorized, ไม่มี loop) ────────────────────────────────────────
    score = pd.Series(0.0, index=df.index)
    score = score.where(~sig_golden,   75 + f_adx.astype(int)*10 + f_vol.astype(int)*8 + (c>e200).astype(int)*5)
    score = score.where(~sig_death,    np.where(score>0, score, 73 + f_adx.astype(int)*10 + f_vol.astype(int)*8))
    score = score.where(~sig_align,    np.where(score>0, score, 68 + f_adx.astype(int)*12 + f_vol.astype(int)*8 + f_atr.astype(int)*7))
    score = score.where(~sig_pullback, np.where(score>0, score, 72 + f_adx.astype(int)*10 + f_vol.astype(int)*8))
    score = score.where(~sig_breakout, np.where(score>0, score, 78 + f_adx.astype(int)*12 + f_atr.astype(int)*8))
    score = score.where(~sig_oversold,   np.where(score>0, score, 65 + f_vol.astype(int)*10))
    score = score.where(~sig_overbought, np.where(score>0, score, 63 + f_vol.astype(int)*10))
    score = score.clip(upper=100)

    # ── Signal Type ───────────────────────────────────────────────────────────
    s = pd.Series("", index=df.index)
    d = pd.Series("NEUTRAL", index=df.index)
    s[sig_oversold]   = "OVERSOLD";    d[sig_oversold]   = "LONG"
    s[sig_overbought] = "OVERBOUGHT";  d[sig_overbought] = "SHORT"
    s[sig_breakout]   = "BREAKOUT";    d[sig_breakout]   = "LONG"
    s[sig_pullback]   = "EMA_PULLBACK";d[sig_pullback]   = "LONG"
    s[sig_align]      = "EMA_ALIGNMENT";d[sig_align]     = "LONG"
    s[sig_death]      = "DEATH_CROSS"; d[sig_death]      = "SHORT"
    s[sig_golden]     = "GOLDEN_CROSS";d[sig_golden]     = "LONG"
    # Strong upgrade
    s = s.where(~((score >= 90) & (d == "LONG")),  "STRONG_BUY")
    s = s.where(~((score >= 90) & (d == "SHORT")), "STRONG_SELL")

    # ── Stop Loss (vectorized) ────────────────────────────────────────────────
    sl  = np.where(d=="LONG",  c - SL_ATR_MULT*atr,
          np.where(d=="SHORT", c + SL_ATR_MULT*atr, np.nan))
    rp  = np.where(atr>0, SL_ATR_MULT*atr/c*100, np.nan)
    vr  = np.where(va20>0, vol/va20.replace(0, np.nan), np.nan)

    # ── Filter & Return ───────────────────────────────────────────────────────
    mask = (s != "") & (score >= MIN_SCORE)
    out  = df[mask].copy()
    out["signal_type"]       = s[mask].values
    out["direction"]         = d[mask].values
    out["score"]             = score[mask].round(2).values
    out["stop_loss"]         = sl[mask]
    out["risk_pct"]          = np.round(rp[mask], 2)
    out["vol_ratio"]         = np.round(vr[mask], 2)
    out["filter_volume"]     = f_vol[mask].values
    out["filter_volatility"] = f_atr[mask].values
    out["filter_adx"]        = f_adx[mask].values

    return out.sort_values("score", ascending=False)


# ═══════════════════════════════════════════════════════════════════════════════
# Bulk Save Signals
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
def _bulk_save_signals(scan_df: pd.DataFrame, sym_map: dict) -> int:
    from radar.models import Signal

    if scan_df.empty: return 0

    def _d(v, p=4):
        try:
            f = float(v)
            return None if (np.isnan(f) or np.isinf(f)) else Decimal(str(round(f,p)))
        except: return None

    now     = timezone.now()
    signals = []
    for _, r in scan_df.iterrows():
        sym = sym_map.get(int(r.get("symbol_id",0)))
        if not sym: continue
        signals.append(Signal(
            symbol=sym, signal_type=str(r["signal_type"]),
            direction=str(r["direction"]),
            score=_d(r["score"],2) or Decimal("0"),
            price=_d(r["close"]) or Decimal("0"),
            stop_loss=_d(r.get("stop_loss")),
            risk_pct=_d(r.get("risk_pct"),2),
            atr_at_signal=_d(r.get("atr14")),
            adx_at_signal=_d(r.get("adx14"),2),
            volume_ratio=_d(r.get("vol_ratio"),2),
            filter_volume=bool(r.get("filter_volume",False)),
            filter_volatility=bool(r.get("filter_volatility",False)),
            filter_adx=bool(r.get("filter_adx",False)),
            created_at=now,
        ))
    if signals:
        Signal.objects.bulk_create(signals, batch_size=500)
        
        # ── ส่ง Alert สำหรับสัญญาณคะแนนสูง (Top 3 หรือ Score > 85) ─────────────
        try:
            high_scores = [s for s in signals if s.score >= 85]
            # ถ้าไม่มี > 85 เลย ให้เอาตัวที่คะแนนสูงสุด 3 อันดับแรก (ถ้าคะแนน > 75)
            if not high_scores:
                high_scores = sorted(signals, key=lambda x: x.score, reverse=True)[:3]
                high_scores = [s for s in high_scores if s.score >= 75]
                
            for s in high_scores:
                alert_service.send_signal(
                    symbol=s.symbol.symbol,
                    signal_type=s.signal_type,
                    score=float(s.score),
                    price=float(s.price),
                    direction=s.direction
                )
        except Exception as e:
            logger.error("การส่ง Alert ล้มเหลว: %s", e)

    return len(signals)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Batch Runner
# ═══════════════════════════════════════════════════════════════════════════════

def run_batch_scan(symbol_ids: list[int],
                   run_indicators: bool = False,
                   strategy_name: Optional[str] = None,
                   custom_strategy: Optional[Strategy] = None,
                   days: int = 300) -> dict:
    from radar.models import Symbol

    t0      = time.perf_counter()
    sym_map = {s.id: s for s in Symbol.objects.filter(id__in=symbol_ids)}
    if not sym_map: return {"scanned":0,"signals":0,"elapsed_sec":0}

    # 1. Load prices + compute indicators (ถ้าต้องการ)
    if run_indicators:
        price_df = _bulk_load_prices(symbol_ids, days)
        if not price_df.empty:
            from radar.indicator_engine import compute_all_indicators, save_indicators
            for sid, grp in price_df.groupby("symbol_id"):
                sym = sym_map.get(sid)
                if sym:
                    ind = compute_all_indicators(grp.copy())
                    save_indicators(sym, ind)

    # 2. Bulk load latest data (cache-aware — Redis ก่อน fallback DB)
    from radar.indicator_cache import (
        cached_load_latest_indicators,
        cached_load_latest_prices,
        cached_load_prev_indicators,
    )
    ind_df    = cached_load_latest_indicators(symbol_ids)
    prev_df   = cached_load_prev_indicators(symbol_ids)
    price_lat = cached_load_latest_prices(symbol_ids)

    if ind_df.empty or price_lat.empty:
        return {"scanned":len(symbol_ids),"signals":0,"elapsed_sec":0}

    # 3. Merge
    df = (price_lat
          .merge(ind_df,  on="symbol_id", how="inner")
          .merge(prev_df, on="symbol_id", how="left"))
    for col in ["ema50_prev","ema200_prev"]:
        if col not in df.columns:
            df[col] = 0.0

    # 4. Scan (ใช้ Strategy ใหม่ถ้ามีระบุมา)
    if custom_strategy:
        sig_df = custom_strategy.apply(df)
        sig_df = sig_df[sig_df['direction'] != 'NEUTRAL']
    elif strategy_name:
        sig_df = run_strategy_scan(df, strategy_name)
        sig_df = sig_df[sig_df['direction'] != 'NEUTRAL']
    else:
        sig_df = scan_signals_vectorized(df)

    # 5. Save
    n = _bulk_save_signals(sig_df, sym_map)

    elapsed = time.perf_counter() - t0
    return {
        "scanned":      len(symbol_ids),
        "signals":      n,
        "elapsed_sec":  round(elapsed,3),
        "per_stock_ms": round(elapsed/max(len(symbol_ids),1)*1000,2),
        "top_signals":  sig_df[["symbol_id","signal_type","direction","score","stop_loss","risk_pct","atr14","adx14"]].head(10).to_dict("records"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Celery Tasks
# ═══════════════════════════════════════════════════════════════════════════════

@shared_task(name="radar.scanner.process_chunk", bind=True, max_retries=2)
def process_chunk_task(self, symbol_ids: list[int], run_indicators: bool = False) -> dict:
    try:
        return run_batch_scan(symbol_ids, run_indicators)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@shared_task(name="radar.scanner.merge_results")
def merge_results_task(chunk_results: list[dict]) -> dict:
    total_s = sum(r.get("scanned",0) for r in chunk_results)
    total_n = sum(r.get("signals",0) for r in chunk_results)
    max_t   = max((r.get("elapsed_sec",0) for r in chunk_results), default=0)
    top_all = []
    for r in chunk_results: top_all.extend(r.get("top_signals",[]))
    top10 = sorted(top_all, key=lambda x: x.get("score",0), reverse=True)[:10]
    logger.info("🏁 %d stocks | %d signals | %.2fs", total_s, total_n, max_t)
    return {"total_scanned":total_s,"total_signals":total_n,"elapsed_sec":max_t,"top_signals":top10}


@shared_task(name="radar.scanner.run_full_scan")
def run_full_scan_task(exchange: Optional[str] = None, run_indicators: bool = False) -> str:
    from radar.models import Symbol
    qs = Symbol.objects.all()
    if exchange:
        qs = qs.filter(exchange__in=["NASDAQ","NYSE"]) if exchange.upper()=="US" \
             else qs.filter(exchange=exchange.upper())
    ids    = list(qs.values_list("id", flat=True))
    chunks = [ids[i:i+CHUNK_SIZE] for i in range(0, len(ids), CHUNK_SIZE)]
    logger.info("🚀 Full scan: %d stocks → %d chunks", len(ids), len(chunks))
    wf = chord(group(process_chunk_task.s(c, run_indicators) for c in chunks))(merge_results_task.s())
    return wf.id


# ═══════════════════════════════════════════════════════════════════════════════
# Quick Scan (Sync — ไม่ต้องการ Celery)
# ═══════════════════════════════════════════════════════════════════════════════

def run_quick_scan(exchange: Optional[str] = None,
                   limit: int = 10000,
                   run_indicators: bool = False,
                   user: Optional[User] = None) -> dict:
    from radar.models import Symbol
    qs = Symbol.objects.all()

    # ── Tier Limits ──
    is_pro = user.profile.is_pro if (user and hasattr(user, 'profile')) else False
    
    # สมาชิกฟรีสแกนได้เฉพาะตลาด SET
    if not is_pro:
        exchange = "SET"
        limit = min(limit, 200) # จำกัดจำนวนหุ้นสำหรับสายฟรี

    if exchange:
        qs = qs.filter(exchange__in=["NASDAQ","NYSE"]) if exchange.upper()=="US" \
             else qs.filter(exchange=exchange.upper())
    ids = list(qs.values_list("id", flat=True)[:limit])
    if not ids: return {"scanned":0,"signals":0,"elapsed_sec":0,"top_signals":[]}

    result = run_batch_scan(ids, run_indicators)

    # เพิ่ม symbol info
    from radar.models import Symbol as S
    info = {s.id:{"symbol":s.symbol,"name":s.name,"exchange":s.exchange}
            for s in S.objects.filter(id__in=ids).only("id","symbol","name","exchange")}
    for sig in result.get("top_signals",[]):
        sig.update(info.get(sig.get("symbol_id"),{}))

    return result
