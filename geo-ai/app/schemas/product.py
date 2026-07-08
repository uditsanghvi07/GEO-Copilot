"""Pydantic schemas for the `products` table."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class ProductCreate(BaseModel):
    """Input schema for creating a Product."""

    name: str = Field(min_length=1, max_length=255)
    website_url: str | None = None
    play_store_url: str | None = None
    category: str | None = None


class ProductUpdate(BaseModel):
    """Input schema for partially updating a Product."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    website_url: str | None = None
    play_store_url: str | None = None
    category: str | None = None


class ProductRead(ORMBase):
    """Output schema for a Product."""

    id: int
    name: str
    website_url: str | None
    play_store_url: str | None
    category: str | None
    created_at: datetime
    updated_at: datetime
