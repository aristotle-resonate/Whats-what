from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.collectors.reddit import RedditCollector


MOCK_TOKEN_RESPONSE = {"access_token": "test_token", "token_type": "bearer"}

MOCK_POSTS_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Best live music venues in Austin?",
                    "selftext": "Looking for great music spots",
                    "url": "https://reddit.com/r/Austin/123",
                    "score": 150,
                    "created_utc": 1712700000.0,
                }
            },
            {
                "data": {
                    "title": "Top restaurants downtown",
                    "selftext": "Best food spots I found",
                    "url": "https://reddit.com/r/Austin/456",
                    "score": 89,
                    "created_utc": 1712700000.0,
                }
            },
            {
                "data": {
                    "title": "Random post about weather",
                    "selftext": "It is hot outside",
                    "url": "https://reddit.com/r/Austin/789",
                    "score": 10,
                    "created_utc": 1712700000.0,
                }
            },
        ]
    }
}


@pytest.fixture
def collector():
    return RedditCollector()


async def test_collect_returns_mention_data(collector):
    with patch("app.collectors.reddit.settings") as mock_settings, \
         patch("app.collectors.reddit.httpx.AsyncClient") as mock_client_cls:

        mock_settings.reddit_client_id = "test_id"
        mock_settings.reddit_client_secret = "test_secret"
        mock_settings.reddit_user_agent = "test/0.1"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        token_resp = MagicMock()
        token_resp.json.return_value = MOCK_TOKEN_RESPONSE
        token_resp.raise_for_status = MagicMock()

        posts_resp = MagicMock()
        posts_resp.json.return_value = MOCK_POSTS_RESPONSE
        posts_resp.raise_for_status = MagicMock()

        mock_client.post = AsyncMock(return_value=token_resp)
        mock_client.get = AsyncMock(return_value=posts_resp)

        results = await collector.collect("austin")

    # Only music and food posts match — weather post is filtered out
    assert len(results) == 2
    assert all("entity_name" in r for r in results)
    assert all(r["category"] in ("music", "food") for r in results)


async def test_collect_returns_empty_on_no_credentials(collector):
    with patch("app.collectors.reddit.settings") as mock_settings:
        mock_settings.reddit_client_id = ""
        mock_settings.reddit_client_secret = ""
        mock_settings.reddit_user_agent = "test/0.1"
        results = await collector.collect("austin")
    assert results == []
