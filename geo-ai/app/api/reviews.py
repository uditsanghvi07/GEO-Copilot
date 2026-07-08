"""Review Intelligence API routes - thin controllers only."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.reviews.agent import ReviewIntelligenceAgent
from app.database.session import get_db
from app.models.common_enums import IngestionStatus
from app.models.product import Product
from app.models.review import Review
from app.models.review_summary import ReviewSummary
from app.schemas.review_intelligence import (
    RatingDistribution,
    ReviewAnalyzeInput,
    ReviewAnalyzeJobAck,
    ReviewAnalyzeRequest,
    ReviewSummaryRead,
    SentimentCounts,
)

router = APIRouter(tags=["reviews"])

_agent = ReviewIntelligenceAgent()


async def _run_analyze_job(product_id: int) -> None:
    """Background task entrypoint for review analysis."""
    result = await _agent.execute(ReviewAnalyzeInput(product_id=product_id))
    if result.success:
        logger.info(f"[review analyze job] product_id={product_id} finished status={result.data.status}")
    else:
        logger.warning(f"[review analyze job] product_id={product_id} failed: {result.error_message}")


@router.post("/reviews/analyze", response_model=ReviewAnalyzeJobAck, status_code=status.HTTP_202_ACCEPTED)
async def trigger_review_analysis(
    payload: ReviewAnalyzeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> ReviewAnalyzeJobAck:
    """Start review intelligence analysis in the background. Poll
    `GET /reviews/summary/{product_id}` for the merged summary."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    review_count = db.query(Review).filter(Review.product_id == product.id).count()
    if review_count == 0:
        return ReviewAnalyzeJobAck(
            product_id=product.id,
            status="not_enough_data",
            message="Not enough data: no reviews found for this product. "
            "Run POST /playstore-audit first to fetch reviews.",
        )

    row = db.query(ReviewSummary).filter(ReviewSummary.product_id == product.id).first()
    if row is None:
        row = ReviewSummary(product_id=product.id, status=IngestionStatus.RUNNING)
        db.add(row)
    else:
        row.status = IngestionStatus.RUNNING
        row.error_message = None
    db.commit()

    background_tasks.add_task(_run_analyze_job, product.id)

    return ReviewAnalyzeJobAck(
        product_id=product.id,
        status=IngestionStatus.RUNNING.value,
        message="Review analysis started in the background. Poll GET /reviews/summary/{product_id}.",
    )


@router.get("/reviews/summary/{product_id}", response_model=ReviewSummaryRead)
async def get_review_summary(product_id: int, db: Session = Depends(get_db)) -> ReviewSummaryRead:
    """Return the latest merged review intelligence summary for a product,
    enriched with a live rating/sentiment distribution from stored reviews."""
    row = (
        db.query(ReviewSummary)
        .filter(ReviewSummary.product_id == product_id)
        .order_by(ReviewSummary.created_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review analysis has been run yet for this product. "
            "Trigger POST /reviews/analyze first.",
        )
    if row.status == IngestionStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Review analysis is still running. Poll again shortly.",
        )

    # Live rating distribution + sentiment buckets from the actual reviews.
    rating_rows = (
        db.query(Review.rating, func.count(Review.id))
        .filter(Review.product_id == product_id, Review.rating.isnot(None))
        .group_by(Review.rating)
        .all()
    )
    dist = RatingDistribution()
    sentiment = SentimentCounts()
    total = 0
    weighted_sum = 0.0
    bucket_by_star = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    for rating_value, count in rating_rows:
        star = int(round(rating_value))
        star = max(1, min(5, star))
        setattr(dist, bucket_by_star[star], getattr(dist, bucket_by_star[star]) + count)
        total += count
        weighted_sum += star * count
        if star >= 4:
            sentiment.positive += count
        elif star == 3:
            sentiment.neutral += count
        else:
            sentiment.negative += count

    average_rating = round(weighted_sum / total, 2) if total else None

    return ReviewSummaryRead(
        id=row.id,
        product_id=row.product_id,
        top_complaints=row.top_complaints,
        top_feature_requests=row.top_feature_requests,
        positive_themes=row.positive_themes,
        negative_themes=row.negative_themes,
        overall_sentiment_score=row.overall_sentiment_score,
        reviews_analyzed_count=row.reviews_analyzed_count,
        batches_processed=row.batches_processed,
        batches_failed=row.batches_failed,
        status=row.status,
        error_message=row.error_message,
        created_at=row.created_at,
        total_reviews=total,
        average_rating=average_rating,
        rating_distribution=dist,
        sentiment_counts=sentiment,
    )
