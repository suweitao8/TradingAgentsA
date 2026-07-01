"""
B站 UP 主管理 API 路由
前缀：/api/bilibili
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.database import get_mongo_db
from app.core.response import ok
from app.services.bilibili_service import bilibili_service, fetch_up_info
from app.utils.timezone import now_tz

logger = logging.getLogger("webapi")
router = APIRouter(prefix="/bilibili", tags=["B站UP主管理"])


class AddUpmasterRequest(BaseModel):
    mid: str
    uname: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class UpdateUpmasterRequest(BaseModel):
    category: Optional[str] = None
    notes: Optional[str] = None


@router.get("/", response_model=dict)
async def get_upmasters(current_user: dict = Depends(get_current_user)):
    """获取 UP 主列表 + 每个的最新动态和股票提取"""
    try:
        result = await bilibili_service.get_upmasters_with_dynamics(current_user["id"])
        return ok(result)
    except Exception as e:
        logger.error(f"获取 UP 主列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {e}")


@router.post("/", response_model=dict)
async def add_upmaster(req: AddUpmasterRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = await bilibili_service.add_upmaster(current_user["id"], req.mid, req.uname or "", req.category or "", req.notes or "")
        if not result.get("added"):
            raise HTTPException(status_code=400, detail=result.get("message", "已存在"))
        return ok(result, message=f"已添加 UP 主: {result.get('uname')}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败: {e}")


@router.delete("/{mid}", response_model=dict)
async def remove_upmaster(mid: str, current_user: dict = Depends(get_current_user)):
    try:
        await bilibili_service.remove_upmaster(current_user["id"], mid)
        return ok({"mid": mid}, message="已移除")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除失败: {e}")


@router.put("/{mid}", response_model=dict)
async def update_upmaster(mid: str, req: UpdateUpmasterRequest, current_user: dict = Depends(get_current_user)):
    try:
        db = get_mongo_db()
        set_fields = {}
        if req.category is not None:
            set_fields["upmasters.$.category"] = req.category
        if req.notes is not None:
            set_fields["upmasters.$.notes"] = req.notes
        if set_fields:
            await db.user_bili_upmasters.update_one({"user_id": current_user["id"], "upmasters.mid": mid}, {"$set": set_fields})
        return ok({"mid": mid}, message="已更新")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {e}")


@router.get("/search-up", response_model=dict)
async def search_up_master(mid: str, current_user: dict = Depends(get_current_user)):
    """根据 UID 查询 UP 主信息（添加前预览）"""
    try:
        info = await fetch_up_info(mid)
        if not info:
            raise HTTPException(status_code=404, detail="未找到该 UID 对应的 UP 主")
        return ok(info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
