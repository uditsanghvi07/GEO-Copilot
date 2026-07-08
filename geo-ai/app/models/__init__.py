"""Import every ORM model module here so `Base.metadata` sees all tables
before `create_all()` runs. Do not remove imports even if they look unused."""

from app.models.audit_report import AuditReport
from app.models.common_enums import IngestionStatus
from app.models.comparison_summary import ComparisonSummary
from app.models.competitor import Competitor
from app.models.generated_content import ContentType, GeneratedContent
from app.models.pipeline_run import PipelineRun, PipelineRunStatus
from app.models.play_store_data import PlayStoreData
from app.models.product import Product
from app.models.report import Report
from app.models.review import Review
from app.models.review_summary import ReviewSummary
from app.models.user import User
from app.models.website_data import WebsiteData

__all__ = [
    "Product",
    "WebsiteData",
    "PlayStoreData",
    "Review",
    "ReviewSummary",
    "Competitor",
    "ComparisonSummary",
    "PipelineRun",
    "PipelineRunStatus",
    "Report",
    "AuditReport",
    "GeneratedContent",
    "ContentType",
    "IngestionStatus",
    "User",
]
