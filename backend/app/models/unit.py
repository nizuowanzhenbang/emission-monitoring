"""发电机组 + 排放口模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class UnitStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    STANDBY = "STANDBY"
    OUTAGE = "OUTAGE"            # 检修停机
    DECOMMISSIONED = "DECOMMISSIONED"


class FuelType(str, enum.Enum):
    COAL = "COAL"                # 燃煤
    GAS = "GAS"                  # 燃气
    OIL = "OIL"                  # 燃油
    BIOMASS = "BIOMASS"


class Unit(Base):
    """发电机组（一台机组通常对应若干排放口）"""
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="UNIT-N")
    name = Column(String(100), nullable=False)
    capacity_mw = Column(Float, nullable=False, comment="装机容量（MW）")
    fuel_type = Column(Enum(FuelType), default=FuelType.COAL, nullable=False)
    status = Column(Enum(UnitStatus), default=UnitStatus.RUNNING, nullable=False, index=True)
    commission_date = Column(DateTime, nullable=True, comment="投产日期")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    points = relationship("EmissionPoint", back_populates="unit", cascade="all, delete-orphan")


class PointCategory(str, enum.Enum):
    STACK = "STACK"                  # 烟囱出口（最终排放）
    PRE_DESULFUR = "PRE_DESULFUR"    # 脱硫前
    POST_DESULFUR = "POST_DESULFUR"  # 脱硫后
    PRE_DENOX = "PRE_DENOX"          # 脱硝前
    POST_DENOX = "POST_DENOX"        # 脱硝后


class EmissionPoint(Base):
    """排放口（机组上的一个采样点位）"""
    __tablename__ = "emission_points"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="EP-U{N}-NNN")
    name = Column(String(100), nullable=False, comment="排放口名称")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    category = Column(Enum(PointCategory), nullable=False, comment="测点类别")
    location = Column(String(100), nullable=True)
    standard_id = Column(Integer, ForeignKey("emission_standards.id"), nullable=True, comment="所适用排放标准")
    is_compliance_point = Column(Boolean, default=True, comment="是否合规上报口（烟囱出口）")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    unit = relationship("Unit", back_populates="points")
    standard = relationship("EmissionStandard")
    devices = relationship("CemsDevice", back_populates="point", cascade="all, delete-orphan")
    readings = relationship("EmissionReading", back_populates="point", cascade="all, delete-orphan")
    alerts = relationship("EmissionAlert", back_populates="point", cascade="all, delete-orphan")
