"""
Views — Alpaca US Stock Trading API
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .. import alpaca_service
from ..models import AlpacaOrder
import django.utils.timezone as tz_utils


def _alpaca_error(e):
    """แปลง requests.HTTPError → Response ที่อ่านได้"""
    import requests as _req
    if isinstance(e, _req.HTTPError) and e.response is not None:
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        return Response({"error": detail, "status_code": e.response.status_code}, status=502)
    return Response({"error": str(e)}, status=502)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alpaca_account(request):
    """GET /api/alpaca/account/"""
    try:
        data = alpaca_service.get_account()
        return Response(data)
    except Exception as e:
        return _alpaca_error(e)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alpaca_positions(request):
    """GET /api/alpaca/positions/"""
    try:
        data = alpaca_service.get_positions()
        return Response({"positions": data})
    except Exception as e:
        return _alpaca_error(e)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alpaca_orders(request):
    """GET /api/alpaca/orders/?status=open"""
    status = request.query_params.get("status", "open")
    if status not in ("open", "closed", "all"):
        status = "open"
    try:
        data = alpaca_service.get_orders(status=status)
        local_pending = list(
            AlpacaOrder.objects.filter(user=request.user, status="pending_confirm")
            .values("id", "symbol", "side", "qty", "order_type", "limit_price", "ai_reasoning", "created_at")
        )
        return Response({"orders": data, "pending_confirm": local_pending})
    except Exception as e:
        return _alpaca_error(e)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def alpaca_propose_order(request):
    """POST /api/alpaca/orders/propose/"""
    data = request.data
    required = ["symbol", "side", "qty"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return Response({"error": f"ขาด field: {missing}"}, status=400)

    side = data.get("side", "").lower()
    if side not in ("buy", "sell"):
        return Response({"error": "side ต้องเป็น buy หรือ sell"}, status=400)

    try:
        qty = float(data["qty"])
        if qty <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return Response({"error": "qty ต้องเป็นตัวเลขมากกว่า 0"}, status=400)

    order = AlpacaOrder.objects.create(
        user=request.user, symbol=data["symbol"].upper(),
        side=side, qty=qty,
        order_type=data.get("order_type", "market"),
        limit_price=data.get("limit_price") or None,
        ai_reasoning=data.get("ai_reasoning", ""),
        status="pending_confirm",
    )
    return Response({
        "order_id": order.id, "status": "pending_confirm",
        "symbol": order.symbol, "side": order.side,
        "qty": float(order.qty), "order_type": order.order_type,
        "limit_price": float(order.limit_price) if order.limit_price else None,
        "ai_reasoning": order.ai_reasoning,
        "message": "รอการยืนยันจากคุณก่อนส่ง order",
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def alpaca_confirm_order(request, order_id):
    """POST /api/alpaca/orders/<order_id>/confirm/"""
    try:
        order = AlpacaOrder.objects.get(id=order_id, user=request.user, status="pending_confirm")
    except AlpacaOrder.DoesNotExist:
        return Response({"error": "ไม่พบ order หรือ order ถูกยืนยัน/ยกเลิกไปแล้ว"}, status=404)

    try:
        result = alpaca_service.place_order(
            symbol=order.symbol, side=order.side,
            qty=float(order.qty), order_type=order.order_type,
            limit_price=float(order.limit_price) if order.limit_price else None,
        )
        order.status = "submitted"
        order.alpaca_order_id = result.get("alpaca_order_id", "")
        order.confirmed_at = tz_utils.now()
        order.save()
        return Response({
            "message": "ส่ง order สำเร็จ",
            "alpaca_order_id": order.alpaca_order_id,
            "status": "submitted",
            "symbol": order.symbol, "side": order.side, "qty": float(order.qty),
        })
    except Exception as e:
        order.status = "rejected"
        order.save()
        return _alpaca_error(e)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def alpaca_cancel_order(request, order_id):
    """POST /api/alpaca/orders/<order_id>/cancel/"""
    try:
        order = AlpacaOrder.objects.get(id=order_id, user=request.user)
    except AlpacaOrder.DoesNotExist:
        return Response({"error": "ไม่พบ order"}, status=404)

    if order.status in ("filled", "cancelled", "rejected"):
        return Response({"error": f"ไม่สามารถยกเลิกได้ สถานะปัจจุบัน: {order.get_status_display()}"}, status=400)

    if order.status == "pending_confirm":
        order.status = "cancelled"
        order.save()
        return Response({"message": "ยกเลิก order สำเร็จ (ยังไม่ได้ส่งไป Alpaca)"})

    try:
        alpaca_service.cancel_order(order.alpaca_order_id)
        order.status = "cancelled"
        order.save()
        return Response({"message": "ส่งคำสั่งยกเลิกไป Alpaca แล้ว"})
    except Exception as e:
        return _alpaca_error(e)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alpaca_portfolio(request):
    """GET /api/alpaca/portfolio/?period=1M&timeframe=1D"""
    period = request.query_params.get("period", "1M")
    timeframe = request.query_params.get("timeframe", "1D")
    try:
        data = alpaca_service.get_portfolio_history(period=period, timeframe=timeframe)
        return Response(data)
    except Exception as e:
        return _alpaca_error(e)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alpaca_market_clock(request):
    """GET /api/alpaca/clock/"""
    try:
        data = alpaca_service.is_market_open()
        return Response(data)
    except Exception as e:
        return _alpaca_error(e)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alpaca_bars(request):
    """GET /api/alpaca/bars/?symbol=AAPL&timeframe=1Day&limit=60"""
    symbol = request.query_params.get("symbol", "").upper()
    timeframe = request.query_params.get("timeframe", "1Day")
    limit = int(request.query_params.get("limit", 60))
    if not symbol:
        return Response({"error": "ต้องระบุ symbol"}, status=400)
    try:
        bars = alpaca_service.get_bars(symbol=symbol, timeframe=timeframe, limit=limit)
        return Response({"symbol": symbol, "timeframe": timeframe, "bars": bars})
    except Exception as e:
        return _alpaca_error(e)
