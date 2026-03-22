"""
Radar Alert System — Line Notify & Telegram
===========================================
ส่งสัญญาณซื้อขายจาก Scanner Engine เข้าแอปแชท

การใช้งาน:
    alert_service.send_signal(symbol, signal_type, score, price)
"""

import logging
import requests
from django.conf import settings
import os

logger = logging.getLogger(__name__)

class AlertService:
    """
    Service สำหรับส่งการแจ้งเตือน
    รองรับ: Line Notify, Telegram Bot
    """

    def __init__(self):
        # โหลดค่าจาก environment ผ่าน settings
        self.line_token    = os.environ.get("LINE_NOTIFY_TOKEN")
        self.tg_bot_token  = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id    = os.environ.get("TELEGRAM_CHAT_ID")

    def send_line_notify(self, message: str) -> bool:
        """ส่งข้อความเข้า Line Notify"""
        if not self.line_token or self.line_token == "your_line_token_here":
            return False
            
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {self.line_token}"}
        payload = {"message": message}
        
        try:
            res = requests.post(url, headers=headers, data=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            logger.error("Line Notify ล้มเหลว: %s", e)
            return False

    def send_telegram(self, message: str) -> bool:
        """ส่งข้อความเข้า Telegram Bot"""
        if not self.tg_bot_token or not self.tg_chat_id:
            return False
            
        url = f"https://api.telegram.org/bot{self.tg_bot_token}/sendMessage"
        payload = {
            "chat_id": self.tg_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            logger.error("Telegram Alert ล้มเหลว: %s", e)
            return False

    def send_signal(self, symbol: str, signal_type: str, score: float, price: float, direction: str = "LONG"):
        """ส่งสัญญาณซื้อขายพร้อมฟอร์แมตข้อความ"""
        
        emoji = "🚀" if direction == "LONG" else "💥"
        type_label = signal_type.replace("_", " ").title()
        
        msg = (
            f"\n{emoji} *Radar Signal Found!*\n"
            f"━━━━━━━━━━━━━━\n"
            f"📈 *Symbol:* {symbol}\n"
            f"🎯 *Signal:* {type_label}\n"
            f"📊 *Score:* {score:.1f}\n"
            f"💰 *Price:* {price:,.2f}\n"
            f"🧭 *Direction:* {direction}\n"
            f"━━━━━━━━━━━━━━\n"
            f"ตรวจสอบกราฟได้ที่: http://localhost:5173/chart/{symbol}"
        )
        
        # ส่งทุกช่องทางที่มี Token
        line_ok = self.send_line_notify(msg)
        tg_ok   = self.send_telegram(msg)
        
        if line_ok or tg_ok:
            logger.info("ส่งแจ้งเตือน %s สำเร็จ", symbol)
        else:
            logger.debug("ไม่ได้ส่งแจ้งเตือน %s (Token ไม่พร้อม)", symbol)

# Singleton instance
alert_service = AlertService()
