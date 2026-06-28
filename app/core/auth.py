"""
单用户本地部署模式 — 认证 stub

本项目为单用户本地部署，不需要账户管理。此模块提供统一的 get_current_user
依赖注入函数，返回固定的管理员身份，供所有路由使用。
"""

from typing import Optional
from fastapi import Header


# 固定的管理员身份（单用户模式）
# id 统一为 "admin"，与 WebSocket、历史分析任务数据保持一致
LOCAL_ADMIN_USER = {
    "id": "admin",
    "username": "admin",
    "email": "admin@local",
    "name": "管理员",
    "is_admin": True,
    "roles": ["admin"],
    "preferences": {},
}


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """获取当前用户信息（单用户本地部署模式）。

    跳过所有 token 校验，直接返回固定的管理员身份。
    前端无需登录即可访问所有接口。
    """
    return LOCAL_ADMIN_USER.copy()
