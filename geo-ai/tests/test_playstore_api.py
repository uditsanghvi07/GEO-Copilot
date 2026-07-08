"""Smoke tests for the /playstore-audit API routes. The actual listing
fetch (`audit_play_store_listing`) is monkeypatched so these run fast and
offline; the heuristic derivation logic is covered separately in
test_playstore_service.py."""

import pytest

import app.agents.playstore.agent as playstore_agent_module
from app.models.common_enums import IngestionStatus
from app.schemas.playstore import PlayStoreAuditOutput


def _create_product(client, play_store_url="https://play.google.com/store/apps/details?id=com.example.app"):
    response = client.post("/products", json={"name": "Test App", "play_store_url": play_store_url})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture()
def mock_successful_audit(monkeypatch):
    async def fake_audit(product_id, play_store_url, package_name, category):
        output = PlayStoreAuditOutput(
            product_id=product_id,
            status=IngestionStatus.SUCCESS,
            app_title="Example App",
            short_description="Does example things",
            rating=4.5,
            rating_count=1000,
            rating_distribution={"1": 10, "2": 10, "3": 20, "4": 200, "5": 760},
            category="Productivity",
            store_last_updated="Jul 1, 2026",
            current_version="1.2.3",
            installs="1,000,000+",
            permissions=["Storage"],
            description_word_count=120,
            has_faq_content=True,
            keyword_density={"task": 0.02},
            days_since_update=6,
            reviews_fetched_count=3,
            error_message=None,
        )
        raw_reviews = [
            {"content": "Great app", "score": 5, "at": None},
            {"content": "Needs work", "score": 3, "at": None},
        ]
        return output, raw_reviews, "Example App full description."

    monkeypatch.setattr(playstore_agent_module, "audit_play_store_listing", fake_audit)


@pytest.fixture()
def mock_failed_audit(monkeypatch):
    async def fake_audit(product_id, play_store_url, package_name, category):
        output = PlayStoreAuditOutput(
            product_id=product_id, status=IngestionStatus.FAILED, error_message="App not found(404)."
        )
        return output, [], None

    monkeypatch.setattr(playstore_agent_module, "audit_play_store_listing", fake_audit)


def test_trigger_audit_missing_product_returns_404(client):
    response = client.post("/playstore-audit", json={"product_id": 999999})
    assert response.status_code == 404


def test_audit_status_missing_returns_404(client):
    product_id = _create_product(client)
    response = client.get(f"/playstore-audit/status/{product_id}")
    assert response.status_code == 404


def test_playstore_audit_end_to_end_success(client, mock_successful_audit):
    product_id = _create_product(client)

    ack = client.post("/playstore-audit", json={"product_id": product_id})
    assert ack.status_code == 202
    assert ack.json()["product_id"] == product_id

    status_response = client.get(f"/playstore-audit/status/{product_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "success"
    assert body["app_title"] == "Example App"
    assert body["rating"] == 4.5
    assert body["reviews_fetched_count"] == 3

    reviews_response = client.get("/products/" + str(product_id))
    assert reviews_response.status_code == 200


def test_playstore_audit_degrades_gracefully_on_invalid_app(client, mock_failed_audit):
    product_id = _create_product(client)

    ack = client.post("/playstore-audit", json={"product_id": product_id})
    assert ack.status_code == 202

    status_response = client.get(f"/playstore-audit/status/{product_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "failed"
    assert body["error_message"] is not None
