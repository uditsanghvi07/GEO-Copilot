"""Review Intelligence agent - implements `BaseAgent`, delegating to
`service.py` and the shared `llm_client` for all LLM calls."""

from loguru import logger

from app.agents.base import BaseAgent
from app.agents.reviews.service import analyze_product_reviews
from app.database.session import SessionLocal
from app.models.common_enums import IngestionStatus
from app.schemas.review_intelligence import ReviewAnalyzeInput, ReviewAnalyzeOutput
from app.utils.exceptions import AgentExecutionError


class ReviewIntelligenceAgent(BaseAgent[ReviewAnalyzeInput, ReviewAnalyzeOutput]):
    """Analyzes stored product reviews via batched map/reduce LLM calls to
    produce a merged intelligence summary (complaints, feature requests,
    themes, sentiment score)."""

    @property
    def name(self) -> str:
        return "review_intelligence"

    async def run(self, input_data: ReviewAnalyzeInput) -> ReviewAnalyzeOutput:
        """Analyze all unanalyzed reviews for `input_data.product_id`.

        Inputs: `ReviewAnalyzeInput`.
        Outputs: `ReviewAnalyzeOutput`.
        Raises: `AgentExecutionError` only on total failure (no reviews or
        all batches failed). Zero reviews returns gracefully via output status.
        """
        db = SessionLocal()
        try:
            output = await analyze_product_reviews(db, input_data.product_id)
        finally:
            db.close()

        if output.status == IngestionStatus.FAILED and output.reviews_analyzed_count == 0:
            if output.message and "Not enough data" in output.message:
                logger.info(
                    f"[{self.name}] product_id={input_data.product_id}: {output.message}"
                )
                return output
            logger.warning(
                f"[{self.name}] analysis failed for product_id={input_data.product_id}: "
                f"{output.error_message}"
            )
            raise AgentExecutionError(output.error_message or "Review analysis failed")

        return output
