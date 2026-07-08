"""Pydantic schemas for the Competitor agent and its API routes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.common_enums import IngestionStatus
from app.schemas.common import ORMBase


class CompetitorComparisonResult(BaseModel):
    """Strict JSON schema for the competitor comparison LLM output."""

    missing_features: list[str] = Field(default_factory=list)
    missing_faqs: list[str] = Field(default_factory=list)
    improvement_plan: list[str] = Field(default_factory=list)
    narrative_summary: str = ""


class CompareInput(BaseModel):
    """Typed input accepted by `CompetitorAgent.run()`."""

    product_id: int
    competitor_urls: list[str] = Field(min_length=1)


class CompareOutput(BaseModel):
    """Typed output returned by `CompetitorAgent.run()`."""

    product_id: int
    status: IngestionStatus
    comparison: CompetitorComparisonResult | None = None
    competitor_scores: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None


class CompareRequest(BaseModel):
    """Request body for POST /compare."""

    product_id: int
    competitor_urls: list[str] = Field(min_length=1)


class CompareJobAck(BaseModel):
    """Immediate acknowledgement returned by POST /compare."""

    product_id: int
    status: str
    message: str


class CompareStatusResponse(BaseModel):
    """Response for GET /compare/status/{product_id}."""

    product_id: int
    status: IngestionStatus
    missing_features: list[str] = []
    missing_faqs: list[str] = []
    improvement_plan: list[str] = []
    narrative_summary: str | None = None
    competitor_scores: list[dict[str, Any]] = []
    our_score: int | None = None
    our_breakdown: dict[str, Any] | None = None
    our_product_name: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class CompetitorRead(ORMBase):
    """Output schema for a competitor row."""

    id: int
    product_id: int
    competitor_name: str
    competitor_url: str | None
    comparison_notes: str | None
    geo_score: int | None = None
    score_breakdown: dict[str, Any] | None = None
