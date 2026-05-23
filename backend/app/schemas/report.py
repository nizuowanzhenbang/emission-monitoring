"""报表 schemas"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict

from app.models.report import ReportType, ReportStatus


class ReportGenerate(BaseModel):
    report_type: ReportType
    period_start: datetime
    period_end: datetime
    title: Optional[str] = None
    notes: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    report_no: str
    report_type: ReportType
    period_start: datetime
    period_end: datetime
    title: str
    summary: Any
    notes: Optional[str]
    status: ReportStatus
    generated_by: Optional[str]
    generated_at: datetime
    submitted_by: Optional[str]
    submitted_at: Optional[datetime]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
