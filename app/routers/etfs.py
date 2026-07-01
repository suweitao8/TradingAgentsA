"""
ETF 自选管理 API 路由

复制自 favorites.py 的模式，prefix="/etfs"。
额外提供 GET /popular 返回预置热门 ETF 清单，供前端一键导入。
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
# 预置热门 ETF 清单（约 30 只，覆盖主流宽基/行业/主题/跨境）
# ---------------------------------------------------------------------------

POPULAR_ETFS: List[dict] = [
    # 宽基指数
    {"fund_code": "510300", "fund_name": "沪深300ETF", "fund_type": "宽基"},
    {"fund_code": "510050", "fund_name": "上证50ETF", "fund_type": "宽基"},
    {"fund_code": "159949", "fund_name": "创业板50ETF", "fund_type": "宽基"},
    {"fund_code": "588000", "fund_name": "科创50ETF", "fund_type": "宽基"},
    {"fund_code": "510500", "fund_name": "中证500ETF", "fund_type": "宽基"},
    {"fund_code": "159901", "fund_name": "深100ETF", "fund_type": "宽基"},
    # 科技/半导体
    {"fund_code": "512480", "fund_name": "半导体ETF", "fund_type": "主题"},
    {"fund_code": "512760", "fund_name": "半导体50ETF", "fund_type": "主题"},
    {"fund_code": "159995", "fund_name": "芯片ETF", "fund_type": "主题"},
    {"fund_code": "515050", "fund_name": "5GETF", "fund_type": "主题"},
    {"fund_code": "515790", "fund_name": "光伏ETF", "fund_type": "主题"},
    {"fund_code": "159998", "fund_name": "计算机ETF", "fund_type": "主题"},
    # 医疗
    {"fund_code": "512010", "fund_name": "医药ETF", "fund_type": "行业"},
    {"fund_code": "512170", "fund_name": "医疗ETF", "fund_type": "行业"},
    {"fund_code": "159992", "fund_name": "创新药ETF", "fund_type": "行业"},
    # 新能源
    {"fund_code": "516160", "fund_name": "新能源车ETF", "fund_type": "主题"},
    {"fund_code": "515030", "fund_name": "新能源ETF", "fund_type": "主题"},
    {"fund_code": "562500", "fund_name": "储能ETF", "fund_type": "主题"},
    # 消费
    {"fund_code": "510150", "fund_name": "消费ETF", "fund_type": "行业"},
    {"fund_code": "159928", "fund_name": "消费ETF", "fund_type": "行业"},
    {"fund_code": "515170", "fund_name": "食品饮料ETF", "fund_type": "行业"},
    # 金融
    {"fund_code": "512000", "fund_name": "券商ETF", "fund_type": "行业"},
    {"fund_code": "512800", "fund_name": "银行ETF", "fund_type": "行业"},
    {"fund_code": "515020", "fund_name": "红利ETF", "fund_type": "策略"},
    # 军工/周期
    {"fund_code": "512660", "fund_name": "军工ETF", "fund_type": "行业"},
    {"fund_code": "512690", "fund_name": "酒ETF", "fund_type": "行业"},
    {"fund_code": "515220", "fund_name": "煤炭ETF", "fund_type": "行业"},
    {"fund_code": "512400", "fund_name": "有色金属ETF", "fund_type": "行业"},
    # 跨境
    {"fund_code": "513050", "fund_name": "中概互联ETF", "fund_type": "跨境"},
    {"fund_code": "513100", "fund_name": "纳指ETF", "fund_type": "跨境"},
    {"fund_code": "159920", "fund_name": "恒生ETF", "fund_type": "跨境"},
]


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


async def _fetch_top_etfs_by_amount(top_n: int = 30) -> list:
    """从东方财富拉取按成交额降序的前 N 只 ETF。

    休市/非交易时段成交额为空时返回空列表，由调用方降级到静态清单。
    """
    import asyncio
    import requests

    try:
        def _do_fetch():
            url = "https://82.push2delay.eastmoney.com/api/qt/clist/get"
            params = {
                "po": "1",           # 降序
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2", "invt": "2",
                "fid": "f6",         # 按成交额排序
                "fs": "b:MK0021",    # 沪深 ETF
                "fields": "f2,f3,f6,f12,f14",
                "pn": "1", "pz": str(top_n + 20),  # 多拉一些，过滤掉无成交额的
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data") or {}
            diff = data.get("diff") or []

            result = []
            for item in diff:
                amount = item.get("f6")
                # 休市时段 amount 为 "-" 或 None，过滤掉
                if amount is None or amount == "-" or amount == 0:
                    continue
                result.append({
                    "fund_code": str(item.get("f12", "")).strip().zfill(6),
                    "fund_name": item.get("f14", ""),
                    "fund_type": "热门",  # 动态拉取无法自动分类，统一标记
                    "current_price": item.get("f2") if item.get("f2") != "-" else None,
                    "change_percent": item.get("f3") if item.get("f3") != "-" else None,
                })
                if len(result) >= top_n:
                    break
            return result

        return await asyncio.to_thread(_do_fetch)
    except Exception as e:
        logger.warning(f"动态拉取热门 ETF 失败: {e}")
        return []


@router.get("/popular", response_model=dict)
async def get_popular_etfs(
    current_user: dict = Depends(get_current_user),
):
    """返回热门 ETF 清单（按成交额动态排名），附带行情 + 是否已加入自选。

    策略：
    1. 优先从东方财富按当日成交额降序拉取 TOP 30（反映真实市场热度）
    2. 休市/非交易时段成交额为空时，降级到硬编码的 POPULAR_ETFS 静态清单
    """
    try:
        # 查当前用户已有 ETF
        added_codes = set()
        try:
            added_codes = await etfs_service.get_added_codes(current_user["id"])
        except Exception:
            pass

        # 1) 动态拉取成交额 TOP ETF
        dynamic_list = await _fetch_top_etfs_by_amount(30)

        if dynamic_list and len(dynamic_list) >= 10:
            # 动态拉取成功，附加 is_added 标记
            for e in dynamic_list:
                e["is_added"] = e["fund_code"] in added_codes
            return ok(dynamic_list)

        # 2) 降级：动态拉取不足（休市），用硬编码清单 + 行情富集
        logger.info("动态热门 ETF 不足，降级到静态清单")
        from app.services.quotes_service import get_quotes_service

        codes = [e["fund_code"] for e in POPULAR_ETFS]
        svc = get_quotes_service()
        quotes = await svc.get_etf_quotes(codes)

        result = []
        for e in POPULAR_ETFS:
            q = quotes.get(e["fund_code"], {})
            result.append({
                **e,
                "current_price": q.get("close"),
                "change_percent": q.get("pct_chg"),
                "is_added": e["fund_code"] in added_codes,
            })
        return ok(result)
    except Exception as e:
        logger.error(f"获取热门 ETF 失败: {e}", exc_info=True)
        result = [{**e, "current_price": None, "change_percent": None, "is_added": False} for e in POPULAR_ETFS]
        return ok(result)


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
