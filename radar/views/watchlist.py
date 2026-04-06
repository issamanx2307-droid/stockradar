"""
Views — Watchlist & Portfolio
"""

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Symbol


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


# ─── Watchlist Views ──────────────────────────────────────────────────────────

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
