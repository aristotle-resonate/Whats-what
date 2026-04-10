from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.spotify import SpotifyCollector

MOCK_TOKEN = {"access_token": "test_token", "token_type": "Bearer"}

MOCK_SEARCH_RESPONSE = {
    "artists": {
        "items": [
            {
                "name": "Khruangbin",
                "genres": ["psychedelic soul", "houston rap"],
                "popularity": 72,
                "external_urls": {"spotify": "https://open.spotify.com/artist/1"},
            },
            {
                "name": "Gary Clark Jr.",
                "genres": ["blues rock", "austin blues"],
                "popularity": 65,
                "external_urls": {"spotify": "https://open.spotify.com/artist/2"},
            },
        ]
    }
}


@pytest.fixture
def collector():
    return SpotifyCollector()


async def test_collect_returns_music_artists(collector):
    with patch("app.collectors.spotify.settings") as mock_settings, \
         patch("app.collectors.spotify.httpx.AsyncClient") as mock_client_cls:

        mock_settings.spotify_client_id = "test_id"
        mock_settings.spotify_client_secret = "test_secret"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        token_resp = MagicMock()
        token_resp.json.return_value = MOCK_TOKEN
        token_resp.raise_for_status = MagicMock()

        search_resp = MagicMock()
        search_resp.json.return_value = MOCK_SEARCH_RESPONSE
        search_resp.raise_for_status = MagicMock()

        mock_client.post = AsyncMock(return_value=token_resp)
        mock_client.get = AsyncMock(return_value=search_resp)

        results = await collector.collect("austin")

    assert len(results) == 2
    assert all(r["category"] == "music" for r in results)
    assert all(r["entity_type"] == "artist" for r in results)


async def test_collect_returns_empty_on_no_credentials(collector):
    with patch("app.collectors.spotify.settings") as mock_settings:
        mock_settings.spotify_client_id = ""
        mock_settings.spotify_client_secret = ""
        results = await collector.collect("austin")
    assert results == []
