"""
管理后台请求/响应 Schema
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class AdminUserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    role: str = Field(default="user", pattern="^(user|admin)$")


class AdminUserUpdate(BaseModel):
    """编辑用户请求"""
    role: Optional[str] = Field(default=None, pattern="^(user|admin)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)


class AdminUserResponse(BaseModel):
    """管理后台用户响应"""
    id: str
    username: str
    role: str
    is_active: bool
    legacy_cookie_id: Optional[str] = None
    created_at: str
    updated_at: str


class AdminUserListResponse(BaseModel):
    """用户列表响应"""
    users: List[AdminUserResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class AdminTaskResponse(BaseModel):
    """管理后台任务响应"""
    task_id: str
    user_id: Optional[str] = None
    name: str
    status: str
    progress: int
    is_public: bool
    created_at: str
    updated_at: str


class AdminTaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[AdminTaskResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class AdminStatsResponse(BaseModel):
    """统计数据响应"""
    total_users: int
    active_users: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int


class AdminConfigItem(BaseModel):
    """配置项"""
    key: str
    value: str
    description: Optional[str] = None


class AdminConfigUpdate(BaseModel):
    """更新配置请求"""
    value: str
    description: Optional[str] = None
