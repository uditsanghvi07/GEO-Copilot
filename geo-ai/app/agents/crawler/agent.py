"""Website Crawler agent - implements `BaseAgent`, delegating all crawling
and persistence logic to `service.py`."""

from loguru import logger

from app.agents.base import BaseAgent
from app.agents.crawler.service import crawl_website, persist_website_data
from app.database.session import SessionLocal
from app.models.common_enums import IngestionStatus
from app.schemas.crawler import WebsiteCrawlInput, WebsiteCrawlOutput
from app.utils.exceptions import AgentExecutionError


class WebsiteCrawlerAgent(BaseAgent[WebsiteCrawlInput, WebsiteCrawlOutput]):
    """Crawls a product's website and extracts AI-discoverability signals
    (headings, FAQ presence, schema.org markup, word count, link/image
    hygiene, freshness signal)."""

    @property
    def name(self) -> str:
        return "website_crawler"

    async def run(self, input_data: WebsiteCrawlInput) -> WebsiteCrawlOutput:
        """Crawl `input_data.website_url` and persist the result to the
        `website_data` table for `input_data.product_id`.

        Inputs: `WebsiteCrawlInput`.
        Outputs: `WebsiteCrawlOutput`.
        Raises: `AgentExecutionError` only when the crawl fails completely
        (no page could be loaded at all) - a partial crawl (e.g. homepage OK,
        FAQ page blocked) is returned normally with `status=PARTIAL` so the
        Orchestrator can record it as a partial failure rather than aborting.
        """
        output = await crawl_website(input_data.product_id, input_data.website_url)

        db = SessionLocal()
        try:
            persist_website_data(db, output)
            from app.services.rag_ingestion import ingest_product_content

            ingest_product_content(db, input_data.product_id)
        finally:
            db.close()

        if output.status == IngestionStatus.PARTIAL:
            logger.info(
                f"[{self.name}] partial crawl for product_id={input_data.product_id} "
                f"({len(output.crawled_pages)} page(s), {len(output.failed_pages)} skipped)"
            )
        elif output.status == IngestionStatus.FAILED:
            logger.warning(
                f"[{self.name}] crawl failed for product_id={input_data.product_id}: "
                f"{output.error_message}"
            )
            raise AgentExecutionError(output.error_message or "Website crawl failed")

        return output
