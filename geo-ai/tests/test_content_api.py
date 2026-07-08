"""Smoke tests for content generation API routes."""

import pytest

from app.models.generated_content import ContentType


@pytest.fixture()
def mock_content_pipeline(monkeypatch):
    monkeypatch.setattr(
        "app.agents.content.service.collection_has_documents", lambda pid: True
    )
    monkeypatch.setattr(
        "app.agents.content.service.retrieve_relevant_chunks",
        lambda pid, query, top_k=5: [
            "AuditCo provides real-time financial dashboards for SMBs.",
            "Our product integrates with Stripe and supports multi-currency billing.",
        ],
    )

    async def fake_chat(messages, **kwargs):
        return (
            "Q: Does AuditCo support Stripe?\n"
            "A: Yes, AuditCo integrates with Stripe for multi-currency billing.\n"
            "Q: Who is AuditCo for?\n"
            "A: AuditCo provides real-time financial dashboards for SMBs."
        )

    import app.agents.content.service as content_service

    monkeypatch.setattr(content_service.llm_client, "chat_completion", fake_chat)


def _create_product(client):
    r = client.post("/products", json={"name": "AuditCo"})
    return r.json()["id"]


def test_generate_faq_without_rag_returns_400(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.content.service.collection_has_documents", lambda pid: False
    )
    product_id = _create_product(client)
    response = client.post("/generate-faq", json={"product_id": product_id})
    assert response.status_code == 400
    assert "/crawl" in response.json()["detail"]


def test_generate_faq_grounded_content(client, mock_content_pipeline):
    product_id = _create_product(client)
    response = client.post("/generate-faq", json={"product_id": product_id})
    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == ContentType.FAQ.value
    assert "Stripe" in body["content_body"] or "SMB" in body["content_body"]


def test_list_content(client, mock_content_pipeline):
    product_id = _create_product(client)
    client.post("/generate-faq", json={"product_id": product_id})
    listing = client.get(f"/content/{product_id}")
    assert listing.status_code == 200
    assert len(listing.json()) >= 1
