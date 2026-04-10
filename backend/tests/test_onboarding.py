"""Tests for GET /auth/me and PUT /auth/onboarding."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.tokens import create_access_token
from app.auth.deps import get_current_user_id
from app.database import get_session
from app.main import app


def _auth_headers(user_id: int = 1, email: str = "hi@example.com") -> dict:
    token = create_access_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


def _mock_user(
    user_id=1,
    email="hi@example.com",
    city="austin",
    onboarding_completed_at=None,
    preferences=None,
):
    u = MagicMock()
    u.id = user_id
    u.email = email
    u.city = city
    u.onboarding_completed_at = onboarding_completed_at
    u.preferences = preferences
    return u


def _make_session_override(execute_side_effects):
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=execute_side_effects)

    async def _override():
        yield session

    return _override, session


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    @pytest.mark.asyncio
    async def test_returns_user_info(self, client):
        prefs = MagicMock()
        prefs.categories = ["music", "food"]
        prefs.favorite_venues = ["Stubb's"]
        prefs.favorite_artists = None
        prefs.vibe_tags = ["live-music"]

        user = _mock_user(preferences=prefs)

        r = MagicMock()
        r.scalar_one_or_none.return_value = user

        override, _ = _make_session_override([r])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/me", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "hi@example.com"
        assert body["categories"] == ["music", "food"]
        assert body["favorite_venues"] == ["Stubb's"]

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_401_without_token(self, client):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401  # HTTPBearer returns 401 when header missing

    @pytest.mark.asyncio
    async def test_404_when_user_not_found(self, client):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None

        override, _ = _make_session_override([r])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/me", headers=_auth_headers(user_id=999))
        assert resp.status_code == 404

        app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# PUT /auth/onboarding
# ---------------------------------------------------------------------------

class TestOnboarding:
    def _valid_body(self):
        return {
            "city": "austin",
            "categories": ["music", "food"],
            "favorite_venues": ["Stubb's"],
            "email_digest": True,
        }

    @pytest.mark.asyncio
    async def test_onboarding_succeeds(self, client):
        user = _mock_user()

        # 3 execute calls: user lookup, digest sub lookup
        r_user = MagicMock()
        r_user.scalar_one_or_none.return_value = user
        r_sub = MagicMock()
        r_sub.scalar_one_or_none.return_value = None  # no existing sub

        override, session = _make_session_override([r_user, r_sub])
        app.dependency_overrides[get_session] = override

        resp = await client.put(
            "/auth/onboarding", json=self._valid_body(), headers=_auth_headers()
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Onboarding complete."

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_invalid_city_returns_422(self, client):
        # Bypass DB for this validation-only test
        override, _ = _make_session_override([MagicMock()] * 5)
        app.dependency_overrides[get_session] = override

        body = self._valid_body()
        body["city"] = "atlantis"
        resp = await client.put("/auth/onboarding", json=body, headers=_auth_headers())
        assert resp.status_code == 422

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_invalid_category_returns_422(self, client):
        override, _ = _make_session_override([MagicMock()] * 5)
        app.dependency_overrides[get_session] = override

        body = self._valid_body()
        body["categories"] = ["astrology"]
        resp = await client.put("/auth/onboarding", json=body, headers=_auth_headers())
        assert resp.status_code == 422

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_existing_subscription_updated(self, client):
        user = _mock_user()
        existing_sub = MagicMock()
        existing_sub.categories = ["music"]

        r_user = MagicMock()
        r_user.scalar_one_or_none.return_value = user
        r_sub = MagicMock()
        r_sub.scalar_one_or_none.return_value = existing_sub

        override, _ = _make_session_override([r_user, r_sub])
        app.dependency_overrides[get_session] = override

        body = self._valid_body()
        body["categories"] = ["music", "networking"]
        resp = await client.put("/auth/onboarding", json=body, headers=_auth_headers())
        assert resp.status_code == 200
        assert existing_sub.categories == ["music", "networking"]

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_no_digest_sub_when_email_digest_false(self, client):
        user = _mock_user()

        r_user = MagicMock()
        r_user.scalar_one_or_none.return_value = user

        override, session = _make_session_override([r_user])
        app.dependency_overrides[get_session] = override

        body = self._valid_body()
        body["email_digest"] = False
        resp = await client.put("/auth/onboarding", json=body, headers=_auth_headers())
        assert resp.status_code == 200
        # Only 1 execute call (user lookup), no sub lookup
        assert session.execute.call_count == 1

        app.dependency_overrides.pop(get_session, None)
