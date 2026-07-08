"""Core crawling + extraction logic for the Website Crawler agent.

Split from `agent.py` per the project's agent/service separation: this
module has no knowledge of `BaseAgent`/`AgentResult` - it just crawls a
site and returns/persists typed data.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import BrowserContext, async_playwright
from sqlalchemy.orm import Session

from app.agents.crawler.constants import (
    BLOG_LINK_HINTS,
    CRAWLER_USER_AGENT,
    FAQ_ELEMENT_CLASS_HINTS,
    FAQ_LINK_HINTS,
    MAX_FETCH_ATTEMPTS,
    MAX_HEADINGS_PER_LEVEL,
    NAVIGATION_TIMEOUT_MS,
    POLITENESS_DELAY_SECONDS,
    RETRY_BASE_DELAY_SECONDS,
)
from app.models.common_enums import IngestionStatus
from app.models.website_data import WebsiteData
from app.schemas.crawler import CrawledPage, FailedPage, WebsiteCrawlOutput
from app.utils.retry import with_retry_and_timeout

SNAPSHOT_ROOT = Path("uploads") / "website_snapshots"


def _normalize_url(url: str) -> str:
    """Ensure a URL has a scheme, defaulting to https."""
    url = url.strip()
    if not url:
        raise ValueError("website_url is empty")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


async def _build_robot_parser(base_url: str) -> RobotFileParser:
    """Best-effort fetch + parse of robots.txt. Defaults to allow-all if the
    fetch fails, so a missing/unreachable robots.txt never blocks a crawl."""
    parser = RobotFileParser()
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(robots_url, headers={"User-Agent": CRAWLER_USER_AGENT})
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            parser.parse([])
    except Exception as exc:  # noqa: BLE001 - robots.txt is best-effort
        logger.warning(f"Could not fetch robots.txt at {robots_url}: {exc!r}")
        parser.parse([])
    return parser


def _can_fetch(parser: RobotFileParser, url: str) -> bool:
    try:
        return parser.can_fetch(CRAWLER_USER_AGENT, url)
    except Exception:  # noqa: BLE001 - never let robots parsing crash a crawl
        return True


@with_retry_and_timeout(
    timeout_seconds=NAVIGATION_TIMEOUT_MS / 1000,
    max_attempts=MAX_FETCH_ATTEMPTS,
    base_delay_seconds=RETRY_BASE_DELAY_SECONDS,
)
async def _load_page(context: BrowserContext, url: str) -> str:
    """Navigate to `url` and return its rendered HTML. Retried (via the
    decorator) up to MAX_FETCH_ATTEMPTS times with exponential backoff on
    timeout/network error."""
    page = await context.new_page()
    try:
        response = await page.goto(url, timeout=NAVIGATION_TIMEOUT_MS, wait_until="domcontentloaded")
        if response is not None and response.status >= 400:
            raise RuntimeError(f"HTTP {response.status} loading {url}")
        return await page.content()
    finally:
        await page.close()


async def _http_fetch_html(url: str) -> str:
    """Plain HTTP GET fallback for sites that hang or block headless Chromium.

    Many bot-protected or HTTP/2-finicky sites still serve usable server-side
    HTML (title, meta description, JSON-LD) to a normal GET with a browser
    user agent. This yields real signals instead of scoring the product 0.
    """
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={
            "User-Agent": CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    ) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code} loading {url}")
    return response.text


async def _fetch_page_html(context: BrowserContext, url: str) -> str:
    """Fetch a page's HTML, preferring rendered Playwright output and falling
    back to a plain HTTP GET for sites that hang or block headless Chromium."""
    try:
        return await _load_page(context, url)
    except Exception as browser_exc:  # noqa: BLE001 - fall back to plain HTTP
        logger.warning(
            f"Browser load failed for {url} ({browser_exc!r}); trying plain HTTP fallback"
        )
        html = await _http_fetch_html(url)
        logger.info(f"HTTP fallback succeeded for {url}")
        return html


def _iter_jsonld_entries(data: object):
    """Yield each dict entry found in a parsed JSON-LD payload, flattening
    lists and `@graph` wrappers."""
    if isinstance(data, list):
        for item in data:
            yield from _iter_jsonld_entries(item)
    elif isinstance(data, dict):
        if isinstance(data.get("@graph"), list):
            for item in data["@graph"]:
                yield from _iter_jsonld_entries(item)
        else:
            yield data


def _extract_page_signals(html: str, page_url: str, base_domain: str) -> dict:
    """Parse one page's HTML and extract every Module 2 signal for it."""
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else None

    meta_description = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}
    for level in ("h1", "h2", "h3"):
        for tag in soup.find_all(level):
            text = tag.get_text(strip=True)
            if text and text not in headings[level] and len(headings[level]) < MAX_HEADINGS_PER_LEVEL:
                headings[level].append(text)

    faq_count = 0
    for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for tag in soup.find_all(level):
            if tag.get_text(strip=True).endswith("?"):
                faq_count += 1
    for hint in FAQ_ELEMENT_CLASS_HINTS:
        pattern = re.compile(hint, re.I)
        faq_count += len(soup.find_all(class_=pattern))
        faq_count += len(soup.find_all(id=pattern))

    schema_types: set[str] = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for entry in _iter_jsonld_entries(data):
            entry_type = entry.get("@type")
            if isinstance(entry_type, list):
                schema_types.update(str(t) for t in entry_type)
            elif entry_type:
                schema_types.add(str(entry_type))

    main = soup.find("main") or soup.find("article") or soup.body or soup
    for junk in main.find_all(["script", "style", "nav", "header", "footer"]):
        junk.decompose()
    word_count = len(main.get_text(separator=" ", strip=True).split())

    internal_links_count = 0
    nav_links: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        abs_url = urljoin(page_url, href)
        parsed = urlparse(abs_url)
        if parsed.netloc in ("", base_domain):
            internal_links_count += 1
        nav_links.append((anchor.get_text(strip=True), abs_url))

    images_missing_alt_count = sum(
        1 for img in soup.find_all("img") if not (img.get("alt") or "").strip()
    )

    last_updated_signal = None
    time_tag = soup.find("time")
    if time_tag and (time_tag.get("datetime") or time_tag.get_text(strip=True)):
        last_updated_signal = time_tag.get("datetime") or time_tag.get_text(strip=True)
    if not last_updated_signal:
        footer = soup.find("footer")
        haystack = footer.get_text(" ", strip=True) if footer else ""
        match = re.search(r"(?:©|copyright)\s*(\d{4})", haystack, re.I)
        if match:
            last_updated_signal = f"copyright year {match.group(1)}"

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "faq_count": faq_count,
        "schema_types": schema_types,
        "word_count": word_count,
        "internal_links_count": internal_links_count,
        "images_missing_alt_count": images_missing_alt_count,
        "last_updated_signal": last_updated_signal,
        "nav_links": nav_links,
    }


def _merge_signals(aggregate: dict, signals: dict) -> None:
    for level in ("h1", "h2", "h3"):
        for text in signals["headings"][level]:
            if text not in aggregate["headings"][level] and len(aggregate["headings"][level]) < MAX_HEADINGS_PER_LEVEL:
                aggregate["headings"][level].append(text)
    aggregate["faq_count"] += signals["faq_count"]
    aggregate["schema_types"].update(signals["schema_types"])
    aggregate["word_count"] += signals["word_count"]
    aggregate["internal_links_count"] += signals["internal_links_count"]
    aggregate["images_missing_alt_count"] += signals["images_missing_alt_count"]


def _is_crawlable_url(url: str) -> bool:
    """Only http(s) URLs can be fetched by Playwright."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _discover_link(nav_links: list[tuple[str, str]], hints: list[str], base_domain: str) -> str | None:
    for text, url in nav_links:
        if not _is_crawlable_url(url):
            continue
        parsed = urlparse(url)
        if parsed.netloc not in ("", base_domain):
            continue
        haystack = f"{text} {url}".lower()
        if any(hint in haystack for hint in hints):
            return url
    return None


async def _check_sitemap_lastmod(base_url: str) -> str | None:
    """Best-effort peek at /sitemap.xml for a `<lastmod>` value."""
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(sitemap_url, headers={"User-Agent": CRAWLER_USER_AGENT})
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        lastmods = sorted(tag.get_text(strip=True) for tag in soup.find_all("lastmod") if tag.get_text(strip=True))
        return f"sitemap lastmod {lastmods[-1]}" if lastmods else None
    except Exception as exc:  # noqa: BLE001 - sitemap check is best-effort
        logger.debug(f"sitemap.xml check failed for {base_url}: {exc!r}")
        return None


def _save_snapshot(snapshot_key: str, role: str, html: str) -> str | None:
    try:
        directory = SNAPSHOT_ROOT / snapshot_key
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{role}.html"
        path.write_text(html, encoding="utf-8")
        return str(path)
    except OSError as exc:  # noqa: BLE001 - snapshot persistence is best-effort
        logger.warning(f"Could not save HTML snapshot for key={snapshot_key} role={role}: {exc!r}")
        return None


async def crawl_website(
    product_id: int, website_url: str, *, snapshot_key: str | None = None
) -> WebsiteCrawlOutput:
    """Crawl a product's homepage plus (if discoverable) an FAQ/Help page
    and a Blog page, and return every extracted Module 2 signal.

    Inputs: product_id, website_url (may be missing a scheme).
    Outputs: `WebsiteCrawlOutput` - always returned, never raises. A
    completely unreachable site is reflected via `status=FAILED` and
    `error_message`, not an exception.
    """
    try:
        normalized_url = _normalize_url(website_url)
    except ValueError as exc:
        return WebsiteCrawlOutput(
            product_id=product_id,
            status=IngestionStatus.FAILED,
            error_message=str(exc),
        )

    base_domain = urlparse(normalized_url).netloc
    robot_parser = await _build_robot_parser(normalized_url)
    storage_key = snapshot_key or str(product_id)

    crawled_pages: list[CrawledPage] = []
    failed_pages: list[FailedPage] = []
    aggregate = {
        "headings": {"h1": [], "h2": [], "h3": []},
        "faq_count": 0,
        "schema_types": set(),
        "word_count": 0,
        "internal_links_count": 0,
        "images_missing_alt_count": 0,
    }
    title: str | None = None
    meta_description: str | None = None
    last_updated_signal: str | None = None
    nav_links: list[tuple[str, str]] = []

    try:
        async with async_playwright() as pw:
            # `--disable-http2` avoids ERR_HTTP2_PROTOCOL_ERROR on sites whose
            # servers negotiate HTTP/2 poorly with headless Chromium (e.g.
            # some CDNs/bot protection). The other flags harden headless runs
            # in containerized/sandboxed environments.
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-http2",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            try:
                context = await browser.new_context(user_agent=CRAWLER_USER_AGENT)

                if not _can_fetch(robot_parser, normalized_url):
                    failed_pages.append(FailedPage(url=normalized_url, reason="disallowed by robots.txt"))
                else:
                    try:
                        html = await _fetch_page_html(context, normalized_url)
                        signals = _extract_page_signals(html, normalized_url, base_domain)
                        title = signals["title"]
                        meta_description = signals["meta_description"]
                        last_updated_signal = signals["last_updated_signal"]
                        nav_links = signals["nav_links"]
                        _merge_signals(aggregate, signals)
                        snapshot_path = _save_snapshot(storage_key, "homepage", html)
                        crawled_pages.append(
                            CrawledPage(url=normalized_url, role="homepage", snapshot_path=snapshot_path)
                        )
                    except Exception as exc:  # noqa: BLE001 - one bad page must not crash the crawl
                        logger.error(f"Homepage fetch failed for product_id={product_id}: {exc!r}")
                        failed_pages.append(FailedPage(url=normalized_url, reason=str(exc)))

                for role, hints in (("faq", FAQ_LINK_HINTS), ("blog", BLOG_LINK_HINTS)):
                    discovered_url = _discover_link(nav_links, hints, base_domain)
                    if not discovered_url:
                        continue

                    await asyncio.sleep(POLITENESS_DELAY_SECONDS)

                    if not _can_fetch(robot_parser, discovered_url):
                        failed_pages.append(FailedPage(url=discovered_url, reason="disallowed by robots.txt"))
                        continue

                    try:
                        html = await _fetch_page_html(context, discovered_url)
                        signals = _extract_page_signals(html, discovered_url, base_domain)
                        _merge_signals(aggregate, signals)
                        if not last_updated_signal:
                            last_updated_signal = signals["last_updated_signal"]
                        snapshot_path = _save_snapshot(storage_key, role, html)
                        crawled_pages.append(CrawledPage(url=discovered_url, role=role, snapshot_path=snapshot_path))
                    except Exception as exc:  # noqa: BLE001 - one bad page must not crash the crawl
                        logger.warning(f"{role} page fetch failed for product_id={product_id}: {exc!r}")
                        failed_pages.append(FailedPage(url=discovered_url, reason=str(exc)))
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001 - browser-level failure (e.g. blocked, crashed)
        logger.error(f"Playwright browser failure for product_id={product_id}: {exc!r}")
        return WebsiteCrawlOutput(
            product_id=product_id,
            status=IngestionStatus.FAILED,
            error_message=f"Browser launch/navigation failure: {exc}",
            failed_pages=[FailedPage(url=normalized_url, reason=str(exc))],
        )

    if not last_updated_signal:
        last_updated_signal = await _check_sitemap_lastmod(normalized_url)

    if not crawled_pages:
        status = IngestionStatus.FAILED
        error_message: str | None = failed_pages[0].reason if failed_pages else "All pages failed to load"
    elif failed_pages:
        status = IngestionStatus.PARTIAL
        error_message = None
    else:
        status = IngestionStatus.SUCCESS
        error_message = None

    return WebsiteCrawlOutput(
        product_id=product_id,
        status=status,
        title=title,
        meta_description=meta_description,
        headings_summary=aggregate["headings"],
        has_faq=aggregate["faq_count"] > 0 or "FAQPage" in aggregate["schema_types"],
        faq_count=aggregate["faq_count"],
        has_schema_markup=len(aggregate["schema_types"]) > 0,
        schema_types=sorted(aggregate["schema_types"]),
        word_count=aggregate["word_count"],
        internal_links_count=aggregate["internal_links_count"],
        images_missing_alt_count=aggregate["images_missing_alt_count"],
        last_updated_signal=last_updated_signal,
        crawled_pages=crawled_pages,
        failed_pages=failed_pages,
        error_message=error_message,
    )


def persist_website_data(db: Session, output: WebsiteCrawlOutput) -> WebsiteData:
    """Upsert the single `website_data` row for `output.product_id`.

    Inputs: db session, `WebsiteCrawlOutput`.
    Outputs: the persisted `WebsiteData` ORM row.
    """
    row = db.query(WebsiteData).filter(WebsiteData.product_id == output.product_id).first()
    if row is None:
        row = WebsiteData(product_id=output.product_id)
        db.add(row)

    row.title = output.title
    row.meta_description = output.meta_description
    row.headings_summary = json.dumps(output.headings_summary)
    row.has_faq = output.has_faq
    row.has_schema_markup = output.has_schema_markup
    row.word_count = output.word_count
    row.faq_count = output.faq_count
    row.schema_types = output.schema_types
    row.internal_links_count = output.internal_links_count
    row.images_missing_alt_count = output.images_missing_alt_count
    row.last_updated_signal = output.last_updated_signal
    row.crawled_pages = [p.model_dump() for p in output.crawled_pages]
    row.failed_pages = [p.model_dump() for p in output.failed_pages]
    row.status = output.status
    row.error_message = output.error_message
    row.raw_html_snapshot_path = output.crawled_pages[0].snapshot_path if output.crawled_pages else None
    row.last_crawled_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row


async def crawl_external_url(url: str, snapshot_key: str) -> WebsiteCrawlOutput:
    """Crawl an external URL (e.g. a competitor site) without persisting to
    `website_data`. Reuses the full Website Crawler extraction logic."""
    return await crawl_website(product_id=0, website_url=url, snapshot_key=snapshot_key)
