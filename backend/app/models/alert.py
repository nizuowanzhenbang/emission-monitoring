"""超标告警 + 处置闭环模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AlertSeverity(str, enum.Enum):
    GENERAL = "GENERAL"     # 超限
    SEVERE = "SEVERE"       # 超限 ≥1.5×
    ESCALATED = "ESCALATED" # 持续 30 分钟升级


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"   # 已确认
    HANDLING = "HANDLING"           # 处置中
    RESOLVED = "RESOLVED"           # 已解决
    CLOSED = "CLOSED"               # 已归档


class EmissionAlert(Base):
    __tablename__ = "emission_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_no = Column(String(50), unique=True, index=True, nullable=False, comment="AL-YYYYMMDD-NNNN")
    point_id = Column(Integer, ForeignKey("emission_points.id"), nullable=False, index=True)
    reading_id = Column(Integer, ForeignKey("emission_readings.id"), nullable=True, comment="触发告警的首个读数")

    severity = Column(Enum(AlertSeverity), default=AlertSeverity.GENERAL, nullable=False, index=True)
    status = Column(Enum(AlertStatus), default=AlertStatus.OPEN, nullable=False, index=True)
    indicators = Column(String(100), nullable=False, comment="超标指标 SO2/NOX/DUST 逗号分隔")
    peak_so2 = Column(Float, nullable=True)
    peak_nox = Column(Float, nullable=True)
    peak_dust = Column(Float, nullable=True)
    description = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=False, comment="超标开始时间")
    ended_at = Column(DateTime, nullable=True, comment="超标结束时间（恢复达标）")
    duration_minutes = Column(Integer, default=0, comment="持续分钟数（实时更新）")

    acknowledged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    handled_by = Column(String(50), nullable=True)
    handle_notes = Column(Text, nullable=True, comment="处置措施")
    handled_at = Column(DateTime, nullable=True)
    resolution = Column(String(200), nullable=True, comment="原因 + 整改结果")
    closed_by = Column(String(50), nullable=True)
    closed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    point = relationship("EmissionPoint", back_populates="alerts")
    reading = relationship("EmissionReading")
