"""Core review intelligence logic: batching, LLM map/reduce, persistence."""

from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

from app.agents.reviews.constants import (
    CHARS_PER_TOKEN_ESTIMATE,
    MAX_BATCH_INPUT_TOKENS,
    MAX_BATCH_SIZE,
    MIN_BATCH_SIZE,
    TARGET_BATCH_SIZE,
)
from app.agents.reviews.prompts import (
    BATCH_ANALYSIS_SYSTEM_PROMPT,
    REDUCE_SUMMARY_SYSTEM_PROMPT,
    build_batch_user_prompt,
    build_reduce_user_prompt,
)
from app.models.common_enums import IngestionStatus
from app.models.review import Review
from app.models.review_summary import ReviewSummary
from app.schemas.review_intelligence import (
    BatchReviewAnalysis,
    MergedReviewSummary,
    ReviewAnalyzeOutput,
)
from app.services.llm_client import llm_client
from app.utils.exceptions import ExternalServiceError


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def _format_review_line(review: Review) -> str:
    rating = review.rating if review.rating is not None else "?"
    text = (review.review_text or "").strip().replace("\n", " ")
    return f"[{rating}] {text}"


def chunk_reviews(reviews: list[Review]) -> list[list[Review]]:
    """Split reviews into batches of ~40-50, respecting a conservative token budget.

    Inputs: list of Review ORM objects.
    Outputs: list of batches, each batch a list of Review objects.
    """
    batches: list[list[Review]] = []
    current_batch: list[Review] = []
    current_tokens = 0

    for review in reviews:
        line = _format_review_line(review)
        line_tokens = _estimate_tokens(line)

        would_exceed_tokens = current_tokens + line_tokens > MAX_BATCH_INPUT_TOKENS
        would_exceed_count = len(current_batch) >= MAX_BATCH_SIZE

        if current_batch and (would_exceed_tokens or would_exceed_count):
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(review)
        current_tokens += line_tokens

        if len(current_batch) >= TARGET_BATCH_SIZE and current_tokens >= MAX_BATCH_INPUT_TOKENS // 2:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

    if current_batch:
        batches.append(current_batch)

    # Merge tiny trailing batches into the previous one when possible.
    if len(batches) >= 2 and len(batches[-1]) < MIN_BATCH_SIZE:
        tail = batches.pop()
        combined_tokens = sum(_estimate_tokens(_format_review_line(r)) for r in batches[-1] + tail)
        if combined_tokens <= MAX_BATCH_INPUT_TOKENS and len(batches[-1]) + len(tail) <= MAX_BATCH_SIZE:
            batches[-1].extend(tail)
        else:
            batches.append(tail)

    return batches


async def _analyze_batch(
    batch: list[Review], batch_index: int, batch_total: int
) -> BatchReviewAnalysis | None:
    """Run the map-step LLM call for one batch. Returns None on failure."""
    reviews_text = "\n".join(_format_review_line(r) for r in batch)
    messages = [
        {"role": "system", "content": BATCH_ANALYSIS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_batch_user_prompt(reviews_text, batch_index, batch_total),
        },
    ]
    try:
        return await llm_client.chat_completion_json(messages, BatchReviewAnalysis)
    except ExternalServiceError as exc:
        logger.error(f"Batch {batch_index}/{batch_total} LLM call failed: {exc!r}")
        return None


async def _reduce_batches(batch_outputs: list[dict]) -> MergedReviewSummary | None:
    """Run the reduce-step LLM call. Returns None on failure."""
    messages = [
        {"role": "system", "content": REDUCE_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": build_reduce_user_prompt(batch_outputs)},
    ]
    try:
        return await llm_client.chat_completion_json(messages, MergedReviewSummary)
    except ExternalServiceError as exc:
        logger.error(f"Reduce-step LLM call failed: {exc!r}")
        return None


async def analyze_product_reviews(db: Session, product_id: int) -> ReviewAnalyzeOutput:
    """Pull unanalyzed reviews, run map/reduce LLM pipeline, persist summary.

    Inputs: db session, product_id.
    Outputs: ReviewAnalyzeOutput — never raises; failures reflected in status.
    """
    unanalyzed = (
        db.query(Review)
        .filter(Review.product_id == product_id, Review.is_analyzed.is_(False))
        .order_by(Review.fetched_at.asc())
        .all()
    )

    if not unanalyzed:
        all_reviews = db.query(Review).filter(Review.product_id == product_id).count()
        if all_reviews == 0:
            _upsert_summary_placeholder(
                db,
                product_id,
                status=IngestionStatus.FAILED,
                error_message="Not enough data: no reviews found for this product. "
                "Run POST /playstore-audit first.",
            )
            return ReviewAnalyzeOutput(
                product_id=product_id,
                status=IngestionStatus.FAILED,
                error_message="Not enough data: no reviews found for this product.",
                message="Not enough data: run POST /playstore-audit first to fetch reviews.",
            )
        latest = (
            db.query(ReviewSummary)
            .filter(ReviewSummary.product_id == product_id)
            .order_by(ReviewSummary.created_at.desc())
            .first()
        )
        if latest and latest.status == IngestionStatus.SUCCESS:
            return ReviewAnalyzeOutput(
                product_id=product_id,
                status=IngestionStatus.SUCCESS,
                reviews_analyzed_count=latest.reviews_analyzed_count,
                batches_processed=latest.batches_processed,
                batches_failed=latest.batches_failed,
                summary=MergedReviewSummary(
                    top_complaints=latest.top_complaints,
                    top_feature_requests=latest.top_feature_requests,
                    positive_themes=latest.positive_themes,
                    negative_themes=latest.negative_themes,
                    overall_sentiment_score=latest.overall_sentiment_score or 0.0,
                ),
                message="All reviews already analyzed.",
            )
        return ReviewAnalyzeOutput(
            product_id=product_id,
            status=IngestionStatus.FAILED,
            message="No unanalyzed reviews found.",
        )

    batches = chunk_reviews(unanalyzed)
    batch_total = len(batches)
    successful_outputs: list[dict] = []
    batches_failed = 0

    for idx, batch in enumerate(batches, start=1):
        result = await _analyze_batch(batch, idx, batch_total)
        if result is None:
            batches_failed += 1
            continue
        successful_outputs.append(result.model_dump())

    if not successful_outputs:
        _upsert_summary_placeholder(
            db,
            product_id,
            status=IngestionStatus.FAILED,
            error_message="All batch LLM calls failed.",
            batches_processed=0,
            batches_failed=batches_failed,
        )
        return ReviewAnalyzeOutput(
            product_id=product_id,
            status=IngestionStatus.FAILED,
            batches_failed=batches_failed,
            error_message="All batch LLM calls failed.",
        )

    merged = await _reduce_batches(successful_outputs)
    if merged is None:
        status = IngestionStatus.PARTIAL
        error_message = "Reduce-step LLM call failed; per-batch outputs saved."
        merged = MergedReviewSummary()
    else:
        status = IngestionStatus.PARTIAL if batches_failed > 0 else IngestionStatus.SUCCESS
        error_message = (
            f"{batches_failed} batch(es) failed during map step." if batches_failed > 0 else None
        )

    review_ids = [r.id for r in unanalyzed]
    db.query(Review).filter(Review.id.in_(review_ids)).update(
        {Review.is_analyzed: True}, synchronize_session=False
    )

    row = _persist_summary(
        db,
        product_id=product_id,
        merged=merged,
        reviews_analyzed_count=len(unanalyzed),
        batches_processed=len(successful_outputs),
        batches_failed=batches_failed,
        batch_outputs=successful_outputs,
        status=status,
        error_message=error_message,
    )

    return ReviewAnalyzeOutput(
        product_id=product_id,
        status=row.status,
        reviews_analyzed_count=row.reviews_analyzed_count,
        batches_processed=row.batches_processed,
        batches_failed=row.batches_failed,
        summary=merged,
        error_message=row.error_message,
    )


def _upsert_summary_placeholder(
    db: Session,
    product_id: int,
    *,
    status: IngestionStatus,
    error_message: str | None = None,
    batches_processed: int = 0,
    batches_failed: int = 0,
) -> ReviewSummary:
    row = db.query(ReviewSummary).filter(ReviewSummary.product_id == product_id).first()
    if row is None:
        row = ReviewSummary(product_id=product_id)
        db.add(row)
    row.status = status
    row.error_message = error_message
    row.batches_processed = batches_processed
    row.batches_failed = batches_failed
    db.commit()
    db.refresh(row)
    return row


def _persist_summary(
    db: Session,
    *,
    product_id: int,
    merged: MergedReviewSummary,
    reviews_analyzed_count: int,
    batches_processed: int,
    batches_failed: int,
    batch_outputs: list[dict],
    status: IngestionStatus,
    error_message: str | None,
) -> ReviewSummary:
    row = db.query(ReviewSummary).filter(ReviewSummary.product_id == product_id).first()
    if row is None:
        row = ReviewSummary(product_id=product_id)
        db.add(row)

    row.top_complaints = merged.top_complaints[:10]
    row.top_feature_requests = merged.top_feature_requests[:10]
    row.positive_themes = merged.positive_themes[:5]
    row.negative_themes = merged.negative_themes[:5]
    row.overall_sentiment_score = merged.overall_sentiment_score
    row.reviews_analyzed_count = reviews_analyzed_count
    row.batches_processed = batches_processed
    row.batches_failed = batches_failed
    row.batch_outputs = batch_outputs
    row.status = status
    row.error_message = error_message
    row.created_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row
