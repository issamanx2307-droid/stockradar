

@shared_task(name="radar.tasks.fetch_news")
def fetch_news():
    """ดึงข่าวหุ้นจาก RSS feeds อัตโนมัติทุก 6 ชั่วโมง"""
    try:
        from radar.news_fetcher import fetch_and_save_news
        stats = fetch_and_save_news(max_per_feed=30)
        logger.info("fetch_news done: %s", stats)
        return stats
    except Exception as e:
        logger.error("fetch_news error: %s", e)
        return {"error": str(e)}
