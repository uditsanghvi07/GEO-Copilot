"""Smoke tests for POST /compare and GET /compare/status."""

import pytest

from app.models.common_enums import IngestionStatus
from app.schemas.competitor import CompetitorComparisonResult
from app.schemas.crawler import CrawledPage, WebsiteCrawlOutput


@pytest.fixture()
def mock_compare_pipeline(monkeypatch, db_session_factory):
    async def fake_crawl(url, snapshot_key):
        return WebsiteCrawlOutput(
            product_id=0,
            status=IngestionStatus.SUCCESS,
            title="Competitor Site",
            meta_description="Competitor meta",
            has_faq=True,
            faq_count=8,
            has_schema_markup=True,
            schema_types=["Organization", "FAQPage", "Product"],
            word_count=3000,
            internal_links_count=80,
            crawled_pages=[CrawledPage(url=url, role="homepage")],
        )

    async def fake_json(messages, schema, **kwargs):
        return CompetitorComparisonResult(
            missing_features=["competitor has detailed API docs", "competitor has pricing FAQ"],
            missing_faqs=["How does pricing work?", "Is there an enterprise plan?"],
            improvement_plan=["Add API documentation page", "Create pricing FAQ section"],
            narrative_summary="Competitor leads on documentation and FAQ coverage.",
        )

    import app.agents.competitor.service as comp_service

    monkeypatch.setattr(comp_service, "crawl_external_url", fake_crawl)
    monkeypatch.setattr(comp_service.llm_client, "chat_completion_json", fake_json)


def _create_product(client):
    r = client.post("/products", json={"name": "OurCo"})
    return r.json()["id"]


def test_compare_returns_job_ack(client, mock_compare_pipeline):
    product_id = _create_product(client)
    response = client.post(
        "/compare",
        json={"product_id": product_id, "competitor_urls": ["https://competitor.example.com"]},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "running"


def test_compare_status_has_missing_lists(client, mock_compare_pipeline):
    product_id = _create_product(client)
    client.post(
        "/compare",
        json={"product_id": product_id, "competitor_urls": ["https://competitor.example.com"]},
    )
    status = client.get(f"/compare/status/{product_id}")
    assert status.status_code == 200
    body = status.json()
    assert len(body["missing_features"]) >= 1
    assert len(body["missing_faqs"]) >= 1
