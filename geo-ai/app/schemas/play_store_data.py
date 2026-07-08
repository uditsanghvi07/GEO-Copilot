"""Pydantic schemas for the `play_store_data` table."""

from datetime import datetime

from pydantic import BaseModel

from app.models.common_enums import IngestionStatus
from app.schemas.common import ORMBase


class PlayStoreDataCreate(BaseModel):
    """Input schema for recording a Play Store listing audit."""

    product_id: int
    app_title: str | None = None
    short_description: str | None = None
    full_description: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    rating_distribution: dict[str, int] = {}
    category: str | None = None
    store_last_updated: str | None = None
    current_version: str | None = None
    installs: str | None = None
    permissions: list[str] = []
    description_word_count: int | None = None
    has_faq_content: bool = False
    keyword_density: dict[str, float] = {}
    days_since_update: int | None = None
    reviews_fetched_count: int | None = None
    status: IngestionStatus = IngestionStatus.PENDING
    error_message: str | None = None


class PlayStoreDataRead(ORMBase):
    """Output schema for a Play Store listing audit."""

    id: int
    product_id: int
    app_title: str | None
    short_description: str | None
    full_description: str | None
    rating: float | None
    rating_count: int | None
    rating_distribution: dict[str, int]
    category: str | None
    store_last_updated: str | None
    current_version: str | None
    installs: str | None
    permissions: list[str]
    description_word_count: int | None
    has_faq_content: bool
    keyword_density: dict[str, float]
    days_since_update: int | None
    reviews_fetched_count: int | None
    status: IngestionStatus
    error_message: str | None
    fetched_at: datetime
