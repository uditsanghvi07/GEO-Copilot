"""Audit API routes - thin controllers only."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.audit.agent import AuditAgent
from app.database.session import get_db
from app.models.audit_report import AuditReport
from app.models.product import Product
from app.schemas.audit import AuditInput, AuditRequest, AuditResponse
from app.utils.exceptions import AgentExecutionError

router = APIRouter(tags=["audit"])

_agent = AuditAgent()


@router.get("/audit/{product_id}", response_model=AuditResponse)
async def get_latest_audit(product_id: int, db: Session = Depends(get_db)) -> AuditReport:
    """Return the latest audit report for a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    report = (
        db.query(AuditReport)
        .filter(AuditReport.product_id == product_id)
        .order_by(AuditReport.created_at.desc())
        .first()
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audit report yet. Run a full audit or POST /audit first.",
        )
    return report


@router.post("/audit", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
async def run_audit(payload: AuditRequest, db: Session = Depends(get_db)) -> AuditReport:
    """Run the Audit Agent: rule-based GEO score + LLM action plan."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    result = await _agent.execute(AuditInput(product_id=payload.product_id))
    if not result.success:
        detail = result.error_message or "Audit failed"
        if "Run POST /crawl" in detail or "Run POST /playstore-audit" in detail or "No ingestion data" in detail:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

    report = db.query(AuditReport).filter(AuditReport.id == result.data.audit_report_id).first()
    return report
