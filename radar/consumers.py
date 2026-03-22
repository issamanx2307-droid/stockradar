"""
WebSocket Consumers — Radar หุ้น
==================================
Channels:
  ws/radar/     — main channel (prices, signals, scanner progress, stats)
"""

import json
import asyncio
import logging
from datetime import date, timedelta

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

# Group names
GROUP_RADAR   = "radar_main"
GROUP_SCANNER = "radar_scanner"


class RadarConsumer(AsyncWebsocketConsumer):
    """
    Main WebSocket consumer
    รับ/ส่งข้อมูล:
      → prices   : ราคาหุ้นล่าสุด
      → signals  : signal ใหม่จาก scanner
      → stats    : dashboard stats
      → scanner  : scanner progress
    """

    async def connect(self):
        await self.channel_layer.group_add(GROUP_RADAR, self.channel_name)
        await self.channel_layer.group_add(GROUP_SCANNER, self.channel_name)
        await self.accept()
        logger.info("WS connected: %s", self.channel_name)

        # ส่งข้อมูล initial ทันทีที่ connect
        await self.send_initial_data()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GROUP_RADAR, self.channel_name)
        await self.channel_layer.group_discard(GROUP_SCANNER, self.channel_name)
        logger.info("WS disconnected: %s", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """รับคำขอจาก frontend"""
        try:
            data = json.loads(text_data or "{}")
            action = data.get("action")

            if action == "subscribe_prices":
                symbols = data.get("symbols", [])
                await self.send_prices(symbols)

            elif action == "get_stats":
                await self.send_stats()

            elif action == "get_signals":
                await self.send_latest_signals()

            elif action == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))

            elif action == "poll_prices":
                # Frontend ขอ poll ทันที (เช่น Watchlist เพิ่งเปิด)
                symbols = data.get("symbols", [])
                if symbols:
                    prices = await self._fetch_live_prices(symbols)
                    await self.send(text_data=json.dumps({"type": "prices", "data": prices}))

        except Exception as e:
            logger.error("WS receive error: %s", e)

    # ── Send helpers ──────────────────────────────────────────────────────────

    async def send_initial_data(self):
        """ส่งข้อมูลครั้งแรกทันทีที่ connect"""
        await self.send_stats()
        await self.send_latest_signals()

    async def send_stats(self):
        stats = await self._get_stats()
        await self.send(text_data=json.dumps({
            "type":  "stats",
            "data":  stats,
        }))

    async def send_prices(self, symbols: list):
        prices = await self._get_prices(symbols)
        await self.send(text_data=json.dumps({
            "type":  "prices",
            "data":  prices,
        }))

    async def send_latest_signals(self):
        signals = await self._get_latest_signals()
        await self.send(text_data=json.dumps({
            "type":  "signals",
            "data":  signals,
        }))

    # ── Group message handlers (รับจาก broadcast) ─────────────────────────────

    async def radar_prices(self, event):
        """รับ broadcast ราคาใหม่"""
        await self.send(text_data=json.dumps({
            "type": "prices",
            "data": event["data"],
        }))

    async def radar_signal(self, event):
        """รับ broadcast signal ใหม่"""
        await self.send(text_data=json.dumps({
            "type": "signal_new",
            "data": event["data"],
        }))

    async def radar_stats(self, event):
        """รับ broadcast stats ใหม่"""
        await self.send(text_data=json.dumps({
            "type": "stats",
            "data": event["data"],
        }))

    async def radar_scanner_progress(self, event):
        """รับ broadcast scanner progress"""
        await self.send(text_data=json.dumps({
            "type": "scanner_progress",
            "data": event["data"],
        }))

    async def radar_scanner_done(self, event):
        """รับ broadcast scanner เสร็จ"""
        await self.send(text_data=json.dumps({
            "type": "scanner_done",
            "data": event["data"],
        }))

    # ── DB Queries (sync_to_async) ────────────────────────────────────────────

    @database_sync_to_async
    def _get_stats(self) -> dict:
        from radar.models import Symbol, Signal
        from django.utils import timezone
        week_ago = timezone.now() - timedelta(days=7)
        return {
            "total_symbols":  Symbol.objects.count(),
            "total_signals":  Signal.objects.count(),
            "buy_signals":    Signal.objects.filter(direction="LONG").count(),
            "sell_signals":   Signal.objects.filter(direction="SHORT").count(),
            "strong_signals": Signal.objects.filter(score__gte=80).count(),
            "recent_signals": Signal.objects.filter(created_at__gte=week_ago).count(),
        }

    @database_sync_to_async
    def _get_prices(self, symbols: list) -> list:
        from radar.models import PriceDaily, Symbol
        if not symbols:
            return []
        prices = []
        for sym_code in symbols[:20]:  # จำกัด 20 ตัว
            p = (PriceDaily.objects
                 .filter(symbol__symbol=sym_code.upper())
                 .order_by("-date").first())
            if p:
                prices.append({
                    "symbol": sym_code.upper(),
                    "close":  float(p.close),
                    "high":   float(p.high),
                    "low":    float(p.low),
                    "volume": p.volume,
                    "date":   str(p.date),
                })
        return prices

    @database_sync_to_async
    def _get_latest_signals(self) -> list:
        from radar.models import Signal
        signals = (Signal.objects
                   .select_related("symbol")
                   .order_by("-created_at", "-score")[:20])
        return [{
            "symbol":      s.symbol.symbol,
            "name":        s.symbol.name,
            "exchange":    s.symbol.exchange,
            "signal_type": s.signal_type,
            "direction":   s.direction,
            "score":       float(s.score),
            "price":       float(s.price),
            "stop_loss":   float(s.stop_loss) if s.stop_loss else None,
            "risk_pct":    float(s.risk_pct)  if s.risk_pct  else None,
            "created_at":  s.created_at.isoformat(),
        } for s in signals]

    @database_sync_to_async
    def _fetch_live_prices(self, symbols: list) -> list:
        """ดึงราคา live จาก yfinance สำหรับ symbols ที่ต้องการ"""
        try:
            from radar.price_poller import _fetch_latest
            from radar.models import Symbol as SymModel
            set_syms = list(SymModel.objects.filter(
                symbol__in=symbols, exchange="SET"
            ).values_list("symbol", flat=True))
            us_syms = list(SymModel.objects.filter(
                symbol__in=symbols
            ).exclude(exchange="SET").values_list("symbol", flat=True))
            result = []
            if set_syms:
                result += _fetch_latest(set_syms, suffix=".BK")
            if us_syms:
                result += _fetch_latest(us_syms, suffix="")
            return result
        except Exception as e:
            logger.error("_fetch_live_prices: %s", e)
            return []
