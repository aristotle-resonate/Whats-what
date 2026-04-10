from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.bandsintown import BandsintownCollector

MOCK_EVENTS = [
    {
        "title": "The Midnight at Stubb's",
        "artist": {"name": "The Midnight"},
        "venue": {"name": "Stubb's Waller Creek Amphitheater", "city": "Austin"},
        "url": "https://bandsintown.com/e/1",
        "datetime": "2026-04-20T20:00:00",
        "offers": [{"status": "available"}],
    },
    {
        "title": "Khruangbin at ACL Live",
        "artist": {"name": "Khruangbin"},
        "venue": {"name": "ACL Live", "city": "Austin"},
        "url": "https://bandsintown.com/e/2",
        "datetime": "2026-04-22T21:00:00",
        "offers": [{"status": "soldout"}],
    },
]


@pytest.fixture
def collector():
    return BandsintownCollector()


async def test_collect_returns_music_events(collector):
    with patch("app.collectors.bandsintown.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.json.return_value = MOCK_EVENTS
        resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)

        results = await collector.collect("austin")

    assert len(results) == 2
    assert all(r["category"] == "music" for r in results)
    assert all(r["entity_type"] == "event" for r in results)
    # Soldout show gets higher mention_count boost
    soldout = next(r for r in results if "Khruangbin" in r["entity_name"])
    available = next(r for r in results if "Midnight" in r["entity_name"])
    assert soldout["mention_count"] > available["mention_count"]


async def test_collect_always_runs(collector):
    """Bandsintown doesn't require an API key."""
    with patch("app.collectors.bandsintown.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)

        results = await collector.collect("austin")

    assert results == []
