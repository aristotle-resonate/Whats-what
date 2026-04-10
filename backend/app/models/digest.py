from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DigestSubscription(Base):
    __tablename__ = "digest_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    format: Mapped[str] = mapped_column(String(20), default="email")

    user: Mapped["User"] = relationship(back_populates="subscriptions")  # noqa: F821
