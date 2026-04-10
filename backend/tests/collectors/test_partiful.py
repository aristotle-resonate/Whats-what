from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.partiful import PartifulCollector

MOCK_HTML = """
<html><body>
<div class="event-listing">
  <h2>Tech Founders Happy Hour</h2>
  <p class="desc">Monthly mixer for Austin founders and builders</p>
  <a href="/event/tech-founders-happy-hour">Details</a>
</div>
<div class="event-listing">
  <h2>Rooftop Sunset Networking</h2>
  <p class="desc">Connect with creatives over drinks</p>
  <a href="/event/rooftop-sunset">Details</a>
</div>
</body></html>
"""


@pytest.fixture
def collector():
    return PartifulCollector()


async def test_collect_returns_networking_events(collector):
    with patch("app.collectors.partiful.httpx.AsyncClient") as mock_client_cls:
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
