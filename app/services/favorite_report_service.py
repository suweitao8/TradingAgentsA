"""
自选股分析报告服务

负责两类报告的生成与查询：
- 每日报告（daily）：复用 SimpleAnalysisService 完整分析（深度=快速），写入 analysis_reports
- 盘中实时报告（realtime）：行情快照 + 单次 LLM 简评，写入 realtime_reports

设计要点：
- 幂等：当日/当小时已存在报告则跳过，避免重复消耗 token
- 限并发：每日报告用 Semaphore 限制并发数，防止几十只股票同时打爆 LLM
- 单只失败不阻塞：try/except 包裹每只股票，错误记入统计
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.database import get_mongo_db
from app.models.favorite_report import QuotesSnapshot, RealtimeReport
from app.services.favorites_service import favorites_service
from app.services.quotes_service import get_quotes_service
from app.utils.timezone import get_tz, now_tz

logger = logging.getLogger(__name__)


def _today_str() -> str:
    """返回当天日期字符串 YYYY-MM-DD（配置时区）"""
    return now_tz().strftime("%Y-%m-%d")


def _current_hour_slot() -> int:
    """返回当前小时（9-15），用于 realtime 报告的小时槽"""
    return now_tz().hour


class FavoriteReportService:
    """自选股分析报告服务"""

    def __init__(self) -> None:
        self.db = None

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    # ===================================================================
    # 每日报告（复用完整分析）
    # ===================================================================

    async def generate_daily_reports(
        self,
        user_id: str,
        trade_date: Optional[str] = None,
        max_concurrent: Optional[int] = None,
        stock_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """对用户每只自选股生成每日报告（复用 SimpleAnalysisService 完整分析）

        Args:
            user_id: 用户ID
            trade_date: 指定交易日，默认当天
            max_concurrent: 最大并发数，默认取配置 FAVORITE_REPORT_MAX_CONCURRENT
            stock_code: 指定单只股票代码，为空则对全部自选股生成

        Returns:
            统计信息 {total, success, skipped, failed, errors}
        """
        from app.models.analysis import AnalysisParameters, SingleAnalysisRequest
        from app.services.simple_analysis_service import get_simple_analysis_service

        trade_date = trade_date or _today_str()
        max_concurrent = max_concurrent or getattr(settings, "FAVORITE_REPORT_MAX_CONCURRENT", 2)

        stats = {"total": 0, "success": 0, "skipped": 0, "failed": 0, "errors": []}
        db = await self._get_db()

        # 取用户自选股（仅 A 股）
        try:
            favs = await favorites_service.get_user_favorites(user_id)
        except Exception as e:
            logger.error(f"❌ [每日报告] 获取用户 {user_id} 自选股失败: {e}")
            stats["errors"].append(f"获取自选股失败: {e}")
            return stats

        a_share_favs = [f for f in favs if (f.get("market") or "A股") == "A股"]
        # 指定单只股票时只处理该只
        if stock_code:
            a_share_favs = [f for f in a_share_favs if f.get("stock_code") == stock_code]
        stats["total"] = len(a_share_favs)
        if not a_share_favs:
            logger.info(f"ℹ️ [每日报告] 用户 {user_id} 无 A 股自选股，跳过")
            return stats

        logger.info(f"📊 [每日报告] 开始为用户 {user_id} 生成 {len(a_share_favs)} 只股票的每日报告（{trade_date}）")

        # 预查当日已生成的 daily 报告，做幂等跳过
        existing_codes = await self._get_existing_daily_codes(user_id, trade_date)

        sem = asyncio.Semaphore(max_concurrent)

        async def _gen_one(fav: Dict[str, Any]) -> None:
            stock_code = fav.get("stock_code") or ""
            stock_name = fav.get("stock_name") or stock_code
            if not stock_code:
                return
            if stock_code in existing_codes:
                stats["skipped"] += 1
                logger.info(f"⏭️ [每日报告] {stock_code} {stock_name} 当日已有报告，跳过")
                return

            async with sem:
                try:
                    # 复用完整分析：深度=快速（2-4分钟）
                    request = SingleAnalysisRequest(
                        symbol=stock_code,
                        parameters=AnalysisParameters(
                            market_type="A股",
                            research_depth="快速",
                        ),
                    )
                    service = get_simple_analysis_service()
                    task_info = await service.create_analysis_task(user_id, request)
                    task_id = task_info.get("task_id")
                    if not task_id:
                        raise RuntimeError("create_analysis_task 未返回 task_id")

                    # 后台执行（同步等待完成，因为是定时任务）
                    await service.execute_analysis_background(task_id, user_id, request)

                    # 给写入的 analysis_reports 文档补充标记字段
                    await self._mark_daily_report(task_id, user_id, stock_code, trade_date)

                    stats["success"] += 1
                    logger.info(f"✅ [每日报告] {stock_code} {stock_name} 完成")
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(f"{stock_code}: {e}")
                    logger.error(f"❌ [每日报告] {stock_code} {stock_name} 失败: {e}")

        await asyncio.gather(*[_gen_one(f) for f in a_share_favs], return_exceptions=False)
        logger.info(f"📊 [每日报告] 用户 {user_id} 完成: {stats}")
        return stats

    async def _get_existing_daily_codes(self, user_id: str, trade_date: str) -> set:
        """查询当日已生成的 daily 报告股票代码集合（幂等用）"""
        db = await self._get_db()
        cursor = db.analysis_reports.find(
            {
                "report_type": "daily",
                "source_user_id": user_id,
                "analysis_date": trade_date,
            },
            {"stock_symbol": 1, "_id": 0},
        )
        codes: set = set()
        async for doc in cursor:
            code = doc.get("stock_symbol")
            if code:
                codes.add(code)
        return codes

    async def _mark_daily_report(self, task_id: str, user_id: str, stock_code: str, trade_date: str) -> None:
        """给 analysis_reports 文档补充自选股每日报告标记字段"""
        try:
            db = await self._get_db()
            await db.analysis_reports.update_many(
                {"task_id": task_id},
                {"$set": {
                    "report_type": "daily",
                    "source_user_id": user_id,
                    "report_scope": "favorite",
                }},
            )
        except Exception as e:
            logger.warning(f"⚠️ [每日报告] 标记 {stock_code} 报告字段失败: {e}")

    # ===================================================================
    # 盘中实时报告（行情 + LLM 简评）
    # ===================================================================

    async def generate_realtime_reports(
        self,
        user_id: str,
        stock_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """对用户每只自选股生成盘中实时报告（行情快照 + LLM 简评）

        Args:
            user_id: 用户ID
            stock_code: 指定单只股票代码，为空则对全部自选股生成

        Returns:
            统计信息 {total, success, skipped, failed, errors}
        """
        stats = {"total": 0, "success": 0, "skipped": 0, "failed": 0, "errors": []}
        db = await self._get_db()

        try:
            favs = await favorites_service.get_user_favorites(user_id)
        except Exception as e:
            logger.error(f"❌ [实时报告] 获取用户 {user_id} 自选股失败: {e}")
            stats["errors"].append(f"获取自选股失败: {e}")
            return stats

        a_share_favs = [f for f in favs if (f.get("market") or "A股") == "A股"]
        # 指定单只股票时只处理该只
        if stock_code:
            a_share_favs = [f for f in a_share_favs if f.get("stock_code") == stock_code]
        stats["total"] = len(a_share_favs)
        if not a_share_favs:
            return stats

        trade_date = _today_str()
        hour_slot = _current_hour_slot()

        # 幂等：同 hour_slot 已存在则跳过
        existing = await self._get_existing_realtime_codes(user_id, trade_date, hour_slot)

        # 批量取行情
        all_codes = [f.get("stock_code") for f in a_share_favs if f.get("stock_code")]
        quotes_map: Dict[str, Dict] = {}
        if all_codes:
            try:
                quotes_map = await get_quotes_service().get_quotes(all_codes)
            except Exception as e:
                logger.error(f"❌ [实时报告] 获取行情失败: {e}")
                stats["errors"].append(f"获取行情失败: {e}")

        # 批量生成 LLM 简评（每只一次调用，但整体串行避免限频；可优化为限并发）
        sem = asyncio.Semaphore(3)

        async def _gen_one(fav: Dict[str, Any]) -> None:
            stock_code = fav.get("stock_code") or ""
            stock_name = fav.get("stock_name") or stock_code
            if not stock_code:
                return
            if stock_code in existing:
                stats["skipped"] += 1
                return

            async with sem:
                try:
                    q = quotes_map.get(stock_code) or {}
                    snapshot = QuotesSnapshot(
                        current_price=q.get("close"),
                        change_percent=q.get("pct_chg"),
                        turnover_rate=q.get("turnover_rate"),
                        volume_ratio=q.get("volume_ratio"),
                        amount=q.get("amount"),
                    )
                    # 行情全空则记为 failed（无法评论）
                    has_any_quote = any(v is not None for v in [
                        snapshot.current_price, snapshot.change_percent,
                        snapshot.turnover_rate, snapshot.volume_ratio,
                    ])
                    if not has_any_quote:
                        stats["failed"] += 1
                        stats["errors"].append(f"{stock_code}: 无行情数据")
                        return

                    commentary, recommendation, risk_level, key_points, model_info = await self._llm_realtime_commentary(
                        stock_code, stock_name, snapshot
                    )

                    report = RealtimeReport(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        user_id=user_id,
                        market_type="A股",
                        trade_date=trade_date,
                        hour_slot=hour_slot,
                        quotes_snapshot=snapshot,
                        commentary=commentary,
                        recommendation=recommendation,
                        risk_level=risk_level,
                        key_points=key_points,
                        status="completed",
                        model_info=model_info,
                    )
                    await db.realtime_reports.update_one(
                        {
                            "user_id": user_id,
                            "stock_code": stock_code,
                            "trade_date": trade_date,
                            "hour_slot": hour_slot,
                        },
                        {"$set": report.model_dump()},
                        upsert=True,
                    )
                    stats["success"] += 1
                    logger.info(f"✅ [实时报告] {stock_code} {stock_name} 完成（{trade_date} {hour_slot}时）")
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(f"{stock_code}: {e}")
                    logger.error(f"❌ [实时报告] {stock_code} {stock_name} 失败: {e}")

        await asyncio.gather(*[_gen_one(f) for f in a_share_favs])
        logger.info(f"📈 [实时报告] 用户 {user_id} 完成（{trade_date} {hour_slot}时）: {stats}")
        return stats

    async def _get_existing_realtime_codes(self, user_id: str, trade_date: str, hour_slot: int) -> set:
        db = await self._get_db()
        cursor = db.realtime_reports.find(
            {
                "user_id": user_id,
                "trade_date": trade_date,
                "hour_slot": hour_slot,
            },
            {"stock_code": 1, "_id": 0},
        )
        return {doc["stock_code"] async for doc in cursor if doc.get("stock_code")}

    async def _llm_realtime_commentary(
        self,
        stock_code: str,
        stock_name: str,
        snapshot: QuotesSnapshot,
    ) -> tuple:
        """调用 LLM 生成单只股票的盘中简评

        Returns:
            (commentary, recommendation, risk_level, key_points, model_info)
        """
        # 拼接 prompt
        price_str = f"{snapshot.current_price:.2f}" if snapshot.current_price is not None else "无数据"
        chg_str = f"{snapshot.change_percent:+.2f}%" if snapshot.change_percent is not None else "无数据"
        turn_str = f"{snapshot.turnover_rate:.2f}%" if snapshot.turnover_rate is not None else "无数据"
        vr_str = f"{snapshot.volume_ratio:.2f}" if snapshot.volume_ratio is not None else "无数据"

        prompt = (
            f"你是A股盘中实时分析助手。请根据以下实时行情数据，对【{stock_name}({stock_code})】给出简短分析。\n\n"
            f"当前行情：\n"
            f"- 最新价：{price_str}\n"
            f"- 涨跌幅：{chg_str}\n"
            f"- 换手率：{turn_str}\n"
            f"- 量比：{vr_str}\n\n"
            f"请严格按以下 JSON 格式返回（不要任何额外文字、不要 markdown 代码块）：\n"
            f'{{"commentary": "200字以内的盘中点评，分析涨跌原因和量价配合", '
            f'"recommendation": "偏多/中性/偏空 三选一", '
            f'"risk_level": "低/中/高 三选一", '
            f'"key_points": ["关键点1", "关键点2", "关键点3"]}}'
        )

        llm, model_info = await self._get_quick_llm()
        if llm is None:
            # 无 LLM 配置时降级：返回基于行情的规则简评
            return self._rule_based_commentary(stock_name, snapshot), "中性", "中", model_info

        try:
            # langchain 风格调用（项目 llm_clients 返回的是 langchain BaseChatModel）
            from langchain_core.messages import HumanMessage
            resp = await llm.ainvoke([HumanMessage(content=prompt)])
            content = resp.content if hasattr(resp, "content") else str(resp)
            return self._parse_llm_commentary(content, model_info)
        except Exception as e:
            logger.error(f"❌ [实时报告] LLM 调用失败 {stock_code}: {e}")
            return self._rule_based_commentary(stock_name, snapshot), "中性", "中", model_info

    async def _get_quick_llm(self) -> tuple:
        """获取快速分析用的 LLM 实例（用数据库配置的 quick_analysis_model）

        Returns:
            (llm_instance_or_None, model_info_str)
        """
        try:
            # 复用 simple_analysis_service 的同步配置查询
            from app.services.simple_analysis_service import get_provider_and_url_by_model_sync
            from tradingagents.graph.trading_graph import create_llm_by_provider

            # 优先用数据库 system_configs.llm_configs 里的配置；模型名取系统设置的 quick_analysis_model
            model_name = self._get_quick_model_name()
            if not model_name:
                return None, "未配置 quick_analysis_model"

            info = get_provider_and_url_by_model_sync(model_name)
            provider = info.get("provider")
            backend_url = info.get("backend_url")
            api_key = info.get("api_key")
            if not provider:
                return None, f"未找到模型 {model_name} 的 provider 配置"

            llm = create_llm_by_provider(
                provider=provider,
                model=model_name,
                backend_url=backend_url,
                temperature=0.3,
                max_tokens=4096,  # thinking 模型（Kimi-K2.5）需要大 max_tokens，否则 reasoning 耗尽后 content 为空
                timeout=60,
                api_key=api_key,
            )
            return llm, f"{provider}/{model_name}"
        except Exception as e:
            logger.error(f"❌ [实时报告] 获取 LLM 实例失败: {e}")
            return None, f"LLM初始化失败: {e}"

    def _get_quick_model_name(self) -> Optional[str]:
        """从数据库 system_configs 读取 quick_analysis_model，回退到默认 qwen-turbo"""
        try:
            from pymongo import MongoClient
            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]
            doc = db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])
            client.close()
            if doc:
                # 兼容多种字段名
                cfg = doc.get("llm_configs") or []
                # 系统设置里的 quick_analysis_model
                sys_settings = doc.get("system_settings") or doc.get("settings") or {}
                model_name = (
                    sys_settings.get("quick_analysis_model")
                    or sys_settings.get("quick_think_llm")
                )
                if model_name:
                    return model_name
                # 回退：取第一个启用的快速模型
                for c in cfg:
                    if c.get("enabled", True) and c.get("model_name"):
                        return c.get("model_name")
            return "qwen-turbo"  # 默认值
        except Exception as e:
            logger.warning(f"⚠️ [实时报告] 读取 quick_model 配置失败: {e}，用默认 qwen-turbo")
            return "qwen-turbo"

    def _parse_llm_commentary(self, content: str, model_info: str) -> tuple:
        """解析 LLM 返回的 JSON 简评，失败则降级

        兼容 thinking 模型（Kimi-K2.5 等）返回：
        - 可能带 <think>...</think> 前缀
        - 可能被 ```json ... ``` 代码块包裹
        - JSON 可能不是从行首开始（前面有思考文字）
        """
        try:
            text = content.strip()

            # 1. 去除 thinking 模型的 <think>...</think> 块
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

            # 2. 去除 markdown 代码块包裹
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)

            # 3. 提取第一个 JSON 对象（兼容 JSON 前后有杂文字的情况）
            json_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if json_match:
                text = json_match.group(0)

            data = json.loads(text)
            commentary = str(data.get("commentary", "")).strip()
            recommendation = str(data.get("recommendation", "中性")).strip()
            risk_level = str(data.get("risk_level", "中")).strip()
            key_points = data.get("key_points", [])
            if not isinstance(key_points, list):
                key_points = [str(key_points)]
            else:
                key_points = [str(k) for k in key_points][:3]
            if not commentary:
                raise ValueError("commentary 为空")
            return commentary, recommendation, risk_level, key_points, model_info
        except Exception as e:
            logger.warning(f"⚠️ [实时报告] 解析 LLM 返回失败: {e}，原文前200字: {content[:200]}")
            # 降级：去掉 <think> 块后把原文当 commentary
            fallback = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            return fallback[:500] if fallback else "（简评生成失败）", "中性", "中", [], model_info

    def _rule_based_commentary(self, stock_name: str, snapshot: QuotesSnapshot) -> str:
        """无 LLM 时的规则降级简评"""
        parts = [f"{stock_name} "]
        if snapshot.change_percent is not None:
            if snapshot.change_percent > 5:
                parts.append(f"涨幅达 {snapshot.change_percent:+.2f}%，表现强势。")
            elif snapshot.change_percent > 0:
                parts.append(f"当前上涨 {snapshot.change_percent:+.2f}%。")
            elif snapshot.change_percent < -5:
                parts.append(f"跌幅达 {snapshot.change_percent:+.2f}%，注意风险。")
            else:
                parts.append(f"当前下跌 {snapshot.change_percent:+.2f}%。")
        if snapshot.turnover_rate is not None and snapshot.turnover_rate > 5:
            parts.append(f"换手率 {snapshot.turnover_rate:.2f}% 较高，交投活跃。")
        if snapshot.volume_ratio is not None and snapshot.volume_ratio > 2:
            parts.append(f"量比 {snapshot.volume_ratio:.2f} 放大，资金关注度高。")
        return "".join(parts) or f"{stock_name} 暂无显著特征。"

    # ===================================================================
    # 报告查询（供 API 层调用）
    # ===================================================================

    async def get_user_stock_reports(
        self,
        user_id: str,
        stock_code: str,
        report_type: str = "all",
        trade_date: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """查询某用户某股票的报告（合并 daily + realtime）

        Returns:
            {"daily": [...], "realtime": [...]}
        """
        db = await self._get_db()
        trade_date = trade_date or _today_str()
        result: Dict[str, Any] = {"daily": [], "realtime": []}

        # daily：从 analysis_reports 查
        if report_type in ("all", "daily"):
            q = {
                "report_type": "daily",
                "source_user_id": user_id,
                "stock_symbol": stock_code,
            }
            if trade_date:
                q["analysis_date"] = trade_date
            cursor = db.analysis_reports.find(q).sort("created_at", -1).limit(limit)
            async for doc in cursor:
                result["daily"].append(self._format_daily_doc(doc))

        # realtime：从 realtime_reports 查
        if report_type in ("all", "realtime"):
            q = {"user_id": user_id, "stock_code": stock_code}
            if trade_date:
                q["trade_date"] = trade_date
            cursor = db.realtime_reports.find(q).sort("created_at", -1).limit(limit)
            async for doc in cursor:
                result["realtime"].append(self._format_realtime_doc(doc))

        return result

    def _format_daily_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化 analysis_reports 文档为前端响应"""
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        return {
            "id": str(doc.get("_id", "")),
            "analysis_id": doc.get("analysis_id", ""),
            "task_id": doc.get("task_id", ""),
            "stock_code": doc.get("stock_symbol", ""),
            "stock_name": doc.get("stock_name", ""),
            "report_type": "daily",
            "trade_date": doc.get("analysis_date", ""),
            "summary": doc.get("summary", ""),
            "recommendation": doc.get("recommendation", ""),
            "confidence_score": doc.get("confidence_score", 0),
            "risk_level": doc.get("risk_level", ""),
            "key_points": doc.get("key_points", []),
            "research_depth": doc.get("research_depth", ""),
            "model_info": doc.get("model_info", ""),
            "status": doc.get("status", "completed"),
            "created_at": created_at,
        }

    def _format_realtime_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化 realtime_reports 文档为前端响应"""
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        snap = doc.get("quotes_snapshot") or {}
        return {
            "id": str(doc.get("_id", "")),
            "stock_code": doc.get("stock_code", ""),
            "stock_name": doc.get("stock_name", ""),
            "report_type": "realtime",
            "trade_date": doc.get("trade_date", ""),
            "hour_slot": doc.get("hour_slot"),
            "quotes_snapshot": snap,
            "commentary": doc.get("commentary", ""),
            "recommendation": doc.get("recommendation", ""),
            "risk_level": doc.get("risk_level", ""),
            "key_points": doc.get("key_points", []),
            "model_info": doc.get("model_info", ""),
            "status": doc.get("status", "completed"),
            "created_at": created_at,
        }

    async def get_latest_report(
        self, user_id: str, stock_code: str
    ) -> Optional[Dict[str, Any]]:
        """取该股票最新一份报告（优先 daily，其次 realtime）"""
        db = await self._get_db()
        # 最新 daily
        doc = await db.analysis_reports.find_one(
            {"report_type": "daily", "source_user_id": user_id, "stock_symbol": stock_code},
            sort=[("created_at", -1)],
        )
        if doc:
            return self._format_daily_doc(doc)
        # 最新 realtime
        doc = await db.realtime_reports.find_one(
            {"user_id": user_id, "stock_code": stock_code},
            sort=[("created_at", -1)],
        )
        if doc:
            return self._format_realtime_doc(doc)
        return None

    async def has_today_report(self, user_id: str, stock_code: str) -> Dict[str, bool]:
        """判断某股票当日是否有报告（前端徽标用）"""
        db = await self._get_db()
        trade_date = _today_str()
        daily = await db.analysis_reports.find_one({
            "report_type": "daily", "source_user_id": user_id,
            "stock_symbol": stock_code, "analysis_date": trade_date,
        }, {"_id": 1})
        realtime = await db.realtime_reports.find_one({
            "user_id": user_id, "stock_code": stock_code, "trade_date": trade_date,
        }, {"_id": 1})
        return {"has_daily": daily is not None, "has_realtime": realtime is not None}


# ===================================================================
# 系统级辅助：遍历所有有自选股的用户（定时任务用）
# ===================================================================

async def collect_users_with_favorites() -> List[str]:
    """收集所有有自选股的 user_id（用于系统级定时任务，无用户上下文）

    兼容 user_favorites 集合（每用户一个文档）。
    """
    db = get_mongo_db()
    user_ids: List[str] = []
    cursor = db.user_favorites.find(
        {"favorites": {"$exists": True, "$ne": []}},
        {"user_id": 1, "_id": 0},
    )
    async for doc in cursor:
        uid = doc.get("user_id")
        if uid:
            user_ids.append(str(uid))
    return user_ids


# ===================================================================
# 全局单例
# ===================================================================

_favorite_report_service: Optional[FavoriteReportService] = None


def get_favorite_report_service() -> FavoriteReportService:
    global _favorite_report_service
    if _favorite_report_service is None:
        _favorite_report_service = FavoriteReportService()
    return _favorite_report_service
