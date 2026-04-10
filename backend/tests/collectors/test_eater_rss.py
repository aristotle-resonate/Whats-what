from unittest.mock import patch, MagicMock
import pytest
from app.collectors.eater_rss import EaterRSSCollector

MOCK_FEED = MagicMock()
MOCK_FEED.entries = [
    MagicMock(
        title="Austin's Best New Restaurants of 2026",
        summary="The hottest new spots opening this spring",
        link="https://austin.eater.com/2026/4/1/best-new-restaurants",
        published_parsed=(2026, 4, 1, 12, 0, 0, 0, 0, 0),
    ),
    MagicMock(
        title="Where to Get the Best Tacos in Austin",
        summary="A definitive guide to Austin taco spots",
        link="https://austin.eater.com/2026/3/15/best-tacos",
        published_parsed=(2026, 3, 15, 10, 0, 0, 0, 0, 0),
    ),
]


@pytest.fixture
def collector():
    return EaterRSSCollector()


async def test_collect_returns_food_mentions(collector):
    with patch("app.collectors.eater_rss.feedparser.parse", return_value=MOCK_FEED):
        results = await collector.collect("austin")

    assert len(results) == 2
    assert all(r["category"] == "food" for r in results)
    assert all(r["entity_type"] == "dish" for r in results)


async def test_collect_skips_city_without_eater(collector):
    results = await collector.collect("san-antonio")
    assert results == []
