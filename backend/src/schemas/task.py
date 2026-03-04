"""
任务相关请求/响应 Schema
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    name: str
    status: str
    progress: int = 0
    stage: Optional[str] = None
    created_at: str
    updated_at: str
    error: Optional[str] = None
    summary: Optional[str] = None


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    task_id: str
    message: str
    task: TaskResponse


class AnalysisRequest(BaseModel):
    """分析请求"""
    task_id: str
    target_player: Optional[str] = None
    scene_type: Optional[str] = None


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    message: str
    task_id: str


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class AnalysisResult(BaseModel):
    """分析结果详情"""
    task_id: str
    status: str
    created_at: str
    name: Optional[str] = None
    target_player: Optional[dict] = None
    coach_comment: Optional[dict] = None
    problems: Optional[List[dict]] = None
    suggestions: Optional[List[dict]] = None
    overall_score: Optional[int] = None
    summary: Optional[dict] = None
    details: Optional[dict] = None
