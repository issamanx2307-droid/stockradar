"""
Broadcaster — ส่ง WebSocket messages จาก Django views/tasks
=============================================================
ใช้งาน:
  from radar.broadcaster import broadcast_signal, broadcast_scanner_progress

  broadcast_signal(signal_obj)
  broadcast_scanner_progress(current=50, total=600, found=12)
  broadcast_scanner_done(signals=20, elapsed=0.15)
  broadcast_stats()
  broadcast_prices(symbol_data_list)
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_channel_layer():
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


def _run_async(coro):
    """รัน coroutine จาก sync context"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


def broadcast_signal(signal_obj) -> bool:
    """Broadcast signal ใหม่ไปยัง WebSocket clients ทั้งหมด"""
    layer = _get_channel_layer()
    if not layer:
        return False
    try:
        data = {
            "symbol":      signal_obj.symbol.symbol,
            "name":        signal_obj.symbol.name,
            "exchange":    signal_obj.symbol.exchange,
            "signal_type": signal_obj.signal_type,
            "direction":   signal_obj.direction,
            "score":       float(signal_obj.score),
            "price":       float(signal_obj.price),
            "stop_loss":   float(signal_obj.stop_loss) if signal_obj.stop_loss else None,
            "risk_pct":    float(signal_obj.risk_pct)  if signal_obj.risk_pct  else None,
            "created_at":  signal_obj.created_at.isoformat(),
        }
        _run_async(layer.group_send("radar_main", {
            "type": "radar.signal",
            "data": data,
        }))
        return True
    except Exception as e:
        logger.debug("broadcast_signal error: %s", e)
        return False


def broadcast_scanner_progress(current: int, total: int, found: int = 0) -> bool:
    """Broadcast scanner progress (เรียกทุก N หุ้น)"""
    layer = _get_channel_layer()
    if not layer:
        return False
    try:
        pct = round(current / max(total, 1) * 100, 1)
        _run_async(layer.group_send("radar_scanner", {
            "type": "radar.scanner_progress",
            "data": {
                "current": current,
                "total":   total,
                "pct":     pct,
                "found":   found,
            },
        }))
        return True
    except Exception as e:
        logger.debug("broadcast_progress error: %s", e)
        return False


def broadcast_scanner_done(signals: int, elapsed: float, exchange: str = "") -> bool:
    """Broadcast scanner เสร็จ"""
    layer = _get_channel_layer()
    if not layer:
        return False
    try:
        _run_async(layer.group_send("radar_scanner", {
            "type": "radar.scanner_done",
            "data": {
                "signals": signals,
                "elapsed": elapsed,
                "exchange": exchange,
            },
        }))
        return True
    except Exception as e:
        logger.debug("broadcast_done error: %s", e)
        return False


def broadcast_stats() -> bool:
    """Broadcast dashboard stats ใหม่"""
    layer = _get_channel_layer()
    if not layer:
        return False
    try:
        from radar.models import Symbol, Signal
        from django.utils import timezone
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        stats = {
            "total_symbols":  Symbol.objects.count(),
            "total_signals":  Signal.objects.count(),
            "buy_signals":    Signal.objects.filter(direction="LONG").count(),
            "sell_signals":   Signal.objects.filter(direction="SHORT").count(),
            "strong_signals": Signal.objects.filter(score__gte=80).count(),
            "recent_signals": Signal.objects.filter(created_at__gte=week_ago).count(),
        }
        _run_async(layer.group_send("radar_main", {
            "type": "radar.stats",
            "data": stats,
        }))
        return True
    except Exception as e:
        logger.debug("broadcast_stats error: %s", e)
        return False


def broadcast_prices(prices: list) -> bool:
    """Broadcast ราคาหุ้นล่าสุด"""
    layer = _get_channel_layer()
    if not layer:
        return False
    try:
        _run_async(layer.group_send("radar_main", {
            "type": "radar.prices",
            "data": prices,
        }))
        return True
    except Exception as e:
        logger.debug("broadcast_prices error: %s", e)
        return False
