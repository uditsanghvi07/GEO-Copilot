"""Review ORM model - individual reviews fetched from Play Store/other
sources, enriched with batch intelligence by the Module 3 Review
Intelligence agent."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Review(Base):
    """A single end-user review for a product."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="play_store")
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, index=True
    )

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
