"""排放监测 Dashboard"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.config import settings
from app.models.alert import EmissionAlert, AlertSeverity, AlertStatus
from app.models.cems import CemsDevice, CemsStatus
from app.models.reading import EmissionReading, ReadingValidity
from app.models.unit import EmissionPoint, Unit
from app.models.user import User
from app.utils.helpers import api_response

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    last_30 = datetime.utcnow() - timedelta(days=30)

    cems_total = db.query(func.count(CemsDevice.id)).scalar() or 0
    cems_online = db.query(func.count(CemsDevice.id)).filter(CemsDevice.status == CemsStatus.ONLINE).scalar() or 0
    cems_fault = db.query(func.count(CemsDevice.id)).filter(CemsDevice.status == CemsStatus.FAULT).scalar() or 0

    today_alerts = (
        db.query(func.count(EmissionAlert.id))
        .filter(EmissionAlert.started_at >= today_start)
        .scalar() or 0
    )
    open_alerts = (
        db.query(func.count(EmissionAlert.id))
        .filter(EmissionAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.HANDLING]))
        .scalar() or 0
    )
    severe_open = (
        db.query(func.count(EmissionAlert.id))
        .filter(
            EmissionAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.HANDLING]),
            EmissionAlert.severity.in_([AlertSeverity.SEVERE, AlertSeverity.ESCALATED]),
        )
        .scalar() or 0
    )

    # 30 天合规率
    total_30 = (
        db.query(func.count(EmissionReading.id))
        .filter(
            EmissionReading.measured_at >= last_30,
            EmissionReading.validity == ReadingValidity.VALID,
        )
        .scalar() or 0
    )
    exceed_30 = (
        db.query(func.count(EmissionReading.id))
        .filter(
            EmissionReading.measured_at >= last_30,
            EmissionReading.validity == ReadingValidity.VALID,
            EmissionReading.severity.in_(["GENERAL", "SEVERE"]),
        )
        .scalar() or 0
    )
    compliance_30 = round((total_30 - exceed_30) * 100 / total_30, 2) if total_30 else 100.0

    # 30 天 CEMS 在线率（VALID / total）
    raw_total = (
        db.query(func.count(EmissionReading.id))
        .filter(EmissionReading.measured_at >= last_30)
        .scalar() or 0
    )
    availability_30 = round(total_30 * 100 / raw_total, 2) if raw_total else 100.0

    return api_response(data={
        "cems": {"total": cems_total, "online": cems_online, "fault": cems_fault},
        "alerts": {
            "today": today_alerts, "open": open_alerts, "severe_open": severe_open,
        },
        "compliance_30d_pct": compliance_30,
        "availability_30d_pct": availability_30,
        "availability_target": int(settings.CEMS_AVAILABILITY_TARGET * 100),
    })


@router.get("/realtime")
def realtime(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """每个合规上报口的最新读数 + 限值，给首页大屏用"""
    sub = (
        db.query(EmissionReading.point_id, func.max(EmissionReading.measured_at).label("mt"))
        .group_by(EmissionReading.point_id)
        .subquery()
    )
    rows = (
        db.query(EmissionReading, EmissionPoint, Unit)
        .join(sub, and_(EmissionReading.point_id == sub.c.point_id, EmissionReading.measured_at == sub.c.mt))
        .join(EmissionPoint, EmissionPoint.id == EmissionReading.point_id)
        .join(Unit, Unit.id == EmissionPoint.unit_id)
        .filter(EmissionPoint.is_compliance_point == True)  # noqa: E712
        .all()
    )
    items = []
    for r, p, u in rows:
        items.append({
            "point_id": p.id, "point_code": p.code, "point_name": p.name,
            "unit_code": u.code, "unit_name": u.name,
            "measured_at": r.measured_at.isoformat() if r.measured_at else None,
            "so2": r.so2_corrected, "nox": r.nox_corrected, "dust": r.dust_corrected,
            "o2": r.o2, "flow": r.flow,
            "validity": r.validity.value if r.validity else None,
            "severity": r.severity,
            "exceeded": r.exceeded.split(",") if r.exceeded else [],
        })
    items.sort(key=lambda x: x["point_code"])
    return api_response(data={
        "limits": {"so2": settings.LIMIT_SO2, "nox": settings.LIMIT_NOX, "dust": settings.LIMIT_DUST},
        "items": items,
    })


@router.get("/trend-24h")
def trend_24h(point_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """单点位 24h 小时均值序列"""
    end = datetime.utcnow()
    start = end - timedelta(hours=24)
    rows = (
        db.query(
            func.strftime("%H:00", EmissionReading.measured_at).label("h"),
            func.avg(EmissionReading.so2_corrected).label("so2"),
            func.avg(EmissionReading.nox_corrected).label("nox"),
            func.avg(EmissionReading.dust_corrected).label("dust"),
        )
        .filter(
            EmissionReading.point_id == point_id,
            EmissionReading.measured_at >= start,
            EmissionReading.validity == ReadingValidity.VALID,
        )
        .group_by("h")
        .order_by("h")
        .all()
    )
    return api_response(data=[
        {"hour": r.h, "so2": round(r.so2 or 0, 2), "nox": round(r.nox or 0, 2), "dust": round(r.dust or 0, 2)}
        for r in rows
    ])


@router.get("/alert-distribution")
def alert_distribution(days: int = 30, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """近 N 天告警等级分布 + 状态分布"""
    start = datetime.utcnow() - timedelta(days=days)
    sev_rows = (
        db.query(EmissionAlert.severity, func.count(EmissionAlert.id))
        .filter(EmissionAlert.started_at >= start)
        .group_by(EmissionAlert.severity)
        .all()
    )
    status_rows = (
        db.query(EmissionAlert.status, func.count(EmissionAlert.id))
        .filter(EmissionAlert.started_at >= start)
        .group_by(EmissionAlert.status)
        .all()
    )
    return api_response(data={
        "by_severity": [{"name": (s.value if hasattr(s, "value") else s), "value": n} for s, n in sev_rows],
        "by_status": [{"name": (s.value if hasattr(s, "value") else s), "value": n} for s, n in status_rows],
    })


@router.get("/point-compliance")
def point_compliance(days: int = 30, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """各排放口近 N 天合规率（用于柱图）"""
    start = datetime.utcnow() - timedelta(days=days)
    points = db.query(EmissionPoint).filter(EmissionPoint.is_compliance_point == True).all()  # noqa: E712
    out = []
    for p in points:
        valid_n = (
            db.query(func.count(EmissionReading.id))
            .filter(
                EmissionReading.point_id == p.id,
                EmissionReading.measured_at >= start,
                EmissionReading.validity == ReadingValidity.VALID,
            )
            .scalar() or 0
        )
        exceed_n = (
            db.query(func.count(EmissionReading.id))
            .filter(
                EmissionReading.point_id == p.id,
                EmissionReading.measured_at >= start,
                EmissionReading.validity == ReadingValidity.VALID,
                EmissionReading.severity.in_(["GENERAL", "SEVERE"]),
            )
            .scalar() or 0
        )
        rate = round((valid_n - exceed_n) * 100 / valid_n, 2) if valid_n else 100.0
        out.append({"point_id": p.id, "point_code": p.code, "compliance_pct": rate, "valid_minutes": valid_n, "exceed_minutes": exceed_n})
    out.sort(key=lambda x: x["compliance_pct"])
    return api_response(data=out)
