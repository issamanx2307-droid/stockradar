"""
economic_calendar.py — ดึงปฏิทินเศรษฐกิจจาก ForexFactory (ฟรี ไม่ต้อง API key)
Cache 1 ชั่วโมง
"""
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

IMPACT_MAP = {"High": 3, "Medium": 2, "Low": 1, "Non-Economic": 0, "Holiday": 0}
COUNTRY_FLAG = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵",
    "CHF": "🇨🇭", "AUD": "🇦🇺", "CAD": "🇨🇦", "NZD": "🇳🇿",
    "CNY": "🇨🇳", "THB": "🇹🇭",
}


def fetch_economic_calendar(days_ahead: int = 7) -> list[dict]:
    cache_key = f"economic_calendar:{days_ahead}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        import requests
        from datetime import datetime, timedelta, timezone

        # ForexFactory JSON feed (no key needed)
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        raw = r.json()

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)

        results = []
        for ev in raw:
            try:
                dt_str = ev.get("date", "")
                if not dt_str:
                    continue
                # ForexFactory: "01-01-2025T00:00:00-05:00" or ISO format
                from dateutil import parser as dtparser
                dt = dtparser.parse(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < now - timedelta(hours=1) or dt > cutoff:
                    continue

                impact = ev.get("impact", "Low")
                currency = ev.get("country", "")

                results.append({
                    "datetime":    dt.isoformat(),
                    "date":        dt.strftime("%Y-%m-%d"),
                    "time":        dt.strftime("%H:%M") + " UTC",
                    "country":     currency,
                    "flag":        COUNTRY_FLAG.get(currency, "🌐"),
                    "event":       ev.get("title", ""),
                    "impact":      impact,
                    "impact_score": IMPACT_MAP.get(impact, 1),
                    "forecast":    ev.get("forecast", ""),
                    "previous":    ev.get("previous", ""),
                    "actual":      ev.get("actual", ""),
                })
            except Exception:
                continue

        # sort by datetime
        results.sort(key=lambda x: x["datetime"])
        cache.set(cache_key, results, timeout=3600)
        return results

    except Exception as e:
        logger.error("Economic calendar fetch error: %s", e)
        return _fallback_calendar()


def _fallback_calendar() -> list[dict]:
    """ข้อมูล fallback เมื่อ fetch ไม่ได้"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return [
        {
            "datetime": now.isoformat(), "date": now.strftime("%Y-%m-%d"),
            "time": "—", "country": "USD", "flag": "🇺🇸",
            "event": "ไม่สามารถดึงข้อมูลได้ในขณะนี้ — ลองใหม่ภายหลัง",
            "impact": "Low", "impact_score": 1,
            "forecast": "", "previous": "", "actual": "",
        }
    ]
