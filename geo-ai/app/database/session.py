"""Engine, session factory, and FastAPI dependency for DB access.

Structured so that migrating from SQLite to Postgres later only requires
changing `DATABASE_URL` in the environment/config - nothing here is
SQLite-specific except the `connect_args` toggle below.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a DB session, closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables that don't yet exist.

    MVP uses `create_all` instead of a migration tool. Every new table must
    still get an entry in MIGRATIONS.md describing the change.
    """
    from app import models  # noqa: F401 - import triggers model registration on Base

    Base.metadata.create_all(bind=engine)
