"""依赖注入：JWT + 角色"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(401, "无效凭证", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_operator(current: User = Depends(get_current_user)) -> User:
    """运行人员（录入校准/处置告警）：ADMIN / OPERATOR"""
    if current.role in (UserRole.ADMIN, UserRole.OPERATOR):
        return current
    raise HTTPException(403, "仅运行人员或管理员可执行")


def require_supervisor(current: User = Depends(get_current_user)) -> User:
    """监督员（告警审核 + 报表归档）：ADMIN / SUPERVISOR"""
    if current.role in (UserRole.ADMIN, UserRole.SUPERVISOR):
        return current
    raise HTTPException(403, "仅监督员或管理员可执行")


def require_analyst(current: User = Depends(get_current_user)) -> User:
    """数据分析（报表生成）：ADMIN / ANALYST / SUPERVISOR"""
    if current.role in (UserRole.ADMIN, UserRole.ANALYST, UserRole.SUPERVISOR):
        return current
    raise HTTPException(403, "仅分析员/监督员/管理员可生成报表")


def require_write(current: User = Depends(get_current_user)) -> User:
    if current.role == UserRole.VIEWER:
        raise HTTPException(403, "只读账户无权操作")
    return current
