"""Declarative base and reusable timestamp mixin for SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the app."""


class CreatedAtMixin:
    """Adds an indexed `created_at` column, used for default sort order."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )


class TimestampMixin(CreatedAtMixin):
    """Adds indexed `created_at` and `updated_at` columns."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
