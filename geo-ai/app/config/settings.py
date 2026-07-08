"""Single source of truth for application configuration.

No module outside `app.config` should read `os.environ` directly. Every
setting is declared here, typed, and loaded from environment variables
(optionally via a local .env file) using pydantic-settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    Inputs: environment variables / .env file.
    Outputs: a validated, typed settings object consumed across the app.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App / environment ---
    ENVIRONMENT: Literal["dev", "prod"] = "dev"
    LOG_LEVEL: str = "INFO"

    # --- LLM (DeepSeek) ---
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BASE_DELAY_SECONDS: float = 1.0

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./geo.db"

    # --- Vector store / embeddings ---
    CHROMA_PERSIST_DIR: str = "./chroma"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-.env"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60 * 24

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Scheduler ---
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_DAYS: int = 7


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


settings = get_settings()
