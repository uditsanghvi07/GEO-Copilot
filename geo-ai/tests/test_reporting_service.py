"""Smoke tests for reporting agent HTML generation."""

from datetime import datetime

from app.agents.reporting.service import generate_report
from app.models.audit_report import AuditReport
from app.models.product import Product
from app.schemas.reporting import ReportGenerateInput


def test_generate_report_creates_html_file(db_session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr("app.agents.reporting.service.REPORTS_DIR", tmp_path)

    db = db_session_factory()
    try:
        product = Product(name="ReportCo", website_url="https://reportco.com")
        db.add(product)
        db.commit()
        db.refresh(product)

        db.add(
            AuditReport(
                product_id=product.id,
                geo_score=65,
                score_breakdown={
                    "total": 65,
                    "documentation_depth": {"max_points": 20, "earned": 10, "details": "ok"},
                },
                recommendations={"action_plan": [{"step": "Add FAQ", "component": "faq_presence", "estimated_point_impact": 5}]},
                created_at=datetime.utcnow(),
            )
        )
        db.commit()

        output = generate_report(db, ReportGenerateInput(product_id=product.id))
        assert output.report_id > 0
        assert tmp_path.joinpath(output.file_path.split("/")[-1]).exists() or __import__("pathlib").Path(output.file_path).exists()

        content = __import__("pathlib").Path(output.file_path).read_text()
        assert "ReportCo" in content
        assert "65" in content
        assert "Add FAQ" in content
    finally:
        db.close()
