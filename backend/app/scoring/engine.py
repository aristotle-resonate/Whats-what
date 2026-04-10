"""
Scoring engine: computes composite trending scores from collected mentions.

Composite = volume(0.50) + sentiment(0.25) + freshness(0.25)

Trend directions:
  new     — entity has no prior TrendingScore
  rising  — composite increased > 0.15 from last score
  fading  — composite decreased > 0.15 from last score
  peak    — stable (within ±0.15)
"""

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.cities import CITIES
from app.database import async_session_factory
from app.models.mention import Mention
from app.models.trending import TrendingScore

# Look-back window for aggregating mentions
WINDOW_DAYS = 7
# Freshness half-life in days (entity 3.5 days old scores 0.5)
FRESHNESS_HALF_LIFE = 3.5
# Minimum composite delta to qualify as rising/fading
TREND_THRESHOLD = 0.15


def freshness_score(published_at: datetime | None, collected_at: datetime, now: datetime) -> float:
    """Exponential decay: 1.0 at 0 days old, ~0.5 at FRESHNESS_HALF_LIFE days."""
    ref = published_at if published_at else collected_at
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    days_old = max(0.0, (now - ref).total_seconds() / 86400)
    return math.exp(-days_old * math.log(2) / FRESHNESS_HALF_LIFE)


def _vader_score(text: str) -> float:
    """VADER compound score normalized from [-1,1] to [0,1]."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    compound = analyzer.polarity_scores(text)["compound"]
    return (compound + 1) / 2


async def _trend_direction(
    session: AsyncSession,
    city: str,
    category: str,
    entity_name: str,
    entity_type: str,
    current_composite: float,
) -> str:
    result = await session.execute(
        select(TrendingScore)
        .where(
            and_(
                TrendingScore.city == city,
                TrendingScore.category == category,
                TrendingScore.entity_name == entity_name,
                TrendingScore.entity_type == entity_type,
            )
        )
        .order_by(TrendingScore.scored_at.desc())
        .limit(1)
    )
    prev = result.scalar_one_or_none()

    if prev is None:
        return "new"
    delta = current_composite - prev.composite_score
    if delta > TREND_THRESHOLD:
        return "rising"
    if delta < -TREND_THRESHOLD:
        return "fading"
    return "peak"


async def compute_scores(session: AsyncSession, city: str) -> int:
    """Compute and persist TrendingScore rows for a city. Returns count written."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=WINDOW_DAYS)

    result = await session.execute(
        select(Mention).where(
            and_(
                Mention.city == city,
                Mention.collected_at >= window_start,
            )
        )
    )
    mentions: list[Mention] = list(result.scalars().all())

    if not mentions:
        return 0

    # Group mentions by (category, entity_name_normalized, entity_type)
    groups: dict[tuple, list[Mention]] = defaultdict(list)
    for m in mentions:
        key = (m.category, m.entity_name.strip().lower(), m.entity_type)
        groups[key].append(m)

    # Raw volume per group; collect for per-category normalization
    raw_volumes: dict[tuple, int] = {
        key: sum(m.mention_count for m in group_mentions)
        for key, group_mentions in groups.items()
    }

    # Max volume per category for normalization
    category_max: dict[str, int] = defaultdict(int)
    for (cat, _, _), vol in raw_volumes.items():
        if vol > category_max[cat]:
            category_max[cat] = vol

    written = 0
    for key, group_mentions in groups.items():
        category, _name_lower, entity_type = key
        entity_name = group_mentions[0].entity_name  # preserve original casing

        # --- Volume ---
        max_vol = category_max[category] or 1
        vol = raw_volumes[key] / max_vol

        # --- Sentiment ---
        sentiment_values: list[float] = []
        for m in group_mentions:
            if m.sentiment_score is not None:
                # Yelp ratings come in as 1-5; normalize if > 1
                raw = m.sentiment_score
                if raw > 1.0:
                    raw = (raw - 1) / 4  # [1,5] → [0,1]
                sentiment_values.append(max(0.0, min(1.0, raw)))
            elif m.content_snippet:
                sentiment_values.append(_vader_score(m.content_snippet))
        sentiment = (
            sum(sentiment_values) / len(sentiment_values) if sentiment_values else 0.5
        )
        sentiment = max(0.0, min(1.0, sentiment))

        # --- Freshness ---
        fresh = max(
            freshness_score(m.published_at, m.collected_at, now) for m in group_mentions
        )
        fresh = max(0.0, min(1.0, fresh))

        composite = (vol * 0.50) + (sentiment * 0.25) + (fresh * 0.25)
        composite = max(0.0, min(1.0, composite))

        trend = await _trend_direction(
            session, city, category, entity_name, entity_type, composite
        )

        session.add(
            TrendingScore(
                entity_name=entity_name,
                entity_type=entity_type,
                city=city,
                category=category,
                volume_score=vol,
                sentiment_score=sentiment,
                freshness_score=fresh,
                composite_score=composite,
                trend_direction=trend,
            )
        )
        written += 1

    await session.commit()
    return written


async def compute_scores_for_city(city: str) -> int:
    """Open a session and compute scores for one city."""
    async with async_session_factory() as session:
        return await compute_scores(session, city)


async def compute_scores_all_cities() -> dict[str, int]:
    """Compute scores for all cities. Returns {city: count}."""
    results: dict[str, int] = {}
    for city in CITIES:
        results[city] = await compute_scores_for_city(city)
    return results
