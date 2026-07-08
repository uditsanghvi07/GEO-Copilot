"""Enums shared across multiple ORM models (avoids duplicate definitions)."""

import enum


class IngestionStatus(str, enum.Enum):
    """Lifecycle status of a background ingestion job (crawl / Play Store
    audit), persisted on the row it populates so `GET .../status/{id}`
    endpoints can report progress without a separate job table."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
