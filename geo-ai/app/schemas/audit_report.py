"""Pydantic schemas for the `audit_reports` table."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMBase


class AuditReportCreate(BaseModel):
    """Input schema for persisting a completed audit report."""

    product_id: int
    geo_score: int
    score_breakdown: dict[str, Any] = {}
    recommendations: dict[str, Any] = {}


class AuditReportRead(ORMBase):
    """Output schema for an audit report."""

    id: int
    product_id: int
    geo_score: int
    score_breakdown: dict[str, Any]
    recommendations: dict[str, Any]
    created_at: datetime
