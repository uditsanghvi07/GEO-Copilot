"""Competitor agent - crawl, score, and compare against competitors."""

from app.agents.base import BaseAgent
from app.agents.competitor.service import run_competitor_comparison
from app.database.session import SessionLocal
from app.schemas.competitor import CompareInput, CompareOutput


class CompetitorAgent(BaseAgent[CompareInput, CompareOutput]):
    """Crawls competitor sites, scores them, and generates a comparison."""

    @property
    def name(self) -> str:
        return "competitor"

    async def run(self, input_data: CompareInput) -> CompareOutput:
        db = SessionLocal()
        try:
            return await run_competitor_comparison(
                db, input_data.product_id, input_data.competitor_urls
            )
        finally:
            db.close()
