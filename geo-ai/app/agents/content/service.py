"""Core content generation logic: RAG retrieval + LLM generation."""

from loguru import logger
from sqlalchemy.orm import Session

from app.agents.content.prompts import PROMPTS_BY_TYPE, build_user_prompt
from app.models.generated_content import ContentType, GeneratedContent
from app.schemas.content import ContentGenerateInput, ContentGenerateOutput
from app.services.llm_client import llm_client
from app.services.rag_retrieval import retrieve_relevant_chunks
from app.utils.exceptions import AgentExecutionError
from app.vector_db.collection_service import collection_has_documents


def _retrieval_query(content_type: ContentType, extra: str | None) -> str:
    base = content_type.value.replace("_", " ")
    if extra:
        return f"{base} {extra}"
    return base


async def generate_content(db: Session, input_data: ContentGenerateInput) -> ContentGenerateOutput:
    """Retrieve RAG chunks and generate content for a product.

    Inputs: db session, ContentGenerateInput.
    Outputs: ContentGenerateOutput.
    Raises: AgentExecutionError if no ingested content in ChromaDB.
    """
    if not collection_has_documents(input_data.product_id):
        raise AgentExecutionError(
            "No ingested content found for this product. Run POST /crawl and "
            "POST /playstore-audit first to populate the RAG index."
        )

    query = _retrieval_query(input_data.content_type, input_data.extra_instructions)
    chunks = retrieve_relevant_chunks(input_data.product_id, query, top_k=5)

    if not chunks:
        raise AgentExecutionError(
            "RAG retrieval returned no chunks. Run POST /crawl first to ingest product content."
        )

    system_prompt = PROMPTS_BY_TYPE.get(
        input_data.content_type.value, "Generate helpful product content."
    )
    user_prompt = build_user_prompt(
        input_data.content_type.value, chunks, input_data.extra_instructions
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    content_body = await llm_client.chat_completion(messages, temperature=0.4, max_tokens=2000)

    row = GeneratedContent(
        product_id=input_data.product_id,
        content_type=input_data.content_type,
        content_body=content_body,
        prompt_used=user_prompt[:4000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    logger.info(
        f"Generated {input_data.content_type.value} for product_id={input_data.product_id} "
        f"using {len(chunks)} chunks"
    )

    return ContentGenerateOutput(
        product_id=input_data.product_id,
        content_type=input_data.content_type,
        content_body=content_body,
        generated_content_id=row.id,
        chunks_used=len(chunks),
    )
