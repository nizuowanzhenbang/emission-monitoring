"""超标告警闭环 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user, require_operator, require_supervisor
from app.models.alert import EmissionAlert, AlertSeverity, AlertStatus
from app.models.unit import EmissionPoint
from app.models.user import User
from app.schemas.alert import AlertAcknowledge, AlertHandle, AlertClose, AlertResponse
from app.utils.helpers import api_response, paginate_response

router = APIRouter(prefix="/api/alerts", tags=["超标告警"])


def _to_dict(a: EmissionAlert) -> dict:
    data = AlertResponse.model_validate(a).model_dump(mode="json")
    if a.point:
        data["point_code"] = a.point.code
        if a.point.unit:
            data["unit_name"] = a.point.unit.name
    return data


@router.get("")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    point_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(EmissionAlert).options(
        joinedload(EmissionAlert.point).joinedload(EmissionPoint.unit)
    )
    if status:
        q = q.filter(EmissionAlert.status == status)
    if severity:
        q = q.filter(EmissionAlert.severity == severity)
    if point_id:
        q = q.filter(EmissionAlert.point_id == point_id)
    total = q.count()
    rows = q.order_by(EmissionAlert.started_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [_to_dict(a) for a in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.get("/{aid}")
def get_alert(aid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    a = db.query(EmissionAlert).options(joinedload(EmissionAlert.point).joinedload(EmissionPoint.unit)).filter(EmissionAlert.id == aid).first()
    if not a:
        raise HTTPException(404, "告警不存在")
    return api_response(data=_to_dict(a))


@router.post("/{aid}/acknowledge")
def acknowledge(aid: int, payload: AlertAcknowledge, db: Session = Depends(get_db), current: User = Depends(require_operator)):
    a = db.query(EmissionAlert).filter(EmissionAlert.id == aid).first()
    if not a:
        raise HTTPException(404, "告警不存在")
    if a.status != AlertStatus.OPEN:
        raise HTTPException(400, f"状态 {a.status.value} 不可确认")
    a.status = AlertStatus.ACKNOWLEDGED
    a.acknowledged_by = current.username
    a.acknowledged_at = datetime.utcnow()
    if payload.notes:
        a.description = (a.description or "") + f"\n[确认备注] {payload.notes}"
    db.commit()
    return api_response(message="已确认")


@router.post("/{aid}/handle")
def handle(aid: int, payload: AlertHandle, db: Session = Depends(get_db), current: User = Depends(require_operator)):
    a = db.query(EmissionAlert).filter(EmissionAlert.id == aid).first()
    if not a:
        raise HTTPException(404, "告警不存在")
    if a.status not in (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.HANDLING):
        raise HTTPException(400, f"状态 {a.status.value} 不可处置")
    a.status = AlertStatus.HANDLING
    a.handle_notes = (a.handle_notes or "") + f"\n[处置 by {current.username}] {payload.handle_notes}"
    a.handled_by = current.username
    a.handled_at = datetime.utcnow()
    if payload.resolution:
        a.resolution = payload.resolution
    db.commit()
    return api_response(message="处置记录已保存")


@router.post("/{aid}/resolve")
def resolve(aid: int, payload: AlertClose, db: Session = Depends(get_db), current: User = Depends(require_operator)):
    a = db.query(EmissionAlert).filter(EmissionAlert.id == aid).first()
    if not a:
        raise HTTPException(404, "告警不存在")
    if a.status not in (AlertStatus.HANDLING, AlertStatus.ACKNOWLEDGED, AlertStatus.OPEN):
        raise HTTPException(400, f"状态 {a.status.value} 不可解决")
    a.status = AlertStatus.RESOLVED
    a.resolution = payload.resolution
    if not a.ended_at:
        a.ended_at = datetime.utcnow()
    db.commit()
    return api_response(message="已标记解决，待监督员归档")


@router.post("/{aid}/close")
def close_alert(aid: int, db: Session = Depends(get_db), current: User = Depends(require_supervisor)):
    a = db.query(EmissionAlert).filter(EmissionAlert.id == aid).first()
    if not a:
        raise HTTPException(404, "告警不存在")
    if a.status != AlertStatus.RESOLVED:
        raise HTTPException(400, f"状态 {a.status.value} 不可归档（需先解决）")
    a.status = AlertStatus.CLOSED
    a.closed_by = current.username
    a.closed_at = datetime.utcnow()
    db.commit()
    return api_response(message="已归档")
