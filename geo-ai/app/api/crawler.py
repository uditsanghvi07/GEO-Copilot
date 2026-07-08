"""Website Crawler API routes - thin controllers only, no business logic."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.crawler.agent import WebsiteCrawlerAgent
from app.database.session import get_db
from app.models.common_enums import IngestionStatus
from app.models.product import Product
from app.models.website_data import WebsiteData
from app.schemas.crawler import CrawlJobAck, CrawlRequest, CrawlStatusResponse, WebsiteCrawlInput

router = APIRouter(tags=["crawler"])

_agent = WebsiteCrawlerAgent()


async def _run_crawl_job(product_id: int, website_url: str) -> None:
    """Background task entrypoint. All persistence (success or failure)
    happens inside the agent itself; this just logs the final outcome."""
    result = await _agent.execute(WebsiteCrawlInput(product_id=product_id, website_url=website_url))
    if result.success:
        logger.info(f"[crawl job] product_id={product_id} finished with status={result.data.status}")
    else:
        logger.warning(f"[crawl job] product_id={product_id} failed: {result.error_message}")


@router.post("/crawl", response_model=CrawlJobAck, status_code=status.HTTP_202_ACCEPTED)
async def trigger_crawl(
    payload: CrawlRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> CrawlJobAck:
    """Start a website crawl for a product in the background and return a
    job reference immediately. Poll `GET /crawl/status/{product_id}` for
    the result."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.website_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Product has no website_url configured"
        )

    row = db.query(WebsiteData).filter(WebsiteData.product_id == product.id).first()
    if row is None:
        row = WebsiteData(product_id=product.id, status=IngestionStatus.RUNNING)
        db.add(row)
    else:
        row.status = IngestionStatus.RUNNING
        row.error_message = None
    db.commit()

    background_tasks.add_task(_run_crawl_job, product.id, product.website_url)

    return CrawlJobAck(
        product_id=product.id,
        status=IngestionStatus.RUNNING.value,
        message="Website crawl started in the background. Poll GET /crawl/status/{product_id}.",
    )


@router.get("/crawl/status/{product_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(product_id: int, db: Session = Depends(get_db)) -> CrawlStatusResponse:
    """Return the latest `website_data` row status for a product."""
    row = db.query(WebsiteData).filter(WebsiteData.product_id == product_id).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No crawl has been run yet for this product"
        )
    return CrawlStatusResponse(
        product_id=row.product_id,
        status=row.status,
        title=row.title,
        meta_description=row.meta_description,
        has_faq=row.has_faq,
        has_schema_markup=row.has_schema_markup,
        word_count=row.word_count,
        schema_types=row.schema_types,
        failed_pages=row.failed_pages,
        error_message=row.error_message,
        last_crawled_at=row.last_crawled_at,
    )
