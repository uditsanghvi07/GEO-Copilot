"""Reporting agent input/output schemas."""

from pydantic import BaseModel


class ReportGenerateInput(BaseModel):
    """Typed input accepted by `ReportingAgent.run()`."""

    product_id: int
    pipeline_run_id: int | None = None


class ReportGenerateOutput(BaseModel):
    """Typed output returned by `ReportingAgent.run()`."""

    product_id: int
    report_id: int
    file_path: str
