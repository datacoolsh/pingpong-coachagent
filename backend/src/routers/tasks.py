"""
任务管理路由 - 历史、队列、状态、分享、删除
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from ..database import get_session
from ..auth.dependencies import get_effective_user_id
from ..services.task_service import (
    get_task,
    find_task_globally,
    update_task,
    delete_task,
    get_user_tasks,
    get_user_run_dir,
    task_to_response_dict,
    load_result_from_file,
)
from ..core.task_queue import task_queue
from ..schemas.task import TaskResponse, TaskListResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["任务管理"])


@router.get("/api/history", response_model=TaskListResponse)
async def get_history_tasks(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """获取历史任务列表"""
    result = get_user_tasks(session, user_id, page, limit, status)

    tasks_response = [task_to_response_dict(t) for t in result["tasks"]]

    return TaskListResponse(
        tasks=tasks_response,
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        has_more=result["has_more"],
    )


@router.get("/api/queue")
async def get_task_queue_status(session: Session = Depends(get_session)):
    """获取当前任务队列"""
    queue_ids = task_queue.get_queue_task_ids()
    queue_tasks = []
    for tid in queue_ids:
        task = get_task(session, tid)
        if task:
            queue_tasks.append(task_to_response_dict(task))

    # 还包括正在处理的任务（从运行时状态获取）
    processing_tasks = []
    for tid, state in task_queue._runtime_state.items():
        if state.get("status") in ["processing", "extracting", "computing", "analyzing"]:
            if tid not in queue_ids:
                task = get_task(session, tid)
                if task:
                    processing_tasks.append(task_to_response_dict(task))

    all_tasks = queue_tasks + processing_tasks
    return {"tasks": all_tasks, "total": len(all_tasks)}


@router.get("/api/tasks/{task_id}/status", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    session: Session = Depends(get_session),
):
    """获取任务状态"""
    task = get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResponse(**task_to_response_dict(task))


@router.post("/api/tasks/{task_id}/share")
async def share_task(
    task_id: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """设置任务为公开分享状态"""
    task = find_task_globally(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="只有任务创建者才能设置分享状态")

    # 更新数据库
    update_task(session, task_id, is_public=True)

    # 更新文件
    task_user_id = task.user_id or user_id
    user_run_dir = get_user_run_dir(task_user_id)
    report_path = user_run_dir / task_id / "report.json"

    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            report["is_public"] = True
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[分享任务] 更新 report.json 失败: {e}")

    return {"success": True, "message": "任务已设置为公开分享", "task_id": task_id, "is_public": True}


@router.delete("/api/tasks/{task_id}")
async def delete_task_endpoint(
    task_id: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """删除任务"""
    task = find_task_globally(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权删除此任务")

    # 从队列中移除
    task_queue.remove_from_queue(task_id)
    task_queue.clear_runtime_state(task_id)

    delete_task(session, task_id)
    return {"success": True, "message": "任务已删除"}
