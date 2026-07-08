"""Typed input/output schemas for the Play Store Analyzer agent, plus the
thin request/ack schemas used by its API routes."""

from datetime import datetime

from pydantic import BaseModel

from app.models.common_enums import IngestionStatus


class PlayStoreAuditInput(BaseModel):
    """Typed input accepted by `PlayStoreAnalyzerAgent.run()`.

    Exactly one of `play_store_url` or `package_name` should resolve to a
    usable package id.
    """

    product_id: int
    play_store_url: str | None = None
    package_name: str | None = None
    category: str | None = None


class PlayStoreAuditOutput(BaseModel):
    """Typed output returned by `PlayStoreAnalyzerAgent.run()`."""

    product_id: int
    status: IngestionStatus
    app_title: str | None = None
    short_description: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    rating_distribution: dict[str, int] = {}
    category: str | None = None
    store_last_updated: str | None = None
    current_version: str | None = None
    installs: str | None = None
    permissions: list[str] = []
    description_word_count: int = 0
    has_faq_content: bool = False
    keyword_density: dict[str, float] = {}
    days_since_update: int | None = None
    reviews_fetched_count: int = 0
    error_message: str | None = None


class PlayStoreAuditRequest(BaseModel):
    """Request body for POST /playstore-audit."""

    product_id: int


class PlayStoreAuditJobAck(BaseModel):
    """Immediate acknowledgement returned by POST /playstore-audit (job runs
    in the background via FastAPI BackgroundTasks)."""

    product_id: int
    status: str
    message: str


class PlayStoreAuditStatusResponse(BaseModel):
    """Response for GET /playstore-audit/status/{product_id}."""

    product_id: int
    status: IngestionStatus
    app_title: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    installs: str | None = None
    reviews_fetched_count: int | None = None
    error_message: str | None = None
    fetched_at: datetime | None = None
