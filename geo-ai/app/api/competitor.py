"""Competitor comparison API routes - thin controllers only."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.competitor.agent import CompetitorAgent
from app.database.session import get_db
from app.models.common_enums import IngestionStatus
from app.models.comparison_summary import ComparisonSummary
from app.models.competitor import Competitor
from app.models.product import Product
from app.schemas.competitor import CompareInput, CompareJobAck, CompareRequest, CompareStatusResponse

router = APIRouter(tags=["competitor"])

_agent = CompetitorAgent()

_GENERIC_COMPETITOR_NAMES = {"play.google.com", "apps.apple.com", "competitor"}


def _resolve_competitor_display_name(entry: dict, db: Session, product_id: int) -> str:
    """Prefer stored app/site title over generic hostnames like play.google.com."""
    signals = entry.get("signals") or {}
    for key in ("app_title", "title"):
        title = signals.get(key)
        if isinstance(title, str) and title.strip():
            return title.strip()

    stored = entry.get("competitor_name")
    if stored and stored.lower() not in _GENERIC_COMPETITOR_NAMES:
        return stored

    url = entry.get("competitor_url")
    if url:
        row = (
            db.query(Competitor)
            .filter(Competitor.product_id == product_id, Competitor.competitor_url == url)
            .first()
        )
        if row and row.competitor_name and row.competitor_name.lower() not in _GENERIC_COMPETITOR_NAMES:
            return row.competitor_name

    return stored or "Competitor"


def _enrich_competitor_scores(
    db: Session, product_id: int, scores: list[dict] | None
) -> list[dict]:
    enriched: list[dict] = []
    for entry in scores or []:
        copy = dict(entry)
        copy["competitor_name"] = _resolve_competitor_display_name(copy, db, product_id)
        enriched.append(copy)
    return enriched


async def _run_compare_job(product_id: int, competitor_urls: list[str]) -> None:
    result = await _agent.execute(
        CompareInput(product_id=product_id, competitor_urls=competitor_urls)
    )
    if result.success:
        logger.info(f"[compare job] product_id={product_id} finished status={result.data.status}")
    else:
        logger.warning(f"[compare job] product_id={product_id} failed: {result.error_message}")


@router.post("/compare", response_model=CompareJobAck, status_code=status.HTTP_202_ACCEPTED)
async def trigger_compare(
    payload: CompareRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> CompareJobAck:
    """Start competitor comparison in the background. Poll GET /compare/status/{product_id}."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    row = db.query(ComparisonSummary).filter(ComparisonSummary.product_id == product.id).first()
    if row is None:
        row = ComparisonSummary(product_id=product.id, status=IngestionStatus.RUNNING)
        db.add(row)
    else:
        row.status = IngestionStatus.RUNNING
        row.error_message = None
    db.commit()

    background_tasks.add_task(_run_compare_job, product.id, payload.competitor_urls)

    return CompareJobAck(
        product_id=product.id,
        status=IngestionStatus.RUNNING.value,
        message="Competitor comparison started. Poll GET /compare/status/{product_id}.",
    )


@router.get("/compare/status/{product_id}", response_model=CompareStatusResponse)
async def get_compare_status(product_id: int, db: Session = Depends(get_db)) -> CompareStatusResponse:
    """Return the latest competitor comparison result for a product."""
    row = (
        db.query(ComparisonSummary)
        .filter(ComparisonSummary.product_id == product_id)
        .order_by(ComparisonSummary.created_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No comparison has been run yet. Trigger POST /compare first.",
        )
    if row.status == IngestionStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Comparison is still running. Poll again shortly.",
        )

    product = db.query(Product).filter(Product.id == product_id).first()

    return CompareStatusResponse(
        product_id=row.product_id,
        status=row.status,
        missing_features=row.missing_features,
        missing_faqs=row.missing_faqs,
        improvement_plan=row.improvement_plan,
        narrative_summary=row.narrative_summary,
        competitor_scores=_enrich_competitor_scores(db, product_id, row.competitor_scores),
        our_score=row.our_score,
        our_breakdown=row.our_breakdown,
        our_product_name=product.name if product else None,
        error_message=row.error_message,
        created_at=row.created_at,
    )
