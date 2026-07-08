"""Tests for competitor compare status name enrichment."""

from app.api.competitor import _enrich_competitor_scores, _resolve_competitor_display_name


def test_resolve_competitor_display_name_prefers_app_title():
    entry = {
        "competitor_name": "play.google.com",
        "competitor_url": "https://play.google.com/store/apps/details?id=org.fcbh.hociem.n2.n",
        "signals": {"app_title": "Ho Bible", "source": "play_store"},
    }
    assert _resolve_competitor_display_name(entry, db=None, product_id=1) == "Ho Bible"  # type: ignore[arg-type]


def test_resolve_competitor_display_name_prefers_website_title():
    entry = {
        "competitor_name": "competitor.example.com",
        "signals": {"title": "Acme Docs"},
    }
    assert _resolve_competitor_display_name(entry, db=None, product_id=1) == "Acme Docs"  # type: ignore[arg-type]


def test_enrich_competitor_scores_rewrites_generic_names():
    scores = [
        {
            "competitor_name": "play.google.com",
            "competitor_url": "https://play.google.com/store/apps/details?id=org.fcbh.hociem.n2.n",
            "signals": {"app_title": "Ho Bible"},
            "geo_score": 23,
        }
    ]
    enriched = _enrich_competitor_scores(db=None, product_id=1, scores=scores)  # type: ignore[arg-type]
    assert enriched[0]["competitor_name"] == "Ho Bible"
