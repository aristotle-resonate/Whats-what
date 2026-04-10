import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG
from app.config import settings

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "music": ["music", "concert", "band", "venue", "live", "festival", "show", "gig", "artist", "dj"],
    "food": ["restaurant", "food", "eat", "bar", "brunch", "taco", "burger", "pizza", "coffee", "brewery", "cocktail"],
    "fitness": ["gym", "fitness", "workout", "run", "yoga", "crossfit", "cycling", "hike", "trail", "sport"],
    "networking": ["meetup", "networking", "event", "happy hour", "mixer", "conference", "workshop", "startup"],
}


def _categorize(title: str, body: str) -> str | None:
    text = (title + " " + body).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords):
            return category
    return None


class RedditCollector(BaseCollector):
    source_name = "reddit"

    async def collect(self, city: str) -> list[MentionData]:
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            return []

        config = CITY_CONFIG[city]
        subreddit = config["reddit_subreddit"]

        async with httpx.AsyncClient() as client:
            # Get OAuth token
            token_resp = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(settings.reddit_client_id, settings.reddit_client_secret),
                headers={"User-Agent": settings.reddit_user_agent},
            )
            token_resp.raise_for_status()
            token = token_resp.json()["access_token"]

            # Fetch hot posts
            posts_resp = await client.get(
                f"https://oauth.reddit.com/r/{subreddit}/hot",
                params={"limit": 50},
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": settings.reddit_user_agent,
                },
            )
            posts_resp.raise_for_status()
            posts = posts_resp.json()["data"]["children"]

        results: list[MentionData] = []
        for post in posts:
            d = post["data"]
            title: str = d.get("title", "")
            body: str = d.get("selftext", "")
            category = _categorize(title, body)
            if category is None:
                continue

            results.append(
                MentionData(
                    entity_name=title[:255],
                    entity_type="event",
                    category=category,
                    content_snippet=(body[:500] if body else None),
                    url=d.get("url"),
                    mention_count=int(d.get("score", 1)),
                    sentiment_score=None,
                    published_at=datetime.fromtimestamp(
                        d["created_utc"], tz=timezone.utc
                    ) if d.get("created_utc") else None,
                )
            )

        return results
