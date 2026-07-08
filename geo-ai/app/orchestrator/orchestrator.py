"""Complete Orchestrator - sequences all agents for a full audit pipeline."""

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.agents.audit.agent import AuditAgent
from app.agents.competitor.agent import CompetitorAgent
from app.agents.content.agent import ContentGenerationAgent
from app.agents.crawler.agent import WebsiteCrawlerAgent
from app.agents.playstore.agent import PlayStoreAnalyzerAgent
from app.agents.reporting.agent import ReportingAgent
from app.agents.reviews.agent import ReviewIntelligenceAgent
from app.database.session import SessionLocal
from app.models.common_enums import IngestionStatus
from app.models.generated_content import ContentType
from app.models.pipeline_run import PipelineRun, PipelineRunStatus
from app.models.product import Product
from app.schemas.audit import AuditInput
from app.schemas.common import AgentResult
from app.schemas.competitor import CompareInput
from app.schemas.content import ContentGenerateInput
from app.schemas.crawler import WebsiteCrawlInput
from app.schemas.playstore import PlayStoreAuditInput
from app.schemas.reporting import ReportGenerateInput
from app.schemas.review_intelligence import ReviewAnalyzeInput


class Orchestrator:
    """Coordinates the full audit pipeline across all specialized agents.

    Pipeline order:
    1. Website Crawler + Play Store Analyzer (concurrent, independent)
    2. Review Intelligence Agent
    3. Audit Agent (rule-based GEO score + action plan)
    4. Competitor Agent (optional, if competitor_urls provided)
    5. Content Generation (faq + meta_description minimum)
    6. Reporting Agent (HTML report, always runs)
    """

    def __init__(self) -> None:
        self._crawler = WebsiteCrawlerAgent()
        self._playstore = PlayStoreAnalyzerAgent()
        self._reviews = ReviewIntelligenceAgent()
        self._audit = AuditAgent()
        self._competitor = CompetitorAgent()
        self._content = ContentGenerationAgent()
        self._reporting = ReportingAgent()

    async def run_full_pipeline(
        self, pipeline_run_id: int, product_id: int, competitor_urls: list[str] | None = None
    ) -> None:
        """Execute the full pipeline, updating the PipelineRun record as stages complete.

        Inputs: pipeline_run_id, product_id, optional competitor_urls.
        Outputs: none (persists stage statuses on PipelineRun).
        """
        competitor_urls = competitor_urls or []
        db = SessionLocal()
        run = None
        try:
            run = db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
            product = db.query(Product).filter(Product.id == product_id).first()
            if run is None or product is None:
                logger.error(f"Pipeline run {pipeline_run_id} or product {product_id} not found")
                return

            run.status = PipelineRunStatus.RUNNING
            run.competitor_urls = competitor_urls
            db.commit()

            stage_statuses: dict[str, Any] = {}

            # --- Stage 1: Concurrent ingestion (crawler + playstore) ---
            ingestion_tasks = []
            if product.website_url:
                ingestion_tasks.append(
                    self._run_stage(
                        "website_crawler",
                        self._crawler.execute(
                            WebsiteCrawlInput(product_id=product_id, website_url=product.website_url)
                        ),
                    )
                )
            else:
                stage_statuses["website_crawler"] = {
                    "status": "skipped",
                    "duration_ms": 0,
                    "error_message": "No website_url configured",
                }

            if product.play_store_url:
                ingestion_tasks.append(
                    self._run_stage(
                        "play_store_analyzer",
                        self._playstore.execute(
                            PlayStoreAuditInput(
                                product_id=product_id,
                                play_store_url=product.play_store_url,
                                category=product.category,
                            )
                        ),
                    )
                )
            else:
                stage_statuses["play_store_analyzer"] = {
                    "status": "skipped",
                    "duration_ms": 0,
                    "error_message": "No play_store_url configured",
                }

            if ingestion_tasks:
                results = await asyncio.gather(*ingestion_tasks)
                for name, stage_result in results:
                    stage_statuses[name] = self._stage_to_dict(stage_result)

            self._persist_stages(db, run, stage_statuses)

            # --- Stage 2: Review Intelligence ---
            name, review_result = await self._run_stage(
                "review_intelligence",
                self._reviews.execute(ReviewAnalyzeInput(product_id=product_id)),
            )
            stage_statuses[name] = self._stage_to_dict(review_result)
            self._persist_stages(db, run, stage_statuses)

            # --- Stage 3: Audit ---
            name, audit_result = await self._run_stage(
                "audit", self._audit.execute(AuditInput(product_id=product_id))
            )
            stage_statuses[name] = self._stage_to_dict(audit_result)
            self._persist_stages(db, run, stage_statuses)

            # --- Stage 4: Competitor (optional) ---
            if competitor_urls:
                name, comp_result = await self._run_stage(
                    "competitor",
                    self._competitor.execute(
                        CompareInput(product_id=product_id, competitor_urls=competitor_urls)
                    ),
                )
                stage_statuses[name] = self._stage_to_dict(comp_result)
            else:
                stage_statuses["competitor"] = {
                    "status": "skipped",
                    "duration_ms": 0,
                    "error_message": "No competitor URLs provided",
                }
            self._persist_stages(db, run, stage_statuses)

            # --- Stage 5: Content Generation (faq + meta_description) ---
            for content_type, stage_key in [
                (ContentType.FAQ, "content_faq"),
                (ContentType.META_DESCRIPTION, "content_meta_description"),
            ]:
                name, content_result = await self._run_stage(
                    stage_key,
                    self._content.execute(
                        ContentGenerateInput(product_id=product_id, content_type=content_type)
                    ),
                )
                stage_statuses[name] = self._stage_to_dict(content_result)
                self._persist_stages(db, run, stage_statuses)

            # --- Stage 6: Reporting (always runs) ---
            name, report_result = await self._run_stage(
                "reporting",
                self._reporting.execute(
                    ReportGenerateInput(product_id=product_id, pipeline_run_id=pipeline_run_id)
                ),
            )
            stage_statuses[name] = self._stage_to_dict(report_result)
            self._finalize_run(db, run, stage_statuses)

            logger.info(
                f"Pipeline run {pipeline_run_id} completed with status={run.status.value}"
            )
            self._log_email_stub(product, run)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Pipeline run {pipeline_run_id} crashed: {exc!r}")
            if run is not None:
                run.status = PipelineRunStatus.FAILED
                run.error_message = str(exc)
                run.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    async def _run_stage(self, stage_name: str, coro) -> tuple[str, AgentResult]:
        """Run a single stage and log outcome."""
        logger.info(f"[pipeline] running stage '{stage_name}'")
        result = await coro
        if result.success:
            logger.info(f"[pipeline] stage '{stage_name}' succeeded in {result.duration_ms:.2f}ms")
        else:
            logger.warning(
                f"[pipeline] stage '{stage_name}' failed: {result.error_message} - continuing"
            )
        return stage_name, result

    def _stage_to_dict(self, result: AgentResult) -> dict[str, Any]:
        if result.success:
            status = "success"
            if result.data is not None and getattr(result.data, "status", None) == IngestionStatus.PARTIAL:
                status = "partial"
        elif result.error_message and "not enough data" in (result.error_message or "").lower():
            status = "partial"
        else:
            status = "failed"
        partial_note = None
        if status == "partial" and result.data is not None:
            failed_pages = getattr(result.data, "failed_pages", None) or []
            if failed_pages:
                partial_note = failed_pages[0].reason if hasattr(failed_pages[0], "reason") else failed_pages[0].get("reason")
        return {
            "status": status,
            "duration_ms": result.duration_ms,
            "error_message": result.error_message or partial_note,
        }

    def _persist_stages(self, db: Session, run: PipelineRun, stage_statuses: dict) -> None:
        run.stage_statuses = dict(stage_statuses)
        db.commit()

    def _finalize_run(self, db: Session, run: PipelineRun, stage_statuses: dict) -> None:
        run.stage_statuses = stage_statuses
        run.completed_at = datetime.utcnow()

        statuses = [s.get("status") for s in stage_statuses.values()]
        if all(s in ("success", "skipped") for s in statuses):
            run.status = PipelineRunStatus.SUCCESS
        elif any(s == "success" for s in statuses) and any(s == "failed" for s in statuses):
            run.status = PipelineRunStatus.PARTIAL
        elif all(s == "failed" for s in statuses):
            run.status = PipelineRunStatus.FAILED
        else:
            run.status = PipelineRunStatus.PARTIAL

        db.commit()

    def _log_email_stub(self, product: Product, run: PipelineRun) -> None:
        """STUB: log where a real SMTP email would be sent with the report summary."""
        reporting = run.stage_statuses.get("reporting", {})
        logger.info(
            f"[EMAIL STUB] Would send audit report email for product '{product.name}' "
            f"(product_id={product.id}, pipeline_run_id={run.id}, "
            f"status={run.status.value}, reporting={reporting.get('status')}). "
            f"Replace Orchestrator._log_email_stub with real SMTP integration."
        )


def create_pipeline_run(db: Session, product_id: int, competitor_urls: list[str]) -> PipelineRun:
    """Create a new PipelineRun record in PENDING state."""
    run = PipelineRun(
        product_id=product_id,
        status=PipelineRunStatus.PENDING,
        competitor_urls=competitor_urls,
        stage_statuses={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
