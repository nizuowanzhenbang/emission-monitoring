"""排放标准配置模型"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, Text, Boolean
from app.database import Base


class StandardType(str, enum.Enum):
    GB13223_NORMAL = "GB13223_NORMAL"     # 标准 GB13223-2011
    GB13223_KEY = "GB13223_KEY"           # 重点地区
    ULTRA_LOW = "ULTRA_LOW"               # 超低排放
    PROVINCIAL = "PROVINCIAL"             # 地方标准
    CUSTOM = "CUSTOM"


class EmissionStandard(Base):
    """每个排放口可绑定一个标准；不绑时默认走 settings.LIMIT_*"""
    __tablename__ = "emission_standards"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    standard_type = Column(Enum(StandardType), default=StandardType.ULTRA_LOW, nullable=False)

    limit_so2 = Column(Float, nullable=False, comment="SO2 限值（mg/Nm³，折算后）")
    limit_nox = Column(Float, nullable=False)
    limit_dust = Column(Float, nullable=False)
    limit_co = Column(Float, nullable=True)
    reference_o2 = Column(Float, default=6.0, comment="基准氧 %")

    effective_from = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
