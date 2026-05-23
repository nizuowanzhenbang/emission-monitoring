"""应用配置（含火电厂大气污染物排放限值，GB13223-2011 超低排放）"""
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./emission.db"
    SECRET_KEY: str = "emission-monitoring-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    APP_NAME: str = "发电厂环保排放在线监测系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: Optional[List[str]] = None

    # ── 基准氧（火电规定为 6%）──
    REFERENCE_O2: float = 6.0

    # ── 超低排放限值（mg/Nm³，折算后）──
    LIMIT_SO2: float = 35.0
    LIMIT_NOX: float = 50.0
    LIMIT_DUST: float = 10.0

    # ── 严重超标倍数 ──
    SEVERE_MULTIPLE: float = 1.5

    # ── 持续超标升级阈值（分钟）──
    PERSIST_ESCALATE_MINUTES: int = 30

    # ── CEMS 月在线率合规线 ──
    CEMS_AVAILABILITY_TARGET: float = 0.95

    # 与 equipment-inspection / plant-safety 集成（v2 启用）
    INTEGRATION_SECRET: str = "coal-integration-shared-secret"
    SAFETY_SYSTEM_URL: str = ""
    INSPECTION_SYSTEM_URL: str = ""

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
