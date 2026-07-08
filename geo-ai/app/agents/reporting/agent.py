"""Reporting agent - compiles and renders HTML audit reports."""

from app.agents.base import BaseAgent
from app.agents.reporting.service import generate_report
from app.database.session import SessionLocal
from app.schemas.reporting import ReportGenerateInput, ReportGenerateOutput


class ReportingAgent(BaseAgent[ReportGenerateInput, ReportGenerateOutput]):
    """Compiles GEO score, action plan, reviews, competitors, and content
    into a single HTML report using Jinja2 templates."""

    @property
    def name(self) -> str:
        return "reporting"

    async def run(self, input_data: ReportGenerateInput) -> ReportGenerateOutput:
        db = SessionLocal()
        try:
            return generate_report(db, input_data)
        finally:
            db.close()
