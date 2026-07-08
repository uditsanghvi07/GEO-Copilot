"""PlayStoreData ORM model - one audit snapshot's worth of Play Store
listing signals for a product, produced by the Play Store Analyzer agent
(Module 2).

Kept as its own table rather than bolted onto `website_data`: the two
sources (a marketing website vs. an app store listing) have almost no
overlapping fields, are fetched by entirely different agents on
independent schedules, and mixing them would force every website-only
product to carry a wall of nullable Play Store columns. See
ARCHITECTURE.md for the full rationale. Raw reviews are persisted
separately into the `reviews` table (source="play_store") for Module 3 to
consume later.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common_enums import IngestionStatus

if TYPE_CHECKING:
    from app.models.product import Product


class PlayStoreData(Base):
    """Extracted, structured signals from a product's Play Store listing."""

    __tablename__ = "play_store_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    app_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # {"1": n, "2": n, "3": n, "4": n, "5": n}
    rating_distribution: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    store_last_updated: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    installs: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # --- Derived signals (heuristic, no AI) ---
    description_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_faq_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    keyword_density: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    days_since_update: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviews_fetched_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="play_store_data_status_enum"),
        nullable=False,
        default=IngestionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)

    product: Mapped["Product"] = relationship("Product", back_populates="play_store_data")
