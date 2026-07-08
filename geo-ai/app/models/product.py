"""Product ORM model - the root entity every other table hangs off of."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.audit_report import AuditReport
    from app.models.comparison_summary import ComparisonSummary
    from app.models.competitor import Competitor
    from app.models.generated_content import GeneratedContent
    from app.models.pipeline_run import PipelineRun
    from app.models.play_store_data import PlayStoreData
    from app.models.report import Report
    from app.models.report import Report
    from app.models.review import Review
    from app.models.review_summary import ReviewSummary
    from app.models.website_data import WebsiteData


class Product(Base, TimestampMixin):
    """A company/product being audited for AI discoverability."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    play_store_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Explicit string class names below (rather than relying on Mapped[]
    # annotation inference) so these modules never need to import each
    # other at runtime, avoiding circular imports across the models package.
    website_data: Mapped[list["WebsiteData"]] = relationship(
        "WebsiteData", back_populates="product", cascade="all, delete-orphan"
    )
    play_store_data: Mapped[list["PlayStoreData"]] = relationship(
        "PlayStoreData", back_populates="product", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="product", cascade="all, delete-orphan"
    )
    review_summaries: Mapped[list["ReviewSummary"]] = relationship(
        "ReviewSummary", back_populates="product", cascade="all, delete-orphan"
    )
    competitors: Mapped[list["Competitor"]] = relationship(
        "Competitor", back_populates="product", cascade="all, delete-orphan"
    )
    comparison_summaries: Mapped[list["ComparisonSummary"]] = relationship(
        "ComparisonSummary", back_populates="product", cascade="all, delete-orphan"
    )
    audit_reports: Mapped[list["AuditReport"]] = relationship(
        "AuditReport", back_populates="product", cascade="all, delete-orphan"
    )
    generated_content: Mapped[list["GeneratedContent"]] = relationship(
        "GeneratedContent", back_populates="product", cascade="all, delete-orphan"
    )
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun", back_populates="product", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="product", cascade="all, delete-orphan"
    )
