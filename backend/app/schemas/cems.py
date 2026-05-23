"""CEMS 设备 schemas"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.cems import CemsStatus


class CemsCreate(BaseModel):
    name: str
    point_id: int
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_no: Optional[str] = None
    install_date: Optional[date] = None
    certification_expiry: Optional[date] = None
    notes: Optional[str] = None


class CemsUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: Optional[CemsStatus] = None
    is_certified: Optional[bool] = None
    certification_expiry: Optional[date] = None
    last_calibration_at: Optional[datetime] = None
    next_calibration_at: Optional[datetime] = None
    notes: Optional[str] = None


class CemsResponse(BaseModel):
    id: int
    code: str
    name: str
    point_id: int
    point_code: Optional[str] = None
    manufacturer: Optional[str]
    model: Optional[str]
    serial_no: Optional[str]
    install_date: Optional[date]
    last_calibration_at: Optional[datetime]
    next_calibration_at: Optional[datetime]
    status: CemsStatus
    is_certified: bool
    certification_expiry: Optional[date]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
