"""排放标准 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_supervisor
from app.models.standard import EmissionStandard
from app.models.user import User
from app.schemas.standard import StandardCreate, StandardResponse
from app.utils.helpers import api_response

router = APIRouter(prefix="/api/standards", tags=["排放标准"])


@router.get("")
def list_standards(
    is_active: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(EmissionStandard).filter(EmissionStandard.is_active == is_active)
    rows = q.order_by(EmissionStandard.code).all()
    return api_response(data=[StandardResponse.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("")
def create_standard(payload: StandardCreate, db: Session = Depends(get_db), _: User = Depends(require_supervisor)):
    if db.query(EmissionStandard).filter(EmissionStandard.code == payload.code).first():
        raise HTTPException(400, "标准编码已存在")
    st = EmissionStandard(**payload.model_dump())
    db.add(st); db.commit(); db.refresh(st)
    return api_response(message="标准已创建", data=StandardResponse.model_validate(st).model_dump(mode="json"))
