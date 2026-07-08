"""Smoke tests for POST /audit."""

from datetime import datetime

import pytest

from app.models.common_enums import IngestionStatus
from app.models.play_store_data import PlayStoreData
from app.models.website_data import WebsiteData
from app.schemas.audit import ActionPlan, ActionPlanStep


def _create_product(client):
    r = client.post("/products", json={"name": "AuditCo", "category": "finance"})
    return r.json()["id"]


def _seed_ingestion(db_factory, product_id: int):
    db = db_factory()
    try:
        db.add(
            WebsiteData(
                product_id=product_id,
                title="AuditCo",
                meta_description="A" * 100,
                has_faq=True,
                faq_count=5,
                schema_types=["Organization", "Product"],
                word_count=1500,
                internal_links_count=30,
                crawled_pages=[{"role": "faq", "url": "https://x.com/faq"}],
                status=IngestionStatus.SUCCESS,
                last_crawled_at=datetime.utcnow(),
            )
        )
        db.add(
            PlayStoreData(
                product_id=product_id,
                app_title="AuditCo App",
                rating=4.5,
                rating_count=1000,
                days_since_update=20,
                status=IngestionStatus.SUCCESS,
                fetched_at=datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def mock_action_plan(monkeypatch):
    async def fake_json(messages, schema, **kwargs):
        return ActionPlan(
            action_plan=[
                ActionPlanStep(step="Add FAQPage schema", component="structured_data", estimated_point_impact=7),
                ActionPlanStep(step="Expand help docs", component="documentation_depth", estimated_point_impact=5),
            ]
        )

    import app.agents.audit.service as audit_service

    monkeypatch.setattr(audit_service.llm_client, "chat_completion_json", fake_json)


def test_audit_missing_ingestion_returns_400(client, db_session_factory):
    product_id = _create_product(client)
    response = client.post("/audit", json={"product_id": product_id})
    assert response.status_code == 400
    assert "/crawl" in response.json()["detail"]


def test_audit_website_only_returns_score(client, db_session_factory, mock_action_plan):
    product_id = _create_product(client)
    db = db_session_factory()
    try:
        db.add(
            WebsiteData(
                product_id=product_id,
                title="WebOnly",
                meta_description="A" * 100,
                has_faq=True,
                faq_count=3,
                schema_types=["Organization"],
                word_count=800,
                internal_links_count=20,
                crawled_pages=[{"role": "home", "url": "https://x.com"}],
                status=IngestionStatus.SUCCESS,
                last_crawled_at=datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post("/audit", json={"product_id": product_id})
    assert response.status_code == 201
    body = response.json()
    assert 0 <= body["geo_score"] <= 100
    assert body["score_breakdown"]["total"] == body["geo_score"]


def test_audit_returns_score_with_breakdown(client, db_session_factory, mock_action_plan):
    product_id = _create_product(client)
    _seed_ingestion(db_session_factory, product_id)

    response = client.post("/audit", json={"product_id": product_id})
    assert response.status_code == 201
    body = response.json()
    assert 0 <= body["geo_score"] <= 100
    assert "total" in body["score_breakdown"]
    assert body["score_breakdown"]["total"] == body["geo_score"]
    assert len(body["recommendations"]["action_plan"]) >= 1
