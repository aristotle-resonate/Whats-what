import re

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG

CITY_SEARCH_TERMS: dict[str, str] = {
    "austin": "Austin",
    "dallas": "Dallas",
    "san-antonio": "San+Antonio",
    "new-york": "New+York",
    "los-angeles": "Los+Angeles",
}

FITNESS_KEYWORDS = ["run", "yoga", "workout", "fitness", "gym", "wellness", "hike"]


def _classify_partiful_event(title: str, desc: str) -> str:
    text = (title + " " + desc).lower()
    if any(kw in text for kw in FITNESS_KEYWORDS):
        return "fitness"
    return "networking"


class PartifulCollector(BaseCollector):
    source_name = "partiful"

    async def collect(self, city: str) -> list[MentionData]:
        search_term = CITY_SEARCH_TERMS.get(city, city)

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; whats-what/0.1)"},
            follow_redirects=True,
            timeout=15.0,
        ) as client:
            resp = await client.get(
                f"https://partiful.com/events?location={search_term}"
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        results: list[MentionData] = []

        cards = (
            soup.find_all("div", class_=re.compile(r"event-listing|EventCard|event-card", re.I))
            or soup.find_all("article")
        )

        for card in cards[:30]:
            title_el = card.find(["h2", "h3", "h1"])
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            desc_el = card.find(["p", "div"], class_=re.compile(r"desc|summary", re.I))
            desc = desc_el.get_text(strip=True) if desc_el else ""

            link_el = card.find("a")
            url = None
            if link_el and link_el.get("href"):
                href = link_el["href"]
                url = href if href.startswith("http") else f"https://partiful.com{href}"

            category = _classify_partiful_event(title, desc)

            results.append(
                MentionData(
                    entity_name=title[:255],
                    entity_type="event",
                    category=category,
                    content_snippet=desc[:500] or None,
                    url=url,
                    mention_count=1,
                    sentiment_score=None,
                    published_at=None,
                )
            )

        return results
