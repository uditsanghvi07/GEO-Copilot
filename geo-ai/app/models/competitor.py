"""Competitor ORM model - competitor products tracked for comparison,
populated and scored by the Competitor agent (Module 4)."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Competitor(Base):
    """A competitor of the audited product."""

    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    competitor_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    comparison_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    crawl_signals: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="competitors")
