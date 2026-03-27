"""
Management command: fetch_news
ดึงข่าวหุ้นจาก RSS feeds แล้วบันทึกลง NewsItem model
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

import datetime


RSS_FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=หุ้น+ตลาดหลักทรัพย์&hl=th&gl=TH&ceid=TH:th",
        "source": "GOOGLE",
    },
    {
        "url": "https://news.google.com/rss/search?q=stock+market+NYSE+NASDAQ&hl=en&gl=US&ceid=US:en",
        "source": "GOOGLE",
    },
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "source": "REUTERS",
    },
    {
        "url": "https://www.bangkokpost.com/rss/data/business.xml",
        "source": "BANGKOKPOST",
    },
    {
        "url": "https://www.thansettakij.com/rss.xml",
        "source": "THANSETTAKIJ",
    },
]

LIMIT_PER_RUN = 50


def _parse_feed(url):
    """Try feedparser first, fall back to requests+lxml."""
    entries = []
    try:
        import feedparser
        feed = feedparser.parse(url)
        for e in feed.entries:
            published_at = None
            if hasattr(e, "published_parsed") and e.published_parsed:
                import time
                published_at = datetime.datetime(*e.published_parsed[:6],
                                                tzinfo=datetime.timezone.utc)
            elif hasattr(e, "updated_parsed") and e.updated_parsed:
                import time
                published_at = datetime.datetime(*e.updated_parsed[:6],
                                                tzinfo=datetime.timezone.utc)
            entries.append({
                "title": getattr(e, "title", "")[:512],
                "url": getattr(e, "link", ""),
                "summary": getattr(e, "summary", "")[:2000],
                "published_at": published_at,
            })
        return entries
    except ImportError:
        pass

    # Fallback: requests + lxml
    try:
        import requests
        from lxml import etree

        resp = requests.get(url, timeout=15, headers={"User-Agent": "StockRadar/1.0"})
        resp.raise_for_status()
        root = etree.fromstring(resp.content)

        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0
        items = root.findall(".//item")
        for item in items:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            summary = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            published_at = None
            if pub_el is not None and pub_el.text:
                from email.utils import parsedate_to_datetime
                try:
                    published_at = parsedate_to_datetime(pub_el.text.strip())
                except Exception:
                    pass
            entries.append({
                "title": title[:512],
                "url": link,
                "summary": summary[:2000],
                "published_at": published_at,
            })

        # Atom feed
        if not entries:
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                summary_el = entry.find("atom:summary", ns)
                pub_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.get("href", "") if link_el is not None else ""
                summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
                published_at = None
                if pub_el is not None and pub_el.text:
                    try:
                        published_at = datetime.datetime.fromisoformat(pub_el.text.strip().replace("Z", "+00:00"))
                    except Exception:
                        pass
                entries.append({
                    "title": title[:512],
                    "url": link,
                    "summary": summary[:2000],
                    "published_at": published_at,
                })
    except Exception:
        pass

    return entries


class Command(BaseCommand):
    help = "ดึงข่าวหุ้นจาก RSS feeds แล้วบันทึกลง NewsItem"

    def handle(self, *args, **options):
        from radar.models import NewsItem

        now = timezone.now()
        total_saved = 0
        total_skipped = 0
        total_fetched = 0

        for feed_cfg in RSS_FEEDS:
            url = feed_cfg["url"]
            source = feed_cfg["source"]

            self.stdout.write(f"[fetch_news] Fetching {source}: {url}")
            try:
                entries = _parse_feed(url)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  ERROR fetching {url}: {exc}"))
                continue

            self.stdout.write(f"  Got {len(entries)} entries")
            total_fetched += len(entries)

            for entry in entries:
                if total_saved >= LIMIT_PER_RUN:
                    break

                item_url = entry.get("url", "").strip()[:2048]
                title = entry.get("title", "").strip()

                if not item_url or not title:
                    total_skipped += 1
                    continue

                # Skip duplicates by URL
                if NewsItem.objects.filter(url=item_url).exists():
                    total_skipped += 1
                    continue

                published_at = entry.get("published_at") or now

                try:
                    NewsItem.objects.create(
                        title=title,
                        url=item_url,
                        summary=entry.get("summary", ""),
                        source=source,
                        published_at=published_at,
                        sentiment="NEUTRAL",
                        sentiment_score=0.0,
                    )
                    total_saved += 1
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"  Could not save '{title[:40]}': {exc}"))
                    total_skipped += 1

            if total_saved >= LIMIT_PER_RUN:
                self.stdout.write(self.style.WARNING(f"  Reached limit of {LIMIT_PER_RUN} items — stopping early"))
                break

        self.stdout.write(
            self.style.SUCCESS(
                f"[fetch_news] Done — fetched={total_fetched}, saved={total_saved}, skipped={total_skipped}"
            )
        )
