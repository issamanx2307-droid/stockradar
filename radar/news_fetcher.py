"""
news_fetcher.py — ดึงข่าวหุ้นจากหลายแหล่ง + วิเคราะห์ Sentiment

แหล่งข่าวฟรี:
  - Reuters Business RSS
  - Yahoo Finance RSS
  - Google News RSS (หุ้นไทย + US)
  - Bangkok Post Business RSS
  - Thansettakij RSS
  - SET Market News (RSS)

Sentiment: keyword-based scoring (ไม่ต้องใช้ AI)
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ── RSS Sources ───────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {
        "source": "REUTERS",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "lang": "en",
    },
    {
        "source": "REUTERS",
        "url": "https://feeds.reuters.com/reuters/companyNews",
        "lang": "en",
    },
    {
        "source": "YAHOO",
        "url": "https://finance.yahoo.com/news/rssindex",
        "lang": "en",
    },
    {
        "source": "GOOGLE",
        "url": "https://news.google.com/rss/search?q=SET+ตลาดหลักทรัพย์&hl=th&gl=TH&ceid=TH:th",
        "lang": "th",
    },
    {
        "source": "GOOGLE",
        "url": "https://news.google.com/rss/search?q=stock+market+NYSE+NASDAQ&hl=en&gl=US&ceid=US:en",
        "lang": "en",
    },
    {
        "source": "BANGKOKPOST",
        "url": "https://www.bangkokpost.com/rss/data/business.xml",
        "lang": "en",
    },
    {
        "source": "THANSETTAKIJ",
        "url": "https://www.thansettakij.com/rss.xml",
        "lang": "th",
    },
]

# ── Sentiment Keywords ────────────────────────────────────────────────────────
BULLISH_EN = [
    "surge", "rally", "soar", "jump", "gain", "rise", "bull", "buy",
    "profit", "growth", "beat", "upgrade", "strong", "record high",
    "outperform", "positive", "optimistic", "expand", "boost",
]
BEARISH_EN = [
    "drop", "fall", "plunge", "crash", "decline", "loss", "bear", "sell",
    "miss", "downgrade", "weak", "layoff", "bankruptcy", "cut", "slump",
    "warning", "risk", "concern", "negative", "recession",
]
BULLISH_TH = [
    "กำไร", "เติบโต", "ขึ้น", "พุ่ง", "แข็งแกร่ง", "บวก", "ซื้อ",
    "ราคาสูง", "ทำนิวไฮ", "ปรับตัวขึ้น", "เพิ่มขึ้น", "ฟื้นตัว",
    "แนวโน้มดี", "ผลประกอบการดี", "ขยายตัว", "ระดมทุน",
]
BEARISH_TH = [
    "ขาดทุน", "ลดลง", "ร่วง", "ดิ่ง", "ขาย", "ลบ", "อ่อนแอ",
    "ราคาต่ำ", "ปรับตัวลง", "เพิ่มขึ้นของขาดทุน", "วิกฤต",
    "ล้มละลาย", "ถดถอย", "เลิกจ้าง", "ปิดกิจการ", "ขาดทุนสุทธิ",
]


def score_sentiment(text: str) -> tuple[str, float]:
    """
    คำนวณ sentiment จาก keywords
    คืน: (label, score)  score ∈ [-1.0, +1.0]
    """
    t = (text or "").lower()
    bull = sum(1 for w in BULLISH_EN + BULLISH_TH if w.lower() in t)
    bear = sum(1 for w in BEARISH_EN + BEARISH_TH if w.lower() in t)

    total = bull + bear
    if total == 0:
        return "NEUTRAL", 0.0

    score = (bull - bear) / total   # -1 ถึง +1
    if score > 0.1:
        label = "BULLISH"
    elif score < -0.1:
        label = "BEARISH"
    else:
        label = "NEUTRAL"
    return label, round(score, 3)


def _parse_date(date_str: str) -> datetime:
    """แปลง date string หลายรูปแบบ → datetime (UTC aware)"""
    if not date_str:
        return datetime.now(timezone.utc)
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    return datetime.now(timezone.utc)

def _fetch_rss(feed: dict) -> list[dict]:
    """ดึง RSS feed และ parse เป็น list of dict"""
    try:
        resp = requests.get(feed["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        xml = resp.text
    except Exception as e:
        logger.warning("RSS fetch ล้มเหลว %s: %s", feed["url"], e)
        return []

    # ── Parse XML อย่างง่าย ──
    items = []
    # แยก <item> blocks
    for block in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL):
        def tag(name: str) -> str:
            # ดึงค่าใน <tag>...</tag> หรือ <tag><![CDATA[...]]></tag>
            m = re.search(
                rf"<{name}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>",
                block, re.DOTALL
            )
            return (m.group(1) or "").strip() if m else ""

        title = tag("title")
        url   = tag("link") or tag("guid")
        if not url:
            continue

        # ทำความสะอาด URL จาก Google News redirect
        gn_match = re.search(r"url=([^&]+)", url)
        if gn_match:
            import urllib.parse
            url = urllib.parse.unquote(gn_match.group(1))

        summary = re.sub(r"<[^>]+>", "", tag("description")).strip()
        pub_date = tag("pubDate") or tag("published") or tag("dc:date")

        items.append({
            "source":       feed["source"],
            "title":        title[:500],
            "summary":      summary[:1000],
            "url":          url[:1000],
            "published_at": _parse_date(pub_date),
        })

    return items


def _match_symbols(text: str, symbol_set: set[str]) -> list[str]:
    """หา symbol ที่ถูกกล่าวถึงใน text"""
    found = []
    words = re.findall(r"\b[A-Z]{1,8}\b", text.upper())
    for w in words:
        if w in symbol_set:
            found.append(w)
    return list(set(found))


def fetch_and_save_news(max_per_feed: int = 50) -> dict:
    """
    ดึงข่าวจากทุก RSS feed แล้วบันทึกลง DB
    คืน: {"fetched": N, "saved": N, "skipped": N}
    """
    from radar.models import NewsItem, Symbol

    # โหลด symbol set ครั้งเดียว
    symbol_set = set(Symbol.objects.values_list("symbol", flat=True))

    stats = {"fetched": 0, "saved": 0, "skipped": 0}

    for feed in RSS_FEEDS:
        items = _fetch_rss(feed)[:max_per_feed]
        stats["fetched"] += len(items)
        time.sleep(0.5)  # ป้องกัน rate limit

        for item in items:
            if not item.get("url") or not item.get("title"):
                stats["skipped"] += 1
                continue

            # Skip ถ้ามีแล้ว
            if NewsItem.objects.filter(url=item["url"]).exists():
                stats["skipped"] += 1
                continue

            full_text = item["title"] + " " + item["summary"]
            sentiment, score = score_sentiment(full_text)
            matched = _match_symbols(full_text, symbol_set)

            try:
                news = NewsItem.objects.create(
                    title=item["title"],
                    summary=item["summary"],
                    url=item["url"],
                    source=item["source"],
                    published_at=item["published_at"],
                    sentiment=sentiment,
                    sentiment_score=score,
                )
                if matched:
                    syms = Symbol.objects.filter(symbol__in=matched)
                    news.symbols.set(syms)

                stats["saved"] += 1
            except Exception as e:
                logger.error("บันทึกข่าวล้มเหลว: %s", e)
                stats["skipped"] += 1

    return stats
