"""PipelineRun ORM model and status enum."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

import enum

from sqlalchemy import Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class PipelineRunStatus(str, enum.Enum):
    """Overall status of a full orchestrated pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class PipelineRun(Base):
    """One end-to-end orchestrated pipeline run for a product."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(PipelineRunStatus, name="pipeline_run_status_enum"),
        nullable=False,
        default=PipelineRunStatus.PENDING,
    )
    stage_statuses: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    competitor_urls: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="pipeline_runs")
