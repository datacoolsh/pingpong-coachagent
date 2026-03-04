"""
认证依赖注入

三个层级：
- get_optional_user: 有 JWT 用 JWT，有 cookie 走回退，都没有返回 None（匿名模式）
- get_current_user: 必须已登录
- require_admin: 必须是管理员
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from ..database import get_session
from ..models.user import User
from .security import decode_token

logger = logging.getLogger(__name__)

# tokenUrl 指向登录接口（仅用于 Swagger UI 文档），auto_error=False 允许匿名访问
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """
    获取当前用户（可选）

    优先级：
    1. JWT Bearer token → 查找用户
    2. cookie user_id → 通过 legacy_cookie_id 查找用户
    3. 都没有 → 返回 None（匿名模式）
    """
    # 1. 尝试 JWT
    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = session.get(User, user_id)
                if user and user.is_active:
                    return user

    # 2. 尝试 cookie 回退
    cookie_user_id = request.cookies.get("user_id")
    if cookie_user_id:
        stmt = select(User).where(User.legacy_cookie_id == cookie_user_id)
        user = session.exec(stmt).first()
        if user and user.is_active:
            return user

    return None


def get_effective_user_id(
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
) -> str:
    """
    获取有效的用户标识（统一替代 get_user_id_from_cookie）

    - 已登录用户 → user.id
    - 匿名用户（有 cookie）→ cookie user_id
    - 完全匿名 → "user_default"
    """
    if user:
        return user.id

    # cookie 回退
    cookie_user_id = request.cookies.get("user_id")
    if cookie_user_id and cookie_user_id.startswith("user_") and len(cookie_user_id) == 11:
        return cookie_user_id

    return "user_default"


def get_current_user(
    user: Optional[User] = Depends(get_optional_user),
) -> User:
    """获取当前已登录用户（必须已登录）"""
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """要求管理员权限"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
