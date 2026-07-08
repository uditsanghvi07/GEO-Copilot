"""Audit agent - rule-based GEO scoring + LLM action plan."""

from app.agents.audit.service import run_audit
from app.agents.base import BaseAgent
from app.database.session import SessionLocal
from app.schemas.audit import AuditInput, AuditOutput


class AuditAgent(BaseAgent[AuditInput, AuditOutput]):
    """Computes a rule-based GEO Score and generates a prioritized action plan."""

    @property
    def name(self) -> str:
        return "audit"

    async def run(self, input_data: AuditInput) -> AuditOutput:
        db = SessionLocal()
        try:
            return await run_audit(db, input_data.product_id)
        finally:
            db.close()
