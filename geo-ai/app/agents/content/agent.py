"""Content Generation agent - RAG-grounded content via shared llm_client."""

from app.agents.base import BaseAgent
from app.agents.content.service import generate_content
from app.database.session import SessionLocal
from app.schemas.content import ContentGenerateInput, ContentGenerateOutput


class ContentGenerationAgent(BaseAgent[ContentGenerateInput, ContentGenerateOutput]):
    """Generates AI-discoverability content grounded in product RAG context."""

    @property
    def name(self) -> str:
        return "content_generation"

    async def run(self, input_data: ContentGenerateInput) -> ContentGenerateOutput:
        db = SessionLocal()
        try:
            return await generate_content(db, input_data)
        finally:
            db.close()
