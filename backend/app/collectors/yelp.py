import httpx

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG
from app.config import settings

YELP_CATEGORY_MAP: dict[str, str] = {
    "restaurants": "food",
    "food": "food",
    "bars": "food",
    "coffee": "food",
    "breweries": "food",
    "musicvenues": "music",
    "jazz": "music",
    "festivals": "music",
    "gyms": "fitness",
    "yoga": "fitness",
    "fitness": "fitness",
    "activelife": "fitness",
}


def _map_category(yelp_categories: list[dict]) -> str:
    for cat in yelp_categories:
        alias = cat.get("alias", "")
        for key, mapped in YELP_CATEGORY_MAP.items():
            if key in alias:
                return mapped
    return "food"  # default for Yelp results


class YelpCollector(BaseCollector):
    source_name = "yelp"

    async def collect(self, city: str) -> list[MentionData]:
        if not settings.yelp_api_key:
            return []

        config = CITY_CONFIG[city]
        location = config["yelp_location"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.yelp.com/v3/businesses/search",
                headers={"Authorization": f"Bearer {settings.yelp_api_key}"},
                params={
                    "location": location,
                    "sort_by": "review_count",
                    "limit": 50,
                },
            )
            resp.raise_for_status()
            businesses = resp.json().get("businesses", [])

        results: list[MentionData] = []
        for biz in businesses:
            category = _map_category(biz.get("categories", []))
            results.append(
                MentionData(
                    entity_name=biz["name"][:255],
                    entity_type="venue",
                    category=category,
                    content_snippet=biz.get("location", {}).get("address1"),
                    url=biz.get("url"),
                    mention_count=biz.get("review_count", 1),
                    sentiment_score=biz.get("rating"),
                    published_at=None,
                )
            )

        return results
