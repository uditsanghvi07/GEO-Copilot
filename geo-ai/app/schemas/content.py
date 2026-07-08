"""Pydantic schemas for the Content Generation agent and its API routes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.generated_content import ContentType
from app.schemas.common import ORMBase


class ContentGenerateInput(BaseModel):
    """Typed input accepted by `ContentGenerationAgent.run()`."""

    product_id: int
    content_type: ContentType
    extra_instructions: str | None = None


class ContentGenerateOutput(BaseModel):
    """Typed output returned by `ContentGenerationAgent.run()`."""

    product_id: int
    content_type: ContentType
    content_body: str
    generated_content_id: int
    chunks_used: int


class GenerateFaqRequest(BaseModel):
    product_id: int


class GenerateBlogRequest(BaseModel):
    product_id: int
    topic_hint: str | None = None


class GenerateMetaRequest(BaseModel):
    product_id: int


class GenerateCampaignRequest(BaseModel):
    product_id: int
    campaign_theme: str = Field(min_length=1)


class GeneratedContentRead(ORMBase):
    id: int
    product_id: int
    content_type: ContentType
    content_body: str
    prompt_used: str | None
    created_at: datetime
