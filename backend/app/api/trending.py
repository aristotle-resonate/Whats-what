"""Trending endpoint: GET /trending."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.cities import CITIES
from app.database import get_session
from app.models.trending import TrendingScore

router = APIRouter(prefix="/trending", tags=["trending"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TrendingEntity(BaseModel):
    entity_name: str
    entity_type: str
    category: str
    composite_score: float
    volume_score: float
    sentiment_score: float
    freshness_score: float
    trend_direction: str
    scored_at: datetime


class TrendingResponse(BaseModel):
    city: str
    category: str | None
    entities: list[TrendingEntity]


# ---------------------------------------------------------------------------
# GET /trending
# ---------------------------------------------------------------------------

@router.get("", response_model=TrendingResponse)
async def get_trending(
    city: str = Query(..., description="City slug (e.g. 'austin')"),
    category: str | None = Query(None, description="Category filter (e.g. 'music')"),
    limit: int = Query(20, ge=1, le=50, description="Max results (1-50)"),
    session: AsyncSession = Depends(get_session),
) -> TrendingResponse:
    """Return the latest trending entities for a given city, optionally filtered by category."""

    if city not in CITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"City must be one of: {', '.join(CITIES)}",
        )

    # Subquery: latest scored_at for each (entity_name, entity_type) pair.
    subq = (
        select(
            TrendingScore.entity_name,
            TrendingScore.entity_type,
            func.max(TrendingScore.scored_at).label("max_scored_at"),
        )
        .where(TrendingScore.city == city)
        .group_by(TrendingScore.entity_name, TrendingScore.entity_type)
    )

    if category is not None:
        subq = subq.where(TrendingScore.category == category)

    subq = subq.subquery()

    # Main query: join back to get all fields for the latest rows.
    stmt = (
        select(TrendingScore)
        .join(
            subq,
            (TrendingScore.entity_name == subq.c.entity_name)
            & (TrendingScore.entity_type == subq.c.entity_type)
            & (TrendingScore.scored_at == subq.c.max_scored_at),
        )
        .where(TrendingScore.city == city)
        .order_by(TrendingScore.composite_score.desc())
        .limit(limit)
    )

    if category is not None:
        stmt = stmt.where(TrendingScore.category == category)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    entities = [
        TrendingEntity(
            entity_name=row.entity_name,
            entity_type=row.entity_type,
            category=row.category,
            composite_score=row.composite_score,
            volume_score=row.volume_score,
            sentiment_score=row.sentiment_score,
            freshness_score=row.freshness_score,
            trend_direction=row.trend_direction,
            scored_at=row.scored_at,
        )
        for row in rows
    ]

    return TrendingResponse(city=city, category=category, entities=entities)
