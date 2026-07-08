"""APScheduler configuration for weekly full-audit pipeline runs."""

from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.models.product import Product
from app.orchestrator.orchestrator import Orchestrator, create_pipeline_run

_scheduler = None


def get_scheduler():
    """Return the module-level scheduler instance (lazy-init)."""
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        _scheduler = AsyncIOScheduler()
    return _scheduler


async def run_scheduled_audits() -> None:
    """Run the full orchestrator pipeline for every product in the database.

    Called by APScheduler on the configured interval. Logs an email stub
    after each run (real SMTP integration is a future seam).
    """
    logger.info("[scheduler] Starting scheduled weekly audit run for all products")
    db: Session = SessionLocal()
    orchestrator = Orchestrator()
    try:
        products = db.query(Product).all()
        logger.info(f"[scheduler] Found {len(products)} product(s) to audit")

        for product in products:
            run = create_pipeline_run(db, product.id, competitor_urls=[])
            logger.info(
                f"[scheduler] Starting pipeline_run_id={run.id} for product '{product.name}'"
            )
            await orchestrator.run_full_pipeline(run.id, product.id, competitor_urls=[])
    finally:
        db.close()

    logger.info("[scheduler] Scheduled audit run completed")


def start_scheduler() -> None:
    """Start APScheduler with the weekly audit job if enabled."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return

    scheduler = get_scheduler()
    if scheduler.running:
        return

    scheduler.add_job(
        run_scheduled_audits,
        trigger="interval",
        days=settings.SCHEDULER_INTERVAL_DAYS,
        id="weekly_full_audit",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started: full audit every {settings.SCHEDULER_INTERVAL_DAYS} day(s)"
    )


def stop_scheduler() -> None:
    """Shut down APScheduler gracefully."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
