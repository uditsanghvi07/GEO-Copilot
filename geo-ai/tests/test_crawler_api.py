"""Smoke tests for the /crawl API routes. The actual crawl (`crawl_website`)
is monkeypatched so these run fast and offline; the crawler's own parsing
logic is covered separately in test_crawler_service.py."""

import pytest

import app.agents.crawler.agent as crawler_agent_module
from app.models.common_enums import IngestionStatus
from app.schemas.crawler import CrawledPage, WebsiteCrawlOutput


def _create_product(client, website_url="https://example.com"):
    response = client.post("/products", json={"name": "Test Co", "website_url": website_url})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture()
def mock_successful_crawl(monkeypatch):
    async def fake_crawl_website(product_id, website_url):
        return WebsiteCrawlOutput(
            product_id=product_id,
            status=IngestionStatus.SUCCESS,
            title="Example Title",
            meta_description="Example description",
            headings_summary={"h1": ["Welcome"], "h2": [], "h3": []},
            has_faq=True,
            faq_count=2,
            has_schema_markup=True,
            schema_types=["Organization"],
            word_count=500,
            internal_links_count=10,
            images_missing_alt_count=1,
            last_updated_signal="copyright year 2026",
            crawled_pages=[CrawledPage(url=website_url, role="homepage", snapshot_path=None)],
            failed_pages=[],
        )

    monkeypatch.setattr(crawler_agent_module, "crawl_website", fake_crawl_website)


@pytest.fixture()
def mock_failed_crawl(monkeypatch):
    async def fake_crawl_website(product_id, website_url):
        return WebsiteCrawlOutput(
            product_id=product_id,
            status=IngestionStatus.FAILED,
            error_message="net::ERR_NAME_NOT_RESOLVED",
        )

    monkeypatch.setattr(crawler_agent_module, "crawl_website", fake_crawl_website)


def test_trigger_crawl_missing_product_returns_404(client):
    response = client.post("/crawl", json={"product_id": 999999})
    assert response.status_code == 404


def test_crawl_status_missing_returns_404(client):
    product_id = _create_product(client)
    response = client.get(f"/crawl/status/{product_id}")
    assert response.status_code == 404


def test_crawl_end_to_end_success(client, mock_successful_crawl):
    product_id = _create_product(client)

    ack = client.post("/crawl", json={"product_id": product_id})
    assert ack.status_code == 202
    assert ack.json()["product_id"] == product_id

    status_response = client.get(f"/crawl/status/{product_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "success"
    assert body["title"] == "Example Title"
    assert body["has_faq"] is True
    assert body["has_schema_markup"] is True
    assert body["word_count"] == 500


def test_crawl_degrades_gracefully_on_unreachable_site(client, mock_failed_crawl):
    product_id = _create_product(client)

    ack = client.post("/crawl", json={"product_id": product_id})
    assert ack.status_code == 202

    status_response = client.get(f"/crawl/status/{product_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "failed"
    assert body["error_message"] is not None
