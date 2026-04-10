import asyncio

from app.celery_app import celery_app
from app.collectors.bandsintown import BandsintownCollector
from app.collectors.cities import CITIES
from app.collectors.eater_rss import EaterRSSCollector
from app.collectors.eventbrite import EventbriteCollector
from app.collectors.luma import LumaCollector
from app.collectors.partiful import PartifulCollector
from app.collectors.reddit import RedditCollector
from app.collectors.spotify import SpotifyCollector
from app.collectors.yelp import YelpCollector

ALL_COLLECTORS = [
    RedditCollector(),
    YelpCollector(),
    EventbriteCollector(),
    BandsintownCollector(),
    SpotifyCollector(),
    EaterRSSCollector(),
    LumaCollector(),
    PartifulCollector(),
]


@celery_app.task(name="collect.run_all")
def run_all_collectors() -> dict:
    """Run all collectors for all cities. Called by Celery beat daily."""
    results = {}
    for city in CITIES:
        city_results = {}
        for collector in ALL_COLLECTORS:
            count = asyncio.run(collector.run(city))
            city_results[collector.source_name] = count
        results[city] = city_results
    return results


@celery_app.task(name="collect.run_city")
def run_collectors_for_city(city: str) -> dict:
    """Run all collectors for a single city."""
    results = {}
    for collector in ALL_COLLECTORS:
        count = asyncio.run(collector.run(city))
        results[collector.source_name] = count
    return results
