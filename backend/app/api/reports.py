"""排放报表 API（日/月/年汇总）"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_analyst, require_supervisor
from app.config import settings
from app.models.alert import EmissionAlert
from app.models.cems import CemsDevice, CemsStatus
from app.models.reading import EmissionReading, ReadingValidity
from app.models.report import EmissionReport, ReportType, ReportStatus
from app.models.unit import EmissionPoint
from app.models.user import User
from app.schemas.report import ReportGenerate, ReportResponse
from app.utils.helpers import api_response, paginate_response, generate_report_no

router = APIRouter(prefix="/api/reports", tags=["排放报表"])


def _compute_summary(start: datetime, end: datetime, db: Session) -> dict:
    """对所有合规上报口计算汇总：均值、最大、超限分钟数、合规率"""
    points = db.query(EmissionPoint).filter(EmissionPoint.is_compliance_point == True).all()  # noqa: E712
    summary_per_point = []
    for p in points:
        base_q = db.query(EmissionReading).filter(
            EmissionReading.point_id == p.id,
            EmissionReading.measured_at >= start,
            EmissionReading.measured_at < end,
        )
        total_n = base_q.count()
        valid_q = base_q.filter(EmissionReading.validity == ReadingValidity.VALID)
        valid_n = valid_q.count()
        availability = round(valid_n * 100 / total_n, 2) if total_n else 0.0
        avg = (
            valid_q.with_entities(
                func.avg(EmissionReading.so2_corrected),
                func.avg(EmissionReading.nox_corrected),
                func.avg(EmissionReading.dust_corrected),
            ).one()
        )
        peak = (
            valid_q.with_entities(
                func.max(EmissionReading.so2_corrected),
                func.max(EmissionReading.nox_corrected),
                func.max(EmissionReading.dust_corrected),
            ).one()
        )
        exceed_minutes = valid_q.filter(EmissionReading.severity.in_(["GENERAL", "SEVERE"])).count()
        compliance_rate = round((valid_n - exceed_minutes) * 100 / valid_n, 2) if valid_n else 100.0
        summary_per_point.append({
            "point_id": p.id, "point_code": p.code, "point_name": p.name,
            "total_minutes": total_n, "valid_minutes": valid_n,
            "availability_pct": availability,
            "avg_so2": round(avg[0] or 0, 2),
            "avg_nox": round(avg[1] or 0, 2),
            "avg_dust": round(avg[2] or 0, 2),
            "peak_so2": round(peak[0] or 0, 2),
            "peak_nox": round(peak[1] or 0, 2),
            "peak_dust": round(peak[2] or 0, 2),
            "exceed_minutes": exceed_minutes,
            "compliance_rate_pct": compliance_rate,
            "limits": {
                "so2": settings.LIMIT_SO2, "nox": settings.LIMIT_NOX, "dust": settings.LIMIT_DUST,
            },
        })
    alerts_n = db.query(func.count(EmissionAlert.id)).filter(
        EmissionAlert.started_at >= start, EmissionAlert.started_at < end,
    ).scalar() or 0
    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "points": summary_per_point,
        "alerts_total": alerts_n,
    }


@router.post("/generate")
def generate(payload: ReportGenerate, db: Session = Depends(get_db), current: User = Depends(require_analyst)):
    if payload.period_end <= payload.period_start:
        raise HTTPException(400, "结束时间必须晚于开始时间")
    summary = _compute_summary(payload.period_start, payload.period_end, db)
    seq = (
        db.query(func.count(EmissionReport.id))
        .filter(
            func.strftime("%Y", EmissionReport.created_at) == payload.period_start.strftime("%Y"),
            func.strftime("%m", EmissionReport.created_at) == payload.period_start.strftime("%m"),
        )
        .scalar() or 0
    ) + 1
    title = payload.title or {
        ReportType.DAILY: f"{payload.period_start.strftime('%Y-%m-%d')} 日报",
        ReportType.MONTHLY: f"{payload.period_start.strftime('%Y-%m')} 月报",
        ReportType.YEARLY: f"{payload.period_start.strftime('%Y')} 年报",
        ReportType.AD_HOC: f"临时报表 {datetime.utcnow().strftime('%Y%m%d-%H%M')}",
    }[payload.report_type]
    r = EmissionReport(
        report_no=generate_report_no(payload.period_start.year, payload.period_start.month, seq),
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
        title=title,
        summary=summary,
        notes=payload.notes,
        status=ReportStatus.DRAFT,
        generated_by=current.username,
    )
    db.add(r); db.commit(); db.refresh(r)
    return api_response(message="报表已生成", data=ReportResponse.model_validate(r).model_dump(mode="json"))


@router.get("")
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ReportStatus] = None,
    report_type: Optional[ReportType] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(EmissionReport)
    if status:
        q = q.filter(EmissionReport.status == status)
    if report_type:
        q = q.filter(EmissionReport.report_type == report_type)
    total = q.count()
    rows = q.order_by(EmissionReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [ReportResponse.model_validate(r).model_dump(mode="json") for r in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.get("/{rid}")
def get_report(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.query(EmissionReport).filter(EmissionReport.id == rid).first()
    if not r:
        raise HTTPException(404, "报表不存在")
    return api_response(data=ReportResponse.model_validate(r).model_dump(mode="json"))


@router.post("/{rid}/submit")
def submit_report(rid: int, db: Session = Depends(get_db), current: User = Depends(require_analyst)):
    r = db.query(EmissionReport).filter(EmissionReport.id == rid).first()
    if not r:
        raise HTTPException(404, "报表不存在")
    if r.status != ReportStatus.DRAFT:
        raise HTTPException(400, f"状态 {r.status.value} 不可提交")
    r.status = ReportStatus.SUBMITTED
    r.submitted_by = current.username
    r.submitted_at = datetime.utcnow()
    db.commit()
    return api_response(message="已提交，待监督员审批")


@router.post("/{rid}/approve")
def approve_report(rid: int, db: Session = Depends(get_db), current: User = Depends(require_supervisor)):
    r = db.query(EmissionReport).filter(EmissionReport.id == rid).first()
    if not r:
        raise HTTPException(404, "报表不存在")
    if r.status != ReportStatus.SUBMITTED:
        raise HTTPException(400, "仅已提交报表可审批")
    r.status = ReportStatus.APPROVED
    r.approved_by = current.username
    r.approved_at = datetime.utcnow()
    db.commit()
    return api_response(message="报表已审批通过")
