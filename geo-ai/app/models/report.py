"""Report ORM model - persisted HTML audit reports produced by the
Reporting agent (Module 6)."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Report(Base, CreatedAtMixin):
    """A rendered HTML audit report file on disk."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    pipeline_run_id: Mapped[int | None] = mapped_column(nullable=True, index=True)

    product: Mapped["Product"] = relationship("Product", back_populates="reports")
