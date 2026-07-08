"""Pydantic schemas for the `reviews` table."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMBase


class ReviewCreate(BaseModel):
    """Input schema for recording a single fetched review."""

    product_id: int
    source: str = "play_store"
    rating: float | None = None
    review_text: str | None = None
    review_date: datetime | None = None
    sentiment_label: str | None = None
    is_analyzed: bool = False


class ReviewRead(ORMBase):
    """Output schema for a review."""

    id: int
    product_id: int
    source: str
    rating: float | None
    review_text: str | None
    review_date: datetime | None
    sentiment_label: str | None
    is_analyzed: bool
    fetched_at: datetime
