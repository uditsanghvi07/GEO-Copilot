"""Core competitor comparison logic: crawl, score, LLM compare."""

import json
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.competitor.prompts import COMPARISON_SYSTEM_PROMPT, build_comparison_user_prompt
from app.agents.crawler.service import crawl_external_url
from app.agents.playstore.service import audit_play_store_listing
from app.models.audit_report import AuditReport
from app.models.common_enums import IngestionStatus
from app.models.comparison_summary import ComparisonSummary
from app.models.competitor import Competitor
from app.models.play_store_data import PlayStoreData
from app.models.product import Product
from app.models.review import Review
from app.models.website_data import WebsiteData
from app.schemas.competitor import CompareOutput, CompetitorComparisonResult
from app.schemas.crawler import WebsiteCrawlOutput
from app.schemas.playstore import PlayStoreAuditOutput
from app.services.geo_scoring_service import compute_geo_score, signals_from_crawl_output
from app.services.llm_client import llm_client


def _is_play_store_url(url: str) -> bool:
    """Return True when the URL points at a Google Play Store app listing."""
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    return "play.google.com" in host and "/store/apps/details" in parsed.path


def _competitor_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    return host.replace("www.", "") or "competitor"


def _crawl_output_to_signals(output: WebsiteCrawlOutput) -> dict:
    return {
        "title": output.title,
        "meta_description": output.meta_description,
        "has_faq": output.has_faq,
        "faq_count": output.faq_count,
        "schema_types": output.schema_types,
        "word_count": output.word_count,
        "internal_links_count": output.internal_links_count,
        "crawled_pages": [p.model_dump() for p in output.crawled_pages],
    }


def _play_store_output_to_signals(
    output: PlayStoreAuditOutput, raw_reviews: list[dict]
) -> dict:
    return {
        "source": "play_store",
        "app_title": output.app_title,
        "short_description": output.short_description,
        "has_faq": output.has_faq_content,
        "description_word_count": output.description_word_count,
        "rating": output.rating,
        "rating_count": output.rating_count,
        "reviews_fetched_count": output.reviews_fetched_count,
        "days_since_update": output.days_since_update,
        "store_last_updated": output.store_last_updated,
    }


def _review_stats_from_play_store(
    output: PlayStoreAuditOutput, raw_reviews: list[dict]
) -> tuple[float | None, int]:
    """Derive avg rating + review count for GEO scoring from Play Store data."""
    avg_rating = float(output.rating) if output.rating is not None else None
    review_count = int(output.rating_count or 0)

    if raw_reviews:
        scores = [float(r["score"]) for r in raw_reviews if r.get("score") is not None]
        if scores and avg_rating is None:
            avg_rating = sum(scores) / len(scores)
        if review_count == 0:
            review_count = len(raw_reviews)

    return avg_rating, review_count


def _score_crawl_output(output: WebsiteCrawlOutput) -> tuple[int, dict]:
    signals = signals_from_crawl_output(
        word_count=output.word_count,
        crawled_pages=[p.model_dump() for p in output.crawled_pages],
        has_faq=output.has_faq,
        faq_count=output.faq_count,
        meta_description=output.meta_description,
        schema_types=output.schema_types,
        internal_links_count=output.internal_links_count,
        last_updated_signal=output.last_updated_signal,
    )
    breakdown = compute_geo_score(signals)
    return breakdown.total, breakdown.to_dict()


def _score_play_store_output(
    output: PlayStoreAuditOutput, raw_reviews: list[dict]
) -> tuple[int, dict, dict]:
    """Score a Play Store competitor using listing metadata + reviews."""
    avg_rating, review_count = _review_stats_from_play_store(output, raw_reviews)
    signals = signals_from_crawl_output(
        word_count=output.description_word_count,
        crawled_pages=[{"role": "play_store", "url": "play_store_listing"}],
        has_faq=output.has_faq_content,
        faq_count=0,
        meta_description=output.short_description,
        schema_types=[],
        internal_links_count=0,
        last_updated_signal=output.store_last_updated,
        avg_review_rating=avg_rating,
        review_count=review_count,
        days_since_update=output.days_since_update,
        play_store_description_word_count=output.description_word_count,
    )
    breakdown = compute_geo_score(signals)
    return breakdown.total, breakdown.to_dict(), _play_store_output_to_signals(output, raw_reviews)


async def _get_our_product_data(db: Session, product_id: int) -> dict:
    product = db.query(Product).filter(Product.id == product_id).first()

    # Prefer the latest audit report as the single source of truth so the
    # competitor table, the Overview score ring, and the LLM narrative all
    # reference the exact same GEO score. The audit stage runs before the
    # competitor stage in the orchestrator, so this is normally available.
    latest_audit = (
        db.query(AuditReport)
        .filter(AuditReport.product_id == product_id)
        .order_by(AuditReport.created_at.desc())
        .first()
    )
    if latest_audit is not None and latest_audit.score_breakdown:
        return {
            "name": product.name if product else "",
            "geo_score": latest_audit.geo_score,
            "score_breakdown": latest_audit.score_breakdown,
            "signals": {},
        }

    # Fallback: recompute from raw signals if no audit report exists yet.
    website = db.query(WebsiteData).filter(WebsiteData.product_id == product_id).first()
    play_store = db.query(PlayStoreData).filter(PlayStoreData.product_id == product_id).first()
    review_stats = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.product_id == product_id)
        .one()
    )
    signals = signals_from_crawl_output(
        word_count=website.word_count if website else 0,
        crawled_pages=website.crawled_pages if website else [],
        has_faq=website.has_faq if website else False,
        faq_count=website.faq_count if website else 0,
        meta_description=website.meta_description if website else None,
        schema_types=website.schema_types if website else [],
        internal_links_count=website.internal_links_count if website else 0,
        last_updated_signal=website.last_updated_signal if website else None,
        avg_review_rating=float(review_stats[0]) if review_stats[0] else None,
        review_count=int(review_stats[1] or 0),
        days_since_update=play_store.days_since_update if play_store else None,
    )
    breakdown = compute_geo_score(signals)
    return {
        "name": product.name if product else "",
        "geo_score": breakdown.total,
        "score_breakdown": breakdown.to_dict(),
        "signals": signals.__dict__,
    }


async def run_competitor_comparison(
    db: Session, product_id: int, competitor_urls: list[str]
) -> CompareOutput:
    """Crawl competitors, score them, run LLM comparison.

    Inputs: db session, product_id, competitor_urls.
    Outputs: CompareOutput.
    """
    our_data = await _get_our_product_data(db, product_id)
    competitor_scores: list[dict] = []

    for url in competitor_urls:
        name = _competitor_name_from_url(url)
        row = (
            db.query(Competitor)
            .filter(Competitor.product_id == product_id, Competitor.competitor_url == url)
            .first()
        )
        if row is None:
            row = Competitor(product_id=product_id, competitor_name=name, competitor_url=url)
            db.add(row)
            db.commit()
            db.refresh(row)

        if _is_play_store_url(url):
            # Play Store listings must use the Play Store scraper — a website
            # crawl cannot read ratings, review volume, or update timestamps.
            ps_output, raw_reviews, _ = await audit_play_store_listing(
                product_id=0, play_store_url=url, package_name=None, category=None
            )
            if ps_output.status == IngestionStatus.FAILED:
                logger.warning(f"Play Store competitor fetch failed for {url}: {ps_output.error_message}")
                geo_score, breakdown = 0, {}
                signals = {"source": "play_store", "error": ps_output.error_message}
                display_name = name
            else:
                geo_score, breakdown, signals = _score_play_store_output(ps_output, raw_reviews)
                display_name = ps_output.app_title or name
                row.competitor_name = display_name
            notes = {
                "source": "play_store",
                "geo_score": geo_score,
                "title": ps_output.app_title,
                "rating": ps_output.rating,
                "rating_count": ps_output.rating_count,
                "has_faq": ps_output.has_faq_content,
            }
        else:
            crawl_output = await crawl_external_url(url, snapshot_key=f"competitor_{row.id}")
            geo_score, breakdown = _score_crawl_output(crawl_output)
            signals = _crawl_output_to_signals(crawl_output)
            display_name = crawl_output.title or name
            row.competitor_name = display_name
            notes = {
                "source": "website",
                "geo_score": geo_score,
                "title": crawl_output.title,
                "has_faq": crawl_output.has_faq,
            }

        row.geo_score = geo_score
        row.score_breakdown = breakdown
        row.crawl_signals = signals
        row.comparison_notes = json.dumps(notes)
        db.commit()

        competitor_scores.append(
            {
                "competitor_name": display_name,
                "competitor_url": url,
                "geo_score": geo_score,
                "score_breakdown": breakdown,
                "signals": signals,
            }
        )

    messages = [
        {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
        {"role": "user", "content": build_comparison_user_prompt(our_data, competitor_scores)},
    ]

    comparison: CompetitorComparisonResult | None = None
    error_message: str | None = None
    status = IngestionStatus.SUCCESS

    try:
        comparison = await llm_client.chat_completion_json(messages, CompetitorComparisonResult)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Competitor comparison LLM failed: {exc!r}")
        status = IngestionStatus.PARTIAL
        error_message = str(exc)
        comparison = CompetitorComparisonResult(
            missing_features=[],
            missing_faqs=[],
            improvement_plan=[],
            narrative_summary="Comparison LLM call failed.",
        )

    summary = db.query(ComparisonSummary).filter(ComparisonSummary.product_id == product_id).first()
    if summary is None:
        summary = ComparisonSummary(product_id=product_id)
        db.add(summary)

    summary.missing_features = comparison.missing_features
    summary.missing_faqs = comparison.missing_faqs
    summary.improvement_plan = comparison.improvement_plan
    summary.narrative_summary = comparison.narrative_summary
    summary.competitor_scores = competitor_scores
    summary.our_score = our_data.get("geo_score")
    summary.our_breakdown = our_data.get("score_breakdown")
    summary.status = status
    summary.error_message = error_message
    db.commit()

    return CompareOutput(
        product_id=product_id,
        status=status,
        comparison=comparison,
        competitor_scores=competitor_scores,
        error_message=error_message,
    )
