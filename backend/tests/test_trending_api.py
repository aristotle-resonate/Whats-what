"""Tests for GET /trending."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import get_session
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trending_row(
    entity_name="Stubb's",
    entity_type="venue",
    category="music",
    city="austin",
    composite_score=0.9,
    volume_score=0.8,
    sentiment_score=0.85,
    freshness_score=0.95,
    trend_direction="rising",
    scored_at=None,
):
    row = MagicMock()
    row.entity_name = entity_name
    row.entity_type = entity_type
    row.category = category
    row.city = city
    row.composite_score = composite_score
    row.volume_score = volume_score
    row.sentiment_score = sentiment_score
    row.freshness_score = freshness_score
    row.trend_direction = trend_direction
    row.scored_at = scored_at or datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
    return row


def _make_session_override(scalars_return_value):
    """Return an async-generator override for get_session."""
    scalars_result = MagicMock()
    scalars_result.all.return_value = scalars_return_value

    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_result

    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)

    async def _override():
        yield session

    return _override, session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetTrending:
    @pytest.mark.asyncio
    async def test_valid_city_and_category_returns_200(self, client):
        rows = [_make_trending_row()]
        override, _ = _make_session_override(rows)
        app.dependency_overrides[get_session] = override

        resp = await client.get("/trending?city=austin&category=music")
        assert resp.status_code == 200
        body = resp.json()
        assert body["city"] == "austin"
        assert body["category"] == "music"
        assert len(body["entities"]) == 1
        entity = body["entities"][0]
        assert entity["entity_name"] == "Stubb's"
        assert entity["entity_type"] == "venue"
        assert entity["category"] == "music"
        assert entity["composite_score"] == 0.9
        assert entity["trend_direction"] == "rising"

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_invalid_city_returns_422(self, client):
        resp = await client.get("/trending?city=atlantis")
        assert resp.status_code == 422

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_unknown_category_returns_200_empty_list(self, client):
        override, _ = _make_session_override([])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/trending?city=austin&category=astrology")
        assert resp.status_code == 200
        body = resp.json()
        assert body["entities"] == []

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_limit_param_is_respected(self, client):
        rows = [
            _make_trending_row(entity_name=f"Venue {i}", composite_score=1.0 - i * 0.1)
            for i in range(3)
        ]
        override, session = _make_session_override(rows)
        app.dependency_overrides[get_session] = override

        resp = await client.get("/trending?city=austin&limit=3")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["entities"]) == 3

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_limit_above_max_returns_422(self, client):
        resp = await client.get("/trending?city=austin&limit=51")
        assert resp.status_code == 422

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_results_ordered_by_composite_score_desc(self, client):
        rows = [
            _make_trending_row(entity_name="A", composite_score=0.9),
            _make_trending_row(entity_name="B", composite_score=0.7),
            _make_trending_row(entity_name="C", composite_score=0.5),
        ]
        override, _ = _make_session_override(rows)
        app.dependency_overrides[get_session] = override

        resp = await client.get("/trending?city=austin&category=music")
        assert resp.status_code == 200
        scores = [e["composite_score"] for e in resp.json()["entities"]]
        assert scores == sorted(scores, reverse=True)

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_no_category_returns_all_categories(self, client):
        rows = [
            _make_trending_row(entity_name="Stubb's", category="music"),
            _make_trending_row(entity_name="Franklin BBQ", category="food"),
        ]
        override, _ = _make_session_override(rows)
        app.dependency_overrides[get_session] = override

        resp = await client.get("/trending?city=austin")
        assert resp.status_code == 200
        body = resp.json()
        assert body["category"] is None
        assert len(body["entities"]) == 2
        categories = {e["category"] for e in body["entities"]}
        assert categories == {"music", "food"}

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_city_required_returns_422_when_missing(self, client):
        resp = await client.get("/trending")
        assert resp.status_code == 422

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_entity_fields_present(self, client):
        row = _make_trending_row()
        override, _ = _make_session_override([row])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/trending?city=austin&category=music")
        assert resp.status_code == 200
        entity = resp.json()["entities"][0]
        expected_fields = {
            "entity_name", "entity_type", "category",
            "composite_score", "volume_score", "sentiment_score",
            "freshness_score", "trend_direction", "scored_at",
        }
        assert expected_fields.issubset(entity.keys())

        app.dependency_overrides.pop(get_session, None)
