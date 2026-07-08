"""Smoke tests for the pure heuristic/derivation functions in the Play
Store Analyzer service - no network involved."""

import pytest

from app.agents.playstore.service import (
    _compute_keyword_density,
    _compute_rating_distribution,
    _has_faq_content,
    extract_package_name,
)


def test_extract_package_name_from_full_url():
    url = "https://play.google.com/store/apps/details?id=com.whatsapp&hl=en"
    assert extract_package_name(url, None) == "com.whatsapp"


def test_extract_package_name_from_bare_package_name():
    assert extract_package_name(None, "com.whatsapp") == "com.whatsapp"


def test_extract_package_name_prefers_explicit_package_name():
    url = "https://play.google.com/store/apps/details?id=com.other.app"
    assert extract_package_name(url, "com.whatsapp") == "com.whatsapp"


def test_extract_package_name_raises_when_unresolvable():
    with pytest.raises(ValueError):
        extract_package_name(None, None)


def test_has_faq_content_detects_faq_keyword():
    assert _has_faq_content("Check our FAQ section for help.") is True


def test_has_faq_content_detects_multiple_questions():
    text = "How do I sign up?\nWhat does this cost?\nGreat app for everyone."
    assert _has_faq_content(text) is True


def test_has_faq_content_false_for_plain_text():
    assert _has_faq_content("This is just a normal app description with no questions.") is False


def test_compute_rating_distribution():
    distribution = _compute_rating_distribution([10, 20, 30, 40, 50])
    assert distribution == {"1": 10, "2": 20, "3": 30, "4": 40, "5": 50}


def test_compute_rating_distribution_handles_missing_histogram():
    assert _compute_rating_distribution(None) == {}
    assert _compute_rating_distribution([1, 2]) == {}


def test_compute_keyword_density_generic_keywords():
    density = _compute_keyword_density("This app is free and easy and fast to use.", None)
    assert "free" in density
    assert "easy" in density
    assert all(0 < value <= 1 for value in density.values())


def test_compute_keyword_density_uses_category_terms():
    density = _compute_keyword_density("Track your budget and manage your bank payment.", "Finance")
    assert "budget" in density or "bank" in density or "payment" in density
