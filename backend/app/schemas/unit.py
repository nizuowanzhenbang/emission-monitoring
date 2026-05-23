"""机组与排放口 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.unit import UnitStatus, FuelType, PointCategory


class UnitCreate(BaseModel):
    name: str
    capacity_mw: float
    fuel_type: FuelType = FuelType.COAL
    commission_date: Optional[datetime] = None
    notes: Optional[str] = None


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    capacity_mw: Optional[float] = None
    fuel_type: Optional[FuelType] = None
    status: Optional[UnitStatus] = None
    notes: Optional[str] = None


class UnitResponse(BaseModel):
    id: int
    code: str
    name: str
    capacity_mw: float
    fuel_type: FuelType
    status: UnitStatus
    commission_date: Optional[datetime]
    notes: Optional[str]
    point_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EmissionPointCreate(BaseModel):
    name: str
    unit_id: int
    category: PointCategory
    location: Optional[str] = None
    standard_id: Optional[int] = None
    is_compliance_point: bool = True
    notes: Optional[str] = None


class EmissionPointResponse(BaseModel):
    id: int
    code: str
    name: str
    unit_id: int
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None
    category: PointCategory
    location: Optional[str]
    standard_id: Optional[int]
    is_compliance_point: bool
    notes: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
