"""
Views — Symbols, Prices, Indicators, Signals, Scanner, Backtest
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from django.utils import timezone
from rest_framework import generics, filters
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from ..decorators import pro_required
from ..throttles import ScannerThrottle, BacktestThrottle
from ..models import Symbol, PriceDaily, Indicator, Signal
from ..serializers import (
    SymbolSerializer, PriceDailySerializer,
    IndicatorSerializer, SignalSerializer,
)


# ─── Symbols ──────────────────────────────────────────────────────────────────

class SymbolListView(generics.ListAPIView):
    serializer_class = SymbolSerializer
    filter_backends  = [filters.OrderingFilter]
    ordering_fields  = ["symbol", "exchange", "sector"]
    ordering         = ["symbol"]

    def get_queryset(self):
        from django.db.models import Case, When, IntegerField, Value, Q
        qs = Symbol.objects.all()
        p  = self.request.query_params
        ex = p.get("exchange")
        sc = p.get("sector")
        search = p.get("search", "").strip()
        if ex:
            qs = qs.filter(exchange__in=["NASDAQ","NYSE"]) if ex.upper()=="US" \
                 else qs.filter(exchange=ex.upper())
        if sc:
            qs = qs.filter(sector__icontains=sc)
        if search:
            qs = qs.filter(
                Q(symbol__icontains=search) | Q(name__icontains=search)
            ).annotate(
                _priority=Case(
                    When(symbol__iexact=search, then=Value(0)),
                    When(symbol__istartswith=search, then=Value(1)),
                    When(symbol__icontains=search, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            ).order_by("_priority", "symbol")
        return qs

    def get_paginator(self):
        # รองรับ ?page_size=N จาก frontend autocomplete
        page_size = self.request.query_params.get("page_size")
        if page_size:
            from rest_framework.pagination import PageNumberPagination
            p = PageNumberPagination()
            p.page_size = min(int(page_size), 50)
            return p
        return super().get_paginator()


# ─── Prices ───────────────────────────────────────────────────────────────────

class PriceListView(generics.ListAPIView):
    serializer_class = PriceDailySerializer
    pagination_class = None

    def get_queryset(self):
        symbol = self.kwargs["symbol"].upper()
        days   = int(self.request.query_params.get("days", 365))
        start  = date.today() - timedelta(days=days)
        return (PriceDaily.objects
                .filter(symbol__symbol=symbol, date__gte=start)
                .order_by("-date"))


# ─── Indicators ───────────────────────────────────────────────────────────────

class IndicatorListView(generics.ListAPIView):
    serializer_class = IndicatorSerializer
    pagination_class = None

    def get_queryset(self):
        symbol = self.kwargs["symbol"].upper()
        days   = int(self.request.query_params.get("days", 365))
        start  = date.today() - timedelta(days=days)
        return (Indicator.objects
                .filter(symbol__symbol=symbol, date__gte=start)
                .order_by("-date"))


# ─── Signals ──────────────────────────────────────────────────────────────────

class SignalListView(generics.ListAPIView):
    serializer_class = SignalSerializer

    def get_queryset(self):
        qs = Signal.objects.select_related("symbol").order_by("-score", "-created_at")
        p  = self.request.query_params

        if p.get("signal_type"): qs = qs.filter(signal_type=p["signal_type"].upper())
        if p.get("direction"):
            qs = qs.filter(direction=p["direction"].upper())
        if p.get("exchange"):
            ex = p["exchange"].upper()
            qs = qs.filter(symbol__exchange__in=["NASDAQ","NYSE"]) if ex=="US" \
                 else qs.filter(symbol__exchange=ex)
        if p.get("min_score"):   qs = qs.filter(score__gte=float(p["min_score"]))
        if p.get("min_adx"):     qs = qs.filter(adx_at_signal__gte=float(p["min_adx"]))
        if p.get("days"):
            since = timezone.now() - timedelta(days=int(p["days"]))
            qs = qs.filter(created_at__gte=since)

        # dedup: เก็บเฉพาะ signal ที่ดีที่สุดต่อ 1 symbol
        limit = int(p.get("page_size", 200))
        seen: set = set()
        deduped = []
        for s in qs:
            sym = s.symbol_id
            if sym not in seen:
                seen.add(sym)
                deduped.append(s)
            if len(deduped) >= limit:
                break
        return deduped


# ─── Scanner (Pro) ────────────────────────────────────────────────────────────

@api_view(["GET"])
@throttle_classes([ScannerThrottle])
def scanner_view(request):
    """
    GET /api/scanner/
    Params: exchange, signal_type, direction, min_score, min_adx,
            min_rsi, max_rsi, filter_adx, filter_volume,
            strategy_name, formula
    """
    p = request.query_params
    from radar.strategies import Strategy, StrategyCondition

    # ── เลือก symbols ─────────────────────────────────────────────────────────
    sym_qs = Symbol.objects.all()
    if p.get("exchange"):
        ex = p["exchange"].upper()
        sym_qs = sym_qs.filter(exchange__in=["NASDAQ","NYSE"]) if ex=="US" \
                 else sym_qs.filter(exchange=ex)

    # ── โหลดข้อมูลแบบ Batch ───────────────────────────────────────────────────
    symbol_ids = list(sym_qs.values_list("id", flat=True))
    if not symbol_ids:
        return Response({"count": 0, "results": []})

    from radar.indicator_cache import (
        cached_load_latest_indicators,
        cached_load_latest_prices,
        cached_load_prev_indicators,
    )
    ind_df    = cached_load_latest_indicators(symbol_ids)
    prev_df   = cached_load_prev_indicators(symbol_ids)
    price_lat = cached_load_latest_prices(symbol_ids)

    # ── Merge & Scan ──────────────────────────────────────────────────────────
    # ถ้าไม่มีราคาเลย ถึงจะคืนค่าว่าง
    if price_lat.empty:
        return Response({"count": 0, "results": []})

    # ใช้ left merge เพื่อให้ข้อมูล symbol_id ไม่หล่นหาย แม้ไม่มี indicator
    df = (price_lat
          .merge(ind_df,  on="symbol_id", how="left")
          .merge(prev_df, on="symbol_id", how="left"))

    # เติมค่า 0 สำหรับฟิลด์ที่เป็นตัวเลขเพื่อไม่ให้การสแกนพัง
    # (ยกเว้น close ที่ต้องการค่าจริง)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # ใช้ Strategy หรือ Formula ถ้ามี
    if p.get("formula"):
        custom_strat = Strategy(
            name="CUSTOM",
            conditions=[StrategyCondition("Custom", p["formula"])]
        )
        res_df = custom_strat.apply(df)
    elif p.get("strategy_name"):
        from radar.strategies import run_strategy_scan
        res_df = run_strategy_scan(df, p["strategy_name"])
    else:
        # กรณีไม่ได้ระบุเงื่อนไขใดๆ (เช่น กดกรองเปล่าๆ)
        # ให้คืนค่าหุ้นทั้งหมดที่มีราคา พร้อมสถานะ NEUTRAL
        from radar.scanner_engine import scan_signals_vectorized
        res_df = scan_signals_vectorized(df)

        # ถ้า scan_signals_vectorized ไม่คืนอะไรเลย (เพราะไม่มีสัญญาณ)
        # ให้เราสร้าง DataFrame พื้นฐานจาก df เพื่อแสดงรายชื่อหุ้น
        if res_df.empty and not df.empty:
            res_df = df.copy()
            res_df['direction'] = 'NEUTRAL'
            res_df['signal_type'] = ''
            res_df['score'] = 0.0
            # กรองเฉพาะตัวที่มีราคาจริง (ไม่ใช่ 0 จากการ fillna)
            res_df = res_df[res_df['close'] > 0]

    # ── Filter Results ────────────────────────────────────────────────────────
    # กรองตาม params เพิ่มเติม
    if p.get("direction"):
        res_df = res_df[res_df['direction'] == p["direction"].upper()]

    # กรองคะแนนเฉพาะเมื่อมีการระบุสูตรหรือกลยุทธ์ หรือถ้าเรามีสัญญาณจริง
    # ถ้าเป็นการ fallback (signal_type ว่าง) ให้ข้ามการกรอง min_score
    if p.get("min_score"):
        min_s = float(p["min_score"])
        if p.get("strategy_name") or p.get("formula"):
            res_df = res_df[res_df['score'] >= min_s]
        else:
            res_df = res_df[(res_df['score'] >= min_s) | (res_df['signal_type'] == "")]

    # กรองเพิ่มเติมตาม flag ADX/Volume
    if p.get("filter_adx") == "true" and "adx14" in res_df.columns:
        res_df = res_df[res_df["adx14"] >= 25]
    if p.get("filter_volume") == "true" and "volume" in res_df.columns and "volume_avg20" in res_df.columns:
        res_df = res_df[res_df["volume"] >= res_df["volume_avg20"] * 1.5]

    # ── Build Final Rows ──────────────────────────────────────────────────────
    # ดึงข้อมูล Symbol มาประกอบ
    sym_map = {s.id: s for s in Symbol.objects.filter(id__in=res_df['symbol_id'].tolist())}

    rows = []
    for _, r in res_df.iterrows():
        sid = int(r['symbol_id'])
        sym = sym_map.get(sid)
        if not sym: continue

        close_val     = float(r['close'])
        stop_val      = float(r['stop_loss']) if not pd.isna(r.get('stop_loss')) else None
        adx_val       = float(r['adx14'])      if not pd.isna(r.get('adx14'))     else None
        vol_val       = float(r['volume'])     if not pd.isna(r.get('volume'))    else None
        vol_avg_val   = float(r['volume_avg20']) if not pd.isna(r.get('volume_avg20')) else None
        atr_val       = float(r['atr14'])      if not pd.isna(r.get('atr14'))     else None
        atr_avg_val   = float(r['atr_avg30'])  if not pd.isna(r.get('atr_avg30')) else None

        filter_adx_ok  = bool(adx_val and adx_val >= 25)
        filter_vol_ok  = bool(vol_val and vol_avg_val and vol_val >= vol_avg_val * 1.5)
        filter_atr_ok  = bool(atr_val and atr_avg_val and atr_val >= atr_avg_val)
        risk_pct_val   = round((close_val - stop_val) / close_val * 100, 2) \
                         if stop_val and stop_val > 0 and close_val > 0 else None

        row = {
            "symbol":             sym.symbol,
            "name":               sym.name,
            "exchange":           sym.exchange,
            "sector":             sym.sector,
            "close":              close_val,
            "score":              float(r['score']),
            "direction":          r['direction'],
            "signal_type":        r['signal_type'],
            "rsi":                float(r['rsi']) if not pd.isna(r.get('rsi')) else None,
            "adx14":              adx_val,
            "stop_loss":          stop_val,
            "filter_adx":         filter_adx_ok,
            "filter_volume":      filter_vol_ok,
            "filter_volatility":  filter_atr_ok,
            "risk_pct":           risk_pct_val,
        }
        rows.append(row)

    return Response({"count": len(rows), "results": rows})


# ─── Scanner Run ──────────────────────────────────────────────────────────────

@api_view(["POST"])
@throttle_classes([ScannerThrottle])
def run_scanner_api(request):
    """POST /api/scanner/run/ — พร้อม WebSocket broadcast"""
    exchange = request.data.get("exchange")
    try:
        from radar.scanner_engine import run_quick_scan
        from radar.broadcaster import broadcast_scanner_done, broadcast_stats
        import time

        t0 = time.perf_counter()
        result = run_quick_scan(exchange=exchange, limit=2000, run_indicators=False, user=request.user)
        elapsed = time.perf_counter() - t0

        # Broadcast ผลลัพธ์ไปยัง WebSocket clients
        broadcast_scanner_done(
            signals=result.get("signals", 0),
            elapsed=elapsed,
            exchange=exchange or "ALL",
        )
        broadcast_stats()

        return Response({"status":"สำเร็จ","result": result})
    except Exception as e:
        return Response({"status":"ล้มเหลว","error":str(e)}, status=500)


# ─── Backtest ─────────────────────────────────────────────────────────────────

@api_view(["POST"])
@throttle_classes([BacktestThrottle])
@pro_required
def run_backtest_api(request):
    """POST /api/backtest/"""
    from radar.backtest_engine import BacktestConfig, run_backtest

    data   = request.data
    symbol = data.get("symbol","").upper()
    if not symbol:
        return Response({"error":"กรุณาระบุ symbol"}, status=400)
    try:
        end_date   = date.fromisoformat(data["end"])   if data.get("end")   else date.today()
        start_date = date.fromisoformat(data["start"]) if data.get("start") else end_date - timedelta(days=365)
    except ValueError:
        return Response({"error":"รูปแบบวันที่ไม่ถูกต้อง YYYY-MM-DD"}, status=400)

    cfg = BacktestConfig(
        symbol=symbol, start_date=start_date, end_date=end_date,
        initial_capital=float(data.get("capital",   100_000)),
        mode=data.get("mode","both"),
        strategy_name=data.get("strategy"),
        stop_loss=float(data.get("sl",   5.0)),
        take_profit=float(data.get("tp", 10.0)),
        commission=float(data.get("commission", 0.15)),
        position_pct=float(data.get("position_pct", 100.0)),
    )
    try:
        results = run_backtest(cfg)
        return Response({"status":"สำเร็จ","symbol":symbol,"results":results})
    except ValueError as e:
        return Response({"error":str(e)}, status=404)
    except Exception as e:
        return Response({"error":f"คำนวณล้มเหลว: {e}"}, status=500)
