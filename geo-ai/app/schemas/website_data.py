"""Pydantic schemas for the `website_data` table."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.common_enums import IngestionStatus
from app.schemas.common import ORMBase


class WebsiteDataCreate(BaseModel):
    """Input schema for recording a website crawl snapshot."""

    product_id: int
    raw_html_snapshot_path: str | None = None
    title: str | None = None
    meta_description: str | None = None
    headings_summary: str | None = None
    has_faq: bool = False
    has_schema_markup: bool = False
    word_count: int | None = None
    faq_count: int | None = None
    schema_types: list[str] = []
    internal_links_count: int | None = None
    images_missing_alt_count: int | None = None
    last_updated_signal: str | None = None
    crawled_pages: list[dict[str, Any]] = []
    failed_pages: list[dict[str, Any]] = []
    status: IngestionStatus = IngestionStatus.PENDING
    error_message: str | None = None


class WebsiteDataRead(ORMBase):
    """Output schema for a website crawl snapshot."""

    id: int
    product_id: int
    raw_html_snapshot_path: str | None
    title: str | None
    meta_description: str | None
    headings_summary: str | None
    has_faq: bool
    has_schema_markup: bool
    word_count: int | None
    faq_count: int | None
    schema_types: list[str]
    internal_links_count: int | None
    images_missing_alt_count: int | None
    last_updated_signal: str | None
    crawled_pages: list[dict[str, Any]]
    failed_pages: list[dict[str, Any]]
    status: IngestionStatus
    error_message: str | None
    last_crawled_at: datetime
