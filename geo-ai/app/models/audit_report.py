"""AuditReport ORM model - the scored output of a full orchestrated audit
pipeline run for a product, produced by the future Scoring agent."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.product import Product


class AuditReport(Base, CreatedAtMixin):
    """A discoverability audit report snapshot for a product."""

    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    geo_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    recommendations: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    product: Mapped["Product"] = relationship("Product", back_populates="audit_reports")
