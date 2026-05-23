"""机组 + 排放口 API"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user, require_operator
from app.models.unit import Unit, UnitStatus, EmissionPoint, PointCategory
from app.models.user import User
from app.schemas.unit import (
    UnitCreate, UnitUpdate, UnitResponse,
    EmissionPointCreate, EmissionPointResponse,
)
from app.utils.helpers import (
    api_response, paginate_response,
    generate_unit_code, generate_emission_point_code,
)

router = APIRouter(prefix="/api", tags=["机组与排放口"])


def _unit_to_dict(u: Unit) -> dict:
    data = UnitResponse.model_validate(u).model_dump(mode="json")
    data["point_count"] = len(u.points or [])
    return data


def _point_to_dict(p: EmissionPoint) -> dict:
    data = EmissionPointResponse.model_validate(p).model_dump(mode="json")
    if p.unit:
        data["unit_code"] = p.unit.code
        data["unit_name"] = p.unit.name
    return data


@router.get("/units")
def list_units(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[UnitStatus] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Unit).options(joinedload(Unit.points))
    if status:
        q = q.filter(Unit.status == status)
    total = q.count()
    rows = q.order_by(Unit.code).offset((page - 1) * page_size).limit(page_size).all()
    items = [_unit_to_dict(u) for u in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.post("/units")
def create_unit(payload: UnitCreate, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    next_seq = (db.query(func.count(Unit.id)).scalar() or 0) + 1
    u = Unit(code=generate_unit_code(next_seq), **payload.model_dump())
    db.add(u); db.commit(); db.refresh(u)
    return api_response(message="机组已登记", data=_unit_to_dict(u))


@router.put("/units/{uid}")
def update_unit(uid: int, payload: UnitUpdate, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    u = db.query(Unit).filter(Unit.id == uid).first()
    if not u:
        raise HTTPException(404, "机组不存在")
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(u, f, v)
    db.commit(); db.refresh(u)
    return api_response(message="已更新", data=_unit_to_dict(u))


@router.get("/emission-points")
def list_points(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    unit_id: Optional[int] = None,
    category: Optional[PointCategory] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(EmissionPoint).options(joinedload(EmissionPoint.unit))
    if unit_id:
        q = q.filter(EmissionPoint.unit_id == unit_id)
    if category:
        q = q.filter(EmissionPoint.category == category)
    total = q.count()
    rows = q.order_by(EmissionPoint.code).offset((page - 1) * page_size).limit(page_size).all()
    items = [_point_to_dict(p) for p in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.post("/emission-points")
def create_point(payload: EmissionPointCreate, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    u = db.query(Unit).filter(Unit.id == payload.unit_id).first()
    if not u:
        raise HTTPException(404, "机组不存在")
    seq = (db.query(func.count(EmissionPoint.id)).filter(EmissionPoint.unit_id == u.id).scalar() or 0) + 1
    # 提取 UNIT-N 的 N
    unit_no = int(u.code.split("-")[-1]) if "-" in u.code else 1
    code = generate_emission_point_code(unit_no, seq)
    p = EmissionPoint(code=code, **payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    p.unit = u  # for serialize
    return api_response(message="排放口已创建", data=_point_to_dict(p))
