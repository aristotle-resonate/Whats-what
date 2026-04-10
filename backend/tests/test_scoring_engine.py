"""Tests for the scoring engine: freshness, sentiment, volume, composite, trend."""

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scoring.engine import (
    FRESHNESS_HALF_LIFE,
    TREND_THRESHOLD,
    _trend_direction,
    _vader_score,
    compute_scores,
    freshness_score,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mention(
    entity_name="Test Venue",
    entity_type="venue",
    category="music",
    city="austin",
    mention_count=1,
    sentiment_score=None,
    content_snippet=None,
    published_at=None,
    collected_at=None,
):
    now = datetime.now(timezone.utc)
    m = MagicMock()
    m.entity_name = entity_name
    m.entity_type = entity_type
    m.category = category
    m.city = city
    m.mention_count = mention_count
    m.sentiment_score = sentiment_score
    m.content_snippet = content_snippet
    m.published_at = published_at
    m.collected_at = collected_at or now
    return m


# ---------------------------------------------------------------------------
# freshness_score
# ---------------------------------------------------------------------------

class TestFreshnessScore:
    def test_zero_days_old_is_one(self):
        now = datetime.now(timezone.utc)
        score = freshness_score(now, now, now)
        assert abs(score - 1.0) < 0.001

    def test_half_life_days_is_half(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=FRESHNESS_HALF_LIFE)
        score = freshness_score(old, old, now)
        assert abs(score - 0.5) < 0.01

    def test_seven_days_old_is_low(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=7)
        score = freshness_score(old, old, now)
        # exp(-7 * ln2 / 3.5) = exp(-2*ln2) = 0.25
        expected = math.exp(-7 * math.log(2) / FRESHNESS_HALF_LIFE)
        assert abs(score - expected) < 0.01

    def test_falls_back_to_collected_at_when_no_published(self):
        now = datetime.now(timezone.utc)
        collected = now - timedelta(days=2)
        score = freshness_score(None, collected, now)
        expected = freshness_score(collected, collected, now)
        assert abs(score - expected) < 0.001

    def test_naive_datetime_handled(self):
        now = datetime.now(timezone.utc)
        naive_old = (now - timedelta(days=1)).replace(tzinfo=None)
        # Should not raise
        score = freshness_score(naive_old, now, now)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _vader_score
# ---------------------------------------------------------------------------

class TestVaderScore:
    def test_positive_text_above_half(self):
        score = _vader_score("Amazing! Best show ever, absolutely loved it!")
        assert score > 0.5

    def test_negative_text_below_half(self):
        score = _vader_score("Terrible. Worst experience. Never going back.")
        assert score < 0.5

    def test_neutral_text_near_half(self):
        score = _vader_score("The event was on Tuesday.")
        # Neutral — compound near 0, score near 0.5
        assert 0.2 <= score <= 0.8

    def test_output_in_range(self):
        for text in ["great", "bad", "ok", ""]:
            s = _vader_score(text)
            assert 0.0 <= s <= 1.0


# ---------------------------------------------------------------------------
# _trend_direction
# ---------------------------------------------------------------------------

class TestTrendDirection:
    @pytest.mark.asyncio
    async def test_new_when_no_prior_score(self):
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)

        direction = await _trend_direction(session, "austin", "music", "The Parish", "venue", 0.6)
        assert direction == "new"

    @pytest.mark.asyncio
    async def test_rising_when_large_increase(self):
        session = AsyncMock()
        prev = MagicMock()
        prev.composite_score = 0.4
        result = MagicMock()
        result.scalar_one_or_none.return_value = prev
        session.execute = AsyncMock(return_value=result)

        # 0.4 + 0.2 > TREND_THRESHOLD → rising
        direction = await _trend_direction(session, "austin", "music", "The Parish", "venue", 0.6)
        assert direction == "rising"

    @pytest.mark.asyncio
    async def test_fading_when_large_decrease(self):
        session = AsyncMock()
        prev = MagicMock()
        prev.composite_score = 0.7
        result = MagicMock()
        result.scalar_one_or_none.return_value = prev
        session.execute = AsyncMock(return_value=result)

        # 0.7 - 0.25 > TREND_THRESHOLD → fading
        direction = await _trend_direction(session, "austin", "music", "The Parish", "venue", 0.45)
        assert direction == "fading"

    @pytest.mark.asyncio
    async def test_peak_when_stable(self):
        session = AsyncMock()
        prev = MagicMock()
        prev.composite_score = 0.6
        result = MagicMock()
        result.scalar_one_or_none.return_value = prev
        session.execute = AsyncMock(return_value=result)

        # delta = 0.05 < TREND_THRESHOLD → peak
        direction = await _trend_direction(session, "austin", "music", "The Parish", "venue", 0.65)
        assert direction == "peak"


# ---------------------------------------------------------------------------
# compute_scores (full pipeline, mocked session)
# ---------------------------------------------------------------------------

class TestComputeScores:
    def _make_session(self, mentions, prev_score=None):
        session = AsyncMock()
        added = []
        session.add = MagicMock(side_effect=added.append)
        session.commit = AsyncMock()

        # First execute → mentions; subsequent → trend lookup
        mentions_result = MagicMock()
        mentions_result.scalars.return_value.all.return_value = mentions

        trend_result = MagicMock()
        trend_result.scalar_one_or_none.return_value = prev_score

        session.execute = AsyncMock(side_effect=[mentions_result, *[trend_result] * 20])
        return session, added

    @pytest.mark.asyncio
    async def test_empty_mentions_returns_zero(self):
        session, added = self._make_session([])
        count = await compute_scores(session, "austin")
        assert count == 0
        assert added == []

    @pytest.mark.asyncio
    async def test_single_entity_scores_correctly(self):
        now = datetime.now(timezone.utc)
        m = _mention(
            entity_name="Stubb's",
            mention_count=10,
            sentiment_score=0.8,
            published_at=now - timedelta(hours=6),
        )
        session, added = self._make_session([m])
        count = await compute_scores(session, "austin")

        assert count == 1
        row = added[0]
        # Only entity → volume = 1.0
        assert abs(row.volume_score - 1.0) < 0.001
        # Sentiment = 0.8 (no normalization needed, already ≤1)
        assert abs(row.sentiment_score - 0.8) < 0.001
        # Freshness ≈ 1.0 (6 hours old)
        assert row.freshness_score > 0.9
        # Composite = 0.5*1 + 0.25*0.8 + 0.25*freshness
        expected_composite = 0.5 * 1.0 + 0.25 * 0.8 + 0.25 * row.freshness_score
        assert abs(row.composite_score - expected_composite) < 0.001
        assert row.trend_direction == "new"

    @pytest.mark.asyncio
    async def test_volume_normalized_across_entities(self):
        now = datetime.now(timezone.utc)
        m1 = _mention(entity_name="Venue A", mention_count=100, published_at=now)
        m2 = _mention(entity_name="Venue B", mention_count=50, published_at=now)

        session = AsyncMock()
        added = []
        session.add = MagicMock(side_effect=added.append)
        session.commit = AsyncMock()

        mentions_result = MagicMock()
        mentions_result.scalars.return_value.all.return_value = [m1, m2]
        trend_result = MagicMock()
        trend_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(side_effect=[mentions_result, trend_result, trend_result])

        await compute_scores(session, "austin")

        scores = {r.entity_name: r.volume_score for r in added}
        assert abs(scores["Venue A"] - 1.0) < 0.001
        assert abs(scores["Venue B"] - 0.5) < 0.001

    @pytest.mark.asyncio
    async def test_yelp_rating_normalized(self):
        """Yelp sentiment_score comes as 1-5; engine should normalize to [0,1]."""
        now = datetime.now(timezone.utc)
        m = _mention(sentiment_score=4.5, published_at=now)
        session, added = self._make_session([m])
        await compute_scores(session, "austin")

        # (4.5 - 1) / 4 = 0.875
        assert abs(added[0].sentiment_score - 0.875) < 0.001

    @pytest.mark.asyncio
    async def test_vader_used_when_no_sentiment_score(self):
        now = datetime.now(timezone.utc)
        m = _mention(
            sentiment_score=None,
            content_snippet="Incredible night, absolutely loved the music!",
            published_at=now,
        )
        session, added = self._make_session([m])
        await compute_scores(session, "austin")

        # VADER positive → sentiment > 0.5
        assert added[0].sentiment_score > 0.5

    @pytest.mark.asyncio
    async def test_default_sentiment_when_no_data(self):
        now = datetime.now(timezone.utc)
        m = _mention(sentiment_score=None, content_snippet=None, published_at=now)
        session, added = self._make_session([m])
        await compute_scores(session, "austin")

        assert abs(added[0].sentiment_score - 0.5) < 0.001

    @pytest.mark.asyncio
    async def test_composite_clamped_to_unit_interval(self):
        now = datetime.now(timezone.utc)
        m = _mention(sentiment_score=1.0, mention_count=9999, published_at=now)
        session, added = self._make_session([m])
        await compute_scores(session, "austin")

        assert 0.0 <= added[0].composite_score <= 1.0

    @pytest.mark.asyncio
    async def test_multiple_mentions_same_entity_aggregated(self):
        """Two mentions for the same entity should merge into one TrendingScore."""
        now = datetime.now(timezone.utc)
        m1 = _mention(entity_name="Stubb's", mention_count=5, sentiment_score=0.8, published_at=now)
        m2 = _mention(entity_name="stubb's", mention_count=3, sentiment_score=0.6, published_at=now - timedelta(hours=2))

        session = AsyncMock()
        added = []
        session.add = MagicMock(side_effect=added.append)
        session.commit = AsyncMock()

        mentions_result = MagicMock()
        mentions_result.scalars.return_value.all.return_value = [m1, m2]
        trend_result = MagicMock()
        trend_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(side_effect=[mentions_result, trend_result])

        count = await compute_scores(session, "austin")

        # Case-insensitive grouping → 1 entity
        assert count == 1
        row = added[0]
        # volume = 5+3=8; normalized = 1.0
        assert abs(row.volume_score - 1.0) < 0.001
        # sentiment = avg(0.8, 0.6) = 0.7
        assert abs(row.sentiment_score - 0.7) < 0.001
