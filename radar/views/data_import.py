"""
Views — Data Import (GitHub Actions), Snapshot, Trigger Engine, Admin API
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from ..models import Symbol, PriceDaily


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
    Body: [{"symbol":"PTT","date":"2025-03-26","open":...,...}, ...]
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


# ─── Latest Snapshot API ──────────────────────────────────────────────────────

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
    from ..models import LatestSnapshot

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


# ─── Trigger Engine API ──────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def trigger_engine(request):
    """POST /api/trigger-engine/ — runs run_engine + refresh_snapshot + fetch_news"""
    token = request.headers.get("X-Import-Token", "")
    import os
    if token != os.environ.get("IMPORT_API_TOKEN", ""):
        return Response({"error": "unauthorized"}, status=401)

    from django.core.management import call_command
    import io

    out = io.StringIO()
    try:
        call_command("run_engine", stdout=out)
        call_command("refresh_snapshot", stdout=out)
        call_command("fetch_news", stdout=out)
    except Exception as e:
        return Response({"status": "error", "detail": str(e)}, status=500)

    return Response({"status": "ok", "output": out.getvalue()})


# ─── Admin API (is_staff only) ────────────────────────────────────────────────

def _require_staff(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return Response({"error": "forbidden"}, status=403)
    return None


@api_view(["GET"])
def admin_stats(request):
    """GET /api/admin/stats/ — system statistics"""
    err = _require_staff(request)
    if err:
        return err
    from django.contrib.auth.models import User as DjangoUser
    from radar.models import Signal, NewsItem
    last_sig = Signal.objects.order_by("-created_at").first()
    return Response({
        "total_users":    DjangoUser.objects.count(),
        "total_signals":  Signal.objects.count(),
        "total_news":     NewsItem.objects.count(),
        "total_symbols":  Symbol.objects.count(),
        "total_prices":   PriceDaily.objects.count(),
        "last_signal_date": last_sig.created_at.isoformat() if last_sig else None,
    })


@api_view(["POST"])
def admin_fetch_news(request):
    """POST /api/admin/fetch-news/ — รัน fetch_news"""
    err = _require_staff(request)
    if err:
        return err
    from django.core.management import call_command
    import io
    out = io.StringIO()
    try:
        call_command("fetch_news", stdout=out)
        return Response({"status": "ok", "message": "ดึงข่าวสำเร็จ"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)


@api_view(["POST"])
def admin_refresh_snapshot(request):
    """POST /api/admin/refresh-snapshot/ — รัน refresh_snapshot"""
    err = _require_staff(request)
    if err:
        return err
    from django.core.management import call_command
    import io
    out = io.StringIO()
    try:
        call_command("refresh_snapshot", stdout=out)
        return Response({"status": "ok", "message": "Refresh snapshot สำเร็จ"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)
