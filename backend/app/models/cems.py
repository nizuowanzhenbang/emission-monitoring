"""CEMS 监测仪表模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class CemsStatus(str, enum.Enum):
    ONLINE = "ONLINE"           # 在线
    OFFLINE = "OFFLINE"         # 离线
    CALIBRATING = "CALIBRATING" # 校准中（数据 INVALID）
    FAULT = "FAULT"             # 故障


class CemsDevice(Base):
    """CEMS（连续排放监测系统）仪表 - 每个排放口对应 1 套或多套"""
    __tablename__ = "cems_devices"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="CEMS-NNNN")
    name = Column(String(100), nullable=False)
    point_id = Column(Integer, ForeignKey("emission_points.id"), nullable=False, index=True)

    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_no = Column(String(100), nullable=True)
    install_date = Column(Date, nullable=True)
    last_calibration_at = Column(DateTime, nullable=True, comment="上次校准时间")
    next_calibration_at = Column(DateTime, nullable=True, comment="下次校准时间（日校）")

    status = Column(Enum(CemsStatus), default=CemsStatus.ONLINE, nullable=False, index=True)
    is_certified = Column(Boolean, default=True, comment="是否在检定有效期内")
    certification_expiry = Column(Date, nullable=True, comment="检定/校验有效期")

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    point = relationship("EmissionPoint", back_populates="devices")
