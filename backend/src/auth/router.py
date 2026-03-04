"""
认证路由

POST /auth/register  — 注册
POST /auth/login     — 登录
POST /auth/refresh   — 刷新 token
GET  /auth/me        — 获取当前用户信息
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models.user import User
from ..schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from .dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, session: Session = Depends(get_session)):
    """用户注册"""
    # 检查用户名是否已存在
    stmt = select(User).where(User.username == body.username)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"新用户注册: {user.username} (id={user.id})")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    """用户登录"""
    stmt = select(User).where(User.username == body.username)
    user = session.exec(stmt).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    logger.info(f"用户登录: {user.username}")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, session: Session = Depends(get_session)):
    """刷新 access token"""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的 refresh token")

    user_id = payload.get("sub")
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        legacy_cookie_id=user.legacy_cookie_id,
    )
