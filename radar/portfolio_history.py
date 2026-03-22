"""
portfolio_history.py — คำนวณ P/L History รายวัน จาก WatchlistTrade + PriceDaily
"""
from datetime import date, timedelta


def calc_portfolio_history(user, days: int = 90) -> list[dict]:
    """
    คำนวณ equity curve รายวัน จากพอร์ตของ user
    คืน list[{date, market_value, invested, pnl, pnl_pct}]
    """
    from radar.models import Watchlist, WatchlistItem, WatchlistTrade, PriceDaily
    from django.db.models import Q

    try:
        wl = Watchlist.objects.get(user=user)
    except Watchlist.DoesNotExist:
        return []

    items = wl.items.prefetch_related("trades", "symbol").all()
    if not items:
        return []

    today = date.today()
    start = today - timedelta(days=days)
    date_range = [start + timedelta(days=i) for i in range(days + 1)]

    # โหลดราคาทุกหุ้นในพอร์ต
    sym_ids = [item.symbol_id for item in items]
    prices_qs = (PriceDaily.objects
                 .filter(symbol_id__in=sym_ids, date__gte=start)
                 .order_by("symbol_id", "date")
                 .values("symbol_id", "date", "close"))

    # จัดเป็น dict: {symbol_id: {date: close}}
    price_map: dict = {}
    for p in prices_qs:
        sid = p["symbol_id"]
        if sid not in price_map:
            price_map[sid] = {}
        price_map[sid][p["date"]] = float(p["close"])

    # คำนวณ avg_cost ณ แต่ละวัน (รวมทุก trade ก่อนหรือเท่ากับวันนั้น)
    result = []
    prev_close_map: dict = {}  # {symbol_id: last known close}

    for d in date_range:
        total_market = 0.0
        total_invested = 0.0

        for item in items:
            # trades ก่อนหรือเท่ากับวันนี้
            trades = [t for t in item.trades.all() if t.trade_date <= d]
            if not trades:
                continue

            qty = 0
            invested = 0.0
            for t in sorted(trades, key=lambda x: x.trade_date):
                if t.action == "BUY":
                    invested += float(t.price) * t.quantity
                    qty      += t.quantity
                else:
                    avg_cost  = invested / qty if qty > 0 else 0
                    invested -= avg_cost * t.quantity
                    qty      -= t.quantity

            if qty <= 0:
                continue

            # ราคาปัจจุบัน ณ วันนั้น (หรือใช้ราคาล่าสุดก่อนหน้า)
            sid = item.symbol_id
            close = price_map.get(sid, {}).get(d)
            if close:
                prev_close_map[sid] = close
            else:
                close = prev_close_map.get(sid)

            if close:
                total_market   += close * qty
                total_invested += invested

        if total_invested > 0:
            pnl     = total_market - total_invested
            pnl_pct = pnl / total_invested * 100
            result.append({
                "date":         d.isoformat(),
                "market_value": round(total_market, 2),
                "invested":     round(total_invested, 2),
                "pnl":          round(pnl, 2),
                "pnl_pct":      round(pnl_pct, 2),
            })

    return result
