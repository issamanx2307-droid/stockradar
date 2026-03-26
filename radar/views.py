"""
API Views — Pro Version
เพิ่ม stop_loss, direction, ADX, ATR ใน scanner response
"""

from datetime import date, timedelta
import re
import numpy as np
import pandas as pd
from django.core.cache import cache
from django.db import models
from django.db.models import Subquery, OuterRef
from django.utils import timezone
from rest_framework import generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .decorators import pro_required
from .models import (
    Symbol,
    PriceDaily,
    Indicator,
    Signal,
    Profile,
    BusinessProfile,
    StockTerm,
    TermQuestion,
)
from .serializers import (
    SymbolSerializer, PriceDailySerializer,
    IndicatorSerializer, SignalSerializer,
    UserSerializer, ProfileSerializer,
    BusinessProfileSerializer,
    StockTermSerializer,
    TermQuestionSerializer,
    TermQuestionCreateSerializer,
    PositionAnalyzeRequestSerializer,
)
from rest_framework.permissions import IsAuthenticated

# ─── Business Profile ─────────────────────────────────────────────────────────

@api_view(["GET"])
def business_profile_api(request):
    """ดึงข้อมูลธุรกิจสำหรับหน้าติดต่อเรา (สาธารณะ)"""
    profile = BusinessProfile.objects.first()
    if not profile:
        return Response({"error": "ไม่พบข้อมูลโพรไฟล์ธุรกิจ"}, status=404)
    return Response(BusinessProfileSerializer(profile).data)


def _normalize_term(value: str) -> str:
    return (value or "").strip().upper()


@api_view(["GET"])
def term_lookup(request):
    q = _normalize_term(request.query_params.get("q", ""))
    if not q:
        return Response({"error": "กรุณาระบุ q"}, status=400)

    cache_key = f"term:{q}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    obj = StockTerm.objects.filter(term=q).first()
    if not obj:
        return Response({"error": "ไม่พบคำศัพท์"}, status=404)

    data = StockTermSerializer(obj).data
    cache.set(cache_key, data, 60 * 60 * 24 * 30)
    return Response(data)


@api_view(["GET"])
def term_search(request):
    q_raw = (request.query_params.get("q", "") or "").strip()
    if not q_raw:
        return Response({"results": []})

    q = q_raw.upper()
    qs = (StockTerm.objects
          .filter(models.Q(term__icontains=q_raw) | models.Q(short_definition__icontains=q_raw))
          .order_by("-is_featured", "-priority", "term")[:20])

    return Response({"results": StockTermSerializer(qs, many=True).data})


@api_view(["GET"])
def featured_terms(request):
    qs = StockTerm.objects.filter(is_featured=True).order_by("-priority", "term")[:50]
    return Response({"results": StockTermSerializer(qs, many=True).data})


_TERM_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\_/]{1,20}")


def _extract_candidate_terms(text: str) -> list[str]:
    tokens = [t.upper() for t in _TERM_TOKEN_RE.findall(text or "")]
    seen = set()
    out = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:10]


@api_view(["POST"])
def qa_ask(request):
    serializer = TermQuestionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    question = serializer.validated_data["question"]

    candidates = _extract_candidate_terms(question)
    if candidates:
        found = StockTerm.objects.filter(term__in=candidates).order_by("-is_featured", "-priority").first()
        if found:
            return Response({"found": True, "term": StockTermSerializer(found).data})

    q_trim = (question or "").strip()
    if len(q_trim) >= 3:
        hit = (StockTerm.objects
               .filter(models.Q(term__icontains=q_trim) | models.Q(short_definition__icontains=q_trim) | models.Q(full_definition__icontains=q_trim))
               .order_by("-is_featured", "-priority", "term")
               .first())
        if hit:
            return Response({"found": True, "term": StockTermSerializer(hit).data})

    normalized_term = candidates[0] if candidates else ""
    asked_by = request.user if getattr(request, "user", None) and request.user.is_authenticated else None

    q_obj = TermQuestion.objects.create(
        asked_by=asked_by,
        question=question,
        normalized_term=normalized_term,
        status="NEW",
    )

    return Response({
        "found": False,
        "message": "ยังไม่มีคำตอบ ระบบได้ส่งคำถามไปให้ผู้ดูแลเพื่อเพิ่มคำตอบแล้ว",
        "ticket": TermQuestionSerializer(q_obj).data,
    }, status=202)


@api_view(["POST"])
def position_analyze_api(request):
    serializer = PositionAnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    symbol_code = (serializer.validated_data["symbol"] or "").strip().upper()
    buy_price = serializer.validated_data["buy_price"]

    sym = Symbol.objects.filter(symbol=symbol_code).first()
    if not sym:
        return Response({"error": "ไม่พบสัญลักษณ์หุ้น"}, status=404)

    from radar.services.position_analysis import analyze_position

    try:
        result = analyze_position(sym, buy_price=buy_price, user=request.user)
        return Response(result)
    except ValueError as e:
        if str(e) == "NO_MARKET_DATA":
            return Response({"error": "ยังไม่มีข้อมูลราคาตลาดสำหรับหุ้นนี้"}, status=404)
        return Response({"error": "วิเคราะห์ไม่สำเร็จ"}, status=400)
    except Exception:
        return Response({"error": "ระบบขัดข้องชั่วคราว"}, status=500)

# ─── Profile & User ───────────────────────────────────────────────────────────

@api_view(["GET", "PUT"])
def user_profile(request):
    """
    ดูข้อมูลโปรไฟล์และแก้ไขการตั้งค่า (Token แจ้งเตือน)
    """
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)
    
    profile = request.user.profile
    
    if request.method == "GET":
        return Response(UserSerializer(request.user).data)
    
    elif request.method == "PUT":
        # อนุญาตให้แก้ไขเฉพาะ Line/Telegram token
        profile.line_notify_token = request.data.get("line_notify_token", profile.line_notify_token)
        profile.telegram_chat_id = request.data.get("telegram_chat_id", profile.telegram_chat_id)
        profile.save()
        return Response(UserSerializer(request.user).data)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@api_view(["GET"])
def dashboard_summary(request):
    week_ago = timezone.now() - timedelta(days=7)

    base = Signal.objects.select_related("symbol").filter(created_at__gte=week_ago)

    # แยกตาม category
    buy_signals  = (base.filter(direction="LONG",
                                signal_type__in=["BUY","STRONG_BUY","GOLDEN_CROSS","EMA_ALIGNMENT","EMA_PULLBACK","OVERSOLD"])
                        .order_by("-score")[:50])
    sell_signals = (base.filter(direction="SHORT",
                                signal_type__in=["SELL","STRONG_SELL","DEATH_CROSS","BREAKDOWN","OVERBOUGHT"])
                        .order_by("-score")[:50])
    breakout_signals = (base.filter(signal_type="BREAKOUT")
                            .order_by("-score")[:50])
    watch_signals    = (base.filter(signal_type__in=["WATCH","ALERT"])
                            .order_by("-score")[:50])

    latest_signals = (Signal.objects.select_related("symbol")
                      .order_by("-created_at", "-score")[:20])
    top_bullish    = (base.filter(direction="LONG").order_by("-score")[:10])

    stats = {
        "total_symbols":  Symbol.objects.count(),
        "total_signals":  Signal.objects.count(),
        "buy_signals":    buy_signals.count(),
        "sell_signals":   sell_signals.count(),
        "breakout_count": breakout_signals.count(),
        "watch_count":    watch_signals.count(),
        "strong_signals": Signal.objects.filter(score__gte=80).count(),
    }

    return Response({
        "stats":            stats,
        "latest_signals":   SignalSerializer(latest_signals,    many=True).data,
        "top_bullish":      SignalSerializer(top_bullish,       many=True).data,
        "buy_signals":      SignalSerializer(buy_signals,       many=True).data,
        "sell_signals":     SignalSerializer(sell_signals,      many=True).data,
        "breakout_signals": SignalSerializer(breakout_signals,  many=True).data,
        "watch_signals":    SignalSerializer(watch_signals,     many=True).data,
    })


# ─── Symbols ──────────────────────────────────────────────────────────────────

class SymbolListView(generics.ListAPIView):
    serializer_class = SymbolSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["symbol", "name", "sector"]
    ordering_fields  = ["symbol", "exchange", "sector"]
    ordering         = ["symbol"]

    def get_queryset(self):
        qs = Symbol.objects.all()
        p  = self.request.query_params
        ex = p.get("exchange")
        sc = p.get("sector")
        if ex:
            qs = qs.filter(exchange__in=["NASDAQ","NYSE"]) if ex.upper()=="US" \
                 else qs.filter(exchange=ex.upper())
        if sc:
            qs = qs.filter(sector__icontains=sc)
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
        qs = Signal.objects.select_related("symbol").order_by("-created_at","-score")
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

        limit = int(p.get("page_size", 200))
        return qs[:limit]


# ─── Scanner (Pro) ────────────────────────────────────────────────────────────

@api_view(["GET"])
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

        row = {
            "symbol":    sym.symbol,
            "name":      sym.name,
            "exchange":  sym.exchange,
            "sector":    sym.sector,
            "close":     float(r['close']),
            "score":     float(r['score']),
            "direction": r['direction'],
            "signal_type": r['signal_type'],
            "rsi":       float(r['rsi']) if not pd.isna(r.get('rsi')) else None,
            "adx14":     float(r['adx14']) if not pd.isna(r.get('adx14')) else None,
            "stop_loss": float(r['stop_loss']) if not pd.isna(r.get('stop_loss')) else None,
        }
        rows.append(row)

    return Response({"count": len(rows), "results": rows})


# ─── Scanner Run ──────────────────────────────────────────────────────────────

@api_view(["POST"])
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
        strategy_name=data.get("strategy"), # เพิ่มการรองรับ strategy name
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


# ─── Cache Management API ─────────────────────────────────────────────────────

@api_view(["GET"])
def cache_stats(request):
    """GET /api/cache/stats/ — ดูสถานะ Redis cache"""
    try:
        from radar.indicator_cache import indicator_cache
        from radar.models import Symbol, Indicator

        stats = indicator_cache.stats()
        stats["total_symbols"] = Symbol.objects.count()
        stats["total_indicators"] = Indicator.objects.count()

        # ทดสอบ cache hit
        sym = Symbol.objects.first()
        if sym:
            cached = indicator_cache.get_latest_indicator(sym.id)
            stats["sample_symbol"] = sym.symbol
            stats["sample_cached"] = cached is not None

        return Response(stats)
    except Exception as e:
        return Response({"error": str(e), "available": False})


@api_view(["POST"])
def cache_warmup(request):
    """POST /api/cache/warmup/ — warm-up Redis cache"""
    try:
        from radar.indicator_cache import warm_up_cache
        exchange = request.data.get("exchange")
        result   = warm_up_cache(exchange)
        return Response({"status": "สำเร็จ", **result})
    except Exception as e:
        return Response({"status": "ล้มเหลว", "error": str(e)}, status=500)


@api_view(["POST"])
def cache_invalidate(request):
    """POST /api/cache/invalidate/ — ล้าง cache"""
    try:
        from radar.indicator_cache import indicator_cache
        exchange = request.data.get("exchange", "ALL")
        if exchange != "ALL":
            indicator_cache.invalidate_exchange(exchange)
        else:
            from django.core.cache import cache
            cache.clear()
        return Response({"status": "สำเร็จ", "cleared": exchange})
    except Exception as e:
        return Response({"status": "ล้มเหลว", "error": str(e)}, status=500)


# ─── News & Sentiment API ─────────────────────────────────────────────────────

@api_view(["GET"])
def news_list(request):
    """
    GET /api/news/
    Params: symbol, source, sentiment, days (default 7), limit (default 50)
    """
    from radar.models import NewsItem

    p     = request.query_params
    days  = int(p.get("days", 7))
    limit = min(int(p.get("limit", 50)), 200)
    since = timezone.now() - timedelta(days=days)

    qs = NewsItem.objects.filter(published_at__gte=since).order_by("-published_at")

    if p.get("symbol"):
        qs = qs.filter(symbols__symbol=p["symbol"].upper())
    if p.get("source"):
        qs = qs.filter(source=p["source"].upper())
    if p.get("sentiment"):
        qs = qs.filter(sentiment=p["sentiment"].upper())

    qs = qs.prefetch_related("symbols")[:limit]

    results = []
    for n in qs:
        results.append({
            "id":              n.id,
            "title":           n.title,
            "summary":         n.summary[:200] if n.summary else "",
            "url":             n.url,
            "source":          n.source,
            "published_at":    n.published_at.isoformat(),
            "sentiment":       n.sentiment,
            "sentiment_score": n.sentiment_score,
            "symbols":         [s.symbol for s in n.symbols.all()],
        })

    # Sentiment Summary
    from django.db.models import Count, Avg
    summary = NewsItem.objects.filter(published_at__gte=since).aggregate(
        total=Count("id"),
        bullish=Count("id", filter=models.Q(sentiment="BULLISH")),
        bearish=Count("id", filter=models.Q(sentiment="BEARISH")),
        neutral=Count("id", filter=models.Q(sentiment="NEUTRAL")),
        avg_score=Avg("sentiment_score"),
    )

    return Response({
        "summary": summary,
        "results": results,
        "count":   len(results),
    })


@api_view(["POST"])
def news_fetch(request):
    """POST /api/news/fetch/ — ดึงข่าวใหม่จาก RSS feeds ทันที"""
    try:
        from radar.news_fetcher import fetch_and_save_news
        stats = fetch_and_save_news(max_per_feed=30)
        return Response({"status": "สำเร็จ", **stats})
    except Exception as e:
        return Response({"status": "ล้มเหลว", "error": str(e)}, status=500)


@api_view(["GET"])
def news_sentiment_summary(request):
    """
    GET /api/news/sentiment/
    ภาพรวม sentiment ตลาดรายวัน + per-symbol
    """
    from radar.models import NewsItem
    from django.db.models import Count, Avg, Q

    days = int(request.query_params.get("days", 7))
    since = timezone.now() - timedelta(days=days)

    # Overall market sentiment
    overall = NewsItem.objects.filter(published_at__gte=since).aggregate(
        total=Count("id"),
        bullish=Count("id", filter=Q(sentiment="BULLISH")),
        bearish=Count("id", filter=Q(sentiment="BEARISH")),
        neutral=Count("id", filter=Q(sentiment="NEUTRAL")),
        avg_score=Avg("sentiment_score"),
    )

    # Sentiment ต่อ source
    by_source = list(
        NewsItem.objects.filter(published_at__gte=since)
        .values("source")
        .annotate(
            count=Count("id"),
            avg_score=Avg("sentiment_score"),
            bullish=Count("id", filter=Q(sentiment="BULLISH")),
            bearish=Count("id", filter=Q(sentiment="BEARISH")),
        )
        .order_by("-count")
    )

    # Top bullish/bearish symbols from news
    from radar.models import Symbol
    top_bullish = list(
        Symbol.objects.filter(
            news__sentiment="BULLISH",
            news__published_at__gte=since
        ).annotate(news_count=Count("news"))
        .order_by("-news_count")
        .values("symbol", "name", "news_count")[:10]
    )
    top_bearish = list(
        Symbol.objects.filter(
            news__sentiment="BEARISH",
            news__published_at__gte=since
        ).annotate(news_count=Count("news"))
        .order_by("-news_count")
        .values("symbol", "name", "news_count")[:10]
    )

    return Response({
        "overall":     overall,
        "by_source":   by_source,
        "top_bullish": top_bullish,
        "top_bearish": top_bearish,
    })

# ─── Watchlist API ────────────────────────────────────────────────────────────

def _get_or_create_watchlist(user):
    from radar.models import Watchlist
    wl, _ = Watchlist.objects.get_or_create(user=user)
    return wl


def _calc_position(item):
    """
    คำนวณสถานะ position จาก trades
    คืน: avg_cost, total_qty, total_invested, realized_pnl
    """
    trades = item.trades.order_by("trade_date", "created_at")
    total_qty      = 0
    total_invested = 0.0
    realized_pnl   = 0.0
    avg_cost       = 0.0

    for t in trades:
        qty   = t.quantity
        price = float(t.price)
        if t.action == "BUY":
            total_invested += qty * price
            total_qty      += qty
            avg_cost = total_invested / total_qty if total_qty > 0 else 0
        else:  # SELL
            realized_pnl   += qty * (price - avg_cost)
            total_qty      -= qty
            total_invested  = avg_cost * total_qty  # recalc invested after sell

    return {
        "avg_cost":       round(avg_cost, 4),
        "total_qty":      total_qty,
        "total_invested": round(total_invested, 2),
        "realized_pnl":   round(realized_pnl, 2),
    }


def _analyze_watchlist_item(item):
    """
    วิเคราะห์ตำแหน่งเดียว + แนะนำ action
    """
    from radar.models import PriceDaily, Indicator
    from datetime import date, timedelta
    import pandas as pd

    pos = _calc_position(item)
    sym = item.symbol

    # ดึงราคาปัจจุบัน + indicators
    latest_price = (PriceDaily.objects
                    .filter(symbol=sym)
                    .order_by("-date")
                    .values("date", "close", "high", "low", "volume")
                    .first())

    latest_ind = (Indicator.objects
                  .filter(symbol=sym)
                  .order_by("-date")
                  .values("date", "ema20", "ema50", "ema200", "rsi", "atr14", "adx14")
                  .first())

    if not latest_price:
        return {**pos, "error": "ไม่มีข้อมูลราคา"}

    current_price = float(latest_price["close"])
    avg_cost      = pos["avg_cost"]
    total_qty     = pos["total_qty"]

    # P/L ปัจจุบัน
    unrealized_pnl     = round((current_price - avg_cost) * total_qty, 2) if avg_cost > 0 else 0
    unrealized_pnl_pct = round((current_price - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0

    # Stop Loss = avg_cost - 1.5 × ATR หรือ -7% อย่างน้อย
    atr   = float(latest_ind["atr14"]) if latest_ind and latest_ind["atr14"] else current_price * 0.05
    ema20 = float(latest_ind["ema20"]) if latest_ind and latest_ind["ema20"] else None
    ema50 = float(latest_ind["ema50"]) if latest_ind and latest_ind["ema50"] else None
    ema200= float(latest_ind["ema200"]) if latest_ind and latest_ind["ema200"] else None
    rsi   = float(latest_ind["rsi"]) if latest_ind and latest_ind["rsi"] else 50
    adx   = float(latest_ind["adx14"]) if latest_ind and latest_ind["adx14"] else 0

    stop_loss_atr    = round(current_price - 1.5 * atr, 4)
    stop_loss_pct    = round(avg_cost * 0.93, 4) if avg_cost > 0 else round(current_price * 0.93, 4)
    stop_loss        = max(stop_loss_atr, stop_loss_pct)

    # ราคาที่ควรซื้อเพิ่ม = EMA20 support หรือ avg_cost - 1 ATR
    buy_more_price = None
    buy_more_reason = ""
    if ema20 and ema20 < current_price:
        buy_more_price  = round(ema20 * 1.005, 4)
        buy_more_reason = f"ใกล้ EMA20 ({ema20:.2f}) — แนวรับ"
    elif avg_cost > 0:
        buy_more_price  = round(avg_cost - atr, 4)
        buy_more_reason = "ต้นทุนเฉลี่ย − 1×ATR"

    # คำแนะนำ
    action = "HOLD"
    reasons = []

    if avg_cost > 0:
        if current_price < stop_loss:
            action = "SELL"
            reasons.append(f"ราคาต่ำกว่า Stop Loss ({stop_loss:.2f})")
        elif unrealized_pnl_pct >= 15 and rsi > 70:
            action = "TAKE_PROFIT"
            reasons.append(f"กำไร {unrealized_pnl_pct:.1f}% และ RSI Overbought ({rsi:.1f})")
        elif unrealized_pnl_pct < -7:
            action = "REVIEW"
            reasons.append(f"ขาดทุน {unrealized_pnl_pct:.1f}% ควรทบทวนแผน")
        elif rsi < 35 and current_price > (ema200 or 0):
            action = "BUY_MORE"
            reasons.append(f"RSI Oversold ({rsi:.1f}) + ราคาเหนือ EMA200")
        elif ema20 and ema50 and ema200 and ema20 > ema50 > ema200:
            action = "HOLD_STRONG"
            reasons.append("EMA Alignment ขาขึ้น (EMA20>50>200)")
        else:
            reasons.append("แนวโน้มปกติ — ถือต่อ")

    action_label = {
        "BUY_MORE":    "🟢 ซื้อเพิ่ม",
        "HOLD_STRONG": "💚 ถือมั่น",
        "HOLD":        "🟡 ถือ",
        "REVIEW":      "🟠 ทบทวน",
        "TAKE_PROFIT": "💰 ขายทำกำไร",
        "SELL":        "🔴 ขาย",
    }.get(action, "🟡 ถือ")

    return {
        "symbol":            sym.symbol,
        "symbol_name":       sym.name,
        "exchange":          sym.exchange,
        "current_price":     current_price,
        "price_date":        str(latest_price["date"]),
        # Position
        "avg_cost":          pos["avg_cost"],
        "total_qty":         pos["total_qty"],
        "total_invested":    pos["total_invested"],
        "realized_pnl":      pos["realized_pnl"],
        # P/L
        "unrealized_pnl":    unrealized_pnl,
        "unrealized_pnl_pct":unrealized_pnl_pct,
        "market_value":      round(current_price * total_qty, 2),
        # Risk
        "stop_loss":         round(stop_loss, 4),
        "atr":               round(atr, 4),
        # Recommendation
        "action":            action,
        "action_label":      action_label,
        "reasons":           reasons,
        "buy_more_price":    buy_more_price,
        "buy_more_reason":   buy_more_reason,
        # Indicators
        "rsi":  round(rsi, 1),
        "adx":  round(adx, 1),
        "ema20":  round(ema20, 2) if ema20 else None,
        "ema50":  round(ema50, 2) if ema50 else None,
        "ema200": round(ema200, 2) if ema200 else None,
    }

@api_view(["GET"])
def watchlist_list(request):
    """GET /api/watchlist/ — ดู watchlist พร้อม analysis"""
    if not request.user.is_authenticated:
        # Dev mode: ใช้ user แรก
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
        if not user:
            return Response({"error": "กรุณา login"}, status=401)
    else:
        user = request.user

    from radar.models import Watchlist, WatchlistItem
    wl = _get_or_create_watchlist(user)
    items = wl.items.select_related("symbol").prefetch_related("trades").all()

    result = []
    total_invested = 0
    total_market   = 0
    total_pnl      = 0

    for item in items:
        analysis = _analyze_watchlist_item(item)
        trades = list(item.trades.order_by("trade_date").values(
            "id", "action", "price", "quantity", "trade_date", "note"
        ))
        for t in trades:
            t["price"]      = float(t["price"])
            t["trade_date"] = str(t["trade_date"])

        result.append({
            **analysis,
            "item_id":   item.id,
            "note":      item.note,
            "alert_high": float(item.alert_price_high) if item.alert_price_high else None,
            "alert_low":  float(item.alert_price_low)  if item.alert_price_low  else None,
            "trades":    trades,
        })
        if not analysis.get("error"):
            total_invested += analysis.get("total_invested", 0)
            total_market   += analysis.get("market_value", 0)
            total_pnl      += analysis.get("unrealized_pnl", 0)

    return Response({
        "count": len(result),
        "max_items": 10,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_market":   round(total_market, 2),
            "total_pnl":      round(total_pnl, 2),
            "total_pnl_pct":  round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0,
        },
        "items": result,
    })


@api_view(["POST"])
def watchlist_add_item(request):
    """POST /api/watchlist/add/ — เพิ่มหุ้นใน watchlist"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import Watchlist, WatchlistItem
    symbol_code = (request.data.get("symbol") or "").strip().upper()
    sym = Symbol.objects.filter(symbol=symbol_code).first()
    if not sym:
        return Response({"error": f"ไม่พบหุ้น {symbol_code}"}, status=404)

    wl = _get_or_create_watchlist(user)
    if wl.items.count() >= 10:
        return Response({"error": "Watchlist เต็มแล้ว (สูงสุด 10 ตัว)"}, status=400)

    item, created = WatchlistItem.objects.get_or_create(
        watchlist=wl, symbol=sym,
        defaults={"note": request.data.get("note", "")}
    )
    if not created:
        return Response({"error": f"{symbol_code} มีใน watchlist แล้ว"}, status=400)

    return Response({"message": f"เพิ่ม {symbol_code} สำเร็จ", "item_id": item.id})


@api_view(["DELETE"])
def watchlist_remove_item(request, item_id):
    """DELETE /api/watchlist/item/<id>/ — ลบหุ้นออกจาก watchlist"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import WatchlistItem
    try:
        item = WatchlistItem.objects.get(id=item_id, watchlist__user=user)
        sym  = item.symbol.symbol
        item.delete()
        return Response({"message": f"ลบ {sym} สำเร็จ"})
    except WatchlistItem.DoesNotExist:
        return Response({"error": "ไม่พบรายการ"}, status=404)


@api_view(["POST"])
def watchlist_add_trade(request, item_id):
    """POST /api/watchlist/item/<id>/trade/ — บันทึกซื้อ/ขาย"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import WatchlistItem, WatchlistTrade
    try:
        item = WatchlistItem.objects.get(id=item_id, watchlist__user=user)
    except WatchlistItem.DoesNotExist:
        return Response({"error": "ไม่พบรายการ"}, status=404)

    action   = (request.data.get("action") or "BUY").upper()
    price    = float(request.data.get("price", 0))
    quantity = int(request.data.get("quantity", 0))
    note     = request.data.get("note", "")
    trade_date = request.data.get("trade_date") or str(timezone.now().date())

    if price <= 0 or quantity <= 0:
        return Response({"error": "ราคาและจำนวนต้องมากกว่า 0"}, status=400)

    from datetime import date as date_type
    try:
        tdate = date_type.fromisoformat(trade_date)
    except ValueError:
        tdate = timezone.now().date()

    trade = WatchlistTrade.objects.create(
        item=item, action=action, price=price,
        quantity=quantity, trade_date=tdate, note=note
    )

    # คืน analysis ใหม่
    analysis = _analyze_watchlist_item(item)
    return Response({"message": "บันทึกสำเร็จ", "trade_id": trade.id, "analysis": analysis})


@api_view(["DELETE"])
def watchlist_delete_trade(request, trade_id):
    """DELETE /api/watchlist/trade/<id>/ — ลบรายการซื้อขาย"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import WatchlistTrade
    try:
        trade = WatchlistTrade.objects.get(
            id=trade_id,
            item__watchlist__user=user
        )
        trade.delete()
        return Response({"message": "ลบสำเร็จ"})
    except WatchlistTrade.DoesNotExist:
        return Response({"error": "ไม่พบรายการ"}, status=404)


@api_view(["POST"])
def watchlist_calc_sell(request, item_id):
    """
    POST /api/watchlist/item/<id>/calc-sell/
    Body: { sell_price, sell_qty }
    คำนวณกำไร/ขาดทุนถ้าขาย
    """
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import WatchlistItem
    try:
        item = WatchlistItem.objects.get(id=item_id, watchlist__user=user)
    except WatchlistItem.DoesNotExist:
        return Response({"error": "ไม่พบรายการ"}, status=404)

    sell_price = float(request.data.get("sell_price", 0))
    sell_qty   = int(request.data.get("sell_qty", 0))
    commission = float(request.data.get("commission_pct", 0.15)) / 100

    pos = _calc_position(item)
    avg_cost  = pos["avg_cost"]
    total_qty = pos["total_qty"]

    if sell_price <= 0 or sell_qty <= 0:
        return Response({"error": "ราคาและจำนวนต้องมากกว่า 0"}, status=400)
    if sell_qty > total_qty:
        return Response({"error": f"จำนวนที่จะขาย ({sell_qty}) มากกว่าที่ถือ ({total_qty})"}, status=400)

    gross_revenue = sell_price * sell_qty
    commission_fee = gross_revenue * commission
    net_revenue    = gross_revenue - commission_fee
    cost_of_sold   = avg_cost * sell_qty
    gross_pnl      = gross_revenue - cost_of_sold
    net_pnl        = net_revenue - cost_of_sold
    pnl_pct        = (gross_pnl / cost_of_sold * 100) if cost_of_sold > 0 else 0

    remaining_qty      = total_qty - sell_qty
    remaining_invested = avg_cost * remaining_qty

    return Response({
        "sell_price":       sell_price,
        "sell_qty":         sell_qty,
        "avg_cost":         round(avg_cost, 4),
        "gross_revenue":    round(gross_revenue, 2),
        "commission_fee":   round(commission_fee, 2),
        "net_revenue":      round(net_revenue, 2),
        "cost_of_sold":     round(cost_of_sold, 2),
        "gross_pnl":        round(gross_pnl, 2),
        "net_pnl":          round(net_pnl, 2),
        "pnl_pct":          round(pnl_pct, 2),
        "remaining_qty":    remaining_qty,
        "remaining_invested": round(remaining_invested, 2),
        "label":            "กำไร" if gross_pnl >= 0 else "ขาดทุน",
    })

# ─── Fundamental Data API ──────────────────────────────────────────────────────

@api_view(["GET"])
def fundamental_data(request, symbol: str):
    """
    GET /api/fundamental/<symbol>/
    คืนข้อมูล P/E, EPS, งบการเงิน จาก yfinance
    Cache 24 ชั่วโมง
    """
    from radar.fundamental_engine import get_fundamental
    from radar.models import Symbol as SymbolModel

    sym_obj = SymbolModel.objects.filter(symbol=symbol.upper()).first()
    exchange = sym_obj.exchange if sym_obj else ""

    try:
        data = get_fundamental(symbol.upper(), exchange=exchange)
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["POST"])
def fundamental_batch(request):
    """
    POST /api/fundamental/batch/
    Body: { symbols: ["PTT","AAPL"] }
    คืนข้อมูล fundamental หลายหุ้นพร้อมกัน (max 10)
    """
    from radar.fundamental_engine import get_fundamental
    from radar.models import Symbol as SymbolModel
    from concurrent.futures import ThreadPoolExecutor

    symbols = request.data.get("symbols", [])[:10]
    if not symbols:
        return Response({"error": "กรุณาระบุ symbols"}, status=400)

    sym_map = {s.symbol: s.exchange for s in SymbolModel.objects.filter(symbol__in=symbols)}

    def fetch(sym):
        return get_fundamental(sym, exchange=sym_map.get(sym, ""))

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(fetch, symbols))

    return Response({"results": results})


@api_view(["GET"])
def watchlist_portfolio_history(request):
    """GET /api/watchlist/history/?days=90 — P/L history รายวัน"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
        if not user:
            return Response({"error": "กรุณา login"}, status=401)
    else:
        user = request.user

    days = int(request.query_params.get("days", 90))
    try:
        from radar.portfolio_history import calc_portfolio_history
        data = calc_portfolio_history(user, days=days)
        return Response({"count": len(data), "history": data})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["POST"])
def watchlist_calc_sell(request, item_id):
    """POST /api/watchlist/item/<id>/calc-sell/ — คำนวณกำไร/ขาดทุนถ้าขาย"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import WatchlistItem
    try:
        item = WatchlistItem.objects.get(id=item_id, watchlist__user=user)
    except WatchlistItem.DoesNotExist:
        return Response({"error": "ไม่พบรายการ"}, status=404)

    sell_price = float(request.data.get("sell_price", 0))
    pos        = _calc_position(item)
    sell_qty   = float(request.data.get("sell_qty") or pos["total_qty"])
    avg_cost   = pos["avg_cost"]

    if sell_price <= 0:
        return Response({"error": "กรุณาระบุ sell_price"}, status=400)

    gross      = sell_price * sell_qty
    cost       = avg_cost * sell_qty
    commission = gross * 0.0017   # ค่าคอม 0.17% (ตลาดไทย)
    net        = gross - commission
    pnl        = net - cost
    pnl_pct    = pnl / cost * 100 if cost else 0
    remaining  = pos["total_qty"] - sell_qty

    return Response({
        "sell_price":    sell_price,
        "sell_qty":      sell_qty,
        "avg_cost":      round(avg_cost, 4),
        "gross_revenue": round(gross, 2),
        "commission":    round(commission, 2),
        "net_revenue":   round(net, 2),
        "cost_basis":    round(cost, 2),
        "pnl":           round(pnl, 2),
        "pnl_pct":       round(pnl_pct, 2),
        "remaining_qty": round(remaining, 2),
        "is_profit":     pnl >= 0,
    })


@api_view(["PATCH"])
def watchlist_update_alert(request, item_id):
    """PATCH /api/watchlist/item/<id>/alert/ — อัปเดต alert ราคา"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
    else:
        user = request.user

    from radar.models import WatchlistItem
    try:
        item = WatchlistItem.objects.get(id=item_id, watchlist__user=user)
    except WatchlistItem.DoesNotExist:
        return Response({"error": "ไม่พบรายการ"}, status=404)

    if "alert_price_high" in request.data:
        item.alert_price_high = request.data["alert_price_high"] or None
    if "alert_price_low" in request.data:
        item.alert_price_low  = request.data["alert_price_low"]  or None
    if "note" in request.data:
        item.note = request.data["note"]
    item.save()
    return Response({"message": "อัปเดต Alert สำเร็จ"})


@api_view(["GET"])
def watchlist_portfolio_history(request):
    """GET /api/watchlist/history/?days=90 — P/L history รายวัน"""
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DjangoUser
        user = DjangoUser.objects.filter(is_superuser=True).first()
        if not user:
            return Response({"error": "กรุณา login"}, status=401)
    else:
        user = request.user

    days = int(request.query_params.get("days", 90))
    try:
        from radar.portfolio_history import calc_portfolio_history
        data = calc_portfolio_history(user, days=days)
        return Response({"count": len(data), "history": data})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ─── Fundamental Data API ─────────────────────────────────────────────────────

@api_view(["GET"])
def fundamental_data(request, symbol: str):
    """GET /api/fundamental/<symbol>/ — P/E, EPS, งบการเงิน จาก yfinance"""
    from radar.fundamental_engine import get_fundamental
    sym_obj  = Symbol.objects.filter(symbol=symbol.upper()).first()
    exchange = sym_obj.exchange if sym_obj else ""
    try:
        data = get_fundamental(symbol.upper(), exchange=exchange)
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["POST"])
def fundamental_batch(request):
    """POST /api/fundamental/batch/ — { symbols: ["PTT","AAPL"] }"""
    from radar.fundamental_engine import get_fundamental
    from concurrent.futures import ThreadPoolExecutor

    symbols  = request.data.get("symbols", [])[:10]
    if not symbols:
        return Response({"error": "กรุณาระบุ symbols"}, status=400)

    sym_map = {s.symbol: s.exchange
               for s in Symbol.objects.filter(symbol__in=symbols)}

    def fetch(sym):
        return get_fundamental(sym, exchange=sym_map.get(sym, ""))

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(fetch, symbols))

    return Response({"results": results})


# ─── Ticker Tape API ──────────────────────────────────────────────────────────

@api_view(["GET"])
def ticker_tape(request):
    """
    GET /api/ticker/ — ดัชนีตลาด สินค้าโภคภัณฑ์ FX Crypto
    Cache 5 นาที · ใช้กับ Ticker Tape ด้านล่างหน้าจอ
    """
    try:
        from radar.ticker_api import fetch_ticker_data
        data = fetch_ticker_data()
        return Response({"count": len(data), "items": data})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ─── Economic Calendar API ────────────────────────────────────────────────────

@api_view(["GET"])
def economic_calendar_api(request):
    """
    GET /api/calendar/?days=7
    ปฏิทินเศรษฐกิจสัปดาห์นี้ จาก ForexFactory
    Cache 1 ชั่วโมง
    """
    try:
        days = int(request.query_params.get("days", 7))
        from radar.economic_calendar import fetch_economic_calendar
        data = fetch_economic_calendar(days_ahead=days)

        # group by date
        from collections import defaultdict
        by_date: dict = defaultdict(list)
        for ev in data:
            by_date[ev["date"]].append(ev)

        return Response({
            "count": len(data),
            "days":  days,
            "by_date": dict(by_date),
            "events": data,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ─── Subscription API ─────────────────────────────────────────────────────────

@api_view(["GET"])
def subscription_status(request):
    """
    GET /api/subscription/ — ดูสถานะ subscription ปัจจุบัน
    """
    if not request.user.is_authenticated:
        from django.contrib.auth.models import User as DU
        user = DU.objects.filter(is_superuser=True).first()
        if not user:
            return Response({"error": "Unauthorized"}, status=401)
    else:
        user = request.user

    try:
        profile = user.profile
    except Exception:
        from radar.models import Profile as P
        profile, _ = P.objects.get_or_create(user=user)

    sub = profile.active_subscription
    lim = profile.limits

    return Response({
        "username":    user.username,
        "email":       user.email,
        "tier":        profile.tier,
        "is_pro":      profile.is_pro,
        "is_premium":  profile.is_premium,
        "limits":      lim,
        "subscription": {
            "plan":       sub.plan.name if sub else None,
            "status":     sub.status    if sub else "FREE",
            "start_date": str(sub.start_date) if sub else None,
            "end_date":   str(sub.end_date)   if sub else None,
            "days_left":  (sub.end_date - __import__("datetime").date.today()).days if sub else None,
        } if sub else None,
    })


@api_view(["GET"])
def subscription_plans(request):
    """
    GET /api/subscription/plans/ — รายการแผนทั้งหมด
    """
    from radar.models import SubscriptionPlan
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price_thb")
    TIER_LIMITS = {
        "FREE":    {"watchlist":3,  "backtest_years":1, "scanner_top":20,  "fundamental":False},
        "PRO":     {"watchlist":10, "backtest_years":3, "scanner_top":100, "fundamental":True},
        "PREMIUM": {"watchlist":20, "backtest_years":5, "scanner_top":500, "fundamental":True},
    }
    data = []
    for p in plans:
        data.append({
            "id":           p.id,
            "name":         p.name,
            "tier":         p.tier,
            "price_thb":    float(p.price_thb),
            "duration_days":p.duration_days,
            "description":  p.description,
            "features":     p.features,
            "limits":       TIER_LIMITS.get(p.tier, {}),
        })
    return Response({"plans": data})


# ─── Subscription API ─────────────────────────────────────────────────────────

@api_view(["GET"])
def subscription_plans(request):
    """GET /api/subscription/plans/ — รายการแผนทั้งหมด"""
    from radar.subscription import PLANS
    return Response({"plans": PLANS})


@api_view(["GET"])
def subscription_status(request):
    """GET /api/subscription/status/ — สถานะ plan ของ user ปัจจุบัน"""
    from radar.subscription import get_user_plan, PLANS

    if not request.user.is_authenticated:
        plan = PLANS["free"]
        return Response({
            "authenticated": False,
            "plan": plan,
            "tier": "free",
            "expires_at": None,
        })

    plan = get_user_plan(request.user)
    tier = request.user.profile.tier.lower()

    # หา expiry date
    expires_at = None
    try:
        sub = request.user.profile.subscriptions.filter(
            is_active=True
        ).order_by("-end_date").first()
        if sub:
            expires_at = sub.end_date.isoformat()
    except Exception:
        pass

    return Response({
        "authenticated": True,
        "username":  request.user.username,
        "tier":      tier,
        "plan":      plan,
        "expires_at": expires_at,
    })


# ─── GitHub Actions Import ────────────────────────────────────────────────────

@api_view(["GET"])
def symbols_export(request):
    """
    คืนรายชื่อหุ้นทั้งหมดพร้อม yahoo ticker format
    ใช้โดย GitHub Actions fetch_prices.py
    Public endpoint (ไม่ต้อง login)
    """
    from django.conf import settings as dj_settings
    symbols = Symbol.objects.values("symbol", "exchange", "name")
    result = []
    for s in symbols:
        if s["exchange"] == "SET":
            yahoo = f"{s['symbol']}.BK"
        else:
            yahoo = s["symbol"]
        result.append({
            "symbol":   s["symbol"],
            "exchange": s["exchange"],
            "yahoo":    yahoo,
        })
    return Response(result)


@api_view(["POST"])
def import_prices(request):
    """
    รับข้อมูลราคาหุ้นจาก GitHub Actions แล้ว upsert ลง DB
    Header: X-Import-Token: <IMPORT_API_TOKEN>
    Body: [{"symbol":"PTT","date":"2025-03-26","open":...,
            "high":...,"low":...,"close":...,"volume":...}, ...]
    """
    from django.conf import settings as dj_settings
    from django.db import transaction

    # ── ตรวจสอบ token ──
    token = request.headers.get("X-Import-Token", "")
    expected = getattr(dj_settings, "IMPORT_API_TOKEN", "")
    if not expected or token != expected:
        return Response({"error": "unauthorized"}, status=401)

    records = request.data
    if not isinstance(records, list):
        return Response({"error": "expected JSON array"}, status=400)

    # ── โหลด symbols map ──
    sym_map = {s.symbol: s for s in Symbol.objects.all()}

    imported = skipped = 0

    with transaction.atomic():
        for rec in records:
            sym_obj = sym_map.get(rec.get("symbol"))
            if not sym_obj:
                skipped += 1
                continue
            try:
                from decimal import Decimal
                PriceDaily.objects.update_or_create(
                    symbol=sym_obj,
                    date=rec["date"],
                    defaults={
                        "open":   Decimal(str(rec["open"])),
                        "high":   Decimal(str(rec["high"])),
                        "low":    Decimal(str(rec["low"])),
                        "close":  Decimal(str(rec["close"])),
                        "volume": int(rec.get("volume", 0)),
                    },
                )
                imported += 1
            except Exception:
                skipped += 1

    return Response({"imported": imported, "skipped": skipped})


# ─────────────────────────────────────────────────────────────────────────────
# Latest Snapshot API
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def latest_snapshot(request):
    """
    GET /api/snapshot/
    คืนข้อมูล latest_snapshot ทุกหุ้น (ราคา + indicator + signal ล่าสุด)

    Query params:
      ?exchange=SET          — กรอง exchange
      ?direction=LONG        — กรอง direction
      ?limit=50              — จำกัดจำนวน (default=100)
      ?min_score=60          — กรอง signal_score >= ค่านี้
    """
    from .models import LatestSnapshot

    qs = LatestSnapshot.objects.all()

    exchange  = request.query_params.get("exchange")
    direction = request.query_params.get("direction")
    min_score = request.query_params.get("min_score")
    limit     = int(request.query_params.get("limit", 100))

    if exchange:
        qs = qs.filter(exchange=exchange.upper())
    if direction:
        qs = qs.filter(direction=direction.upper())
    if min_score:
        qs = qs.filter(signal_score__gte=float(min_score))

    qs = qs.order_by("-signal_score")[:limit]

    data = list(qs.values(
        "symbol", "name", "exchange", "sector",
        "price_date", "close", "open", "high", "low", "volume",
        "ema20", "ema50", "ema200",
        "rsi", "macd", "macd_hist", "adx14", "atr14",
        "bb_upper", "bb_lower",
        "highest_high_20", "lowest_low_20", "volume_avg20",
        "signal_type", "direction", "signal_score",
        "stop_loss", "risk_pct", "signal_date",
    ))
    return Response(data)
