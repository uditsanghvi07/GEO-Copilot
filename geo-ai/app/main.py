"""FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import audit, auth, competitor, content, crawler, health, pipeline, playstore, products, reviews
from app.config import settings
from app.database.session import init_db
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.utils.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup/shutdown side effects: logging, DB, scheduler."""
    configure_logging()
    logger.info(f"Starting AI GEO Copilot API (environment={settings.ENVIRONMENT})")
    init_db()
    logger.info("Database tables ensured (create_all)")
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutting down AI GEO Copilot API")


app = FastAPI(
    title="AI GEO Copilot",
    description="Enterprise AI Discoverability Platform - audits and improves how "
    "discoverable a product is across generative AI systems.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(crawler.router)
app.include_router(playstore.router)
app.include_router(reviews.router)
app.include_router(audit.router)
app.include_router(competitor.router)
app.include_router(content.router)
app.include_router(pipeline.router)
