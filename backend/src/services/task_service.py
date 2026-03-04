"""
任务 CRUD 服务 - 数据库持久化

替代旧的 TaskManager 中的 CRUD 操作，使用 SQLite 存储。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select, col

from ..models.task import Task
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_runs_dir() -> Path:
    """获取 runs 目录"""
    runs_dir = settings.runs_dir
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def get_user_run_dir(user_id: str) -> Path:
    """获取用户专属的运行目录"""
    user_dir = get_runs_dir() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def create_task(
    session: Session,
    task_id: str,
    name: str,
    video_path: str,
    user_id: Optional[str] = None,
) -> Task:
    """创建新任务"""
    now = datetime.now()
    task = Task(
        task_id=task_id,
        user_id=user_id,
        name=name,
        status="pending",
        progress=0,
        video_path=video_path,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(f"创建任务: {task_id}, user_id={user_id}")
    return task


def get_task(session: Session, task_id: str) -> Optional[Task]:
    """获取任务"""
    return session.get(Task, task_id)


def find_task_globally(session: Session, task_id: str) -> Optional[Task]:
    """全局查找任务（一条 SELECT 替代旧的文件系统遍历）"""
    return session.get(Task, task_id)


def update_task(session: Session, task_id: str, **updates) -> Optional[Task]:
    """更新任务字段"""
    task = session.get(Task, task_id)
    if not task:
        return None
    for key, value in updates.items():
        if hasattr(task, key):
            setattr(task, key, value)
    task.updated_at = datetime.now()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task_id: str) -> bool:
    """删除任务记录"""
    task = session.get(Task, task_id)
    if not task:
        return False

    # 删除文件系统中的任务目录
    if task.user_id:
        task_dir = get_user_run_dir(task.user_id) / task_id
    else:
        task_dir = get_runs_dir() / task_id

    if task_dir.exists():
        import shutil
        shutil.rmtree(task_dir)

    session.delete(task)
    session.commit()
    logger.info(f"删除任务: {task_id}")
    return True


def get_user_tasks(
    session: Session,
    user_id: str,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
) -> dict:
    """获取用户的任务列表（分页）"""
    stmt = select(Task).where(Task.user_id == user_id)
    if status:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.order_by(col(Task.created_at).desc())

    # 总数
    count_stmt = select(Task).where(Task.user_id == user_id)
    if status:
        count_stmt = count_stmt.where(Task.status == status)
    all_tasks = session.exec(count_stmt).all()
    total = len(all_tasks)

    # 分页
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    tasks = session.exec(stmt).all()

    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": offset + limit < total,
    }


def get_all_tasks(
    session: Session,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
) -> dict:
    """获取所有任务（管理用，跨用户）"""
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.order_by(col(Task.created_at).desc())

    count_stmt = select(Task)
    if status:
        count_stmt = count_stmt.where(Task.status == status)
    total = len(session.exec(count_stmt).all())

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    tasks = session.exec(stmt).all()

    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": offset + limit < total,
    }


def task_to_response_dict(task: Task) -> dict:
    """将 Task ORM 对象转为 API 响应字典"""
    return {
        "task_id": task.task_id,
        "name": task.name,
        "status": task.status,
        "progress": task.progress,
        "stage": task.stage,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "updated_at": task.updated_at.isoformat() if task.updated_at else "",
        "error": task.error,
    }


def load_result_from_file(task: Task) -> Optional[dict]:
    """从文件系统加载任务结果"""
    if task.user_id:
        run_dir = get_user_run_dir(task.user_id) / task.task_id
    else:
        run_dir = get_runs_dir() / task.task_id

    report_path = run_dir / "report.json"
    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取报告文件失败: {report_path}, error={e}")
    return None
