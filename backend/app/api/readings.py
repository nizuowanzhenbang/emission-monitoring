"""CEMS 时序读数 API：批量摄取 + 折算 + 自动告警 + 均值聚合"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user, require_operator
from app.config import settings
from app.models.alert import EmissionAlert, AlertSeverity, AlertStatus
from app.models.cems import CemsDevice, CemsStatus
from app.models.reading import EmissionReading, ReadingValidity
from app.models.standard import EmissionStandard
from app.models.unit import EmissionPoint
from app.models.user import User
from app.schemas.reading import ReadingIn, ReadingBatch, ReadingResponse
from app.utils.emission_calc import correct_to_reference_o2, classify_severity
from app.utils.helpers import api_response, paginate_response, generate_alert_no

router = APIRouter(prefix="/api/readings", tags=["时序读数"])


def _get_limits(point: EmissionPoint, db: Session) -> tuple[float, float, float, float]:
    """返回 (SO2, NOX, DUST, 基准氧)"""
    if point.standard_id:
        st = db.query(EmissionStandard).filter(EmissionStandard.id == point.standard_id).first()
        if st:
            return st.limit_so2, st.limit_nox, st.limit_dust, st.reference_o2
    return settings.LIMIT_SO2, settings.LIMIT_NOX, settings.LIMIT_DUST, settings.REFERENCE_O2


def _enrich_reading(r: EmissionReading, point: EmissionPoint, db: Session) -> tuple[EmissionReading, str, list[str]]:
    """折算 + 严重度判定"""
    so2_l, nox_l, dust_l, _ref = _get_limits(point, db)
    # 折算
    r.so2_corrected = correct_to_reference_o2(r.so2, r.o2)
    r.nox_corrected = correct_to_reference_o2(r.nox, r.o2)
    r.dust_corrected = correct_to_reference_o2(r.dust, r.o2)
    # 仅 VALID 数据参与超标判定
    if r.validity != ReadingValidity.VALID:
        r.severity = None
        r.exceeded = None
        return r, "INVALID", []
    severity, exceeded = classify_severity(r.so2_corrected, r.nox_corrected, r.dust_corrected)
    # 这里用动态阈值覆盖默认（基于 standard）：
    multiples = []
    if r.so2_corrected is not None and r.so2_corrected > so2_l:
        multiples.append((r.so2_corrected / so2_l, "SO2"))
    if r.nox_corrected is not None and r.nox_corrected > nox_l:
        multiples.append((r.nox_corrected / nox_l, "NOX"))
    if r.dust_corrected is not None and r.dust_corrected > dust_l:
        multiples.append((r.dust_corrected / dust_l, "DUST"))
    exceeded = [m[1] for m in multiples]
    if not multiples:
        severity = "NORMAL"
    elif max(m[0] for m in multiples) >= settings.SEVERE_MULTIPLE:
        severity = "SEVERE"
    else:
        severity = "GENERAL"
    r.severity = severity
    r.exceeded = ",".join(exceeded) if exceeded else None
    return r, severity, exceeded


def _ensure_alert(point: EmissionPoint, reading: EmissionReading, severity: str, exceeded: list[str], db: Session) -> Optional[EmissionAlert]:
    """同一点位若已有 OPEN/未结告警则更新（峰值+持续时间），否则建新告警"""
    if severity == "NORMAL" or not exceeded:
        # 恢复达标 → 把仍 OPEN 的告警标 ended_at（不自动关闭，等人工处置）
        open_alert = (
            db.query(EmissionAlert)
            .filter(
                EmissionAlert.point_id == point.id,
                EmissionAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.HANDLING]),
                EmissionAlert.ended_at.is_(None),
            )
            .order_by(EmissionAlert.started_at.desc())
            .first()
        )
        if open_alert:
            open_alert.ended_at = reading.measured_at
        return None

    existing = (
        db.query(EmissionAlert)
        .filter(
            EmissionAlert.point_id == point.id,
            EmissionAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.HANDLING]),
            EmissionAlert.ended_at.is_(None),
        )
        .order_by(EmissionAlert.started_at.desc())
        .first()
    )
    if existing:
        # 更新峰值
        if reading.so2_corrected and (existing.peak_so2 is None or reading.so2_corrected > existing.peak_so2):
            existing.peak_so2 = reading.so2_corrected
        if reading.nox_corrected and (existing.peak_nox is None or reading.nox_corrected > existing.peak_nox):
            existing.peak_nox = reading.nox_corrected
        if reading.dust_corrected and (existing.peak_dust is None or reading.dust_corrected > existing.peak_dust):
            existing.peak_dust = reading.dust_corrected
        existing.duration_minutes = int((reading.measured_at - existing.started_at).total_seconds() // 60)
        # 升级条件
        if severity == "SEVERE" and existing.severity == AlertSeverity.GENERAL:
            existing.severity = AlertSeverity.SEVERE
        if existing.duration_minutes >= settings.PERSIST_ESCALATE_MINUTES and existing.severity != AlertSeverity.ESCALATED:
            existing.severity = AlertSeverity.ESCALATED
        # 合并 indicators
        old = set((existing.indicators or "").split(","))
        new = old | set(exceeded)
        existing.indicators = ",".join(sorted(x for x in new if x))
        return existing

    # 新告警
    seq = (
        db.query(func.count(EmissionAlert.id))
        .filter(func.date(EmissionAlert.created_at) == datetime.utcnow().date())
        .scalar() or 0
    ) + 1
    sev_enum = AlertSeverity.SEVERE if severity == "SEVERE" else AlertSeverity.GENERAL
    alert = EmissionAlert(
        alert_no=generate_alert_no(seq),
        point_id=point.id,
        reading_id=reading.id,
        severity=sev_enum,
        status=AlertStatus.OPEN,
        indicators=",".join(exceeded),
        peak_so2=reading.so2_corrected,
        peak_nox=reading.nox_corrected,
        peak_dust=reading.dust_corrected,
        description=f"{point.code} 超标：{','.join(exceeded)}",
        started_at=reading.measured_at,
        duration_minutes=0,
    )
    db.add(alert)
    return alert


@router.post("/ingest")
def ingest(payload: ReadingBatch, db: Session = Depends(get_db), _: User = Depends(require_operator)):
    """批量摄取读数：折算 → 自动告警建/合并。

    单批最大 1000 条；超出请客户端分批。
    """
    if not payload.readings:
        return api_response(message="空批次", data={"saved": 0, "alerts_created": 0})
    if len(payload.readings) > 1000:
        raise HTTPException(400, "单批 ≤ 1000 条")

    # 预取所有涉及的 point + standard
    point_ids = list({r.point_id for r in payload.readings})
    cems_ids = list({r.cems_id for r in payload.readings if r.cems_id})
    points = {
        p.id: p for p in db.query(EmissionPoint).filter(EmissionPoint.id.in_(point_ids)).all()
    }
    cems_map = {c.id: c for c in db.query(CemsDevice).filter(CemsDevice.id.in_(cems_ids)).all()} if cems_ids else {}

    saved = 0
    alerts_created = 0
    for item in payload.readings:
        point = points.get(item.point_id)
        if not point:
            continue
        # CEMS 校准/故障时自动覆盖 validity
        validity = item.validity
        if item.cems_id and item.cems_id in cems_map:
            cs = cems_map[item.cems_id].status
            if cs == CemsStatus.CALIBRATING:
                validity = ReadingValidity.CALIBRATING
            elif cs == CemsStatus.FAULT:
                validity = ReadingValidity.INVALID

        r = EmissionReading(
            point_id=item.point_id, cems_id=item.cems_id,
            measured_at=item.measured_at,
            so2=item.so2, nox=item.nox, dust=item.dust, co=item.co,
            o2=item.o2, temperature=item.temperature, humidity=item.humidity,
            flow=item.flow, velocity=item.velocity,
            validity=validity,
        )
        db.add(r); db.flush()
        r, severity, exceeded = _enrich_reading(r, point, db)
        # 仅合规上报口才参与告警
        if point.is_compliance_point:
            alert = _ensure_alert(point, r, severity, exceeded, db)
            if alert and alert.id is None:
                alerts_created += 1
        saved += 1

    db.commit()
    return api_response(message=f"已写入 {saved} 条", data={"saved": saved, "alerts_created": alerts_created})


def _row_to_dict(r: EmissionReading) -> dict:
    return ReadingResponse.model_validate(r).model_dump(mode="json")


@router.get("")
def list_readings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    point_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    validity: Optional[ReadingValidity] = None,
    only_exceeded: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(EmissionReading)
    if point_id:
        q = q.filter(EmissionReading.point_id == point_id)
    if start:
        q = q.filter(EmissionReading.measured_at >= start)
    if end:
        q = q.filter(EmissionReading.measured_at < end)
    if validity:
        q = q.filter(EmissionReading.validity == validity)
    if only_exceeded:
        q = q.filter(EmissionReading.severity.in_(["GENERAL", "SEVERE"]))
    total = q.count()
    rows = q.order_by(EmissionReading.measured_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [_row_to_dict(r) for r in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.get("/latest")
def latest_per_point(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """每个合规上报口的最新一条读数（用于 Dashboard 实时数字）"""
    sub = (
        db.query(EmissionReading.point_id, func.max(EmissionReading.measured_at).label("mt"))
        .group_by(EmissionReading.point_id)
        .subquery()
    )
    rows = (
        db.query(EmissionReading)
        .join(sub, and_(EmissionReading.point_id == sub.c.point_id, EmissionReading.measured_at == sub.c.mt))
        .options(joinedload(EmissionReading.point).joinedload(EmissionPoint.unit))
        .all()
    )
    items = []
    for r in rows:
        if not r.point or not r.point.is_compliance_point:
            continue
        items.append({
            **_row_to_dict(r),
            "point_code": r.point.code,
            "point_name": r.point.name,
            "unit_name": r.point.unit.name if r.point.unit else None,
        })
    return api_response(data=items)


@router.get("/hourly")
def hourly_average(
    point_id: int = Query(...),
    hours: int = Query(24, ge=1, le=24 * 30),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """单点位 N 小时内的小时均值（仅 VALID）"""
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    rows = (
        db.query(
            func.strftime("%Y-%m-%d %H:00", EmissionReading.measured_at).label("h"),
            func.avg(EmissionReading.so2_corrected).label("so2"),
            func.avg(EmissionReading.nox_corrected).label("nox"),
            func.avg(EmissionReading.dust_corrected).label("dust"),
            func.avg(EmissionReading.o2).label("o2"),
            func.count(EmissionReading.id).label("n"),
        )
        .filter(
            EmissionReading.point_id == point_id,
            EmissionReading.measured_at >= start,
            EmissionReading.measured_at < end,
            EmissionReading.validity == ReadingValidity.VALID,
        )
        .group_by("h")
        .order_by("h")
        .all()
    )
    data = [
        {"hour": r.h, "so2": round(r.so2 or 0, 2), "nox": round(r.nox or 0, 2),
         "dust": round(r.dust or 0, 2), "o2": round(r.o2 or 0, 2), "count": r.n}
        for r in rows
    ]
    return api_response(data=data)
