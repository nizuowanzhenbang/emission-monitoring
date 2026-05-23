"""通用工具"""
from datetime import datetime
from typing import Any


def api_response(data: Any = None, message: str = "ok", code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data}


def paginate_response(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def generate_unit_code(seq: int) -> str:
    return f"UNIT-{seq}"


def generate_emission_point_code(unit_no: int, seq: int) -> str:
    """排放口编号：EP-U{N}-NNN"""
    return f"EP-U{unit_no}-{seq:03d}"


def generate_cems_code(seq: int) -> str:
    return f"CEMS-{seq:04d}"


def generate_alert_no(seq: int) -> str:
    return f"AL-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def generate_report_no(year: int, month: int, seq: int) -> str:
    return f"RPT-{year}{month:02d}-{seq:02d}"
