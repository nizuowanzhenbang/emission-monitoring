"""seed：2 机组 + 6 排放口 + 6 CEMS 仪表 + 48h 分钟级真实风格读数 + 若干告警 + 1 张月报。

时序数据策略：
- 烟囱出口（合规上报口）：SO2 ~25mg、NOx ~40mg、烟尘 ~6mg 折算后，加噪声
- 在第 20~25 小时和第 33~36 小时注入 2 段超标段（一段一般、一段严重），制造告警
- 同时给 1# 机组 PRE_DESULFUR 配一段，方便对比脱硫前后差距

用法：
    python seed_data.py
"""
from datetime import datetime, timedelta, date
import random

from app.database import Base, engine, SessionLocal
from app.api.deps import hash_password
from app.config import settings
from app.models.user import User, UserRole
from app.models.unit import Unit, EmissionPoint, FuelType, UnitStatus, PointCategory
from app.models.cems import CemsDevice, CemsStatus
from app.models.reading import EmissionReading, ReadingValidity
from app.models.alert import EmissionAlert, AlertSeverity, AlertStatus
from app.models.standard import EmissionStandard, StandardType
from app.models.report import EmissionReport, ReportType, ReportStatus
from app.utils.emission_calc import correct_to_reference_o2
from app.utils.helpers import (
    generate_unit_code, generate_emission_point_code, generate_cems_code,
    generate_alert_no, generate_report_no,
)


random.seed(42)


def seed_users(db):
    for username, pwd, role, full in [
        ("admin",      "admin123",      UserRole.ADMIN,      "李工（环保部主任）"),
        ("operator",   "operator123",   UserRole.OPERATOR,   "刘师傅（运行人员）"),
        ("analyst",    "analyst123",    UserRole.ANALYST,    "张工（环保分析）"),
        ("supervisor", "supervisor123", UserRole.SUPERVISOR, "王工（监督员）"),
        ("viewer",     "viewer123",     UserRole.VIEWER,     "陈先生（值长）"),
    ]:
        if db.query(User).filter(User.username == username).first():
            continue
        db.add(User(username=username, full_name=full,
                    hashed_password=hash_password(pwd), role=role, is_active=True))
    db.commit()


def seed_standards(db) -> EmissionStandard:
    if db.query(EmissionStandard).count() > 0:
        return db.query(EmissionStandard).first()
    st = EmissionStandard(
        code="ULTRA-LOW-2014",
        name="火电厂超低排放限值（2014）",
        standard_type=StandardType.ULTRA_LOW,
        limit_so2=35.0, limit_nox=50.0, limit_dust=10.0,
        reference_o2=6.0,
        notes="燃煤机组超低排放：SO₂≤35, NOx≤50, 烟尘≤10 mg/Nm³",
    )
    db.add(st); db.commit(); db.refresh(st)
    return st


def seed_units_and_points(db, std: EmissionStandard) -> list[tuple[Unit, list[EmissionPoint]]]:
    if db.query(Unit).count() > 0:
        return [(u, [p for p in db.query(EmissionPoint).filter(EmissionPoint.unit_id == u.id).all()]) for u in db.query(Unit).all()]

    units_def = [
        ("1号机组（300MW）", 300.0),
        ("2号机组（600MW）", 600.0),
    ]
    out = []
    for i, (name, cap) in enumerate(units_def, 1):
        u = Unit(
            code=generate_unit_code(i), name=name, capacity_mw=cap,
            fuel_type=FuelType.COAL, status=UnitStatus.RUNNING,
            commission_date=datetime(2015, 6, 1),
        )
        db.add(u); db.flush()

        points = []
        defs = [
            ("脱硫前", PointCategory.PRE_DESULFUR, False),
            ("脱硫后", PointCategory.POST_DESULFUR, False),
            (f"{i}号烟囱出口", PointCategory.STACK, True),
        ]
        for j, (pname, cat, is_compl) in enumerate(defs, 1):
            p = EmissionPoint(
                code=generate_emission_point_code(i, j),
                name=f"{u.code}-{pname}",
                unit_id=u.id, category=cat,
                location=f"{u.code} 锅炉尾部" if "脱硫" in pname else f"{u.code} 烟囱",
                standard_id=std.id,
                is_compliance_point=is_compl,
            )
            db.add(p); db.flush()
            points.append(p)
        db.commit()
        out.append((u, points))
    return out


def seed_cems(db, units_points) -> dict[int, CemsDevice]:
    """每个排放口 1 套 CEMS"""
    if db.query(CemsDevice).count() > 0:
        return {c.point_id: c for c in db.query(CemsDevice).all()}
    out = {}
    seq = 0
    for u, points in units_points:
        for p in points:
            seq += 1
            c = CemsDevice(
                code=generate_cems_code(seq),
                name=f"{p.code} CEMS",
                point_id=p.id,
                manufacturer="聚光科技",
                model="CEMS-2000",
                serial_no=f"SN-{2020000 + seq}",
                install_date=date(2020, 3, 15),
                last_calibration_at=datetime.utcnow() - timedelta(days=2),
                next_calibration_at=datetime.utcnow() + timedelta(days=5),
                status=CemsStatus.ONLINE,
                is_certified=True,
                certification_expiry=date(2027, 3, 14),
            )
            db.add(c); db.flush()
            out[p.id] = c
    db.commit()
    return out


def _base_values(category: PointCategory, hour: int) -> tuple[float, float, float, float, float]:
    """根据点位类别给出基准的 (SO2实测, NOx实测, 烟尘实测, O2, flow)"""
    if category == PointCategory.PRE_DESULFUR:
        # 脱硫前高浓度
        so2 = 1800 + random.uniform(-150, 150)
        nox = 220 + random.uniform(-15, 15)
        dust = 25 + random.uniform(-3, 3)
    elif category == PointCategory.POST_DESULFUR:
        so2 = 28 + random.uniform(-4, 6)
        nox = 200 + random.uniform(-15, 15)
        dust = 15 + random.uniform(-2, 3)
    else:  # STACK
        so2 = 22 + random.uniform(-3, 5)
        nox = 38 + random.uniform(-5, 7)
        dust = 6 + random.uniform(-1.5, 2.0)
    o2 = 6.2 + random.uniform(-0.3, 0.3)
    flow = 1_200_000 + random.uniform(-50_000, 50_000)  # Nm³/h
    return so2, nox, dust, o2, flow


def seed_readings(db, units_points, cems_by_point) -> int:
    if db.query(EmissionReading).count() > 0:
        return db.query(EmissionReading).count()

    total = 0
    end = datetime.utcnow().replace(second=0, microsecond=0)
    start = end - timedelta(hours=48)

    # 注入 2 段超标（仅作用于合规上报口，即 STACK）：
    # 段 A：相对 start 第 20-25 小时（一般超标，SO2 略超）
    # 段 B：相对 start 第 33-36 小时（严重超标，NOx 大幅超）
    seg_a = (start + timedelta(hours=20), start + timedelta(hours=25))
    seg_b = (start + timedelta(hours=33), start + timedelta(hours=36))

    # 5 分钟间隔（48h × 12 = 576 条/点位；6 点位 ~= 3456 条），不过于浪费
    interval = timedelta(minutes=5)
    t = start
    while t < end:
        for u, points in units_points:
            for p in points:
                so2, nox, dust, o2, flow = _base_values(p.category, t.hour)

                # 注入异常（仅 STACK）
                if p.category == PointCategory.STACK:
                    if seg_a[0] <= t < seg_a[1]:
                        so2 += 25  # 折算后超 35
                    if seg_b[0] <= t < seg_b[1]:
                        nox += 60  # 折算后远超 50（≥1.5×）

                # 1% 几率 CEMS 故障导致 INVALID
                validity = ReadingValidity.VALID
                if random.random() < 0.005:
                    validity = ReadingValidity.INVALID

                so2_c = correct_to_reference_o2(so2, o2)
                nox_c = correct_to_reference_o2(nox, o2)
                dust_c = correct_to_reference_o2(dust, o2)

                severity = "NORMAL"
                exceeded = []
                if validity == ReadingValidity.VALID and p.is_compliance_point:
                    multiples = []
                    if so2_c and so2_c > settings.LIMIT_SO2:
                        multiples.append(so2_c / settings.LIMIT_SO2); exceeded.append("SO2")
                    if nox_c and nox_c > settings.LIMIT_NOX:
                        multiples.append(nox_c / settings.LIMIT_NOX); exceeded.append("NOX")
                    if dust_c and dust_c > settings.LIMIT_DUST:
                        multiples.append(dust_c / settings.LIMIT_DUST); exceeded.append("DUST")
                    if multiples:
                        severity = "SEVERE" if max(multiples) >= settings.SEVERE_MULTIPLE else "GENERAL"

                cems = cems_by_point.get(p.id)
                r = EmissionReading(
                    point_id=p.id, cems_id=cems.id if cems else None,
                    measured_at=t,
                    so2=round(so2, 2), nox=round(nox, 2), dust=round(dust, 2),
                    o2=round(o2, 2), flow=round(flow, 1),
                    temperature=round(125 + random.uniform(-5, 5), 1),
                    humidity=round(8 + random.uniform(-1, 1), 1),
                    velocity=round(13 + random.uniform(-0.5, 0.5), 2),
                    so2_corrected=so2_c, nox_corrected=nox_c, dust_corrected=dust_c,
                    validity=validity,
                    severity=severity if validity == ReadingValidity.VALID else None,
                    exceeded=",".join(exceeded) if exceeded else None,
                )
                db.add(r)
                total += 1
        if total % 500 == 0:
            db.commit()  # 防止单次 flush 过大
        t += interval
    db.commit()
    return total


def seed_alerts(db, units_points):
    if db.query(EmissionAlert).count() > 0:
        return
    # 找 STACK 点位的超标数据，建对应告警
    seq = 0
    for u, points in units_points:
        stack = next((p for p in points if p.category == PointCategory.STACK), None)
        if not stack:
            continue
        seg_rows = (
            db.query(EmissionReading)
            .filter(
                EmissionReading.point_id == stack.id,
                EmissionReading.severity.in_(["GENERAL", "SEVERE"]),
            )
            .order_by(EmissionReading.measured_at)
            .all()
        )
        if not seg_rows:
            continue

        # 简单按时间分两段
        first = seg_rows[0]
        mid_index = len(seg_rows) // 2
        mid = seg_rows[mid_index]
        # 段 A：一般超标，已处置完成
        seq += 1
        a = EmissionAlert(
            alert_no=generate_alert_no(seq),
            point_id=stack.id, reading_id=first.id,
            severity=AlertSeverity.GENERAL, status=AlertStatus.CLOSED,
            indicators=first.exceeded or "SO2",
            peak_so2=max((r.so2_corrected or 0) for r in seg_rows[:mid_index]),
            peak_nox=max((r.nox_corrected or 0) for r in seg_rows[:mid_index]),
            peak_dust=max((r.dust_corrected or 0) for r in seg_rows[:mid_index]),
            description=f"{stack.code} 折算 SO₂ 短时超标",
            started_at=first.measured_at,
            ended_at=seg_rows[mid_index - 1].measured_at if mid_index > 0 else first.measured_at,
            duration_minutes=int(((seg_rows[mid_index - 1].measured_at if mid_index > 0 else first.measured_at) - first.measured_at).total_seconds() // 60),
            acknowledged_by="operator", acknowledged_at=first.measured_at + timedelta(minutes=2),
            handled_by="operator", handle_notes="临时增大石灰石浆液循环量，30 分钟内恢复达标",
            handled_at=first.measured_at + timedelta(minutes=8),
            resolution="脱硫吸收塔浆液品质波动，已加碱+提升循环量",
            closed_by="supervisor", closed_at=first.measured_at + timedelta(hours=2),
        )
        db.add(a)

        # 段 B：严重超标（处置中，未关闭）
        seq += 1
        b = EmissionAlert(
            alert_no=generate_alert_no(seq),
            point_id=stack.id, reading_id=mid.id,
            severity=AlertSeverity.SEVERE, status=AlertStatus.HANDLING,
            indicators=mid.exceeded or "NOX",
            peak_so2=max((r.so2_corrected or 0) for r in seg_rows[mid_index:]),
            peak_nox=max((r.nox_corrected or 0) for r in seg_rows[mid_index:]),
            peak_dust=max((r.dust_corrected or 0) for r in seg_rows[mid_index:]),
            description=f"{stack.code} NOx 严重超标（>1.5×限值）",
            started_at=mid.measured_at,
            duration_minutes=15,
            acknowledged_by="operator", acknowledged_at=mid.measured_at + timedelta(minutes=1),
            handled_by="operator", handle_notes="脱硝喷氨自动失效，已切手动并复位 SCR 控制器",
            handled_at=mid.measured_at + timedelta(minutes=4),
        )
        db.add(b)
    db.commit()


def seed_monthly_report(db):
    if db.query(EmissionReport).count() > 0:
        return
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    r = EmissionReport(
        report_no=generate_report_no(month_start.year, month_start.month, 1),
        report_type=ReportType.MONTHLY,
        period_start=month_start,
        period_end=now,
        title=f"{month_start.strftime('%Y-%m')} 月度排放报告（草稿）",
        summary={"hint": "调 /api/reports/generate 重新生成最新数据"},
        status=ReportStatus.DRAFT,
        generated_by="analyst",
    )
    db.add(r); db.commit()


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
        std = seed_standards(db)
        units_points = seed_units_and_points(db, std)
        cems_map = seed_cems(db, units_points)
        n = seed_readings(db, units_points, cems_map)
        seed_alerts(db, units_points)
        seed_monthly_report(db)
        print("[seed] 完成：")
        print(f"  users={db.query(User).count()}")
        print(f"  units={db.query(Unit).count()} / points={db.query(EmissionPoint).count()}")
        print(f"  cems={db.query(CemsDevice).count()}")
        print(f"  readings={n}")
        print(f"  alerts={db.query(EmissionAlert).count()}")
        print(f"  reports={db.query(EmissionReport).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
