"""排放标准 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.standard import StandardType


class StandardCreate(BaseModel):
    code: str
    name: str
    standard_type: StandardType = StandardType.ULTRA_LOW
    limit_so2: float
    limit_nox: float
    limit_dust: float
    limit_co: Optional[float] = None
    reference_o2: float = 6.0
    notes: Optional[str] = None


class StandardResponse(BaseModel):
    id: int
    code: str
    name: str
    standard_type: StandardType
    limit_so2: float
    limit_nox: float
    limit_dust: float
    limit_co: Optional[float]
    reference_o2: float
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
