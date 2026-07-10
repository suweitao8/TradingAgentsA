"""
ETF 自选管理 API 路由

复制自 favorites.py 的模式，prefix="/etfs"。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from app.core.auth import get_current_user
from app.services.etfs_service import etfs_service
from app.core.response import ok

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/etfs", tags=["ETF自选管理"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------

class AddEtfRequest(BaseModel):
    """添加 ETF 请求"""
    fund_code: str
    fund_name: str
    fund_type: str = "主题"
    tags: List[str] = []
    notes: str = ""
    alert_price_high: Optional[float] = None
    alert_price_low: Optional[float] = None


class UpdateEtfRequest(BaseModel):
    """更新 ETF 请求"""
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    alert_price_high: Optional[float] = None
    alert_price_low: Optional[float] = None


class BatchAddEtfItem(BaseModel):
    """批量导入的单条 ETF"""
    fund_code: str
    fund_name: str
    fund_type: str = "主题"


class BatchAddEtfRequest(BaseModel):
    """批量导入 ETF 请求"""
    items: List[BatchAddEtfItem]


# ---------------------------------------------------------------------------
# 路由端点
# ---------------------------------------------------------------------------

@router.get("/", response_model=dict)
async def get_etfs(
    current_user: dict = Depends(get_current_user),
):
    """获取用户 ETF 自选列表（含实时行情）"""
    try:
        etfs = await etfs_service.get_user_etfs(current_user["id"])
        return ok(etfs)
    except Exception as e:
        logger.error(f"获取 ETF 自选失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 ETF 自选失败: {str(e)}",
        )


@router.post("/", response_model=dict)
async def add_etf(
    request: AddEtfRequest,
    current_user: dict = Depends(get_current_user),
):
    """添加 ETF 到自选"""
    try:
        is_exist = await etfs_service.is_etf(current_user["id"], request.fund_code)
        if is_exist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该 ETF 已在自选中",
            )

        success = await etfs_service.add_etf(
            user_id=current_user["id"],
            fund_code=request.fund_code,
            fund_name=request.fund_name,
            fund_type=request.fund_type,
            tags=request.tags,
            notes=request.notes,
            alert_price_high=request.alert_price_high,
            alert_price_low=request.alert_price_low,
        )
        if success:
            return ok({"fund_code": request.fund_code}, "添加成功")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加失败",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加 ETF 失败: {str(e)}",
        )


@router.post("/batch", response_model=dict)
async def batch_add_etfs(
    request: BatchAddEtfRequest,
    current_user: dict = Depends(get_current_user),
):
    """批量导入 ETF（自动跳过已存在的）"""
    try:
        added = []
        existed = []
        failed = []

        for item in request.items:
            try:
                is_exist = await etfs_service.is_etf(current_user["id"], item.fund_code)
                if is_exist:
                    existed.append(item.fund_code)
                    continue
                ok_add = await etfs_service.add_etf(
                    user_id=current_user["id"],
                    fund_code=item.fund_code,
                    fund_name=item.fund_name,
                    fund_type=item.fund_type,
                )
                if ok_add:
                    added.append(item.fund_code)
                else:
                    failed.append(item.fund_code)
            except Exception:
                failed.append(item.fund_code)

        return ok(
            {"added": added, "existed": existed, "failed": failed},
            f"导入完成: 成功 {len(added)} / 已存在 {len(existed)} / 失败 {len(failed)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导入失败: {str(e)}",
        )


@router.put("/{fund_code}", response_model=dict)
async def update_etf(
    fund_code: str,
    request: UpdateEtfRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新 ETF 自选信息"""
    try:
        success = await etfs_service.update_etf(
            user_id=current_user["id"],
            fund_code=fund_code,
            tags=request.tags,
            notes=request.notes,
            alert_price_high=request.alert_price_high,
            alert_price_low=request.alert_price_low,
        )
        if success:
            return ok({"fund_code": fund_code}, "更新成功")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETF 不存在",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新 ETF 失败: {str(e)}",
        )


@router.delete("/{fund_code}", response_model=dict)
async def remove_etf(
    fund_code: str,
    current_user: dict = Depends(get_current_user),
):
    """从自选中移除 ETF"""
    try:
        success = await etfs_service.remove_etf(current_user["id"], fund_code)
        if success:
            return ok({"fund_code": fund_code}, "移除成功")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETF 不存在",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除 ETF 失败: {str(e)}",
        )


@router.get("/check/{fund_code}", response_model=dict)
async def check_etf(
    fund_code: str,
    current_user: dict = Depends(get_current_user),
):
    """检查 ETF 是否已在自选中"""
    try:
        is_exist = await etfs_service.is_etf(current_user["id"], fund_code)
        return ok({"is_favorite": is_exist})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查失败: {str(e)}",
        )


@router.get("/tags", response_model=dict)
async def get_user_tags(
    current_user: dict = Depends(get_current_user),
):
    """获取用户所有 ETF 标签"""
    try:
        tags = await etfs_service.get_user_tags(current_user["id"])
        return ok(tags)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标签失败: {str(e)}",
        )
