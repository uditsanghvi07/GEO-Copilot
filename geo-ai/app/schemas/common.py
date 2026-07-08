"""Schemas shared across agents and API responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class AgentResult(BaseModel, Generic[DataT]):
    """Standard envelope returned by every agent's `execute()` call.

    This is what lets the Orchestrator record partial failures without
    crashing the whole pipeline: a failed agent still returns a well-typed
    AgentResult with success=False and an error_message.
    """

    success: bool
    data: DataT | None = None
    error_message: str | None = None
    duration_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    status: str
    environment: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard typed error response body."""

    error: str
    detail: str | None = None


class ORMBase(BaseModel):
    """Base for Pydantic "Read" schemas that map from SQLAlchemy ORM objects."""

    model_config = {"from_attributes": True}
