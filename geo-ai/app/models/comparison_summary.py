"""ComparisonSummary ORM model - product-level competitor comparison result
produced by the Competitor agent (Module 4).

Per-competitor scores and notes live on `competitors` rows; this table holds
the merged LLM comparison output and polling status for
GET /compare/status/{product_id}. See ARCHITECTURE.md.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin
from app.models.common_enums import IngestionStatus

if TYPE_CHECKING:
    from app.models.product import Product


class ComparisonSummary(Base, CreatedAtMixin):
    """Merged competitor comparison result for a product."""

    __tablename__ = "comparison_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    missing_features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_faqs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    improvement_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitor_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    # Snapshot of OUR product's score at comparison time, so the table and the
    # LLM narrative always reference the same numbers (avoids showing a stale
    # score in the narrative while the table pulls a newer audit score).
    our_score: Mapped[int | None] = mapped_column(nullable=True)
    our_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="comparison_summary_status_enum"),
        nullable=False,
        default=IngestionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="comparison_summaries")
