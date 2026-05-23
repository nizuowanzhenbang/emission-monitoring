"""排放数据计算工具

核心：基准氧折算（GB13223-2011）
   C_折算 = C_实测 × (21 - O2_基准) / (21 - O2_实测)
   O2_实测 应严格小于 21；规范要求 O2 范围 [0, 21)。
当 O2_实测 ≥ 20.5 时视为异常数据，不做折算。
"""
from typing import Optional

from app.config import settings


def correct_to_reference_o2(measured: Optional[float], o2_actual: Optional[float]) -> Optional[float]:
    """基准氧折算"""
    if measured is None or o2_actual is None:
        return None
    if o2_actual >= 20.5 or o2_actual < 0:
        return None
    ref = settings.REFERENCE_O2
    try:
        return round(measured * (21.0 - ref) / (21.0 - o2_actual), 3)
    except ZeroDivisionError:
        return None


def calc_emission_mass(corrected_mg_per_nm3: Optional[float], flow_nm3_per_h: Optional[float], minutes: int = 1) -> Optional[float]:
    """累计排放质量（kg）= 折算浓度(mg/Nm³) × 流量(Nm³/h) × 时长(h) / 1e6"""
    if corrected_mg_per_nm3 is None or flow_nm3_per_h is None:
        return None
    hours = minutes / 60.0
    return round(corrected_mg_per_nm3 * flow_nm3_per_h * hours / 1_000_000.0, 6)


def classify_severity(
    so2_c: Optional[float], nox_c: Optional[float], dust_c: Optional[float],
) -> tuple[str, list[str]]:
    """对一行折算后的污染物判定告警级别。

    返回 (severity, exceeded_indicators)
       severity ∈ {NORMAL, GENERAL, SEVERE}
    """
    multiples = []
    exceeded = []
    if so2_c is not None and so2_c > settings.LIMIT_SO2:
        multiples.append(so2_c / settings.LIMIT_SO2)
        exceeded.append("SO2")
    if nox_c is not None and nox_c > settings.LIMIT_NOX:
        multiples.append(nox_c / settings.LIMIT_NOX)
        exceeded.append("NOX")
    if dust_c is not None and dust_c > settings.LIMIT_DUST:
        multiples.append(dust_c / settings.LIMIT_DUST)
        exceeded.append("DUST")

    if not multiples:
        return "NORMAL", []
    if max(multiples) >= settings.SEVERE_MULTIPLE:
        return "SEVERE", exceeded
    return "GENERAL", exceeded
