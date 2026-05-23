"""告警 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity, AlertStatus


class AlertAcknowledge(BaseModel):
    notes: Optional[str] = None


class AlertHandle(BaseModel):
    handle_notes: str
    resolution: Optional[str] = None


class AlertClose(BaseModel):
    resolution: str


class AlertResponse(BaseModel):
    id: int
    alert_no: str
    point_id: int
    point_code: Optional[str] = None
    unit_name: Optional[str] = None
    severity: AlertSeverity
    status: AlertStatus
    indicators: str
    peak_so2: Optional[float]
    peak_nox: Optional[float]
    peak_dust: Optional[float]
    description: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: int
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    handled_by: Optional[str]
    handle_notes: Optional[str]
    handled_at: Optional[datetime]
    resolution: Optional[str]
    closed_by: Optional[str]
    closed_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
