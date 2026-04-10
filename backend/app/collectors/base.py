from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.mention import Mention
from app.models.source import CollectionError, Source


class MentionData(dict):
    """
    Dict with required keys:
    - entity_name: str
    - entity_type: str  (venue | artist | event | dish)
    - category: str     (music | food | fitness | networking)
    - content_snippet: str | None
    - url: str | None
    - mention_count: int
    - sentiment_score: float | None
    - published_at: datetime | None
    """


class BaseCollector(ABC):
    source_name: str  # must be set on each subclass

    @abstractmethod
    async def collect(self, city: str) -> list[MentionData]:
        """Fetch data for a city and return a list of MentionData dicts."""
        ...

    async def run(self, city: str) -> int:
        """
        Run the collector for a city.
        Saves mentions to DB, logs errors to collection_errors.
        Returns count of mentions saved.
        """
        try:
            mentions = await self.collect(city)
            async with async_session_factory() as session:
                for m in mentions:
                    session.add(
                        Mention(
                            city=city,
                            source=self.source_name,
                            entity_name=m["entity_name"],
                            entity_type=m["entity_type"],
                            category=m["category"],
                            content_snippet=m.get("content_snippet"),
                            url=m.get("url"),
                            mention_count=m.get("mention_count", 1),
                            sentiment_score=m.get("sentiment_score"),
                            published_at=m.get("published_at"),
                        )
                    )
                await session.commit()
            try:
                await self._mark_source_run(city)
            except Exception:
                # Don't fail the whole run if marking source run fails
                pass
            return len(mentions)
        except Exception as exc:
            await self._log_error(city, str(exc))
            return 0

    async def _mark_source_run(self, city: str) -> None:
        async with async_session_factory() as session:
            result = await session.execute(
                __import__("sqlalchemy").select(Source).where(
                    Source.name == self.source_name,
                    Source.city == city,
                )
            )
            source = result.scalar_one_or_none()
            if source:
                source.last_run_at = datetime.utcnow()
                await session.commit()

    async def _log_error(self, city: str, error_message: str) -> None:
        async with async_session_factory() as session:
            session.add(
                CollectionError(
                    source=self.source_name,
                    city=city,
                    error_message=error_message,
                )
            )
            await session.commit()
