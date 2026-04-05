"""
Alpaca REST API Service — Paper Trading & Live Trading
ใช้ requests โดยตรง (ไม่ต้องติดตั้ง SDK เพิ่ม)

Docs: https://docs.alpaca.markets/reference/
"""

import os
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

def _get_config():
    """อ่าน config จาก settings หรือ environment"""
    api_key    = getattr(settings, "ALPACA_API_KEY",    os.environ.get("ALPACA_API_KEY", ""))
    secret_key = getattr(settings, "ALPACA_SECRET_KEY", os.environ.get("ALPACA_SECRET_KEY", ""))
    base_url   = getattr(settings, "ALPACA_BASE_URL",   os.environ.get("ALPACA_BASE_URL",   "https://paper-api.alpaca.markets"))
    return api_key, secret_key, base_url

DATA_URL = "https://data.alpaca.markets"

def _headers():
    api_key, secret_key, _ = _get_config()
    return {
        "APCA-API-KEY-ID":     api_key,
        "APCA-API-SECRET-KEY": secret_key,
        "Content-Type":        "application/json",
    }

def _base():
    _, _, base_url = _get_config()
    return base_url.rstrip("/")


# ── Account ───────────────────────────────────────────────────────────────────

def get_account():
    """ดูยอดเงิน equity, buying_power, cash, P&L"""
    r = requests.get(f"{_base()}/v2/account", headers=_headers(), timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "account_number":  data.get("account_number"),
        "status":          data.get("status"),
        "currency":        data.get("currency", "USD"),
        "equity":          float(data.get("equity", 0)),
        "cash":            float(data.get("cash", 0)),
        "buying_power":    float(data.get("buying_power", 0)),
        "portfolio_value": float(data.get("portfolio_value", 0)),
        "daytrade_count":  data.get("daytrade_count", 0),
        "pattern_day_trader": data.get("pattern_day_trader", False),
        "trading_blocked": data.get("trading_blocked", False),
        "is_paper":        "paper" in _base(),
    }


# ── Positions ─────────────────────────────────────────────────────────────────

def get_positions():
    """ดู positions ที่ถือไว้ปัจจุบัน พร้อม unrealized P&L"""
    r = requests.get(f"{_base()}/v2/positions", headers=_headers(), timeout=10)
    r.raise_for_status()
    positions = r.json()
    result = []
    for p in positions:
        result.append({
            "symbol":            p.get("symbol"),
            "qty":               float(p.get("qty", 0)),
            "avg_entry_price":   float(p.get("avg_entry_price", 0)),
            "current_price":     float(p.get("current_price", 0)),
            "market_value":      float(p.get("market_value", 0)),
            "cost_basis":        float(p.get("cost_basis", 0)),
            "unrealized_pl":     float(p.get("unrealized_pl", 0)),
            "unrealized_plpc":   float(p.get("unrealized_plpc", 0)),
            "change_today":      float(p.get("change_today", 0)),
            "side":              p.get("side"),
        })
    return result


# ── Orders ────────────────────────────────────────────────────────────────────

def get_orders(status="open", limit=50):
    """ดูรายการ orders  status: open | closed | all"""
    params = {"status": status, "limit": limit, "direction": "desc"}
    r = requests.get(f"{_base()}/v2/orders", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    orders = r.json()
    result = []
    for o in orders:
        result.append({
            "id":           o.get("id"),
            "symbol":       o.get("symbol"),
            "side":         o.get("side"),
            "qty":          o.get("qty"),
            "filled_qty":   o.get("filled_qty"),
            "type":         o.get("type"),
            "status":       o.get("status"),
            "limit_price":  o.get("limit_price"),
            "filled_avg_price": o.get("filled_avg_price"),
            "submitted_at": o.get("submitted_at"),
            "filled_at":    o.get("filled_at"),
        })
    return result


def place_order(symbol, side, qty, order_type="market", limit_price=None, time_in_force="day"):
    """ส่ง order ไป Alpaca จริง (เรียกหลัง user confirm เท่านั้น)"""
    payload = {
        "symbol":        symbol.upper(),
        "qty":           str(qty),
        "side":          side,          # buy | sell
        "type":          order_type,    # market | limit
        "time_in_force": time_in_force, # day | gtc | opg | cls | ioc | fok
    }
    if limit_price and order_type == "limit":
        payload["limit_price"] = str(limit_price)

    r = requests.post(f"{_base()}/v2/orders", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "alpaca_order_id": data.get("id"),
        "status":          data.get("status"),
        "symbol":          data.get("symbol"),
        "side":            data.get("side"),
        "qty":             data.get("qty"),
        "type":            data.get("type"),
        "submitted_at":    data.get("submitted_at"),
    }


def cancel_order(alpaca_order_id):
    """ยกเลิก order ใน Alpaca"""
    r = requests.delete(f"{_base()}/v2/orders/{alpaca_order_id}", headers=_headers(), timeout=10)
    if r.status_code == 204:
        return {"status": "cancelled", "alpaca_order_id": alpaca_order_id}
    r.raise_for_status()
    return r.json()


# ── Market Data ───────────────────────────────────────────────────────────────

def get_bars(symbol, timeframe="1Day", limit=60):
    """ดึง OHLCV bars ของหุ้น US จาก Alpaca Data API"""
    params = {
        "symbols":   symbol.upper(),
        "timeframe": timeframe,
        "limit":     limit,
        "feed":      "iex",  # iex = ฟรี, sip = ต้องจ่าย
        "sort":      "desc",
    }
    r = requests.get(
        f"{DATA_URL}/v2/stocks/bars",
        headers=_headers(),
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    bars_raw = data.get("bars", {}).get(symbol.upper(), [])
    bars = []
    for b in bars_raw:
        bars.append({
            "t": b.get("t"),  # timestamp
            "o": b.get("o"),  # open
            "h": b.get("h"),  # high
            "l": b.get("l"),  # low
            "c": b.get("c"),  # close
            "v": b.get("v"),  # volume
        })
    return bars


def get_bars_multi(symbols, timeframe="1Day", start=None, end=None, limit=200):
    """
    ดึง OHLCV bars หลาย symbols ใน 1 request
    Alpaca multi-bar endpoint: GET /v2/stocks/bars?symbols=AAPL,TSLA,...
    คืน dict: { "AAPL": [bars], "TSLA": [bars], ... }
    """
    params = {
        "symbols":   ",".join(s.upper() for s in symbols),
        "timeframe": timeframe,
        "limit":     limit,
        "feed":      "iex",
        "sort":      "asc",
    }
    if start:
        params["start"] = start if isinstance(start, str) else start.isoformat()
    if end:
        params["end"] = end if isinstance(end, str) else end.isoformat()

    result = {}
    page_token = None

    while True:
        if page_token:
            params["page_token"] = page_token

        r = requests.get(
            f"{DATA_URL}/v2/stocks/bars",
            headers=_headers(),
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        for sym, bars_raw in data.get("bars", {}).items():
            if sym not in result:
                result[sym] = []
            for b in bars_raw:
                result[sym].append({
                    "t": b.get("t"),
                    "o": b.get("o"),
                    "h": b.get("h"),
                    "l": b.get("l"),
                    "c": b.get("c"),
                    "v": b.get("v"),
                })

        page_token = data.get("next_page_token")
        if not page_token:
            break

    return result


def get_latest_quote(symbol):
    """ดูราคาล่าสุด (bid/ask) ของหุ้น US"""
    r = requests.get(
        f"{DATA_URL}/v2/stocks/{symbol.upper()}/quotes/latest",
        headers=_headers(),
        params={"feed": "iex"},
        timeout=10,
    )
    r.raise_for_status()
    q = r.json().get("quote", {})
    return {
        "symbol":    symbol.upper(),
        "bid_price": q.get("bp"),
        "ask_price": q.get("ap"),
        "bid_size":  q.get("bs"),
        "ask_size":  q.get("as"),
        "timestamp": q.get("t"),
    }


# ── Portfolio History ─────────────────────────────────────────────────────────

def get_portfolio_history(period="1M", timeframe="1D"):
    """ดู P&L ย้อนหลัง  period: 1D|1W|1M|3M|1A  timeframe: 1Min|5Min|15Min|1H|1D"""
    params = {"period": period, "timeframe": timeframe, "extended_hours": False}
    r = requests.get(
        f"{_base()}/v2/account/portfolio/history",
        headers=_headers(),
        params=params,
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    timestamps     = data.get("timestamp", [])
    equity_values  = data.get("equity", [])
    profit_loss    = data.get("profit_loss", [])
    profit_loss_pct = data.get("profit_loss_pct", [])
    history = []
    for i, ts in enumerate(timestamps):
        history.append({
            "timestamp":       ts,
            "equity":          equity_values[i] if i < len(equity_values) else None,
            "profit_loss":     profit_loss[i] if i < len(profit_loss) else None,
            "profit_loss_pct": profit_loss_pct[i] if i < len(profit_loss_pct) else None,
        })
    return {
        "history":       history,
        "base_value":    data.get("base_value"),
        "timeframe":     data.get("timeframe"),
    }


# ── Health Check ──────────────────────────────────────────────────────────────

def is_market_open():
    """ตรวจสอบว่าตลาด US เปิดอยู่ไหม"""
    r = requests.get(f"{_base()}/v2/clock", headers=_headers(), timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "is_open":     data.get("is_open"),
        "next_open":   data.get("next_open"),
        "next_close":  data.get("next_close"),
        "timestamp":   data.get("timestamp"),
    }
