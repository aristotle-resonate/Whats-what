"""Authenticated endpoints: current user profile and onboarding preferences."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user_id
from app.collectors.cities import CITIES
from app.database import get_session
from app.models.digest import DigestSubscription
from app.models.mention import CATEGORIES
from app.models.user import User, UserPreferences

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    id: int
    email: str
    city: str | None
    onboarding_completed: bool
    categories: list[str] | None
    favorite_venues: list[str] | None
    favorite_artists: list[str] | None
    vibe_tags: list[str] | None


@router.get("/me")
async def get_me(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    prefs = user.preferences
    return UserResponse(
        id=user.id,
        email=user.email,
        city=user.city,
        onboarding_completed=user.onboarding_completed_at is not None,
        categories=prefs.categories if prefs else None,
        favorite_venues=prefs.favorite_venues if prefs else None,
        favorite_artists=prefs.favorite_artists if prefs else None,
        vibe_tags=prefs.vibe_tags if prefs else None,
    )


# ---------------------------------------------------------------------------
# PUT /auth/onboarding
# ---------------------------------------------------------------------------

class OnboardingBody(BaseModel):
    city: str
    categories: list[str]
    favorite_venues: list[str] = []
    favorite_artists: list[str] = []
    vibe_tags: list[str] = []
    email_digest: bool = True


@router.put("/onboarding")
async def complete_onboarding(
    body: OnboardingBody,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if body.city not in CITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"City must be one of: {', '.join(CITIES)}",
        )
    invalid = [c for c in body.categories if c not in CATEGORIES]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown categories: {invalid}. Valid: {list(CATEGORIES)}",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.city = body.city
    user.onboarding_completed_at = datetime.now(timezone.utc)

    # Upsert preferences
    if user.preferences is None:
        prefs = UserPreferences(user_id=user.id)
        session.add(prefs)
    else:
        prefs = user.preferences

    prefs.categories = body.categories
    prefs.favorite_venues = body.favorite_venues or None
    prefs.favorite_artists = body.favorite_artists or None
    prefs.vibe_tags = body.vibe_tags or None

    # Upsert digest subscription (one per city)
    if body.email_digest:
        result = await session.execute(
            select(DigestSubscription).where(
                DigestSubscription.user_id == user_id,
                DigestSubscription.city == body.city,
            )
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            session.add(
                DigestSubscription(
                    user_id=user_id,
                    city=body.city,
                    categories=body.categories,
                )
            )
        else:
            sub.categories = body.categories

    await session.commit()
    return {"message": "Onboarding complete.", "city": body.city}
