"""Smoke test for the centralized Settings object."""

from app.config import settings


def test_settings_has_expected_defaults():
    assert settings.DATABASE_URL.startswith("sqlite")
    assert settings.EMBEDDING_MODEL_NAME == "BAAI/bge-small-en-v1.5"
    assert settings.ENVIRONMENT in {"dev", "prod"}
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://localhost:3000" in settings.CORS_ORIGINS
