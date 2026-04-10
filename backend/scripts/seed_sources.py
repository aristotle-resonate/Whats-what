"""
Run once to populate the sources table with all city/source combos.
Usage: cd backend && python scripts/seed_sources.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.collectors.cities import CITIES
from app.database import async_session_factory
from app.models.source import Source

SOURCES = [
    {"name": "reddit",      "categories": ["music", "food", "fitness", "networking"], "rate_limit_daily": 100},
    {"name": "yelp",        "categories": ["food", "fitness"],                        "rate_limit_daily": 500},
    {"name": "eventbrite",  "categories": ["networking", "fitness", "music"],         "rate_limit_daily": 1000},
    {"name": "bandsintown", "categories": ["music"],                                  "rate_limit_daily": 500},
    {"name": "spotify",     "categories": ["music"],                                  "rate_limit_daily": 100},
    {"name": "eater_rss",   "categories": ["food"],                                   "rate_limit_daily": 50},
    {"name": "luma",        "categories": ["fitness", "networking"],                  "rate_limit_daily": 100},
    {"name": "partiful",    "categories": ["networking"],                              "rate_limit_daily": 100},
]


async def seed() -> None:
    async with async_session_factory() as session:
        for city in CITIES:
            for source in SOURCES:
                # Skip eater_rss for san-antonio
                if source["name"] == "eater_rss" and city == "san-antonio":
                    continue
                existing = await session.execute(
                    __import__("sqlalchemy").select(Source).where(
                        Source.name == source["name"],
                        Source.city == city,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                session.add(
                    Source(
                        name=source["name"],
                        city=city,
                        categories=source["categories"],
                        active=True,
                        rate_limit_daily=source["rate_limit_daily"],
                    )
                )
        await session.commit()
        print(f"Seeded sources for {len(CITIES)} cities.")


if __name__ == "__main__":
    asyncio.run(seed())
