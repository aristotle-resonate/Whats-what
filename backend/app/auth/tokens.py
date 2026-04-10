"""JWT creation/decoding and magic-link token generation."""

import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

ALGORITHM = "HS256"
MAGIC_TOKEN_BYTES = 32
JWT_TTL_DAYS = 30


def generate_magic_token() -> str:
    """Return a cryptographically random URL-safe token string."""
    return secrets.token_urlsafe(MAGIC_TOKEN_BYTES)


def create_access_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_TTL_DAYS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
