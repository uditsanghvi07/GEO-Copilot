"""Smoke tests for the pure extraction/discovery functions in the Website
Crawler service - no network or Playwright involved."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.crawler.constants import BLOG_LINK_HINTS, FAQ_LINK_HINTS, ROBOTS_RESTRICTED_NOTE
from app.agents.crawler.service import (
    _discover_link,
    _extract_page_signals,
    _normalize_url,
    crawl_website,
)
from app.models.common_enums import IngestionStatus

SAMPLE_HTML = """
<html>
<head>
<title>Acme Home</title>
<meta name="description" content="Acme does things.">
<script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
</head>
<body>
<nav><a href="/faq">FAQ</a><a href="/blog">Blog</a></nav>
<main>
<h1>Welcome to Acme</h1>
<h2>What is Acme?</h2>
<p>Acme is a company that makes widgets for everyone around the world.</p>
<img src="a.png">
<img src="b.png" alt="logo">
<a href="https://acme.com/pricing">Pricing</a>
<a href="https://external.com">External</a>
</main>
<footer>&copy; 2026 Acme Inc.</footer>
</body>
</html>
"""


def test_extract_page_signals_basic():
    signals = _extract_page_signals(SAMPLE_HTML, "https://acme.com/", "acme.com")

    assert signals["title"] == "Acme Home"
    assert signals["meta_description"] == "Acme does things."
    assert signals["headings"]["h1"] == ["Welcome to Acme"]
    assert "Organization" in signals["schema_types"]
    assert signals["faq_count"] >= 1
    assert signals["images_missing_alt_count"] == 1
    assert signals["internal_links_count"] >= 2
    assert signals["last_updated_signal"] == "copyright year 2026"


def test_discover_link_finds_faq_and_blog():
    nav_links = [
        ("FAQ", "https://acme.com/faq"),
        ("Blog", "https://acme.com/blog"),
        ("External", "https://external.com"),
    ]
    assert _discover_link(nav_links, FAQ_LINK_HINTS, "acme.com") == "https://acme.com/faq"
    assert _discover_link(nav_links, BLOG_LINK_HINTS, "acme.com") == "https://acme.com/blog"


def test_discover_link_returns_none_when_no_match():
    nav_links = [("Pricing", "https://acme.com/pricing")]
    assert _discover_link(nav_links, FAQ_LINK_HINTS, "acme.com") is None


def test_normalize_url_adds_scheme():
    assert _normalize_url("example.com") == "https://example.com"
    assert _normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_rejects_empty():
    with pytest.raises(ValueError):
        _normalize_url("   ")


@pytest.mark.asyncio
async def test_crawl_website_robots_blocked_uses_restricted_homepage_fetch():
    sample_signals = _extract_page_signals(
        """
    <html><head><title>Netflix India</title>
    <meta name="description" content="Watch shows online">
    </head><body><main><h1>Unlimited movies</h1><p>Stream anywhere.</p></main></body></html>
    """,
        "https://www.netflix.com/in/",
        "www.netflix.com",
    )

    async def fake_http_only(*_args, **_kwargs):
        return {"signals": sample_signals, "snapshot_path": "/tmp/homepage.html"}

    with (
        patch("app.agents.crawler.service._build_robot_parser", new_callable=AsyncMock) as mock_robots,
        patch("app.agents.crawler.service._can_fetch", return_value=False),
        patch("app.agents.crawler.service._try_http_homepage_only", side_effect=fake_http_only),
        patch("app.agents.crawler.service._check_sitemap_lastmod", new_callable=AsyncMock, return_value=None),
    ):
        mock_robots.return_value = object()
        output = await crawl_website(1, "https://www.netflix.com/in/")

    assert output.status == IngestionStatus.PARTIAL
    assert output.title == "Netflix India"
    assert output.meta_description == "Watch shows online"
    assert output.word_count > 0
    assert len(output.crawled_pages) == 1
    assert output.failed_pages[0].reason == ROBOTS_RESTRICTED_NOTE
