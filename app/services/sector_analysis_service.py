"""
板块利好利空分析服务

职责：
1. 从 AKShare 拉取全量概念板块列表（缓存到 MongoDB，24h TTL）
2. 对未分析的市场快讯调 LLM 做"对哪个概念板块利好/利空"的结构化分析
3. 将分析结果回写到 stock_news 集合的 sector_analysis / sector_analyzed 字段

设计要点：
- LLM 只分析 sector_analyzed=False 的新快讯，不重复分析
- 概念板块词表缓存，避免每分钟重复拉取 AKShare（AKShare 限频）
- 板块词表太大时截取 TOP 100 传入 prompt（控制 token）
- LLM 调用复用项目已有的 create_llm_by_provider + 数据库配置的 quick_analysis_model
"""
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.database import get_database

logger = logging.getLogger(__name__)


class SectorAnalysisService:
    """板块利好利空分析服务"""

    # LLM prompt 中最多传入的概念板块数量（控制 token 成本）
    _MAX_SECTORS_IN_PROMPT = 100

    def __init__(self):
        self._db = None
        self._news_collection = None
        self._sector_cache_collection = None

    # ==================== 集合获取 ====================

    def _get_db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    def _get_news_collection(self):
        """stock_news 集合（存快讯原文 + 板块分析结果）"""
        if self._news_collection is None:
            self._news_collection = self._get_db().stock_news
        return self._news_collection

    def _get_sector_cache_collection(self):
        """concept_sectors_cache 集合（缓存 AKShare 概念板块列表）"""
        if self._sector_cache_collection is None:
            self._sector_cache_collection = self._get_db().concept_sectors_cache
        return self._sector_cache_collection

    # ==================== 概念板块词表（带缓存） ====================

    async def get_concept_sectors(self, force_refresh: bool = False) -> List[str]:
        """
        获取概念板块名称列表（带 MongoDB 缓存，TTL 由 NEWS_FLASH_SECTOR_CACHE_TTL 控制）。

        缓存命中直接返回；缓存过期或 force_refresh 时从 AKShare 重新拉取。

        Returns:
            概念板块名称列表，如 ["半导体", "AI算力", "固态电池", ...]
        """
        cache_coll = self._get_sector_cache_collection()
        ttl = timedelta(seconds=settings.NEWS_FLASH_SECTOR_CACHE_TTL)

        # 1. 尝试读缓存
        if not force_refresh:
            doc = await cache_coll.find_one({"_id": "concept_sectors"})
            if doc:
                cached_at = doc.get("updated_at")
                if cached_at and (datetime.utcnow() - cached_at) < ttl:
                    sectors = doc.get("sectors", [])
                    if sectors:
                        logger.debug(f"📋 概念板块缓存命中: {len(sectors)} 个板块")
                        return sectors
                    # 缓存为空列表（上次拉取失败），继续往下拉
                elif sectors := doc.get("sectors", []):
                    # 缓存过期但非空：先返回旧数据兜底，后台再刷新
                    logger.debug(f"📋 概念板块缓存已过期，用旧数据兜底: {len(sectors)} 个")
                    return sectors

        # 2. 从 AKShare 拉取
        sectors = await self._fetch_concept_sectors_from_akshare()

        # 3. 写缓存（即使为空也写，防止连续失败重复请求）
        await cache_coll.update_one(
            {"_id": "concept_sectors"},
            {"$set": {
                "sectors": sectors,
                "updated_at": datetime.utcnow(),
                "count": len(sectors),
            }},
            upsert=True,
        )
        logger.info(f"📋 概念板块缓存已更新: {len(sectors)} 个板块")
        return sectors

    async def _fetch_concept_sectors_from_akshare(self) -> List[str]:
        """拉取概念板块列表（多数据源容错，优先同花顺）"""
        import akshare as ak

        # 方案1（首选）：同花顺概念板块（stock_board_concept_name_ths）
        # 同花顺数据源不依赖 push2.eastmoney.com，容器内网络兼容性更好
        try:
            df = ak.stock_board_concept_name_ths()
            if df is not None and not df.empty and "name" in df.columns:
                sectors = df["name"].dropna().astype(str).str.strip().tolist()
                sectors = [s for s in sectors if s]
                sectors = list(dict.fromkeys(sectors))  # 去重保序
                if sectors:
                    logger.info(f"✅ 同花顺概念板块拉取成功: {len(sectors)} 个")
                    return sectors
        except Exception as e:
            logger.warning(f"⚠️ 同花顺概念板块拉取失败: {e}，尝试东方财富")

        # 方案2：东方财富概念板块（stock_board_concept_name_em，依赖 push2 域名）
        try:
            df = ak.stock_board_concept_name_em()
            if df is not None and not df.empty:
                col = "板块名称" if "板块名称" in df.columns else df.columns[1]
                sectors = df[col].dropna().astype(str).str.strip().tolist()
                sectors = [s for s in sectors if s]
                sectors = list(dict.fromkeys(sectors))
                if sectors:
                    logger.info(f"✅ 东方财富概念板块拉取成功: {len(sectors)} 个")
                    return sectors
        except Exception as e:
            logger.warning(f"⚠️ 东方财富概念板块拉取失败: {e}，尝试资金流接口")

        # 方案3：东方财富概念资金流（stock_fund_flow_concept，另一域名）
        try:
            df = ak.stock_fund_flow_concept()
            if df is not None and not df.empty and "行业" in df.columns:
                sectors = df["行业"].dropna().astype(str).str.strip().tolist()
                sectors = [s for s in sectors if s]
                sectors = list(dict.fromkeys(sectors))
                if sectors:
                    logger.info(f"✅ 概念资金流板块拉取成功: {len(sectors)} 个")
                    return sectors
        except Exception as e:
            logger.error(f"❌ 所有概念板块数据源均失败: {e}")

        return []


    # ==================== LLM 分析 ====================

    async def _get_llm(self) -> Tuple[Any, str]:
        """
        获取 LLM 实例（复用 favorite_report_service 的 quick_model 配置范式）。

        Returns:
            (llm_instance_or_None, model_info_str)
        """
        try:
            from app.services.simple_analysis_service import get_provider_and_url_by_model_sync
            from tradingagents.graph.trading_graph import create_llm_by_provider

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
                temperature=0.2,       # 低温度：降低随机性，板块判断更稳定
                max_tokens=2048,       # 结构化输出不需要大 max_tokens
                timeout=30,            # 快讯分析不能太慢
                api_key=api_key,
            )
            return llm, f"{provider}/{model_name}"
        except Exception as e:
            logger.error(f"❌ [板块分析] 获取 LLM 实例失败: {e}")
            return None, f"LLM初始化失败: {e}"

    def _get_quick_model_name(self) -> Optional[str]:
        """从数据库 system_configs 读取 quick_analysis_model，回退默认"""
        try:
            from pymongo import MongoClient

            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]
            doc = db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])
            client.close()
            if doc:
                sys_settings = doc.get("system_settings") or doc.get("settings") or {}
                model_name = (
                    sys_settings.get("quick_analysis_model")
                    or sys_settings.get("quick_think_llm")
                )
                if model_name:
                    return model_name
                cfg = doc.get("llm_configs") or []
                for c in cfg:
                    if c.get("enabled", True) and c.get("model_name"):
                        return c.get("model_name")
            return "qwen-turbo"
        except Exception as e:
            logger.warning(f"⚠️ [板块分析] 读取 quick_model 配置失败: {e}")
            return "qwen-turbo"

    async def analyze_news_sector_impact(
        self, title: str, content: str, candidate_sectors: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        用 LLM 分析单条快讯对概念板块的利好利空影响。

        Args:
            title: 快讯标题
            content: 快讯正文
            candidate_sectors: 候选概念板块名称列表

        Returns:
            结构化分析结果，或 None（LLM 失败时）:
            {
                "sectors": [
                    {"name": "半导体", "impact": "利好", "reason": "..."},
                    ...
                ],
                "overall_sentiment": "利好/利空/中性"
            }
        """
        llm, model_info = await self._get_llm()
        if llm is None:
            logger.warning(f"⚠️ [板块分析] LLM 不可用: {model_info}，跳过")
            return None

        # 截取 TOP N 板块（控制 prompt token）
        sectors_str = "、".join(candidate_sectors[: self._MAX_SECTORS_IN_PROMPT])

        # 正文过长截断（控制 token）
        content_trimmed = (content or "")[:500]

        prompt = f"""你是一位 A 股概念板块分析专家。请分析以下快讯对哪些概念板块是利好或利空。

## 候选概念板块
{sectors_str}

## 快讯内容
标题：{title}
正文：{content_trimmed}

## 输出要求
请只输出 JSON（不要输出其他文字），格式如下：
```json
{{
  "sectors": [
    {{"name": "板块名称（必须从候选列表中选取）", "impact": "利好", "reason": "一句话原因"}},
    {{"name": "板块名称", "impact": "利空", "reason": "一句话原因"}}
  ],
  "overall_sentiment": "利好"
}}
```

规则：
1. 只分析这条快讯明确影响到的板块，通常 1-3 个；如果没有明确影响任何板块，返回空 sectors 列表和 overall_sentiment="中性"
2. impact 只能是 "利好"、"利空"、"中性" 三个值之一
3. overall_sentiment 是这条快讯对市场整体的定性判断
4. 板块名称必须从上面的候选概念板块列表中选取，不要自行编造"""

        try:
            from langchain_core.messages import HumanMessage

            resp = await llm.ainvoke([HumanMessage(content=prompt)])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            result = self._parse_llm_result(raw)
            if result:
                logger.info(
                    f"✅ [板块分析] 「{title[:30]}...」→ "
                    f"{len(result.get('sectors', []))} 个板块, 整体={result.get('overall_sentiment')}"
                )
            return result
        except Exception as e:
            logger.error(f"❌ [板块分析] LLM 调用失败: {e}")
            return None

    def _parse_llm_result(self, raw: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 返回的 JSON（兼容 thinking 模型的 <think> 标签和 markdown 代码块包裹）。

        参照 favorite_report_service._parse_llm_commentary 的容错策略。
        """
        try:
            text = raw.strip()

            # 1. 去除 thinking 模型的 <think>...</think> 块
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

            # 2. 去除 markdown 代码块包裹
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)

            # 3. 提取第一个 JSON 对象
            json_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if json_match:
                text = json_match.group(0)

            data = json.loads(text)

            # 校验结构
            sectors = data.get("sectors", [])
            if not isinstance(sectors, list):
                sectors = []

            # 清洗每条板块记录
            cleaned_sectors = []
            valid_impacts = {"利好", "利空", "中性"}
            for s in sectors:
                if not isinstance(s, dict):
                    continue
                name = str(s.get("name", "")).strip()
                impact = str(s.get("impact", "中性")).strip()
                reason = str(s.get("reason", "")).strip()
                if not name:
                    continue
                if impact not in valid_impacts:
                    impact = "中性"
                cleaned_sectors.append({"name": name, "impact": impact, "reason": reason})

            overall = str(data.get("overall_sentiment", "中性")).strip()
            if overall not in valid_impacts:
                overall = "中性"

            return {"sectors": cleaned_sectors, "overall_sentiment": overall}
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ [板块分析] JSON 解析失败: {e}，原始返回: {raw[:200]}")
            return None

    # ==================== 批量分析入口 ====================

    async def analyze_unanalyzed_news(self, batch_size: Optional[int] = None) -> Dict[str, int]:
        """
        找出所有未做板块分析的快讯，逐条调 LLM 分析并回写。

        由定时任务（每分钟）或手动触发端点调用。

        Args:
            batch_size: 单轮最大分析条数（默认取配置 NEWS_FLASH_ANALYSIS_BATCH）

        Returns:
            统计信息: {"total": N, "analyzed": N, "failed": N}
        """
        if not settings.NEWS_FLASH_ANALYSIS_ENABLED:
            logger.debug("⏭️ [板块分析] LLM 板块分析未启用，跳过")
            return {"total": 0, "analyzed": 0, "failed": 0}

        batch_size = batch_size or settings.NEWS_FLASH_ANALYSIS_BATCH
        news_coll = self._get_news_collection()

        # 查找未分析快讯（sector_analyzed != True），按发布时间倒序取最近一批
        cursor = news_coll.find(
            {"sector_analyzed": {"$ne": True}},
            {"title": 1, "content": 1, "publish_time": 1},
        ).sort("publish_time", -1).limit(batch_size)

        news_list = await cursor.to_list(length=batch_size)
        if not news_list:
            logger.debug("⏭️ [板块分析] 没有待分析的快讯")
            return {"total": 0, "analyzed": 0, "failed": 0}

        logger.info(f"🔍 [板块分析] 待分析快讯 {len(news_list)} 条，开始 LLM 分析...")

        # 获取概念板块词表（带缓存）
        candidate_sectors = await self.get_concept_sectors()
        if not candidate_sectors:
            logger.warning("⚠️ [板块分析] 概念板块词表为空，无法分析")
            return {"total": len(news_list), "analyzed": 0, "failed": len(news_list)}

        analyzed = 0
        failed = 0

        for news in news_list:
            news_id = news["_id"]
            title = news.get("title", "")
            content = news.get("content", "")

            # 空标题跳过（无法分析）
            if not title.strip():
                await news_coll.update_one(
                    {"_id": news_id},
                    {"$set": {"sector_analyzed": True, "sector_analysis": None}},
                )
                continue

            result = await self.analyze_news_sector_impact(title, content, candidate_sectors)

            if result is not None:
                # 分析成功：回写结果，标记已分析
                await news_coll.update_one(
                    {"_id": news_id},
                    {"$set": {
                        "sector_analysis": result,
                        "sector_analyzed": True,
                        "sector_analyzed_at": datetime.utcnow(),
                    }},
                )
                analyzed += 1
            else:
                # 分析失败：标记失败但不标记已分析，下次重试
                failed += 1
                logger.warning(f"⚠️ [板块分析] 快讯 {news_id} 分析失败，下次重试")

        logger.info(
            f"📊 [板块分析] 本轮完成: 共 {len(news_list)} 条, "
            f"成功 {analyzed} 条, 失败 {failed} 条"
        )
        return {"total": len(news_list), "analyzed": analyzed, "failed": failed}


# ==================== 单例 ====================

_service_instance: Optional[SectorAnalysisService] = None


def get_sector_analysis_service() -> SectorAnalysisService:
    """获取板块分析服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = SectorAnalysisService()
        logger.info("✅ 板块利好利空分析服务初始化成功")
    return _service_instance
