from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG
from app.config import settings

EVENTBRITE_CATEGORY_MAP: dict[str, str] = {
    "103": "music",
    "101": "networking",
    "110": "food",
    "107": "fitness",
    "108": "fitness",
    "111": "networking",
    "113": "networking",
}


class EventbriteCollector(BaseCollector):
    source_name = "eventbrite"

    async def collect(self, city: str) -> list[MentionData]:
        if not settings.eventbrite_api_key:
            return []

        config = CITY_CONFIG[city]
        city_name = config["eventbrite_city"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.eventbriteapi.com/v3/events/search/",
                headers={"Authorization": f"Bearer {settings.eventbrite_api_key}"},
                params={
                    "location.address": city_name,
                    "location.within": "25mi",
                    "expand": "category",
                    "page_size": 50,
                },
            )
            resp.raise_for_status()
            events = resp.json().get("events", [])

        results: list[MentionData] = []
        for event in events:
            category_id = event.get("category_id", "")
            category = EVENTBRITE_CATEGORY_MAP.get(str(category_id), "networking")

            start_utc = event.get("start", {}).get("utc")
            published_at = None
            if start_utc:
                try:
                    published_at = datetime.fromisoformat(
                        start_utc.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            results.append(
                MentionData(
                    entity_name=event["name"]["text"][:255],
                    entity_type="event",
                    category=category,
                    content_snippet=event.get("description", {}).get("text", "")[:500] or None,
                    url=event.get("url"),
                    mention_count=event.get("capacity", 1),
                    sentiment_score=None,
                    published_at=published_at,
                )
            )

        return results
