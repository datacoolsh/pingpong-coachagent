"""
WebSocket 路由 - 实时任务状态推送
"""

import os
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlmodel import Session

from ..database import get_session
from ..services.task_service import get_task, task_to_response_dict
from ..core.task_queue import task_queue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    """WebSocket 连接 - 实时接收任务状态更新"""
    await websocket.accept()
    logger.info(f"[WebSocket] 连接已建立: task_id={task_id}")

    # 使用独立的 session 查询初始状态
    from ..database import engine
    with Session(engine) as session:
        task = get_task(session, task_id)
        if not task:
            logger.warning(f"[WebSocket] 任务不存在: task_id={task_id}")
            await websocket.close(code=1008, reason="任务不存在")
            return
        initial_state = task_to_response_dict(task)

    # 添加 WebSocket 连接
    task_queue.add_websocket(task_id, websocket)

    try:
        # 发送初始状态
        await websocket.send_json(initial_state)

        # 保持连接
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] 客户端断开连接: task_id={task_id}")
    except Exception as e:
        logger.error(f"[WebSocket] 连接异常: task_id={task_id}, error={e}")
    finally:
        task_queue.remove_websocket(task_id, websocket)
