from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.luma import LumaCollector

MOCK_HTML = """
<html><body>
<div class="event-card">
  <h3 class="event-name">Austin Run Club - Saturday Morning</h3>
  <div class="event-description">Weekly 5K run through Zilker Park</div>
  <a href="/event/austin-run-club-sat" class="event-link">View</a>
</div>
<div class="event-card">
  <h3 class="event-name">Wellness Wednesday: Breathwork Session</h3>
  <div class="event-description">Join us for a 60-minute breathwork journey</div>
  <a href="/event/wellness-wednesday" class="event-link">View</a>
</div>
</body></html>
"""


@pytest.fixture
def collector():
    return LumaCollector()


async def test_collect_returns_wellness_events(collector):
    with patch("app.collectors.luma.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.text = MOCK_HTML
        resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)

        results = await collector.collect("austin")

    assert len(results) >= 1
    assert all(r["entity_type"] == "event" for r in results)
    assert all(r["category"] in ("fitness", "networking") for r in results)
