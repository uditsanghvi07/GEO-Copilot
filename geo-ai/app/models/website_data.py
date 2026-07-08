"""WebsiteData ORM model - one crawl snapshot's worth of extracted signals
for a product's website, produced by the Website Crawler agent (Module 2).

One row per product; each crawl run UPSERTs this row rather than appending
history, keeping the MVP simple. `status`/`error_message`/`failed_pages`
let the crawler degrade gracefully (partial/failed crawl) without ever
needing to raise past the agent boundary.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common_enums import IngestionStatus

if TYPE_CHECKING:
    from app.models.product import Product


class WebsiteData(Base):
    """Extracted, structured signals from crawling a product's website."""

    __tablename__ = "website_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_html_snapshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON-serialized {"h1": [...], "h2": [...], "h3": [...]} - a summarized
    # list of heading text, not the full page text.
    headings_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_faq: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_schema_markup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_crawled_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, index=True
    )

    # --- Module 2 additions ---
    faq_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schema_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    internal_links_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    images_missing_alt_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_updated_signal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crawled_pages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    failed_pages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="website_data_status_enum"),
        nullable=False,
        default=IngestionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="website_data")
