"""Pydantic schemas for the `generated_content` table."""

from datetime import datetime

from pydantic import BaseModel

from app.models.generated_content import ContentType
from app.schemas.common import ORMBase


class GeneratedContentCreate(BaseModel):
    """Input schema for persisting a piece of AI-generated content."""

    product_id: int
    content_type: ContentType
    content_body: str
    prompt_used: str | None = None


class GeneratedContentRead(ORMBase):
    """Output schema for a piece of AI-generated content."""

    id: int
    product_id: int
    content_type: ContentType
    content_body: str
    prompt_used: str | None
    created_at: datetime
