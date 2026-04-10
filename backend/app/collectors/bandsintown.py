from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG
from app.config import settings


class BandsintownCollector(BaseCollector):
    source_name = "bandsintown"

    async def collect(self, city: str) -> list[MentionData]:
        config = CITY_CONFIG[city]
        location = config["bandsintown_location"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://rest.bandsintown.com/events/search",
                params={
                    "app_id": settings.bandsintown_app_id,
                    "location": location,
                    "radius": 25,
                    "per_page": 50,
                },
            )
            resp.raise_for_status()
            events = resp.json()

        if not isinstance(events, list):
            return []

        results: list[MentionData] = []
        for event in events:
            artist_name = event.get("artist", {}).get("name", "Unknown Artist")
            venue_name = event.get("venue", {}).get("name", "")
            title = f"{artist_name} at {venue_name}" if venue_name else artist_name

            is_soldout = any(
                o.get("status") == "soldout"
                for o in event.get("offers", [])
            )
            mention_count = 100 if is_soldout else 10

            published_at = None
            dt_str = event.get("datetime")
            if dt_str:
                try:
                    published_at = datetime.fromisoformat(dt_str).replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    pass

            results.append(
                MentionData(
                    entity_name=title[:255],
                    entity_type="event",
                    category="music",
                    content_snippet=f"Live at {venue_name}" if venue_name else None,
                    url=event.get("url"),
                    mention_count=mention_count,
                    sentiment_score=None,
                    published_at=published_at,
                )
            )

        return results
