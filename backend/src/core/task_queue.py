"""
内存任务队列 + WebSocket 连接管理

从旧 TaskManager 中提取，只保留运行时内存状态（队列、WebSocket）。
持久化 CRUD 已移至 services/task_service.py。
"""

import asyncio
import logging
from typing import Optional, List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class TaskQueue:
    """内存任务队列与 WebSocket 管理"""

    def __init__(self):
        self.queue: List[str] = []
        self.websocket_connections: dict[str, list[WebSocket]] = {}
        # 运行时缓存：task_id -> 实时状态 dict（用于 WebSocket 推送）
        self._runtime_state: dict[str, dict] = {}

    # ---- 队列管理 ----

    def add_to_queue(self, task_id: str):
        """添加任务到队列"""
        if task_id not in self.queue:
            self.queue.append(task_id)

    def get_next_task(self) -> Optional[str]:
        """获取下一个待处理任务"""
        if self.queue:
            return self.queue.pop(0)
        return None

    def get_queue_task_ids(self) -> List[str]:
        """获取队列中的任务 ID 列表"""
        return list(self.queue)

    def remove_from_queue(self, task_id: str):
        """从队列中移除"""
        if task_id in self.queue:
            self.queue.remove(task_id)

    # ---- 运行时状态缓存（用于 WebSocket 推送） ----

    def set_runtime_state(self, task_id: str, state: dict):
        """设置运行时状态缓存"""
        self._runtime_state[task_id] = state
        # 触发 WebSocket 推送
        self._notify_websocket_sync(task_id, state)

    def get_runtime_state(self, task_id: str) -> Optional[dict]:
        """获取运行时状态缓存"""
        return self._runtime_state.get(task_id)

    def clear_runtime_state(self, task_id: str):
        """清除运行时状态缓存"""
        self._runtime_state.pop(task_id, None)

    # ---- WebSocket 管理 ----

    def add_websocket(self, task_id: str, websocket: WebSocket):
        """添加 WebSocket 连接"""
        if task_id not in self.websocket_connections:
            self.websocket_connections[task_id] = []
        self.websocket_connections[task_id].append(websocket)

    def remove_websocket(self, task_id: str, websocket: WebSocket):
        """移除 WebSocket 连接"""
        if task_id in self.websocket_connections:
            try:
                self.websocket_connections[task_id].remove(websocket)
            except ValueError:
                pass
            if not self.websocket_connections[task_id]:
                del self.websocket_connections[task_id]

    def _notify_websocket_sync(self, task_id: str, task_data: dict):
        """同步方式通知 WebSocket 客户端"""
        if task_id not in self.websocket_connections:
            return

        task_to_send = dict(task_data)

        # 清理可能不可序列化的字段
        if "result" in task_to_send and task_to_send["result"] is not None:
            result = task_to_send["result"]
            if not isinstance(result, dict):
                task_to_send["result"] = str(result) if result else None

        dead_connections = []

        for ws in list(self.websocket_connections[task_id]):
            try:
                if ws.client is None:
                    dead_connections.append(ws)
                    continue

                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.ensure_future(
                        ws.send_json(task_to_send), loop=loop
                    )

                    def on_error(fut):
                        try:
                            fut.exception()
                        except Exception:
                            pass

                    future.add_done_callback(on_error)
                except RuntimeError:
                    pass

            except (WebSocketDisconnect, RuntimeError):
                dead_connections.append(ws)
            except Exception:
                dead_connections.append(ws)

        # 清理断开的连接
        for ws in dead_connections:
            try:
                self.websocket_connections[task_id].remove(ws)
            except (ValueError, KeyError):
                pass

        if (
            task_id in self.websocket_connections
            and not self.websocket_connections[task_id]
        ):
            del self.websocket_connections[task_id]


# 全局单例
task_queue = TaskQueue()
