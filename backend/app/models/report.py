"""排放报表模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, JSON
from app.database import Base


class ReportType(str, enum.Enum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    AD_HOC = "AD_HOC"


class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class EmissionReport(Base):
    __tablename__ = "emission_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_no = Column(String(50), unique=True, index=True, nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    title = Column(String(200), nullable=False)
    summary = Column(JSON, nullable=True, comment="结构化指标汇总")
    notes = Column(Text, nullable=True)

    status = Column(Enum(ReportStatus), default=ReportStatus.DRAFT, nullable=False, index=True)
    generated_by = Column(String(50), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    submitted_by = Column(String(50), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
