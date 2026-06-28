"""
设置 API 路由 — 偏好设置

单用户本地部署模式下，偏好设置存储在 system_configs 集合中，
不再绑定用户账户。本路由提供偏好设置的读写接口。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.core.auth import get_current_user
from app.services.preferences_service import get_preferences_async, update_preferences

router = APIRouter()


class PreferencesUpdateRequest(BaseModel):
    """偏好设置更新请求（支持部分更新）"""
    pass  # 接受任意字段，在服务层校验


@router.get("/preferences")
async def get_user_preferences(user: dict = Depends(get_current_user)):
    """获取偏好设置"""
    prefs = await get_preferences_async()
    return {
        "success": True,
        "data": prefs.model_dump(),
        "message": "获取偏好设置成功"
    }


@router.put("/preferences")
async def update_user_preferences(
    payload: Dict[str, Any],
    user: dict = Depends(get_current_user)
):
    """更新偏好设置（支持部分更新）"""
    prefs = await update_preferences(payload)
    return {
        "success": True,
        "data": prefs.model_dump(),
        "message": "更新偏好设置成功"
    }
