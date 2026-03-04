"""
管理后台路由

所有接口使用 require_admin 保护。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col, func

from ..database import get_session
from ..auth.dependencies import require_admin
from ..auth.security import hash_password
from ..models.user import User
from ..models.task import Task
from ..models.system_config import SystemConfig
from ..services.task_service import delete_task
from ..schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserResponse,
    AdminUserListResponse,
    AdminTaskResponse,
    AdminTaskListResponse,
    AdminStatsResponse,
    AdminConfigItem,
    AdminConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ---- 用户管理 ----

@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    page: int = 1,
    limit: int = 20,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """用户列表（分页）"""
    total = len(session.exec(select(User)).all())
    offset = (page - 1) * limit
    stmt = select(User).order_by(col(User.created_at).desc()).offset(offset).limit(limit)
    users = session.exec(stmt).all()

    return AdminUserListResponse(
        users=[
            AdminUserResponse(
                id=u.id,
                username=u.username,
                role=u.role,
                is_active=u.is_active,
                legacy_cookie_id=u.legacy_cookie_id,
                created_at=u.created_at.isoformat() if u.created_at else "",
                updated_at=u.updated_at.isoformat() if u.updated_at else "",
            )
            for u in users
        ],
        total=total,
        page=page,
        limit=limit,
        has_more=offset + limit < total,
    )


@router.post("/users", response_model=AdminUserResponse)
def create_user(
    body: AdminUserCreate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """创建用户"""
    existing = session.exec(select(User).where(User.username == body.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"管理员 {admin.username} 创建用户: {user.username}")

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        legacy_cookie_id=user.legacy_cookie_id,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.put("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """编辑用户（角色/状态/密码）"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    user.updated_at = datetime.now()
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"管理员 {admin.username} 更新用户: {user.username}")

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        legacy_cookie_id=user.legacy_cookie_id,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """删除用户"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    session.delete(user)
    session.commit()

    logger.info(f"管理员 {admin.username} 删除用户: {user.username}")
    return {"success": True, "message": "用户已删除"}


# ---- 任务管理 ----

@router.get("/tasks", response_model=AdminTaskListResponse)
def list_all_tasks(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """所有任务列表（跨用户）"""
    stmt = select(Task)
    count_stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
        count_stmt = count_stmt.where(Task.status == status)

    total = len(session.exec(count_stmt).all())
    offset = (page - 1) * limit
    stmt = stmt.order_by(col(Task.created_at).desc()).offset(offset).limit(limit)
    tasks = session.exec(stmt).all()

    return AdminTaskListResponse(
        tasks=[
            AdminTaskResponse(
                task_id=t.task_id,
                user_id=t.user_id,
                name=t.name,
                status=t.status,
                progress=t.progress,
                is_public=t.is_public,
                created_at=t.created_at.isoformat() if t.created_at else "",
                updated_at=t.updated_at.isoformat() if t.updated_at else "",
            )
            for t in tasks
        ],
        total=total,
        page=page,
        limit=limit,
        has_more=offset + limit < total,
    )


@router.delete("/tasks/{task_id}")
def admin_delete_task(
    task_id: str,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """删除任务"""
    success = delete_task(session, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")

    logger.info(f"管理员 {admin.username} 删除任务: {task_id}")
    return {"success": True, "message": "任务已删除"}


# ---- 统计 ----

@router.get("/stats", response_model=AdminStatsResponse)
def get_stats(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """统计数据"""
    total_users = len(session.exec(select(User)).all())
    active_users = len(session.exec(select(User).where(User.is_active == True)).all())
    total_tasks = len(session.exec(select(Task)).all())
    completed_tasks = len(session.exec(select(Task).where(Task.status == "completed")).all())
    failed_tasks = len(session.exec(select(Task).where(Task.status == "failed")).all())

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
    )


# ---- 配置管理 ----

@router.get("/config", response_model=list[AdminConfigItem])
def get_all_config(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """获取所有配置"""
    configs = session.exec(select(SystemConfig)).all()
    return [
        AdminConfigItem(key=c.key, value=c.value, description=c.description)
        for c in configs
    ]


@router.put("/config/{key}", response_model=AdminConfigItem)
def update_config(
    key: str,
    body: AdminConfigUpdate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """更新配置"""
    config = session.get(SystemConfig, key)
    if not config:
        # 创建新配置
        config = SystemConfig(key=key, value=body.value, description=body.description)
    else:
        config.value = body.value
        if body.description is not None:
            config.description = body.description
        config.updated_at = datetime.now()

    session.add(config)
    session.commit()
    session.refresh(config)

    logger.info(f"管理员 {admin.username} 更新配置: {key}={body.value}")
    return AdminConfigItem(key=config.key, value=config.value, description=config.description)
