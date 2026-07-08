"""Pydantic schemas for the Orchestrator pipeline and dashboard API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.pipeline_run import PipelineRunStatus
from app.schemas.common import ORMBase


class StageStatus(BaseModel):
    """Status of a single pipeline stage."""

    status: str  # success | partial | failed | skipped
    duration_ms: float = 0
    error_message: str | None = None


class RunFullAuditRequest(BaseModel):
    """Request body for POST /run-full-audit."""

    product_id: int
    competitor_urls: list[str] = Field(default_factory=list)


class RunFullAuditAck(BaseModel):
    """Immediate acknowledgement from POST /run-full-audit."""

    pipeline_run_id: int
    product_id: int
    status: str
    message: str


class PipelineRunStatusResponse(ORMBase):
    """Response for GET /run-full-audit/status/{pipeline_run_id}."""

    id: int
    product_id: int
    started_at: datetime
    completed_at: datetime | None
    status: PipelineRunStatus
    stage_statuses: dict[str, Any]
    competitor_urls: list[str]
    error_message: str | None


class ReportRead(ORMBase):
    """Response schema for GET /report/{product_id}."""

    id: int
    product_id: int
    file_path: str
    created_at: datetime
    html_content: str | None = None


class DashboardProductSummary(BaseModel):
    """One row in the dashboard grid."""

    product_id: int
    name: str
    category: str | None
    geo_score: int | None
    last_audit_date: datetime | None
    pipeline_status: str | None
    last_pipeline_date: datetime | None
    website_url: str | None
    play_store_url: str | None


class DashboardResponse(BaseModel):
    """Response for GET /dashboard."""

    products: list[DashboardProductSummary]
    total: int
