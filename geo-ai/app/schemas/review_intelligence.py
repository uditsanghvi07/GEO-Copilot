"""Pydantic schemas for the Review Intelligence agent and its API routes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.common_enums import IngestionStatus
from app.schemas.common import ORMBase


class BatchReviewAnalysis(BaseModel):
    """Strict JSON schema returned by the per-batch LLM map step."""

    recurring_complaints: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    positive_themes: list[str] = Field(default_factory=list)
    negative_themes: list[str] = Field(default_factory=list)
    sentiment_lean: Literal["positive", "neutral", "negative"] = "neutral"


class MergedReviewSummary(BaseModel):
    """Strict JSON schema returned by the reduce LLM step."""

    top_complaints: list[str] = Field(default_factory=list, max_length=10)
    top_feature_requests: list[str] = Field(default_factory=list, max_length=10)
    positive_themes: list[str] = Field(default_factory=list)
    negative_themes: list[str] = Field(default_factory=list)
    overall_sentiment_score: float = Field(ge=-1.0, le=1.0, default=0.0)


class ReviewAnalyzeInput(BaseModel):
    """Typed input accepted by `ReviewIntelligenceAgent.run()`."""

    product_id: int


class ReviewAnalyzeOutput(BaseModel):
    """Typed output returned by `ReviewIntelligenceAgent.run()`."""

    product_id: int
    status: IngestionStatus
    reviews_analyzed_count: int = 0
    batches_processed: int = 0
    batches_failed: int = 0
    summary: MergedReviewSummary | None = None
    error_message: str | None = None
    message: str | None = None


class ReviewAnalyzeRequest(BaseModel):
    """Request body for POST /reviews/analyze."""

    product_id: int


class ReviewAnalyzeJobAck(BaseModel):
    """Immediate acknowledgement returned by POST /reviews/analyze."""

    product_id: int
    status: str
    message: str


class RatingDistribution(BaseModel):
    """Real star-rating breakdown for a product's reviews."""

    one: int = 0
    two: int = 0
    three: int = 0
    four: int = 0
    five: int = 0


class SentimentCounts(BaseModel):
    """Concrete review counts bucketed by rating: positive (4-5), neutral (3), negative (1-2)."""

    positive: int = 0
    neutral: int = 0
    negative: int = 0


class ReviewSummaryRead(ORMBase):
    """Output schema for GET /reviews/summary/{product_id}."""

    id: int
    product_id: int
    top_complaints: list[str]
    top_feature_requests: list[str]
    positive_themes: list[str]
    negative_themes: list[str]
    overall_sentiment_score: float | None
    reviews_analyzed_count: int
    batches_processed: int
    batches_failed: int
    status: IngestionStatus
    error_message: str | None
    created_at: datetime
    # Computed live from the reviews table (not stored on the summary row):
    total_reviews: int = 0
    average_rating: float | None = None
    rating_distribution: RatingDistribution = Field(default_factory=RatingDistribution)
    sentiment_counts: SentimentCounts = Field(default_factory=SentimentCounts)
