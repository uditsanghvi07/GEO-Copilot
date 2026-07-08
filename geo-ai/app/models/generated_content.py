"""GeneratedContent ORM model - AI-generated artifacts produced by the
Content Generation agent (Module 5)."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ContentType(str, enum.Enum):
    """Supported kinds of AI-generated content."""

    FAQ = "faq"
    BLOG = "blog"
    META = "meta"
    META_DESCRIPTION = "meta_description"
    PRODUCT_DESCRIPTION = "product_description"
    RELEASE_NOTES = "release_notes"
    CAMPAIGN = "campaign"
    CAMPAIGN_BUNDLE = "campaign_bundle"


class GeneratedContent(Base, CreatedAtMixin):
    """A single piece of AI-generated content for a product."""

    __tablename__ = "generated_content"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type_enum"), nullable=False
    )
    content_body: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="generated_content")
