"""Pure, rule-based GEO Score computation shared by Audit and Competitor agents.

No LLM calls here — scoring is deterministic from stored signals only.
Authority proxy: we do not have backlink data in the MVP, so
`internal_links_count` from the website crawl is used as a site-structure
authority proxy (more internal cross-linking suggests a richer, more
discoverable content graph for AI crawlers to traverse).
"""

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class ScoreComponent(BaseModel):
    """One scored component with its max cap and earned points."""

    max_points: int
    earned: float
    details: str = ""


class GeoScoreBreakdown(BaseModel):
    """Full GEO score breakdown — components sum to at most 100."""

    documentation_depth: ScoreComponent
    faq_presence: ScoreComponent
    metadata_quality: ScoreComponent
    structured_data: ScoreComponent
    authority_signals: ScoreComponent
    review_quality: ScoreComponent
    freshness: ScoreComponent
    total: int = Field(ge=0, le=100)

    def to_dict(self) -> dict:
        return {
            "documentation_depth": self.documentation_depth.model_dump(),
            "faq_presence": self.faq_presence.model_dump(),
            "metadata_quality": self.metadata_quality.model_dump(),
            "structured_data": self.structured_data.model_dump(),
            "authority_signals": self.authority_signals.model_dump(),
            "review_quality": self.review_quality.model_dump(),
            "freshness": self.freshness.model_dump(),
            "total": self.total,
        }


@dataclass
class GeoScoringSignals:
    """All inputs needed for a single GEO score computation."""

    word_count: int = 0
    crawled_pages: list[dict] = field(default_factory=list)
    has_faq: bool = False
    faq_count: int = 0
    meta_description: str | None = None
    schema_types: list[str] = field(default_factory=list)
    internal_links_count: int = 0
    avg_review_rating: float | None = None
    review_count: int = 0
    days_since_update: int | None = None
    last_updated_signal: str | None = None
    play_store_description_word_count: int = 0


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_documentation_depth(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 20 points — help/docs/blog pages + word count."""
    max_pts = 20
    roles = {p.get("role", "") for p in signals.crawled_pages}
    has_docs = bool(roles & {"faq", "blog", "help", "docs"})
    page_bonus = 8 if has_docs else 0
    word_score = _clamp(signals.word_count / 2000) * 12
    earned = min(max_pts, page_bonus + word_score)
    return ScoreComponent(
        max_points=max_pts,
        earned=round(earned, 1),
        details=f"pages={list(roles)}, word_count={signals.word_count}",
    )


def score_faq_presence(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 15 points — has_faq flag + FAQ entry count."""
    max_pts = 15
    if not signals.has_faq and signals.faq_count == 0:
        return ScoreComponent(max_points=max_pts, earned=0, details="no FAQ detected")
    base = 6 if signals.has_faq else 0
    count_score = _clamp(signals.faq_count / 10) * 9
    earned = min(max_pts, base + count_score)
    return ScoreComponent(
        max_points=max_pts,
        earned=round(earned, 1),
        details=f"has_faq={signals.has_faq}, faq_count={signals.faq_count}",
    )


def score_metadata_quality(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 10 points — meta description presence + healthy length (50-160)."""
    max_pts = 10
    desc = (signals.meta_description or "").strip()
    if not desc:
        return ScoreComponent(max_points=max_pts, earned=0, details="missing meta description")
    length = len(desc)
    if 50 <= length <= 160:
        earned = max_pts
        detail = f"length={length} (optimal)"
    elif length < 50:
        earned = _clamp(length / 50) * max_pts
        detail = f"length={length} (too short)"
    else:
        earned = max(4, max_pts - (length - 160) * 0.05)
        detail = f"length={length} (too long)"
    return ScoreComponent(max_points=max_pts, earned=round(min(max_pts, earned), 1), details=detail)


def score_structured_data(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 20 points — Organization/Product/FAQPage schema types."""
    max_pts = 20
    types = {t.lower() for t in signals.schema_types}
    points = 0.0
    if "organization" in types:
        points += 6
    if "product" in types or "softwareapplication" in types:
        points += 7
    if "faqpage" in types:
        points += 7
    other_bonus = min(3, len(types - {"organization", "product", "softwareapplication", "faqpage"}) * 1)
    earned = min(max_pts, points + other_bonus)
    return ScoreComponent(
        max_points=max_pts,
        earned=round(earned, 1),
        details=f"schema_types={signals.schema_types}",
    )


def score_authority_signals(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 10 points — internal_links_count as authority proxy (no backlink API)."""
    max_pts = 10
    links = signals.internal_links_count
    earned = _clamp(links / 50) * max_pts
    return ScoreComponent(
        max_points=max_pts,
        earned=round(earned, 1),
        details=f"internal_links_count={links} (proxy for site-structure authority)",
    )


def score_review_quality(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 15 points — average rating + review volume."""
    max_pts = 15
    if signals.review_count == 0 or signals.avg_review_rating is None:
        return ScoreComponent(max_points=max_pts, earned=0, details="no reviews")
    rating_score = _clamp(signals.avg_review_rating / 5.0) * 10
    volume_score = _clamp(signals.review_count / 100) * 5
    earned = min(max_pts, rating_score + volume_score)
    return ScoreComponent(
        max_points=max_pts,
        earned=round(earned, 1),
        details=f"avg_rating={signals.avg_review_rating:.2f}, count={signals.review_count}",
    )


def score_freshness(signals: GeoScoringSignals) -> ScoreComponent:
    """Up to 10 points — recency of site/listing updates."""
    max_pts = 10
    if signals.days_since_update is not None:
        if signals.days_since_update <= 30:
            earned = max_pts
        elif signals.days_since_update <= 90:
            earned = 7
        elif signals.days_since_update <= 180:
            earned = 4
        else:
            earned = 1
        detail = f"days_since_update={signals.days_since_update}"
    elif signals.last_updated_signal:
        earned = 5
        detail = f"last_updated_signal={signals.last_updated_signal}"
    else:
        earned = 0
        detail = "no freshness signal"
    return ScoreComponent(max_points=max_pts, earned=round(earned, 1), details=detail)


def compute_geo_score(signals: GeoScoringSignals) -> GeoScoreBreakdown:
    """Compute the full GEO score breakdown from signals.

    Inputs: GeoScoringSignals dataclass.
    Outputs: GeoScoreBreakdown with total 0-100.
    """
    components = [
        score_documentation_depth(signals),
        score_faq_presence(signals),
        score_metadata_quality(signals),
        score_structured_data(signals),
        score_authority_signals(signals),
        score_review_quality(signals),
        score_freshness(signals),
    ]
    total = int(round(min(100, sum(c.earned for c in components))))
    return GeoScoreBreakdown(
        documentation_depth=components[0],
        faq_presence=components[1],
        metadata_quality=components[2],
        structured_data=components[3],
        authority_signals=components[4],
        review_quality=components[5],
        freshness=components[6],
        total=total,
    )


def signals_from_crawl_output(
    *,
    word_count: int = 0,
    crawled_pages: list | None = None,
    has_faq: bool = False,
    faq_count: int = 0,
    meta_description: str | None = None,
    schema_types: list | None = None,
    internal_links_count: int = 0,
    last_updated_signal: str | None = None,
    avg_review_rating: float | None = None,
    review_count: int = 0,
    days_since_update: int | None = None,
    play_store_description_word_count: int = 0,
) -> GeoScoringSignals:
    """Build GeoScoringSignals from raw crawl/audit dicts or ORM fields."""
    return GeoScoringSignals(
        word_count=word_count,
        crawled_pages=crawled_pages or [],
        has_faq=has_faq,
        faq_count=faq_count,
        meta_description=meta_description,
        schema_types=schema_types or [],
        internal_links_count=internal_links_count,
        last_updated_signal=last_updated_signal,
        avg_review_rating=avg_review_rating,
        review_count=review_count,
        days_since_update=days_since_update,
        play_store_description_word_count=play_store_description_word_count,
    )
