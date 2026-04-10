"""Auth endpoints: request magic link, verify token, return JWT."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.email import send_magic_link
from app.auth.tokens import JWT_TTL_DAYS, create_access_token, generate_magic_token
from app.database import get_session
from app.models.magic_link import MAGIC_TOKEN_TTL_MINUTES, MagicLink
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RequestLinkBody(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    onboarding_completed: bool


@router.post("/request-link", status_code=status.HTTP_202_ACCEPTED)
async def request_link(
    body: RequestLinkBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Send a magic sign-in link to the given email address."""
    token = generate_magic_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=MAGIC_TOKEN_TTL_MINUTES)

    magic = MagicLink(email=body.email, token=token, expires_at=expires_at)
    session.add(magic)
    await session.commit()

    send_magic_link(body.email, token)

    return {"message": "If that address is valid, a sign-in link is on its way."}


@router.get("/verify")
async def verify_token(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Validate a magic link token and return a JWT access token."""
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(MagicLink).where(MagicLink.token == token)
    )
    magic = result.scalar_one_or_none()

    if magic is None or magic.used_at is not None or magic.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired link.",
        )

    # Mark as used
    magic.used_at = now

    # Get-or-create user
    result = await session.execute(select(User).where(User.email == magic.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=magic.email)
        session.add(user)
        await session.flush()  # populate user.id

    await session.commit()
    await session.refresh(user)

    access_token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        onboarding_completed=user.onboarding_completed_at is not None,
    )
