from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.eventbrite import EventbriteCollector

MOCK_EVENTBRITE_RESPONSE = {
    "events": [
        {
            "name": {"text": "Austin Startup Networking Mixer"},
            "description": {"text": "Meet local founders and investors"},
            "url": "https://eventbrite.com/e/123",
            "capacity": 100,
            "start": {"utc": "2026-04-15T19:00:00Z"},
            "category_id": "101",
        },
        {
            "name": {"text": "Morning Yoga in the Park"},
            "description": {"text": "Free community yoga session"},
            "url": "https://eventbrite.com/e/456",
            "capacity": 30,
            "start": {"utc": "2026-04-16T08:00:00Z"},
            "category_id": "107",
        },
    ]
}

CATEGORY_MAP = {"101": "networking", "107": "fitness", "103": "music", "110": "food"}


@pytest.fixture
def collector():
    return EventbriteCollector()


async def test_collect_returns_events(collector):
    with patch("app.collectors.eventbrite.settings") as mock_settings, \
         patch("app.collectors.eventbrite.httpx.AsyncClient") as mock_client_cls:

        mock_settings.eventbrite_api_key = "test_key"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.json.return_value = MOCK_EVENTBRITE_RESPONSE
        resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)

        results = await collector.collect("austin")

    assert len(results) == 2
    assert all(r["entity_type"] == "event" for r in results)


async def test_collect_returns_empty_on_no_key(collector):
    with patch("app.collectors.eventbrite.settings") as mock_settings:
        mock_settings.eventbrite_api_key = ""
        results = await collector.collect("austin")
    assert results == []
