from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.yelp import YelpCollector

MOCK_YELP_RESPONSE = {
    "businesses": [
        {
            "name": "Franklin Barbecue",
            "categories": [{"alias": "bbq", "title": "BBQ"}],
            "url": "https://yelp.com/franklin",
            "review_count": 4200,
            "rating": 4.5,
            "location": {"address1": "900 E 11th St"},
        },
        {
            "name": "Stubb's Waller Creek Amphitheater",
            "categories": [{"alias": "musicvenues", "title": "Music Venues"}],
            "url": "https://yelp.com/stubbs",
            "review_count": 1800,
            "rating": 4.4,
            "location": {"address1": "801 Red River St"},
        },
    ]
}


@pytest.fixture
def collector():
    return YelpCollector()


async def test_collect_returns_food_and_music(collector):
    with patch("app.collectors.yelp.settings") as mock_settings, \
         patch("app.collectors.yelp.httpx.AsyncClient") as mock_client_cls:

        mock_settings.yelp_api_key = "test_key"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.json.return_value = MOCK_YELP_RESPONSE
        resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)

        results = await collector.collect("austin")

    assert len(results) == 2
    categories = {r["category"] for r in results}
    assert "food" in categories
    assert "music" in categories


async def test_collect_returns_empty_on_no_key(collector):
    with patch("app.collectors.yelp.settings") as mock_settings:
        mock_settings.yelp_api_key = ""
        results = await collector.collect("austin")
    assert results == []
