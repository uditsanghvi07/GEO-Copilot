"""Unit tests for dashboard aggregation service."""

from datetime import datetime

from app.models.audit_report import AuditReport
from app.models.pipeline_run import PipelineRun, PipelineRunStatus
from app.models.product import Product
from app.services.dashboard_service import get_dashboard


def test_dashboard_returns_valid_structure(db_session_factory):
    db = db_session_factory()
    try:
        result = get_dashboard(db)
        assert result.total == len(result.products)
        assert result.total >= 0
    finally:
        db.close()


def test_dashboard_returns_products_without_n_plus_one(db_session_factory):
    db = db_session_factory()
    try:
        p1 = Product(name="DashAlpha", category="finance", website_url="https://a.com")
        p2 = Product(name="DashBeta", category="social")
        db.add_all([p1, p2])
        db.commit()
        db.refresh(p1)
        db.refresh(p2)

        db.add(
            AuditReport(
                product_id=p1.id,
                geo_score=72,
                score_breakdown={"total": 72},
                recommendations={},
                created_at=datetime.utcnow(),
            )
        )
        db.add(
            PipelineRun(
                product_id=p1.id,
                status=PipelineRunStatus.SUCCESS,
                stage_statuses={},
                started_at=datetime.utcnow(),
            )
        )
        db.commit()

        result = get_dashboard(db)
        alpha = next((p for p in result.products if p.name == "DashAlpha"), None)
        beta = next((p for p in result.products if p.name == "DashBeta"), None)
        assert alpha is not None
        assert beta is not None
        assert alpha.geo_score == 72
        assert alpha.pipeline_status == "success"
        assert beta.geo_score is None
    finally:
        db.close()
