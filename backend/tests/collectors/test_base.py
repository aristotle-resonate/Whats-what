from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.collectors.base import BaseCollector, MentionData


class ConcreteCollector(BaseCollector):
    source_name = "test_source"

    async def collect(self, city: str) -> list[MentionData]:
        return [
            MentionData(
                entity_name="Test Venue",
                entity_type="venue",
                category="music",
                content_snippet="Great show",
                url="https://example.com",
                mention_count=3,
                sentiment_score=0.8,
                published_at=None,
            )
        ]


@pytest.fixture
def collector():
    return ConcreteCollector()


async def test_run_saves_mentions(collector):
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    mock_session.commit = AsyncMock()

    # Create a context manager that returns the mock session
    mock_factory = MagicMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_factory.return_value = mock_cm

    with patch("app.collectors.base.async_session_factory", mock_factory):
        count = await collector.run("austin")

    assert count == 1
    # Check that add and commit were called
    assert mock_session.add.call_count >= 1
    assert mock_session.commit.call_count >= 1


async def test_run_logs_error_on_exception(collector):
    async def failing_collect(city):
        raise ValueError("API error")

    collector.collect = failing_collect

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_cm)

    with patch("app.collectors.base.async_session_factory", mock_factory):
        count = await collector.run("austin")

    assert count == 0
    mock_session.add.assert_called()
