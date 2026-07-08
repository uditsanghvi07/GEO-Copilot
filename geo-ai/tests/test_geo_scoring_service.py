"""Unit tests for the pure GEO scoring function."""

from app.services.geo_scoring_service import GeoScoringSignals, compute_geo_score


def test_perfect_signals_score_near_maximum():
    signals = GeoScoringSignals(
        word_count=2500,
        crawled_pages=[{"role": "faq"}, {"role": "blog"}],
        has_faq=True,
        faq_count=12,
        meta_description="A" * 120,
        schema_types=["Organization", "Product", "FAQPage"],
        internal_links_count=60,
        avg_review_rating=4.8,
        review_count=150,
        days_since_update=10,
    )
    breakdown = compute_geo_score(signals)
    assert breakdown.total >= 85
    assert breakdown.total <= 100
    component_sum = sum(
        [
            breakdown.documentation_depth.earned,
            breakdown.faq_presence.earned,
            breakdown.metadata_quality.earned,
            breakdown.structured_data.earned,
            breakdown.authority_signals.earned,
            breakdown.review_quality.earned,
            breakdown.freshness.earned,
        ]
    )
    assert breakdown.total == int(round(min(100, component_sum)))


def test_empty_signals_score_low():
    signals = GeoScoringSignals()
    breakdown = compute_geo_score(signals)
    assert breakdown.total <= 15
    assert breakdown.metadata_quality.earned == 0
    assert breakdown.review_quality.earned == 0


def test_partial_signals_score_mid_range():
    signals = GeoScoringSignals(
        word_count=800,
        crawled_pages=[{"role": "homepage"}],
        has_faq=True,
        faq_count=3,
        meta_description="A decent meta description that is long enough for partial credit here.",
        schema_types=["Organization"],
        internal_links_count=20,
        avg_review_rating=3.5,
        review_count=30,
        days_since_update=60,
    )
    breakdown = compute_geo_score(signals)
    assert 25 <= breakdown.total <= 75
    assert breakdown.faq_presence.earned > 0
    assert breakdown.structured_data.earned > 0


def test_breakdown_components_sum_correctly():
    signals = GeoScoringSignals(
        meta_description="X" * 100,
        has_faq=True,
        faq_count=5,
        schema_types=["FAQPage"],
        internal_links_count=10,
        avg_review_rating=4.0,
        review_count=50,
    )
    breakdown = compute_geo_score(signals)
    earned_sum = (
        breakdown.documentation_depth.earned
        + breakdown.faq_presence.earned
        + breakdown.metadata_quality.earned
        + breakdown.structured_data.earned
        + breakdown.authority_signals.earned
        + breakdown.review_quality.earned
        + breakdown.freshness.earned
    )
    assert breakdown.total == int(round(min(100, earned_sum)))
