"""
认证相关请求/响应 Schema
"""

from typing import Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    role: str
    is_active: bool
    legacy_cookie_id: Optional[str] = None
