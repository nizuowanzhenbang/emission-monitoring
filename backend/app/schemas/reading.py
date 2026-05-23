"""读数 schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.models.reading import ReadingValidity


class ReadingIn(BaseModel):
    """单条原始读数（实测值，折算由服务端完成）"""
    point_id: int
    cems_id: Optional[int] = None
    measured_at: datetime
    so2: Optional[float] = None
    nox: Optional[float] = None
    dust: Optional[float] = None
    co: Optional[float] = None
    o2: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    flow: Optional[float] = None
    velocity: Optional[float] = None
    validity: ReadingValidity = ReadingValidity.VALID


class ReadingBatch(BaseModel):
    """批量接收（实际生产由 OPC/Modbus 适配器推送）"""
    readings: List[ReadingIn]


class ReadingResponse(BaseModel):
    id: int
    point_id: int
    cems_id: Optional[int]
    measured_at: datetime
    so2: Optional[float]
    nox: Optional[float]
    dust: Optional[float]
    co: Optional[float]
    o2: Optional[float]
    temperature: Optional[float]
    humidity: Optional[float]
    flow: Optional[float]
    velocity: Optional[float]
    so2_corrected: Optional[float]
    nox_corrected: Optional[float]
    dust_corrected: Optional[float]
    validity: ReadingValidity
    severity: Optional[str]
    exceeded: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
