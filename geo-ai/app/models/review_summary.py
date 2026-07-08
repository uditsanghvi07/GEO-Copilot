"""ReviewSummary ORM model - merged LLM intelligence output for a product's
reviews, produced by the Review Intelligence agent (Module 3).

Kept as its own table rather than columns on `audit_reports`: review
intelligence is produced independently of (and often before) a GEO audit
run, can be re-run when new reviews arrive, and has a different lifecycle
(`is_analyzed` flags on individual reviews). The Audit Agent (Module 4)
reads this table as input but does not own it. See ARCHITECTURE.md.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, Float, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin
from app.models.common_enums import IngestionStatus

if TYPE_CHECKING:
    from app.models.product import Product


class ReviewSummary(Base, CreatedAtMixin):
    """Merged review intelligence summary for a product."""

    __tablename__ = "review_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    top_complaints: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    top_feature_requests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    positive_themes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    negative_themes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    overall_sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews_analyzed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batches_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batches_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batch_outputs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="review_summary_status_enum"),
        nullable=False,
        default=IngestionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="review_summaries")
