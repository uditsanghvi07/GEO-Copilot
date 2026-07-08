"""Core audit logic: signal gathering, rule-based scoring, LLM action plan."""

import json
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.audit.prompts import ACTION_PLAN_SYSTEM_PROMPT, build_action_plan_user_prompt
from app.models.audit_report import AuditReport
from app.models.common_enums import IngestionStatus
from app.models.play_store_data import PlayStoreData
from app.models.product import Product
from app.models.review import Review
from app.models.review_summary import ReviewSummary
from app.models.website_data import WebsiteData
from app.schemas.audit import ActionPlan, AuditOutput
from app.services.geo_scoring_service import compute_geo_score, signals_from_crawl_output
from app.services.llm_client import llm_client
from app.utils.exceptions import AgentExecutionError


def _require_ingestion_data(
    db: Session, product_id: int
) -> tuple[WebsiteData | None, PlayStoreData | None]:
    """Return available ingestion rows. At least one successful source is required."""
    website = db.query(WebsiteData).filter(WebsiteData.product_id == product_id).first()
    play_store = db.query(PlayStoreData).filter(PlayStoreData.product_id == product_id).first()

    website_ok = website is not None and website.status in (
        IngestionStatus.SUCCESS,
        IngestionStatus.PARTIAL,
    )
    play_store_ok = play_store is not None and play_store.status in (
        IngestionStatus.SUCCESS,
        IngestionStatus.PARTIAL,
    )

    if not website_ok and not play_store_ok:
        raise AgentExecutionError(
            "No ingestion data available. Run POST /crawl and/or "
            "POST /playstore-audit first for this product."
        )

    return (website if website_ok else None, play_store if play_store_ok else None)


def _build_scoring_signals(
    db: Session,
    product_id: int,
    website: WebsiteData | None,
    play_store: PlayStoreData | None,
):
    review_stats = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.product_id == product_id)
        .one()
    )
    avg_rating = float(review_stats[0]) if review_stats[0] is not None else None
    review_count = int(review_stats[1] or 0)

    crawled_pages = website.crawled_pages or [] if website else []
    word_count = (
        (website.word_count or 0)
        if website
        else (play_store.description_word_count or 0 if play_store else 0)
    )
    has_faq = website.has_faq if website else bool(play_store and play_store.has_faq_content)
    faq_count = (website.faq_count or 0) if website else 0
    meta_description = (
        website.meta_description
        if website
        else (play_store.short_description if play_store else None)
    )
    schema_types = website.schema_types or [] if website else []
    internal_links_count = (website.internal_links_count or 0) if website else 0
    last_updated_signal = website.last_updated_signal if website else None

    return signals_from_crawl_output(
        word_count=word_count,
        crawled_pages=crawled_pages,
        has_faq=has_faq,
        faq_count=faq_count,
        meta_description=meta_description,
        schema_types=schema_types,
        internal_links_count=internal_links_count,
        last_updated_signal=last_updated_signal,
        avg_review_rating=avg_rating,
        review_count=review_count,
        days_since_update=play_store.days_since_update if play_store else None,
        play_store_description_word_count=play_store.description_word_count if play_store else 0,
    )


async def _generate_action_plan(
    product_name: str, breakdown: dict, review_summary: ReviewSummary | None
) -> dict:
    review_dict = None
    if review_summary:
        review_dict = {
            "top_complaints": review_summary.top_complaints,
            "top_feature_requests": review_summary.top_feature_requests,
            "positive_themes": review_summary.positive_themes,
            "negative_themes": review_summary.negative_themes,
            "overall_sentiment_score": review_summary.overall_sentiment_score,
        }
    messages = [
        {"role": "system", "content": ACTION_PLAN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_action_plan_user_prompt(breakdown, review_dict, product_name),
        },
    ]
    try:
        plan = await llm_client.chat_completion_json(messages, ActionPlan)
        return plan.model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Action plan LLM call failed: {exc!r}")
        return {"action_plan": [], "error": str(exc)}


async def run_audit(db: Session, product_id: int) -> AuditOutput:
    """Compute GEO score and generate action plan for a product.

    Inputs: db session, product_id.
    Outputs: AuditOutput.
    Raises: AgentExecutionError if prerequisite ingestion data is missing.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise AgentExecutionError(f"Product {product_id} not found")

    website, play_store = _require_ingestion_data(db, product_id)
    signals = _build_scoring_signals(db, product_id, website, play_store)
    breakdown = compute_geo_score(signals)
    breakdown_dict = breakdown.to_dict()

    review_summary = (
        db.query(ReviewSummary)
        .filter(ReviewSummary.product_id == product_id, ReviewSummary.status == IngestionStatus.SUCCESS)
        .order_by(ReviewSummary.created_at.desc())
        .first()
    )

    recommendations = await _generate_action_plan(product.name, breakdown_dict, review_summary)

    report = AuditReport(
        product_id=product_id,
        geo_score=breakdown.total,
        score_breakdown=breakdown_dict,
        recommendations=recommendations,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return AuditOutput(
        product_id=product_id,
        geo_score=report.geo_score,
        score_breakdown=report.score_breakdown,
        recommendations=report.recommendations,
        audit_report_id=report.id,
    )
