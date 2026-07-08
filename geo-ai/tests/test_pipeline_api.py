"""Smoke tests for pipeline orchestrator and API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.common_enums import IngestionStatus
from app.models.pipeline_run import PipelineRunStatus
from app.schemas.audit import AuditOutput
from app.schemas.common import AgentResult
from app.schemas.competitor import CompareOutput
from app.schemas.content import ContentGenerateOutput
from app.schemas.crawler import WebsiteCrawlOutput
from app.schemas.playstore import PlayStoreAuditOutput
from app.schemas.reporting import ReportGenerateOutput
from app.schemas.review_intelligence import ReviewAnalyzeOutput


def _success_result(data=None):
    return AgentResult(success=True, data=data, error_message=None, duration_ms=10.0)


def _failed_result(msg="stage failed"):
    return AgentResult(success=False, data=None, error_message=msg, duration_ms=5.0)


@pytest.fixture()
def mock_all_agents(monkeypatch, tmp_path):
    monkeypatch.setattr("app.agents.reporting.service.REPORTS_DIR", tmp_path)

    import app.orchestrator.orchestrator as orch_module
    import app.api.pipeline as pipeline_module

    orch = orch_module.Orchestrator()

    orch._crawler.execute = AsyncMock(
        return_value=_success_result(
            WebsiteCrawlOutput(product_id=1, status=IngestionStatus.SUCCESS, title="Test")
        )
    )
    orch._playstore.execute = AsyncMock(
        return_value=_success_result(
            PlayStoreAuditOutput(product_id=1, status=IngestionStatus.SUCCESS, app_title="App")
        )
    )
    orch._reviews.execute = AsyncMock(
        return_value=_success_result(
            ReviewAnalyzeOutput(product_id=1, status=IngestionStatus.SUCCESS, reviews_analyzed_count=10)
        )
    )
    orch._audit.execute = AsyncMock(
        return_value=_success_result(
            AuditOutput(product_id=1, geo_score=60, score_breakdown={"total": 60}, recommendations={}, audit_report_id=1)
        )
    )
    orch._competitor.execute = AsyncMock(
        return_value=_failed_result("competitor skipped")
    )
    orch._content.execute = AsyncMock(
        return_value=_success_result(
            ContentGenerateOutput(
                product_id=1,
                content_type="faq",
                content_body="FAQ content",
                generated_content_id=1,
                chunks_used=2,
            )
        )
    )
    orch._reporting.execute = AsyncMock(
        return_value=_success_result(
            ReportGenerateOutput(product_id=1, report_id=1, file_path=str(tmp_path / "report.html"))
        )
    )

    monkeypatch.setattr(pipeline_module, "_orchestrator", orch)
    return orch


def _create_product(client):
    r = client.post(
        "/products",
        json={
            "name": "PipelineCo",
            "website_url": "https://pipelineco.com",
            "play_store_url": "https://play.google.com/store/apps/details?id=com.pipelineco",
        },
    )
    return r.json()["id"]


def test_run_full_audit_returns_pipeline_run_id(client, mock_all_agents):
    product_id = _create_product(client)
    response = client.post(
        "/run-full-audit",
        json={"product_id": product_id, "competitor_urls": []},
    )
    assert response.status_code == 202
    body = response.json()
    assert "pipeline_run_id" in body
    assert body["product_id"] == product_id


def test_pipeline_status_shows_stages(client, mock_all_agents):
    product_id = _create_product(client)
    ack = client.post("/run-full-audit", json={"product_id": product_id})
    run_id = ack.json()["pipeline_run_id"]

    status = client.get(f"/run-full-audit/status/{run_id}")
    assert status.status_code == 200
    body = status.json()
    assert "stage_statuses" in body
    assert "reporting" in body["stage_statuses"]
    assert body["status"] in ("success", "partial")


def test_pipeline_produces_report_even_with_competitor_skipped(client, mock_all_agents, tmp_path):
    product_id = _create_product(client)
    ack = client.post("/run-full-audit", json={"product_id": product_id, "competitor_urls": []})
    run_id = ack.json()["pipeline_run_id"]

    status = client.get(f"/run-full-audit/status/{run_id}")
    assert status.json()["stage_statuses"]["competitor"]["status"] == "skipped"
    assert status.json()["stage_statuses"]["reporting"]["status"] == "success"


def test_dashboard_endpoint(client, db_session_factory):
    db = db_session_factory()
    from app.models.product import Product

    db.add(Product(name="DashCo"))
    db.commit()
    db.close()

    response = client.get("/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert "products" in body


def test_dev_trigger_scheduled_audit(client):
    response = client.post("/dev/trigger-scheduled-audit")
    assert response.status_code == 202
