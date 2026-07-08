"""Shared pytest fixtures: an isolated in-memory SQLite DB per test session,
wired into the app via a `get_db` dependency override, plus a TestClient."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def _test_engine():
    # StaticPool keeps a single shared connection alive for the in-memory
    # SQLite DB - without it, every checkout would get its own isolated
    # (and table-less) in-memory database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app import models  # noqa: F401 - register all tables on Base

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(_test_engine, monkeypatch):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Agents intentionally open their own DB session (so they stay
    # independently callable outside of an HTTP request, per the
    # architecture rules) via a module-level `SessionLocal` bound at import
    # time - overriding the `get_db` FastAPI dependency alone doesn't reach
    # them. Redirect each agent module's `SessionLocal` to the same test
    # engine so a background job triggered by a request writes to the DB
    # the test can actually observe.
    import app.agents.crawler.agent as crawler_agent_module
    import app.agents.playstore.agent as playstore_agent_module
    import app.agents.reviews.agent as reviews_agent_module
    import app.agents.audit.agent as audit_agent_module
    import app.agents.competitor.agent as competitor_agent_module
    import app.agents.content.agent as content_agent_module
    import app.agents.reporting.agent as reporting_agent_module
    import app.orchestrator.orchestrator as orchestrator_module

    monkeypatch.setattr(crawler_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(playstore_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(reviews_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(audit_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(competitor_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(content_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(reporting_agent_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(orchestrator_module, "SessionLocal", TestingSessionLocal)

    # Avoid starting APScheduler during tests
    monkeypatch.setattr("app.services.scheduler_service.settings.SCHEDULER_ENABLED", False)

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session_factory(_test_engine):
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)
