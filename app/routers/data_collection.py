"""
数据采集 API 路由
整合自选股实时行情 + 技术指标 + 新闻数据采集，提供一键采集和 Markdown 导出能力。
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.response import ok
from app.services.favorites_service import favorites_service

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/data-collection", tags=["数据采集"])


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    """数据采集请求"""
    stock_codes: List[str] = Field(default_factory=list, description="股票代码列表，为空则使用自选股")
    include_news: bool = Field(True, description="是否采集新闻")
    news_limit: int = Field(3, ge=1, le=20, description="每只股票新闻条数")
    hist_days: int = Field(420, ge=30, le=1000, description="历史K线回看天数")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """安全转换为 float"""
    if value is None:
        return default
    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            if math.isnan(float(value)):
                return default
        except Exception:
            pass
        return float(value)
    s = str(value).strip()
    if s in ("", "-", "--", "None", "nan", "NaN"):
        return default
    s = s.replace(",", "").replace("%", "")
    try:
        return float(s)
    except Exception:
        return default


def _amount_to_yi(value: Any) -> Optional[float]:
    """成交额 / 市值转亿元"""
    v = _safe_float(value)
    if v is None or math.isnan(v):
        return None
    return round(v / 1e8, 2)


def _get_market_board(code: str) -> str:
    """根据代码判断市场板块"""
    code = str(code).strip().zfill(6)
    if code.startswith("688"):
        return "科创板"
    if code.startswith("300"):
        return "创业板"
    if code.startswith(("000", "001", "002", "003")):
        return "深市主板"
    if code.startswith(("600", "601", "603", "605")):
        return "沪市主板"
    return "其他"


# ---------------------------------------------------------------------------
# 实时行情采集
# ---------------------------------------------------------------------------

def _fetch_spot_data_em(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    东方财富全市场快照，字段最全（量比/PE/PB/市值等）。
    若接口不可用或被限流则返回空 dict，由上层回退。
    """
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        if df is None or getattr(df, "empty", True):
            logger.warning("AKShare 东方财富 spot 返回空数据")
            return {}

        codes_set = {str(c).strip().zfill(6) for c in codes}

        def find_col(candidates: List[str]) -> Optional[str]:
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        code_col = find_col(["代码", "股票代码", "code"])
        name_col = find_col(["名称", "股票简称", "name"])
        price_col = find_col(["最新价", "现价", "最新"])
        pct_col = find_col(["涨跌幅", "涨跌幅%"])
        speed_col = find_col(["涨速"])
        min5_col = find_col(["5分钟涨跌", "5分钟涨跌幅"])
        ratio_col = find_col(["量比"])
        turnover_col = find_col(["换手率", "换手率%"])
        amount_col = find_col(["成交额"])
        total_mv_col = find_col(["总市值"])
        circ_mv_col = find_col(["流通市值"])
        pe_col = find_col(["市盈率-动态", "动态市盈率"])
        pb_col = find_col(["市净率"])

        if not code_col or not price_col:
            logger.error(f"AKShare 东方财富 spot 缺少必要列: code={code_col}, price={price_col}")
            return {}

        result: Dict[str, Dict[str, Any]] = {}
        for _, row in df.iterrows():
            code_raw = row.get(code_col)
            if not code_raw:
                continue
            code = str(code_raw).strip().zfill(6)
            if code not in codes_set:
                continue

            result[code] = {
                "code": code,
                "name": str(row.get(name_col, "")) if name_col else "",
                "market_board": _get_market_board(code),
                "price": _safe_float(row.get(price_col)),
                "change_percent": _safe_float(row.get(pct_col) if pct_col else None),
                "speed": _safe_float(row.get(speed_col) if speed_col else None),
                "min5_change": _safe_float(row.get(min5_col) if min5_col else None),
                "volume_ratio": _safe_float(row.get(ratio_col) if ratio_col else None),
                "turnover_rate": _safe_float(row.get(turnover_col) if turnover_col else None),
                "amount_yi": _amount_to_yi(row.get(amount_col) if amount_col else None),
                "total_mv_yi": _amount_to_yi(row.get(total_mv_col) if total_mv_col else None),
                "circ_mv_yi": _amount_to_yi(row.get(circ_mv_col) if circ_mv_col else None),
                "pe": _safe_float(row.get(pe_col) if pe_col else None),
                "pb": _safe_float(row.get(pb_col) if pb_col else None),
            }

        logger.info(f"东方财富 spot 拉取完成: 请求 {len(codes_set)} 只, 命中 {len(result)} 只")
        return result

    except Exception as e:
        logger.warning(f"东方财富 spot 不可用: {e}")
        return {}


def _fetch_spot_data_sina(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    新浪源全市场快照，字段较少（最新价/涨跌幅/成交额），作为东方财富不可用时的回退。
    新浪源代码格式为 sz000001 / sh600036，需去掉前缀。
    """
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot()
        if df is None or getattr(df, "empty", True):
            logger.warning("AKShare 新浪 spot 返回空数据")
            return {}

        codes_set = {str(c).strip().zfill(6) for c in codes}

        def find_col(candidates: List[str]) -> Optional[str]:
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        code_col = find_col(["代码", "股票代码", "code"])
        name_col = find_col(["名称", "股票简称", "name"])
        price_col = find_col(["最新价", "现价", "最新"])
        pct_col = find_col(["涨跌幅", "涨跌幅%"])
        amount_col = find_col(["成交额"])

        if not code_col or not price_col:
            logger.error(f"新浪 spot 缺少必要列: code={code_col}, price={price_col}")
            return {}

        result: Dict[str, Dict[str, Any]] = {}
        for _, row in df.iterrows():
            code_raw = str(row.get(code_col, "")).strip()
            # 新浪源代码格式 sz000001 / sh600036，取后6位
            code = code_raw[-6:].zfill(6) if len(code_raw) >= 6 else code_raw.zfill(6)
            if code not in codes_set:
                continue

            result[code] = {
                "code": code,
                "name": str(row.get(name_col, "")) if name_col else "",
                "market_board": _get_market_board(code),
                "price": _safe_float(row.get(price_col)),
                "change_percent": _safe_float(row.get(pct_col) if pct_col else None),
                "speed": None,
                "min5_change": None,
                "volume_ratio": None,
                "turnover_rate": None,
                "amount_yi": _amount_to_yi(row.get(amount_col) if amount_col else None),
                "total_mv_yi": None,
                "circ_mv_yi": None,
                "pe": None,
                "pb": None,
            }

        logger.info(f"新浪 spot 拉取完成: 请求 {len(codes_set)} 只, 命中 {len(result)} 只")
        return result

    except Exception as e:
        logger.warning(f"新浪 spot 不可用: {e}")
        return {}


def _fetch_spot_data(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    获取实时行情快照。优先东方财富（字段全），失败回退新浪源（字段少但稳定）。
    """
    result = _fetch_spot_data_em(codes)
    if result:
        return result
    logger.warning("东方财富 spot 不可用，回退到新浪源")
    return _fetch_spot_data_sina(codes)


# ---------------------------------------------------------------------------
# 历史K线获取 + 技术指标计算
# ---------------------------------------------------------------------------

def _get_kline_df(code: str, hist_days: int) -> pd.DataFrame:
    """
    获取历史K线并转为 DataFrame，用于技术指标计算。
    优先用 DataSourceManager 的 fallback 机制。
    """
    from app.services.data_sources.manager import DataSourceManager

    mgr = DataSourceManager()
    items, source = mgr.get_kline_with_fallback(
        code=str(code).zfill(6),
        period="day",
        limit=hist_days,
        adj="qfq",
    )

    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)
    # 统一列名
    col_map = {"time": "date", "日期": "date"}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 确保有 close 列
    if "close" not in df.columns:
        return pd.DataFrame()

    # 按日期排序
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)

    return df


def _calc_indicators(df: pd.DataFrame, latest_price: Optional[float]) -> Dict[str, Any]:
    """
    计算技术指标，复用 tradingagents/tools/analysis/indicators.py 的 add_all_indicators。
    额外计算乖离率、涨跌幅、布林位置等。
    """
    empty = {
        "ma5": None, "ma10": None, "ma20": None, "ma60": None,
        "ma5_bias": None, "ma20_bias": None, "ma60_bias": None,
        "macd_dif": None, "macd_dea": None, "macd_hist": None,
        "rsi14": None, "boll_position": None,
        "pct_5d": None, "pct_20d": None, "pct_60d": None,
        "pct_60d_drawdown": None, "pct_ytd": None,
        "avg_amount_20d_yi": None,
        "avg_turnover_5d": None, "avg_turnover_20d": None,
    }

    if df is None or df.empty or "close" not in df.columns:
        return empty

    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if len(close) < 20:
        return empty

    last = _safe_float(latest_price)
    if last is None or math.isnan(last):
        last = float(close.iloc[-1])

    res: Dict[str, Any] = {}

    # 用项目已有的技术指标库
    try:
        from tradingagents.tools.analysis.indicators import add_all_indicators

        df_copy = df.copy()
        df_copy["close"] = pd.to_numeric(df_copy["close"], errors="coerce")
        if "high" in df_copy.columns:
            df_copy["high"] = pd.to_numeric(df_copy["high"], errors="coerce")
        if "low" in df_copy.columns:
            df_copy["low"] = pd.to_numeric(df_copy["low"], errors="coerce")
        df_copy = add_all_indicators(df_copy, close_col="close", rsi_style="international")

        last_row = df_copy.iloc[-1]
        res["ma5"] = _safe_float(last_row.get("ma5"))
        res["ma10"] = _safe_float(last_row.get("ma10"))
        res["ma20"] = _safe_float(last_row.get("ma20"))
        res["ma60"] = _safe_float(last_row.get("ma60"))
        res["macd_dif"] = _safe_float(last_row.get("macd_dif"))
        res["macd_dea"] = _safe_float(last_row.get("macd_dea"))
        res["macd_hist"] = _safe_float(last_row.get("macd"))
        res["rsi14"] = _safe_float(last_row.get("rsi"))

        # 布林位置 = (close - lower) / (upper - lower)
        boll_upper = _safe_float(last_row.get("boll_upper"))
        boll_lower = _safe_float(last_row.get("boll_lower"))
        if boll_upper is not None and boll_lower is not None and boll_upper != boll_lower:
            res["boll_position"] = round((last - boll_lower) / (boll_upper - boll_lower), 2)
    except Exception as e:
        logger.warning(f"技术指标计算失败: {e}")

    # 乖离率
    for n, key in [(5, "ma5_bias"), (20, "ma20_bias"), (60, "ma60_bias")]:
        ma_val = res.get(f"ma{n}")
        if ma_val and not math.isnan(ma_val) and ma_val != 0:
            res[key] = round((last / ma_val - 1) * 100, 2)

    # 涨跌幅
    def pct_change_days(n: int) -> Optional[float]:
        if len(close) <= n:
            return None
        base = close.iloc[-1 - n]
        if base == 0 or math.isnan(base):
            return None
        return round((last / base - 1) * 100, 2)

    res["pct_5d"] = pct_change_days(5)
    res["pct_20d"] = pct_change_days(20)
    res["pct_60d"] = pct_change_days(60)

    # 60日高点回撤
    if "high" in df.columns and len(df) >= 60:
        high = pd.to_numeric(df["high"], errors="coerce")
        high_60 = high.tail(60).max()
        if high_60 and not math.isnan(high_60) and high_60 > 0:
            res["pct_60d_drawdown"] = round((last / high_60 - 1) * 100, 2)

    # 年初至今涨跌幅
    if "date" in df.columns:
        cur_year = datetime.now().year
        ytd_df = df[pd.to_datetime(df["date"]).dt.year == cur_year]
        if not ytd_df.empty:
            ytd_close = pd.to_numeric(ytd_df["close"], errors="coerce").dropna()
            if len(ytd_close) > 0 and ytd_close.iloc[0] != 0:
                res["pct_ytd"] = round((last / ytd_close.iloc[0] - 1) * 100, 2)

    # 近20日均成交额（亿元）
    if "amount" in df.columns:
        amount = pd.to_numeric(df["amount"], errors="coerce")
        if len(amount.dropna()) > 0:
            res["avg_amount_20d_yi"] = round(amount.tail(20).mean() / 1e8, 2)

    # 对齐 empty 字段
    for k in empty:
        res.setdefault(k, empty[k])

    return res


# ---------------------------------------------------------------------------
# 新闻采集
# ---------------------------------------------------------------------------

async def _fetch_news(code: str, limit: int) -> List[Dict[str, Any]]:
    """获取个股新闻，复用 news_data_service 的查询能力"""
    try:
        from app.services.news_data_service import get_news_data_service, NewsQueryParams

        service = get_news_data_service()
        params = NewsQueryParams(
            symbol=str(code).zfill(6),
            limit=limit,
            sort_by="publish_time",
            sort_order=-1,
        )
        news_list = await service.query_news(params)

        # 如果库中没有，尝试实时拉取
        if not news_list:
            try:
                from app.worker.news_data_sync_service import get_news_data_sync_service

                sync_service = get_news_data_sync_service()
                await sync_service.sync_single_stock(str(code).zfill(6), hours_back=72, max_news=limit)
                # 重新查询
                news_list = await service.query_news(params)
            except Exception as e:
                logger.warning(f"实时拉取新闻失败 {code}: {e}")

        # 格式化返回
        result = []
        for item in news_list[:limit]:
            result.append({
                "code": str(code).zfill(6),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "publish_time": str(item.get("publish_time", "")),
            })
        return result

    except Exception as e:
        logger.warning(f"获取新闻失败 {code}: {e}")
        return []


# ---------------------------------------------------------------------------
# 核心采集端点
# ---------------------------------------------------------------------------

@router.post("/collect", response_model=dict)
async def collect_data(
    request: CollectRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    一键采集自选股数据：实时行情 + 技术指标 + 新闻。

    - stock_codes 为空时自动获取用户自选股列表
    - 返回结构化数据供前端表格展示和 Markdown 导出
    """
    warnings: List[str] = []
    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 确定股票代码列表
    codes = [str(c).strip().zfill(6) for c in request.stock_codes if c and str(c).strip()]
    if not codes:
        # 从自选股获取
        try:
            favorites = await favorites_service.get_user_favorites(current_user["id"])
            codes = [str(f.get("stock_code", "")).strip().zfill(6) for f in favorites if f.get("stock_code")]
            if not codes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="没有指定股票代码，且自选股列表为空",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取自选股列表失败: {str(e)}",
            )

    logger.info(f"📊 数据采集开始: {len(codes)} 只股票, include_news={request.include_news}")

    # 2. 批量获取实时行情（在线程中执行阻塞IO）
    spot_data = await asyncio.to_thread(_fetch_spot_data, codes)

    # 3. 逐股获取历史K线 + 计算技术指标
    stocks_result: List[Dict[str, Any]] = []

    for code in codes:
        spot = spot_data.get(code, {})
        if not spot:
            warnings.append(f"{code} 实时行情未命中，将尝试用K线最新数据")

        try:
            # 获取历史K线并计算技术指标
            kline_df = await asyncio.to_thread(_get_kline_df, code, request.hist_days)
            indicators = _calc_indicators(kline_df, spot.get("price"))

            # K线最新行兜底：当 spot 缺失或字段为空时用 K线最新值补充
            kline_latest: Dict[str, Any] = {}
            if kline_df is not None and not kline_df.empty:
                last_row = kline_df.iloc[-1]
                kline_latest = {
                    "price": _safe_float(last_row.get("close")) or spot.get("price"),
                    "change_percent": _safe_float(last_row.get("pct_chg")) or spot.get("change_percent"),
                    "turnover_rate": _safe_float(last_row.get("turnover_rate")) or spot.get("turnover_rate"),
                    "amount_yi": _amount_to_yi(last_row.get("amount")) or spot.get("amount_yi"),
                    "name": str(last_row.get("name", "")) if "name" in last_row else "",
                }

            # 合并：spot 优先，K线兜底
            price = spot.get("price") or kline_latest.get("price")
            name = spot.get("name") or kline_latest.get("name") or code

            if not price:
                warnings.append(f"{code} 无法获取任何价格数据，跳过")
                continue

            stock_item = {
                "code": code,
                "name": name,
                "market_board": spot.get("market_board") or _get_market_board(code),
                "price": price,
                "change_percent": spot.get("change_percent") or kline_latest.get("change_percent"),
                "speed": spot.get("speed"),
                "min5_change": spot.get("min5_change"),
                "volume_ratio": spot.get("volume_ratio"),
                "turnover_rate": spot.get("turnover_rate") or kline_latest.get("turnover_rate"),
                "amount_yi": spot.get("amount_yi") or kline_latest.get("amount_yi"),
                "total_mv_yi": spot.get("total_mv_yi"),
                "circ_mv_yi": spot.get("circ_mv_yi"),
                "pe": spot.get("pe"),
                "pb": spot.get("pb"),
                **indicators,
            }
            stocks_result.append(stock_item)

        except Exception as e:
            warnings.append(f"{code} {spot.get('name', '')} 处理失败: {e}")

    # 4. 获取新闻（如果启用）
    news_result: List[Dict[str, Any]] = []
    if request.include_news:
        for code in codes:
            news = await _fetch_news(code, request.news_limit)
            news_result.extend(news)

    logger.info(f"📊 数据采集完成: 股票 {len(stocks_result)} 只, 新闻 {len(news_result)} 条, 警告 {len(warnings)} 条")

    return ok(data={
        "stocks": stocks_result,
        "news": news_result,
        "warnings": warnings,
        "collected_at": collected_at,
        "total_stocks": len(stocks_result),
        "total_news": len(news_result),
    })
