"""Tests for POST /auth/request-link and GET /auth/verify."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.tokens import create_access_token, decode_access_token, generate_magic_token
from app.database import get_session
from app.main import app


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

class TestTokenHelpers:
    def test_generate_magic_token_is_unique(self):
        assert generate_magic_token() != generate_magic_token()

    def test_generate_magic_token_length(self):
        assert len(generate_magic_token()) > 20

    def test_create_and_decode_roundtrip(self):
        token = create_access_token(42, "user@example.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "user@example.com"

    def test_decode_invalid_token_raises(self):
        import jwt
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token("not.a.real.token")

    def test_decode_tampered_token_raises(self):
        import jwt
        good = create_access_token(1, "a@b.com")
        # flip one char in the signature
        parts = good.split(".")
        parts[2] = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(".".join(parts))


# ---------------------------------------------------------------------------
# Helpers for mocking the DB session dependency
# ---------------------------------------------------------------------------

def _make_session_override(execute_side_effects):
    """Build an async-generator override for get_session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=execute_side_effects)

    async def _override():
        yield session

    return _override, session


# ---------------------------------------------------------------------------
# POST /auth/request-link
# ---------------------------------------------------------------------------

class TestRequestLink:
    @pytest.mark.asyncio
    async def test_accepted_with_valid_email(self, client):
        override, _ = _make_session_override([AsyncMock()])
        app.dependency_overrides[get_session] = override

        resp = await client.post("/auth/request-link", json={"email": "hi@example.com"})
        assert resp.status_code == 202
        assert "message" in resp.json()

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_rejects_invalid_email(self, client):
        resp = await client.post("/auth/request-link", json={"email": "not-an-email"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_email_sent_when_api_key_set(self, client):
        override, _ = _make_session_override([AsyncMock()])
        app.dependency_overrides[get_session] = override

        with patch("app.api.auth.send_magic_link") as mock_send:
            with patch("app.config.settings.resend_api_key", "test-key"):
                resp = await client.post(
                    "/auth/request-link", json={"email": "hi@example.com"}
                )
            mock_send.assert_called_once()
            assert mock_send.call_args[0][0] == "hi@example.com"

        app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# GET /auth/verify
# ---------------------------------------------------------------------------

def _make_magic_link(
    email="hi@example.com",
    token="goodtoken",
    used_at=None,
    expires_at=None,
):
    m = MagicMock()
    m.email = email
    m.token = token
    m.used_at = used_at
    m.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=10))
    return m


def _make_user(user_id=1, email="hi@example.com", onboarding_completed_at=None):
    u = MagicMock()
    u.id = user_id
    u.email = email
    u.onboarding_completed_at = onboarding_completed_at
    return u


class TestVerifyToken:
    @pytest.mark.asyncio
    async def test_valid_token_returns_jwt(self, client):
        magic = _make_magic_link()
        user = _make_user()

        r1, r2 = MagicMock(), MagicMock()
        r1.scalar_one_or_none.return_value = magic
        r2.scalar_one_or_none.return_value = user

        override, _ = _make_session_override([r1, r2])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/verify?token=goodtoken")
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user_id"] == 1

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_unknown_token_returns_400(self, client):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None

        override, _ = _make_session_override([r])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/verify?token=nope")
        assert resp.status_code == 400

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_already_used_token_returns_400(self, client):
        magic = _make_magic_link(used_at=datetime.now(timezone.utc) - timedelta(minutes=5))
        r = MagicMock()
        r.scalar_one_or_none.return_value = magic

        override, _ = _make_session_override([r])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/verify?token=usedtoken")
        assert resp.status_code == 400

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_expired_token_returns_400(self, client):
        magic = _make_magic_link(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        r = MagicMock()
        r.scalar_one_or_none.return_value = magic

        override, _ = _make_session_override([r])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/verify?token=expiredtoken")
        assert resp.status_code == 400

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_new_user_created_when_not_found(self, client):
        magic = _make_magic_link()
        new_user = _make_user(user_id=99)

        r1 = MagicMock()
        r1.scalar_one_or_none.return_value = magic

        r2 = MagicMock()
        r2.scalar_one_or_none.return_value = None  # user doesn't exist yet

        override, session = _make_session_override([r1, r2])

        # After flush/refresh, user.id becomes available
        async def _refresh(obj):
            obj.id = 99

        session.refresh = AsyncMock(side_effect=_refresh)
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/verify?token=goodtoken")
        assert resp.status_code == 200
        assert session.add.called  # User was added

        app.dependency_overrides.pop(get_session, None)

    @pytest.mark.asyncio
    async def test_returned_jwt_is_decodable(self, client):
        magic = _make_magic_link()
        user = _make_user(user_id=7, email="hi@example.com")

        r1, r2 = MagicMock(), MagicMock()
        r1.scalar_one_or_none.return_value = magic
        r2.scalar_one_or_none.return_value = user

        override, _ = _make_session_override([r1, r2])
        app.dependency_overrides[get_session] = override

        resp = await client.get("/auth/verify?token=goodtoken")
        jwt_token = resp.json()["access_token"]
        payload = decode_access_token(jwt_token)
        assert payload["sub"] == "7"
        assert payload["email"] == "hi@example.com"

        app.dependency_overrides.pop(get_session, None)
