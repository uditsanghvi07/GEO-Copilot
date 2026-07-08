"""Core Play Store fetching + derived-signal logic for the Play Store
Analyzer agent. No AI/embeddings involved - every derived signal here is a
plain heuristic."""

import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from google_play_scraper import Sort, app as gps_app, permissions as gps_permissions, reviews as gps_reviews
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.playstore.constants import (
    CATEGORY_KEYWORDS,
    FETCH_TIMEOUT_SECONDS,
    GENERIC_KEYWORDS,
    MAX_FETCH_ATTEMPTS,
    RETRY_BASE_DELAY_SECONDS,
    REVIEWS_TO_FETCH,
)
from app.models.common_enums import IngestionStatus
from app.models.play_store_data import PlayStoreData
from app.models.review import Review
from app.schemas.playstore import PlayStoreAuditOutput
from app.utils.retry import with_retry_and_timeout


def extract_package_name(play_store_url: str | None, package_name: str | None) -> str:
    """Resolve a usable Play Store package id from either an explicit
    package name or a full Play Store listing URL.

    Inputs: play_store_url (e.g. ".../details?id=com.foo.bar"), package_name.
    Outputs: the package id (str).
    Raises: ValueError if neither input yields a usable package id.
    """
    if package_name:
        return package_name.strip()
    if play_store_url:
        url = play_store_url.strip()
        parsed = urlparse(url)
        query_id = parse_qs(parsed.query).get("id")
        if query_id and query_id[0]:
            return query_id[0]
        # Fallback: URL might just be the bare package id itself.
        if "." in url and "/" not in url:
            return url
        # A search URL (…/store/search?q=…) has no app id - guide the user.
        if "/search" in parsed.path or parsed.path.endswith("/store/search"):
            raise ValueError(
                "This is a Play Store search link, not an app page. Open the "
                "specific app in the Play Store and copy that URL - it should "
                "look like https://play.google.com/store/apps/details?id=com.example.app"
            )
    raise ValueError(
        "Could not resolve a Play Store app id. Paste the app's Play Store URL "
        "(https://play.google.com/store/apps/details?id=...) or the package id "
        "itself (e.g. com.application.zomato)."
    )


@with_retry_and_timeout(
    timeout_seconds=FETCH_TIMEOUT_SECONDS,
    max_attempts=MAX_FETCH_ATTEMPTS,
    base_delay_seconds=RETRY_BASE_DELAY_SECONDS,
)
async def _fetch_app_details(package_id: str) -> dict:
    return await asyncio.to_thread(gps_app, package_id)


@with_retry_and_timeout(
    timeout_seconds=FETCH_TIMEOUT_SECONDS,
    max_attempts=MAX_FETCH_ATTEMPTS,
    base_delay_seconds=RETRY_BASE_DELAY_SECONDS,
)
async def _fetch_reviews(package_id: str, count: int) -> list[dict]:
    reviews_list, _ = await asyncio.to_thread(gps_reviews, package_id, sort=Sort.NEWEST, count=count)
    return reviews_list


@with_retry_and_timeout(
    timeout_seconds=FETCH_TIMEOUT_SECONDS,
    max_attempts=MAX_FETCH_ATTEMPTS,
    base_delay_seconds=RETRY_BASE_DELAY_SECONDS,
)
async def _fetch_permissions(package_id: str) -> dict[str, list[str]]:
    return await asyncio.to_thread(gps_permissions, package_id)


def _compute_rating_distribution(histogram: list[int] | None) -> dict[str, int]:
    if not histogram or len(histogram) < 5:
        return {}
    return {str(star): int(histogram[star - 1]) for star in range(1, 6)}


def _compute_keyword_density(description: str, category: str | None) -> dict[str, float]:
    words = re.findall(r"[a-zA-Z']+", description.lower())
    total_words = len(words) or 1

    keywords = list(GENERIC_KEYWORDS)
    if category:
        for key, terms in CATEGORY_KEYWORDS.items():
            if key in category.lower():
                keywords = terms + keywords
                break

    density: dict[str, float] = {}
    for keyword in keywords:
        count = words.count(keyword.lower())
        if count > 0:
            density[keyword] = round(count / total_words, 4)
    return density


def _has_faq_content(description: str) -> bool:
    if "faq" in description.lower() or "frequently asked" in description.lower():
        return True
    question_lines = sum(1 for line in description.splitlines() if line.strip().endswith("?"))
    return question_lines >= 2


def _days_since(updated_unix_ts: int | None) -> int | None:
    if not updated_unix_ts:
        return None
    updated_at = datetime.fromtimestamp(updated_unix_ts, tz=timezone.utc)
    return (datetime.now(timezone.utc) - updated_at).days


async def audit_play_store_listing(
    product_id: int, play_store_url: str | None, package_name: str | None, category: str | None
) -> tuple[PlayStoreAuditOutput, list[dict], str | None]:
    """Fetch a Play Store listing + recent reviews and compute derived,
    non-AI signals.

    Inputs: product_id, play_store_url and/or package_name, category hint.
    Outputs: (`PlayStoreAuditOutput`, raw review dicts to persist, full
    description text). Always returns rather than raising - failures are
    reflected via `status=FAILED` and `error_message`.
    """
    try:
        package_id = extract_package_name(play_store_url, package_name)
    except ValueError as exc:
        return (
            PlayStoreAuditOutput(product_id=product_id, status=IngestionStatus.FAILED, error_message=str(exc)),
            [],
            None,
        )

    try:
        details = await _fetch_app_details(package_id)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never raise past this point
        logger.error(f"Play Store details fetch failed for product_id={product_id} pkg={package_id}: {exc!r}")
        return (
            PlayStoreAuditOutput(
                product_id=product_id, status=IngestionStatus.FAILED, error_message=str(exc)
            ),
            [],
            None,
        )

    raw_reviews: list[dict] = []
    reviews_error: str | None = None
    try:
        raw_reviews = await _fetch_reviews(package_id, REVIEWS_TO_FETCH)
    except Exception as exc:  # noqa: BLE001 - listing details still useful even if reviews fail
        logger.warning(f"Play Store reviews fetch failed for product_id={product_id} pkg={package_id}: {exc!r}")
        reviews_error = str(exc)

    permission_groups: dict[str, list[str]] = {}
    try:
        permission_groups = await _fetch_permissions(package_id)
    except Exception as exc:  # noqa: BLE001 - permissions are optional metadata
        logger.debug(f"Play Store permissions fetch failed for product_id={product_id} pkg={package_id}: {exc!r}")

    permissions_flat = sorted({perm for perms in permission_groups.values() for perm in perms})

    full_description = details.get("description") or ""
    resolved_category = category or details.get("genre")

    output = PlayStoreAuditOutput(
        product_id=product_id,
        status=IngestionStatus.PARTIAL if reviews_error else IngestionStatus.SUCCESS,
        app_title=details.get("title"),
        short_description=details.get("summary"),
        rating=details.get("score"),
        rating_count=details.get("ratings"),
        rating_distribution=_compute_rating_distribution(details.get("histogram")),
        category=resolved_category,
        store_last_updated=details.get("lastUpdatedOn"),
        current_version=details.get("version"),
        installs=details.get("installs"),
        permissions=permissions_flat,
        description_word_count=len(full_description.split()),
        has_faq_content=_has_faq_content(full_description),
        keyword_density=_compute_keyword_density(full_description, resolved_category),
        days_since_update=_days_since(details.get("updated")),
        reviews_fetched_count=len(raw_reviews),
        error_message=reviews_error,
    )
    return output, raw_reviews, full_description


def persist_play_store_data(
    db: Session, output: PlayStoreAuditOutput, full_description: str | None, raw_reviews: list[dict]
) -> PlayStoreData:
    """Upsert the `play_store_data` row and insert new `reviews` rows.

    Inputs: db session, audit output, full description text (not part of
    the output schema to keep API responses light), raw review dicts.
    Outputs: the persisted `PlayStoreData` ORM row.
    """
    row = db.query(PlayStoreData).filter(PlayStoreData.product_id == output.product_id).first()
    if row is None:
        row = PlayStoreData(product_id=output.product_id)
        db.add(row)

    row.app_title = output.app_title
    row.short_description = output.short_description
    row.full_description = full_description
    row.rating = output.rating
    row.rating_count = output.rating_count
    row.rating_distribution = output.rating_distribution
    row.category = output.category
    row.store_last_updated = output.store_last_updated
    row.current_version = output.current_version
    row.installs = output.installs
    row.permissions = output.permissions
    row.description_word_count = output.description_word_count
    row.has_faq_content = output.has_faq_content
    row.keyword_density = output.keyword_density
    row.days_since_update = output.days_since_update
    row.reviews_fetched_count = output.reviews_fetched_count
    row.status = output.status
    row.error_message = output.error_message
    row.fetched_at = datetime.utcnow()

    existing_review_texts = {
        r.review_text
        for r in db.query(Review)
        .filter(Review.product_id == output.product_id, Review.source == "play_store")
        .all()
    }
    for raw in raw_reviews:
        content = raw.get("content")
        if not content or content in existing_review_texts:
            continue
        db.add(
            Review(
                product_id=output.product_id,
                source="play_store",
                rating=float(raw["score"]) if raw.get("score") is not None else None,
                review_text=content,
                review_date=raw.get("at"),
                sentiment_label=None,
            )
        )
        existing_review_texts.add(content)

    db.commit()
    db.refresh(row)
    return row
