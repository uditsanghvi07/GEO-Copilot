"""Dashboard aggregation service — batch queries, no N+1."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_report import AuditReport
from app.models.pipeline_run import PipelineRun
from app.models.product import Product
from app.schemas.pipeline import DashboardProductSummary, DashboardResponse


def get_dashboard(db: Session) -> DashboardResponse:
    """Build an aggregated dashboard summary across all products.

    Uses 3 batch queries (products, latest audits, latest pipeline runs)
    instead of per-product lookups to avoid N+1.
    """
    products = db.query(Product).order_by(Product.updated_at.desc()).all()
    if not products:
        return DashboardResponse(products=[], total=0)

    product_ids = [p.id for p in products]

    # Latest audit per product — one query, dedupe in Python
    audits = (
        db.query(AuditReport)
        .filter(AuditReport.product_id.in_(product_ids))
        .order_by(AuditReport.created_at.desc())
        .all()
    )
    latest_audit: dict[int, AuditReport] = {}
    for audit in audits:
        if audit.product_id not in latest_audit:
            latest_audit[audit.product_id] = audit

    # Latest pipeline run per product — one query, dedupe in Python
    runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.product_id.in_(product_ids))
        .order_by(PipelineRun.started_at.desc())
        .all()
    )
    latest_run: dict[int, PipelineRun] = {}
    for run in runs:
        if run.product_id not in latest_run:
            latest_run[run.product_id] = run

    summaries = []
    for product in products:
        audit = latest_audit.get(product.id)
        run = latest_run.get(product.id)
        summaries.append(
            DashboardProductSummary(
                product_id=product.id,
                name=product.name,
                category=product.category,
                geo_score=audit.geo_score if audit else None,
                last_audit_date=audit.created_at if audit else None,
                pipeline_status=run.status.value if run else None,
                last_pipeline_date=run.started_at if run else None,
                website_url=product.website_url,
                play_store_url=product.play_store_url,
            )
        )

    return DashboardResponse(products=summaries, total=len(summaries))
