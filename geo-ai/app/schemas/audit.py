"""Pydantic schemas for the Audit agent and its API routes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class ActionPlanStep(BaseModel):
    """One prioritized action from the LLM action plan."""

    step: str
    component: str
    estimated_point_impact: float = Field(ge=0)


class ActionPlan(BaseModel):
    """Strict JSON schema for the audit LLM action plan."""

    action_plan: list[ActionPlanStep] = Field(default_factory=list)


class AuditInput(BaseModel):
    """Typed input accepted by `AuditAgent.run()`."""

    product_id: int


class AuditOutput(BaseModel):
    """Typed output returned by `AuditAgent.run()`."""

    product_id: int
    geo_score: int
    score_breakdown: dict[str, Any]
    recommendations: dict[str, Any]
    audit_report_id: int


class AuditRequest(BaseModel):
    """Request body for POST /audit."""

    product_id: int


class AuditResponse(ORMBase):
    """Response schema for POST /audit."""

    id: int
    product_id: int
    geo_score: int
    score_breakdown: dict[str, Any]
    recommendations: dict[str, Any]
    created_at: datetime
