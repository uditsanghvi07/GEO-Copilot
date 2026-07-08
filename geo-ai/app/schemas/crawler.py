"""Typed input/output schemas for the Website Crawler agent, plus the thin
request/ack schemas used by its API routes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.common_enums import IngestionStatus


class WebsiteCrawlInput(BaseModel):
    """Typed input accepted by `WebsiteCrawlerAgent.run()`."""

    product_id: int
    website_url: str


class FailedPage(BaseModel):
    """Record of a single page that failed to load during a crawl."""

    url: str
    reason: str


class CrawledPage(BaseModel):
    """Record of a single page that loaded successfully during a crawl."""

    url: str
    role: str  # "homepage" | "faq" | "blog"
    snapshot_path: str | None = None


class WebsiteCrawlOutput(BaseModel):
    """Typed output returned by `WebsiteCrawlerAgent.run()`."""

    product_id: int
    status: IngestionStatus
    title: str | None = None
    meta_description: str | None = None
    headings_summary: dict[str, list[str]] = {}
    has_faq: bool = False
    faq_count: int = 0
    has_schema_markup: bool = False
    schema_types: list[str] = []
    word_count: int = 0
    internal_links_count: int = 0
    images_missing_alt_count: int = 0
    last_updated_signal: str | None = None
    crawled_pages: list[CrawledPage] = []
    failed_pages: list[FailedPage] = []
    error_message: str | None = None


class CrawlRequest(BaseModel):
    """Request body for POST /crawl."""

    product_id: int


class CrawlJobAck(BaseModel):
    """Immediate acknowledgement returned by POST /crawl (job runs in the
    background via FastAPI BackgroundTasks)."""

    product_id: int
    status: str
    message: str


class CrawlStatusResponse(BaseModel):
    """Response for GET /crawl/status/{product_id}."""

    product_id: int
    status: IngestionStatus
    title: str | None = None
    meta_description: str | None = None
    has_faq: bool = False
    has_schema_markup: bool = False
    word_count: int | None = None
    schema_types: list[str] = []
    failed_pages: list[dict[str, Any]] = []
    error_message: str | None = None
    last_crawled_at: datetime | None = None
