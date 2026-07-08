"""Play Store Analyzer agent - implements `BaseAgent`, delegating all
fetching, derived-signal computation, and persistence to `service.py`."""

from loguru import logger

from app.agents.base import BaseAgent
from app.agents.playstore.service import audit_play_store_listing, persist_play_store_data
from app.database.session import SessionLocal
from app.models.common_enums import IngestionStatus
from app.schemas.playstore import PlayStoreAuditInput, PlayStoreAuditOutput
from app.utils.exceptions import AgentExecutionError


class PlayStoreAnalyzerAgent(BaseAgent[PlayStoreAuditInput, PlayStoreAuditOutput]):
    """Fetches a product's Play Store listing + recent reviews and computes
    heuristic (non-AI) discoverability signals. Reviews are persisted raw
    for the Module 3 sentiment analysis agent to process later."""

    @property
    def name(self) -> str:
        return "play_store_analyzer"

    async def run(self, input_data: PlayStoreAuditInput) -> PlayStoreAuditOutput:
        """Audit `input_data`'s Play Store listing and persist the result.

        Inputs: `PlayStoreAuditInput`.
        Outputs: `PlayStoreAuditOutput`.
        Raises: `AgentExecutionError` only when the listing itself could not
        be fetched at all (invalid package id, app not found, network
        failure after retries) - a successful listing fetch with a failed
        reviews fetch is returned normally with `status=PARTIAL`.
        """
        output, raw_reviews, full_description = await audit_play_store_listing(
            product_id=input_data.product_id,
            play_store_url=input_data.play_store_url,
            package_name=input_data.package_name,
            category=input_data.category,
        )

        db = SessionLocal()
        try:
            persist_play_store_data(db, output, full_description, raw_reviews)
            from app.services.rag_ingestion import ingest_product_content

            ingest_product_content(db, input_data.product_id)
        finally:
            db.close()

        if output.status == IngestionStatus.FAILED:
            logger.warning(
                f"[{self.name}] audit failed for product_id={input_data.product_id}: "
                f"{output.error_message}"
            )
            raise AgentExecutionError(output.error_message or "Play Store audit failed")

        return output
