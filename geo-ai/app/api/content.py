"""Content generation API routes - thin controllers only."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.content.agent import ContentGenerationAgent
from app.database.session import get_db
from app.models.generated_content import ContentType, GeneratedContent
from app.models.product import Product
from app.schemas.content import (
    ContentGenerateInput,
    GenerateBlogRequest,
    GenerateCampaignRequest,
    GenerateFaqRequest,
    GenerateMetaRequest,
    GeneratedContentRead,
)
from app.utils.exceptions import AgentExecutionError

router = APIRouter(tags=["content"])

_agent = ContentGenerationAgent()


def _handle_agent_result(result, detail_prefix: str = "Content generation failed"):
    if not result.success:
        detail = result.error_message or detail_prefix
        if "Run POST /crawl" in detail or "No ingested content" in detail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
    return result.data


@router.post("/generate-faq", response_model=GeneratedContentRead, status_code=status.HTTP_201_CREATED)
async def generate_faq(payload: GenerateFaqRequest, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.id == payload.product_id).first() is None:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await _agent.execute(
        ContentGenerateInput(product_id=payload.product_id, content_type=ContentType.FAQ)
    )
    data = _handle_agent_result(result)
    return db.query(GeneratedContent).filter(GeneratedContent.id == data.generated_content_id).first()


@router.post("/generate-blog", response_model=GeneratedContentRead, status_code=status.HTTP_201_CREATED)
async def generate_blog(payload: GenerateBlogRequest, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.id == payload.product_id).first() is None:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await _agent.execute(
        ContentGenerateInput(
            product_id=payload.product_id,
            content_type=ContentType.BLOG,
            extra_instructions=payload.topic_hint,
        )
    )
    data = _handle_agent_result(result)
    return db.query(GeneratedContent).filter(GeneratedContent.id == data.generated_content_id).first()


@router.post("/generate-meta", response_model=GeneratedContentRead, status_code=status.HTTP_201_CREATED)
async def generate_meta(payload: GenerateMetaRequest, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.id == payload.product_id).first() is None:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await _agent.execute(
        ContentGenerateInput(
            product_id=payload.product_id, content_type=ContentType.META_DESCRIPTION
        )
    )
    data = _handle_agent_result(result)
    return db.query(GeneratedContent).filter(GeneratedContent.id == data.generated_content_id).first()


@router.post("/generate-campaign", response_model=GeneratedContentRead, status_code=status.HTTP_201_CREATED)
async def generate_campaign(payload: GenerateCampaignRequest, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.id == payload.product_id).first() is None:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await _agent.execute(
        ContentGenerateInput(
            product_id=payload.product_id,
            content_type=ContentType.CAMPAIGN_BUNDLE,
            extra_instructions=payload.campaign_theme,
        )
    )
    data = _handle_agent_result(result)
    return db.query(GeneratedContent).filter(GeneratedContent.id == data.generated_content_id).first()


@router.get("/content/{product_id}", response_model=list[GeneratedContentRead])
async def list_generated_content(product_id: int, db: Session = Depends(get_db)) -> list[GeneratedContent]:
    """List all generated content for a product, most recent first."""
    return (
        db.query(GeneratedContent)
        .filter(GeneratedContent.product_id == product_id)
        .order_by(GeneratedContent.created_at.desc())
        .all()
    )
