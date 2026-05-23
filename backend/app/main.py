"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, SessionLocal, Base

from app.models.user import User, UserRole
from app.models.unit import Unit, EmissionPoint
from app.models.cems import CemsDevice
from app.models.reading import EmissionReading
from app.models.alert import EmissionAlert
from app.models.standard import EmissionStandard
from app.models.report import EmissionReport

from app.api import auth, units, cems, readings, alerts, standards, reports, dashboard
from app.api.deps import hash_password

_ = (User, Unit, EmissionPoint, CemsDevice, EmissionReading, EmissionAlert, EmissionStandard, EmissionReport)


def _create_default_users(db) -> None:
    defaults = [
        ("admin",      "admin123",      UserRole.ADMIN,      "李工（环保部主任）"),
        ("operator",   "operator123",   UserRole.OPERATOR,   "刘师傅（运行人员）"),
        ("analyst",    "analyst123",    UserRole.ANALYST,    "张工（环保分析）"),
        ("supervisor", "supervisor123", UserRole.SUPERVISOR, "王工（监督员）"),
        ("viewer",     "viewer123",     UserRole.VIEWER,     "陈先生（值长）"),
    ]
    created = []
    for username, pwd, role, full in defaults:
        if db.query(User).filter(User.username == username).first():
            continue
        db.add(User(
            username=username, full_name=full,
            hashed_password=hash_password(pwd),
            role=role, is_active=True,
            created_at=datetime.utcnow(),
        ))
        created.append(username)
    if created:
        db.commit()
        print(f"[启动] 已创建默认账户：{', '.join(created)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _create_default_users(db)
    finally:
        db.close()
    print(f"[启动] {settings.APP_NAME} v{settings.APP_VERSION} 已就绪")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="发电厂环保排放在线监测：CEMS + 折算浓度 + 超标告警闭环 + 合规报表",
    lifespan=lifespan,
)

allowed = settings.ALLOWED_ORIGINS or [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(units.router)
app.include_router(cems.router)
app.include_router(readings.router)
app.include_router(alerts.router)
app.include_router(standards.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", tags=["系统"])
def root():
    return {"message": f"欢迎使用 {settings.APP_NAME}", "docs": "/docs"}
