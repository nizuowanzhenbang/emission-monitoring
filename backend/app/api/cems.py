"""CEMS 设备 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user, require_operator
from app.models.cems import CemsDevice, CemsStatus
from app.models.unit import EmissionPoint
from app.models.user import User
from app.schemas.cems import CemsCreate, CemsUpdate, CemsResponse
from app.utils.helpers import api_response, paginate_response, generate_cems_code

router = APIRouter(prefix="/api/cems", tags=["CEMS 设备"])


def _to_dict(c: CemsDevice) -> dict:
    data = CemsResponse.model_validate(c).model_dump(mode="json")
    if c.point:
        data["point_code"] = c.point.code
    return data


@router.get("")
def list_cems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    point_id: Optional[int] = None,
    status: Optional[CemsStatus] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(CemsDevice).options(joinedload(CemsDevice.point))
    if point_id:
        q = q.filter(CemsDevice.point_id == point_id)
    if status:
        q = q.filter(CemsDevice.status == status)
    total = q.count()
    rows = q.order_by(CemsDevice.code).offset((page - 1) * page_size).limit(page_size).all()
    items = [_to_dict(c) for c in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.post("")
def create_cems(payload: CemsCreate, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    p = db.query(EmissionPoint).filter(EmissionPoint.id == payload.point_id).first()
    if not p:
        raise HTTPException(404, "排放口不存在")
    seq = (db.query(func.count(CemsDevice.id)).scalar() or 0) + 1
    c = CemsDevice(code=generate_cems_code(seq), **payload.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return api_response(message="已登记 CEMS 设备", data=_to_dict(c))


@router.put("/{cid}")
def update_cems(cid: int, payload: CemsUpdate, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    c = db.query(CemsDevice).filter(CemsDevice.id == cid).first()
    if not c:
        raise HTTPException(404, "CEMS 不存在")
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, f, v)
    db.commit(); db.refresh(c)
    return api_response(message="已更新", data=_to_dict(c))


@router.post("/{cid}/calibrate-start")
def start_calibration(cid: int, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    c = db.query(CemsDevice).filter(CemsDevice.id == cid).first()
    if not c:
        raise HTTPException(404, "CEMS 不存在")
    c.status = CemsStatus.CALIBRATING
    c.last_calibration_at = datetime.utcnow()
    db.commit()
    return api_response(message=f"{c.code} 进入校准状态（数据将标 INVALID）")


@router.post("/{cid}/calibrate-finish")
def finish_calibration(cid: int, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    c = db.query(CemsDevice).filter(CemsDevice.id == cid).first()
    if not c:
        raise HTTPException(404, "CEMS 不存在")
    c.status = CemsStatus.ONLINE
    db.commit()
    return api_response(message=f"{c.code} 校准完成，恢复在线")
