"""Core reporting logic: compile data, render Jinja2 HTML, persist report."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger
from sqlalchemy.orm import Session

from app.models.audit_report import AuditReport
from app.models.common_enums import IngestionStatus
from app.models.comparison_summary import ComparisonSummary
from app.models.generated_content import GeneratedContent
from app.models.product import Product
from app.models.report import Report
from app.models.review_summary import ReviewSummary
from app.schemas.reporting import ReportGenerateInput, ReportGenerateOutput

REPORTS_DIR = Path("reports")
TEMPLATE_DIR = Path(__file__).parent / "templates"


def export_pdf_stub(html_path: str) -> None:
    """STUB: Future ReportLab PDF export.

    Replace this function with ReportLab (or similar) to generate a PDF
    from the rendered HTML report. The HTML file at `html_path` is the
    source of truth until PDF export is implemented.
    """
    logger.debug(
        f"[PDF STUB] PDF export not implemented. HTML report available at: {html_path}. "
        f"Wire ReportLab here when ready."
    )


def _gather_report_context(db: Session, product_id: int) -> dict:
    """Collect all data needed for the HTML report template."""
    product = db.query(Product).filter(Product.id == product_id).first()

    audit = (
        db.query(AuditReport)
        .filter(AuditReport.product_id == product_id)
        .order_by(AuditReport.created_at.desc())
        .first()
    )

    review_summary = (
        db.query(ReviewSummary)
        .filter(ReviewSummary.product_id == product_id, ReviewSummary.status == IngestionStatus.SUCCESS)
        .order_by(ReviewSummary.created_at.desc())
        .first()
    )

    comparison = (
        db.query(ComparisonSummary)
        .filter(
            ComparisonSummary.product_id == product_id,
            ComparisonSummary.status.in_([IngestionStatus.SUCCESS, IngestionStatus.PARTIAL]),
        )
        .order_by(ComparisonSummary.created_at.desc())
        .first()
    )

    content_rows = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.product_id == product_id)
        .order_by(GeneratedContent.created_at.desc())
        .limit(10)
        .all()
    )

    action_plan = []
    if audit and audit.recommendations:
        action_plan = audit.recommendations.get("action_plan", [])

    return {
        "product_name": product.name if product else f"Product {product_id}",
        "generated_at": datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
            "%d %b %Y, %I:%M %p IST"
        ),
        "geo_score": audit.geo_score if audit else None,
        "score_breakdown": audit.score_breakdown if audit else {},
        "action_plan": action_plan,
        "review_summary": review_summary,
        "comparison": comparison,
        "generated_content": [
            {
                "content_type": row.content_type.value,
                "preview": row.content_body[:500] + ("..." if len(row.content_body) > 500 else ""),
            }
            for row in content_rows
        ],
    }


def generate_report(db: Session, input_data: ReportGenerateInput) -> ReportGenerateOutput:
    """Render an HTML audit report and persist it.

    Inputs: db session, ReportGenerateInput.
    Outputs: ReportGenerateOutput.
    """
    context = _gather_report_context(db, input_data.product_id)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("audit_report.html.j2")
    html = template.render(**context)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"report_{input_data.product_id}_{timestamp}.html"
    file_path = REPORTS_DIR / filename
    file_path.write_text(html, encoding="utf-8")

    export_pdf_stub(str(file_path))

    row = Report(
        product_id=input_data.product_id,
        file_path=str(file_path),
        pipeline_run_id=input_data.pipeline_run_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    logger.info(f"Report generated for product_id={input_data.product_id} at {file_path}")

    return ReportGenerateOutput(
        product_id=input_data.product_id,
        report_id=row.id,
        file_path=str(file_path),
    )
