"""Unit tests for competitor scoring helpers."""

from app.agents.competitor.service import (
    _is_play_store_url,
    _score_play_store_output,
)
from app.models.common_enums import IngestionStatus
from app.schemas.playstore import PlayStoreAuditOutput


def test_is_play_store_url_detects_listing():
    url = "https://play.google.com/store/apps/details?id=org.fcbh.hociem.n2.n&hl=en_IN"
    assert _is_play_store_url(url) is True


def test_is_play_store_url_rejects_website():
    assert _is_play_store_url("https://competitor.example.com") is False


def test_score_play_store_output_includes_reviews_and_freshness():
    output = PlayStoreAuditOutput(
        product_id=0,
        status=IngestionStatus.SUCCESS,
        app_title="Ho Bible",
        short_description="Read and listen to the Bible in Ho",
        rating=4.6,
        rating_count=1200,
        description_word_count=450,
        has_faq_content=True,
        days_since_update=10,
        store_last_updated="16 Jun 2026",
        reviews_fetched_count=50,
    )
    raw_reviews = [{"score": 5, "content": "Great app"}]

    geo_score, breakdown, signals = _score_play_store_output(output, raw_reviews)

    assert breakdown["review_quality"]["earned"] > 0
    assert breakdown["freshness"]["earned"] > 0
    assert signals["rating"] == 4.6
    assert geo_score > 0
