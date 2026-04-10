import re

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG

FITNESS_KEYWORDS = ["run", "yoga", "workout", "fitness", "gym", "hike", "crossfit", "cycle", "wellness", "breathwork", "meditation"]
NETWORKING_KEYWORDS = ["networking", "meetup", "mixer", "happy hour", "startup", "founder", "entrepreneur", "community"]


def _classify_luma_event(title: str, desc: str) -> str:
    text = (title + " " + desc).lower()
    if any(kw in text for kw in FITNESS_KEYWORDS):
        return "fitness"
    return "networking"


class LumaCollector(BaseCollector):
    source_name = "luma"

    async def collect(self, city: str) -> list[MentionData]:
        config = CITY_CONFIG[city]
        luma_city = config["luma_city"]

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; whats-what/0.1)"},
            follow_redirects=True,
            timeout=15.0,
        ) as client:
            resp = await client.get(f"https://lu.ma/{luma_city}")
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        results: list[MentionData] = []

        # Try multiple selectors — Luma's markup may vary
        cards = (
            soup.find_all("div", class_=re.compile(r"event-card|event-item|EventCard", re.I))
            or soup.find_all("a", attrs={"data-testid": re.compile(r"event", re.I)})
        )

        for card in cards[:30]:
            title_el = card.find(["h3", "h2", "div"], class_=re.compile(r"name|title", re.I))
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            desc_el = card.find(["div", "p"], class_=re.compile(r"desc|summary|detail", re.I))
            desc = desc_el.get_text(strip=True) if desc_el else ""

            link_el = card.find("a")
            url = None
            if link_el and link_el.get("href"):
                href = link_el["href"]
                url = href if href.startswith("http") else f"https://lu.ma{href}"

            category = _classify_luma_event(title, desc)

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
