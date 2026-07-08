"""Play Store Analyzer API routes - thin controllers only, no business logic."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.playstore.agent import PlayStoreAnalyzerAgent
from app.database.session import get_db
from app.models.common_enums import IngestionStatus
from app.models.play_store_data import PlayStoreData
from app.models.product import Product
from app.schemas.playstore import (
    PlayStoreAuditInput,
    PlayStoreAuditJobAck,
    PlayStoreAuditRequest,
    PlayStoreAuditStatusResponse,
)

router = APIRouter(tags=["playstore"])

_agent = PlayStoreAnalyzerAgent()


async def _run_playstore_job(product_id: int, play_store_url: str | None, category: str | None) -> None:
    """Background task entrypoint. All persistence (success or failure)
    happens inside the agent itself; this just logs the final outcome."""
    result = await _agent.execute(
        PlayStoreAuditInput(product_id=product_id, play_store_url=play_store_url, category=category)
    )
    if result.success:
        logger.info(f"[playstore job] product_id={product_id} finished with status={result.data.status}")
    else:
        logger.warning(f"[playstore job] product_id={product_id} failed: {result.error_message}")


@router.post(
    "/playstore-audit", response_model=PlayStoreAuditJobAck, status_code=status.HTTP_202_ACCEPTED
)
async def trigger_playstore_audit(
    payload: PlayStoreAuditRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> PlayStoreAuditJobAck:
    """Start a Play Store listing audit for a product in the background and
    return a job reference immediately. Poll
    `GET /playstore-audit/status/{product_id}` for the result."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.play_store_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Product has no play_store_url configured"
        )

    row = db.query(PlayStoreData).filter(PlayStoreData.product_id == product.id).first()
    if row is None:
        row = PlayStoreData(product_id=product.id, status=IngestionStatus.RUNNING)
        db.add(row)
    else:
        row.status = IngestionStatus.RUNNING
        row.error_message = None
    db.commit()

    background_tasks.add_task(_run_playstore_job, product.id, product.play_store_url, product.category)

    return PlayStoreAuditJobAck(
        product_id=product.id,
        status=IngestionStatus.RUNNING.value,
        message="Play Store audit started in the background. Poll GET /playstore-audit/status/{product_id}.",
    )


@router.get("/playstore-audit/status/{product_id}", response_model=PlayStoreAuditStatusResponse)
async def get_playstore_audit_status(
    product_id: int, db: Session = Depends(get_db)
) -> PlayStoreAuditStatusResponse:
    """Return the latest `play_store_data` row status for a product."""
    row = db.query(PlayStoreData).filter(PlayStoreData.product_id == product_id).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Play Store audit has been run yet for this product",
        )
    return PlayStoreAuditStatusResponse(
        product_id=row.product_id,
        status=row.status,
        app_title=row.app_title,
        rating=row.rating,
        rating_count=row.rating_count,
        installs=row.installs,
        reviews_fetched_count=row.reviews_fetched_count,
        error_message=row.error_message,
        fetched_at=row.fetched_at,
    )
