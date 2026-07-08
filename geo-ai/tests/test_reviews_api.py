"""Smoke tests for /reviews/analyze and /reviews/summary API routes."""

from datetime import datetime

import pytest

from app.models.common_enums import IngestionStatus
from app.schemas.review_intelligence import BatchReviewAnalysis, MergedReviewSummary


def _create_product(client):
    response = client.post("/products", json={"name": "Test App", "category": "social"})
    assert response.status_code == 201
    return response.json()["id"]


def _seed_reviews(db_session_factory, product_id: int, count: int) -> None:
    from app.models.review import Review

    db = db_session_factory()
    try:
        for i in range(count):
            db.add(
                Review(
                    product_id=product_id,
                    source="play_store",
                    rating=3.0 + (i % 3),
                    review_text=f"Review {i}: app is {'great' if i % 2 == 0 else 'slow and buggy'}",
                    review_date=datetime.utcnow(),
                    is_analyzed=False,
                )
            )
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def mock_llm_pipeline(monkeypatch):
    import app.agents.reviews.service as service_module

    call_count = {"batch": 0}

    async def batch_side_effect(messages, schema, **kwargs):
        call_count["batch"] += 1
        return BatchReviewAnalysis(
            recurring_complaints=["slow performance", "login issues"],
            feature_requests=["dark mode", "offline support"],
            positive_themes=["easy to use"],
            negative_themes=["crashes often"],
            sentiment_lean="negative",
        )

    async def fake_reduce(outputs):
        return MergedReviewSummary(
            top_complaints=[
                "slow performance",
                "login issues",
                "crashes",
                "battery drain",
                "ads",
            ],
            top_feature_requests=[
                "dark mode",
                "offline support",
                "better notifications",
            ],
            positive_themes=["easy to use", "good design", "reliable messaging"],
            negative_themes=["crashes often", "slow updates", "privacy concerns"],
            overall_sentiment_score=-0.3,
        )

    monkeypatch.setattr(service_module.llm_client, "chat_completion_json", batch_side_effect)
    monkeypatch.setattr(service_module, "_reduce_batches", fake_reduce)
    return call_count


def test_analyze_zero_reviews_returns_not_enough_data(client):
    product_id = _create_product(client)
    response = client.post("/reviews/analyze", json={"product_id": product_id})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "not_enough_data"
    assert "not enough data" in body["message"].lower()


def test_summary_missing_returns_404(client):
    product_id = _create_product(client)
    response = client.get(f"/reviews/summary/{product_id}")
    assert response.status_code == 404


def test_analyze_fifty_reviews_produces_merged_summary(client, db_session_factory, mock_llm_pipeline):
    product_id = _create_product(client)
    _seed_reviews(db_session_factory, product_id, 55)

    ack = client.post("/reviews/analyze", json={"product_id": product_id})
    assert ack.status_code == 202
    assert ack.json()["status"] == "running"

    summary_response = client.get(f"/reviews/summary/{product_id}")
    assert summary_response.status_code == 200
    body = summary_response.json()
    assert body["status"] == "success"
    assert len(body["top_complaints"]) >= 1
    assert len(body["top_feature_requests"]) >= 1
    assert body["reviews_analyzed_count"] == 55
    assert mock_llm_pipeline["batch"] >= 1


def test_analyze_missing_product_returns_404(client):
    response = client.post("/reviews/analyze", json={"product_id": 999999})
    assert response.status_code == 404
