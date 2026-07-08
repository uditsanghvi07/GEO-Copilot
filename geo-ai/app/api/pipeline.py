"""Pipeline, dashboard, and report API routes."""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models.pipeline_run import PipelineRun
from app.models.product import Product
from app.models.report import Report
from app.orchestrator.orchestrator import Orchestrator, create_pipeline_run
from app.schemas.pipeline import (
    DashboardResponse,
    PipelineRunStatusResponse,
    ReportRead,
    RunFullAuditAck,
    RunFullAuditRequest,
)
from app.services.dashboard_service import get_dashboard
from app.services.scheduler_service import run_scheduled_audits

router = APIRouter(tags=["pipeline"])

_orchestrator = Orchestrator()


async def _run_pipeline_job(
    pipeline_run_id: int, product_id: int, competitor_urls: list[str]
) -> None:
    await _orchestrator.run_full_pipeline(pipeline_run_id, product_id, competitor_urls)


@router.post("/run-full-audit", response_model=RunFullAuditAck, status_code=status.HTTP_202_ACCEPTED)
async def trigger_full_audit(
    payload: RunFullAuditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RunFullAuditAck:
    """Trigger the full orchestrated audit pipeline in the background."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    run = create_pipeline_run(db, product.id, payload.competitor_urls)
    background_tasks.add_task(
        _run_pipeline_job, run.id, product.id, payload.competitor_urls
    )

    return RunFullAuditAck(
        pipeline_run_id=run.id,
        product_id=product.id,
        status="running",
        message="Full audit pipeline started. Poll GET /run-full-audit/status/{pipeline_run_id}.",
    )


@router.get("/run-full-audit/status/{pipeline_run_id}", response_model=PipelineRunStatusResponse)
async def get_pipeline_status(
    pipeline_run_id: int, db: Session = Depends(get_db)
) -> PipelineRunStatusResponse:
    """Return per-stage status for a pipeline run."""
    run = db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")
    return run


@router.get("/reports/{product_id}", response_model=list[ReportRead])
async def list_reports(product_id: int, db: Session = Depends(get_db)) -> list[ReportRead]:
    """List all generated HTML reports for a product, newest first."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    rows = (
        db.query(Report)
        .filter(Report.product_id == product_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    results: list[ReportRead] = []
    for row in rows:
        html_content = None
        path = Path(row.file_path)
        if path.exists():
            html_content = path.read_text(encoding="utf-8")
        results.append(
            ReportRead(
                id=row.id,
                product_id=row.product_id,
                file_path=row.file_path,
                created_at=row.created_at,
                html_content=html_content,
            )
        )
    return results


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a report record and its HTML file from disk."""
    row = db.query(Report).filter(Report.id == report_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    file_path = Path(row.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError as exc:
            logger.warning(f"Could not delete report file {file_path}: {exc!r}")

    db.delete(row)
    db.commit()


@router.get("/report/{product_id}", response_model=ReportRead)
async def get_latest_report(product_id: int, db: Session = Depends(get_db)) -> ReportRead:
    """Return the latest HTML report for a product, including file content."""
    row = (
        db.query(Report)
        .filter(Report.product_id == product_id)
        .order_by(Report.created_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report generated yet. Run POST /run-full-audit first.",
        )

    html_content = None
    path = Path(row.file_path)
    if path.exists():
        html_content = path.read_text(encoding="utf-8")

    return ReportRead(
        id=row.id,
        product_id=row.product_id,
        file_path=row.file_path,
        created_at=row.created_at,
        html_content=html_content,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    """Aggregated product summary for a frontend dashboard grid."""
    return get_dashboard(db)


@router.post("/dev/trigger-scheduled-audit", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scheduled_audit_dev(background_tasks: BackgroundTasks) -> dict:
    """Dev-only: manually trigger the weekly scheduled audit without waiting.

    Only available when ENVIRONMENT=dev.
    """
    if settings.ENVIRONMENT != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in dev environment.",
        )

    background_tasks.add_task(run_scheduled_audits)
    logger.info("[dev] Manually triggered scheduled audit run")
    return {"status": "started", "message": "Scheduled audit triggered for all products."}
