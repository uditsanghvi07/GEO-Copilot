"""Smoke tests for review batching logic (no LLM/network)."""

from app.agents.reviews.constants import MAX_BATCH_SIZE
from app.agents.reviews.service import chunk_reviews
from app.models.review import Review


def _make_review(review_id: int, text: str, rating: float = 4.0) -> Review:
    return Review(
        id=review_id,
        product_id=1,
        source="play_store",
        rating=rating,
        review_text=text,
        is_analyzed=False,
    )


def test_chunk_reviews_splits_large_set():
    reviews = [_make_review(i, f"Review number {i} with some text content here.") for i in range(60)]
    batches = chunk_reviews(reviews)
    assert len(batches) >= 2
    assert sum(len(b) for b in batches) == 60
    assert all(len(b) <= MAX_BATCH_SIZE for b in batches)


def test_chunk_reviews_single_small_batch():
    reviews = [_make_review(i, "Short review.") for i in range(5)]
    batches = chunk_reviews(reviews)
    assert len(batches) == 1
    assert len(batches[0]) == 5


def test_chunk_reviews_respects_token_budget_for_long_reviews():
    long_text = "word " * 2000
    reviews = [_make_review(i, long_text) for i in range(10)]
    batches = chunk_reviews(reviews)
    assert len(batches) >= 2
