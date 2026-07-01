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


import re as _re

# 宽基指数名称特征（用于过滤，用户要板块/主题热门，不要沪深300/上证50这类宽基）
_BROAD_INDEX_KEYWORDS = ("沪深300", "上证50", "上证180", "深证", "深100", "中证500",
                         "中证1000", "中证A500", "创业板50", "创业板指", "科创50",
                         "科创100", "科创200", "双创50", "MSCI", "国证2000")


def _is_broad_index(name: str) -> bool:
    """判断是否宽基指数（过于宽泛，板块热门排名时应过滤掉）。"""
    for kw in _BROAD_INDEX_KEYWORDS:
        if kw in name:
            return True
    return False


def _extract_sector(name: str) -> str:
    """从 ETF 名称中提取板块/主题关键词，用于同类去重。

    例：'科创芯片ETF富国' -> '科创芯片'，'集成电路ETF嘉实' -> '集成电路'
    """
    # 去掉常见后缀
    cleaned = name
    for suffix in ("ETF", "指数", "基金", "LOF"):
        cleaned = cleaned.replace(suffix, "")
    # 去掉基金公司名（常见后缀）
    for company in ("华泰柏瑞", "华夏", "易方达", "嘉实", "南方", "富国", "国泰",
                    "汇添富", "广发", "博时", "鹏华", "景顺", "银华", "大成",
                    "摩根", "前海开源", "兴业", "兴银", "东财", "建信", "招商"):
        if cleaned.endswith(company):
            cleaned = cleaned[:-len(company)]
    return cleaned.strip() or name


async def _fetch_top_etfs_by_amount(top_n: int = 30) -> list:
    """拉取热门板块 ETF，模拟同花顺的板块热度排名逻辑。

    策略：
    1. 按涨跌幅绝对值降序排列（涨幅大的板块最活跃），拉取前 100 只
    2. 过滤掉宽基指数（沪深300/上证50 等，用户要板块热门不要宽基）
    3. 过滤掉可转债 ETF、货币基金等非股票型
    4. 同板块去重（科创50 有 5 家公司的，只保留涨幅最高那只）
    5. 取前 N 只，从名称推断板块类型
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
                "fid": "f3",         # 按涨跌幅排序（成交额休市为空，涨跌幅有数据）
                "fs": "b:MK0021",    # 沪深 ETF
                "fields": "f2,f3,f6,f8,f12,f14",
                "pn": "1", "pz": "100",  # 多拉后端过滤
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data") or {}
            diff = data.get("diff") or []

            # Step 1: 提取有效条目（有价格、有涨跌幅）
            items = []
            for d in diff:
                price = d.get("f2")
                pct = d.get("f3")
                if price in (None, "-", 0) or pct in (None, "-"):
                    continue
                name = d.get("f14", "")
                code = str(d.get("f12", "")).strip().zfill(6)
                items.append({
                    "fund_code": code,
                    "fund_name": name,
                    "current_price": float(price) if price != "-" else None,
                    "change_percent": float(pct) if pct != "-" else None,
                    "_amount": d.get("f6"),
                    "_turnover": d.get("f8"),
                })

            # Step 2: 过滤宽基指数和非股票型
            filtered = []
            for it in items:
                name = it["fund_name"]
                if _is_broad_index(name):
                    continue
                # 过滤可转债/货币/QDII 债券型
                if any(kw in name for kw in ("可转债", "货币", "国债", "信用债", "短融")):
                    continue
                filtered.append(it)

            # Step 3: 同板块去重（按提取的板块关键词分组，每组保留涨幅绝对值最大的）
            sector_best = {}  # sector_key -> item
            sector_order = []  # 保持排序顺序
            for it in filtered:
                sector = _extract_sector(it["fund_name"])
                abs_pct = abs(it["change_percent"]) if it["change_percent"] is not None else 0
                if sector not in sector_best:
                    sector_best[sector] = it
                    sector_order.append(sector)
                else:
                    existing = sector_best[sector]
                    existing_abs = abs(existing["change_percent"]) if existing["change_percent"] is not None else 0
                    if abs_pct > existing_abs:
                        sector_best[sector] = it

            # Step 4: 按涨幅绝对值重新排序（板块级别），取 top_n
            result_sectors = sorted(
                sector_order,
                key=lambda s: abs(sector_best[s]["change_percent"]) if sector_best[s]["change_percent"] else 0,
                reverse=True,
            )[:top_n]

            # Step 5: 构建返回结果，从名称推断 fund_type
            result = []
            for sector in result_sectors:
                it = sector_best[sector]
                name = it["fund_name"]
                result.append({
                    "fund_code": it["fund_code"],
                    "fund_name": name,
                    "fund_type": _guess_fund_type(name),
                    "current_price": it["current_price"],
                    "change_percent": it["change_percent"],
                })
            return result

        return await asyncio.to_thread(_do_fetch)
    except Exception as e:
        logger.warning(f"动态拉取热门 ETF 失败: {e}")
        return []


def _guess_fund_type(name: str) -> str:
    """从 ETF 名称推断板块/类型标签。"""
    type_map = [
        ("半导体", "半导体"), ("芯片", "芯片"), ("集成电路", "芯片"),
        ("光伏", "光伏"), ("新能源车", "新能源车"), ("新能源", "新能源"),
        ("锂电", "锂电池"), ("储能", "储能"), ("风电", "风电"),
        ("医药", "医药"), ("医疗", "医疗"), ("创新药", "创新药"), ("生物", "生物医药"),
        ("食品", "食品饮料"), ("白酒", "白酒"), ("酒", "白酒"),
        ("券商", "券商"), ("银行", "银行"), ("保险", "保险"), ("金融", "金融"),
        ("军工", "军工"), ("国防", "军工"),
        ("煤炭", "煤炭"), ("有色", "有色金属"), ("钢铁", "钢铁"),
        ("房地产", "房地产"), ("建材", "建材"),
        ("消费", "消费"), ("电子", "电子"), ("计算机", "计算机"), ("软件", "软件"),
        ("通信", "通信"), ("5G", "5G"), ("人工智能", "AI"), ("AI", "AI"),
        ("机器人", "机器人"), ("物联网", "物联网"),
        ("互联网", "互联网"), ("传媒", "传媒"), ("游戏", "游戏"),
        ("稀土", "稀土"), ("石油", "石油"), ("化工", "化工"),
        ("央企", "央企"), ("国企", "国企"),
        ("科创", "科创"), ("纳指", "纳指"), ("恒生", "恒生"), ("中概", "中概"),
        ("地产", "地产"), ("环保", "环保"), ("电力", "电力"), ("农业", "农业"),
        ("基建", "基建"), ("机械", "机械"), ("航空", "航空"),
    ]
    for keyword, label in type_map:
        if keyword in name:
            return label
    return "主题"


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
