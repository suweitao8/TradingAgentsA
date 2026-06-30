"""
自选股分析报告 API 路由

提供报告查询、手动触发生成、当日徽标判断。
路径前缀：/api/favorites/reports（在 main.py 中以 prefix="/api" 挂载 favorites router，
本 router 再 include 到 favorites router 下，前缀 /reports）
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.auth import get_current_user
from app.core.response import ok
from app.models.favorite_report import GenerateReportRequest
from app.services.favorite_report_service import get_favorite_report_service

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/reports", tags=["自选股分析报告"])


@router.get("/{stock_code}", response_model=dict)
async def get_stock_reports(
    stock_code: str,
    report_type: str = Query("all", description="all/daily/realtime"),
    trade_date: Optional[str] = Query(None, description="交易日 YYYY-MM-DD，默认当天"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """查询当前用户某只自选股的分析报告（每日 + 盘中实时）"""
    try:
        svc = get_favorite_report_service()
        result = await svc.get_user_stock_reports(
            user_id=current_user["id"],
            stock_code=stock_code,
            report_type=report_type,
            trade_date=trade_date,
            limit=limit,
        )
        return ok(result)
    except Exception as e:
        logger.error(f"❌ 查询自选股报告失败 {stock_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询报告失败: {e}",
        )


@router.get("/{stock_code}/latest", response_model=dict)
async def get_latest_report(
    stock_code: str,
    current_user: dict = Depends(get_current_user),
):
    """取该股票最新一份报告（优先 daily，其次 realtime）"""
    try:
        svc = get_favorite_report_service()
        report = await svc.get_latest_report(current_user["id"], stock_code)
        return ok(report)
    except Exception as e:
        logger.error(f"❌ 查询最新报告失败 {stock_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询最新报告失败: {e}",
        )


@router.get("/{stock_code}/has-today", response_model=dict)
async def has_today_report(
    stock_code: str,
    current_user: dict = Depends(get_current_user),
):
    """判断该股票当日是否已有报告（前端徽标用）"""
    try:
        svc = get_favorite_report_service()
        result = await svc.has_today_report(current_user["id"], stock_code)
        return ok(result)
    except Exception as e:
        logger.error(f"❌ 查询当日报告徽标失败 {stock_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询当日报告状态失败: {e}",
        )


@router.post("/generate", response_model=dict)
async def generate_reports(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """手动触发生成报告（异步后台执行）

    - report_type: daily / realtime
    - stock_code: 单只股票代码，为空则对当前用户全部自选股生成
    """
    try:
        user_id = current_user["id"]
        svc = get_favorite_report_service()
        report_type = request.report_type
        stock_code = request.stock_code

        async def _run():
            """后台生成报告（带异常捕获，避免被 BackgroundTasks 静默吞掉）"""
            try:
                logger.info(f"🚀 [BackgroundTask] 开始生成报告: type={report_type}, user={user_id}")
                if report_type == "daily":
                    await get_favorite_report_service().generate_daily_reports(user_id)
                elif report_type == "realtime":
                    await get_favorite_report_service().generate_realtime_reports(user_id)
                else:
                    logger.warning(f"⚠️ 未知 report_type: {report_type}")
                logger.info(f"✅ [BackgroundTask] 报告生成完成: type={report_type}, user={user_id}")
            except Exception as e:
                logger.error(f"❌ [BackgroundTask] 报告生成失败: type={report_type}, user={user_id}", exc_info=True)

        background_tasks.add_task(_run)
        return ok(
            {"status": "scheduled", "report_type": report_type, "stock_code": stock_code},
            message="生成任务已提交，请稍后查看",
        )
    except Exception as e:
        logger.error(f"❌ 触发生成报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发生成失败: {e}",
        )
