from datetime import datetime, timezone
from time import mktime

import feedparser

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG


class EaterRSSCollector(BaseCollector):
    source_name = "eater_rss"

    async def collect(self, city: str) -> list[MentionData]:
        config = CITY_CONFIG[city]
        rss_url = config.get("eater_rss")
        if not rss_url:
            return []

        feed = feedparser.parse(rss_url)

        results: list[MentionData] = []
        for entry in feed.entries[:30]:
            title: str = getattr(entry, "title", "") or ""
            summary: str = getattr(entry, "summary", "") or ""
            link: str = getattr(entry, "link", "") or ""

            published_at = None
            parsed_time = getattr(entry, "published_parsed", None)
            if parsed_time:
                try:
                    published_at = datetime.fromtimestamp(
                        mktime(parsed_time), tz=timezone.utc
                    )
                except (OverflowError, ValueError):
                    pass

            results.append(
                MentionData(
                    entity_name=title[:255],
                    entity_type="dish",
                    category="food",
                    content_snippet=summary[:500] or None,
                    url=link or None,
                    mention_count=1,
                    sentiment_score=None,
                    published_at=published_at,
                )
            )

        return results
