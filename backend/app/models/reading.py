"""时序读数模型 - CEMS 分钟级数据"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class ReadingValidity(str, enum.Enum):
    VALID = "VALID"              # 有效（折算后入合规均值）
    INVALID = "INVALID"          # 无效（仪表故障/异常值）
    CALIBRATING = "CALIBRATING"  # 校准期数据（无效但已记录）
    SUBSTITUTED = "SUBSTITUTED"  # 替代值（按规范替代填补）


class EmissionReading(Base):
    """分钟级 CEMS 读数。

    实测列 + 折算列分开，折算字段在写入时一次性算好，避免取均值时反复计算。
    """
    __tablename__ = "emission_readings"

    id = Column(Integer, primary_key=True, index=True)
    point_id = Column(Integer, ForeignKey("emission_points.id"), nullable=False, index=True)
    cems_id = Column(Integer, ForeignKey("cems_devices.id"), nullable=True, index=True)
    measured_at = Column(DateTime, nullable=False, index=True, comment="采样时间（建议分钟整点）")

    # ── 实测污染物浓度（mg/Nm³）──
    so2 = Column(Float, nullable=True)
    nox = Column(Float, nullable=True)
    dust = Column(Float, nullable=True)
    co = Column(Float, nullable=True)

    # ── 烟气参数 ──
    o2 = Column(Float, nullable=True, comment="氧含量 %")
    temperature = Column(Float, nullable=True, comment="烟温 ℃")
    humidity = Column(Float, nullable=True, comment="湿度 %")
    flow = Column(Float, nullable=True, comment="干基标态流量 Nm³/h")
    velocity = Column(Float, nullable=True, comment="烟气流速 m/s")

    # ── 折算到 6% 基准氧（mg/Nm³）──
    so2_corrected = Column(Float, nullable=True)
    nox_corrected = Column(Float, nullable=True)
    dust_corrected = Column(Float, nullable=True)

    validity = Column(Enum(ReadingValidity), default=ReadingValidity.VALID, nullable=False, index=True)
    severity = Column(String(20), nullable=True, comment="NORMAL / GENERAL / SEVERE")
    exceeded = Column(String(50), nullable=True, comment="超标指标列表（逗号分隔）")

    created_at = Column(DateTime, default=datetime.utcnow)

    point = relationship("EmissionPoint", back_populates="readings")
    cems = relationship("CemsDevice")

    __table_args__ = (
        Index("ix_reading_point_time", "point_id", "measured_at"),
    )
