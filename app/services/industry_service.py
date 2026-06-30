"""
IndustryService: 用大模型批量识别 A 股所属细分行业赛道（如「半导体设备」「锂电池」「MLCC」「PCB」）。

设计要点：
- 三级查询：stock_basic_info.industry（持久化）→ Redis 缓存 → LLM 批量识别
- LLM 结果写回 stock_basic_info（$set industry）并缓存到 Redis（TTL 30 天）
- LLM 不可用 / 失败时返回占位 "-"，绝不阻塞自选股列表加载
- 每批最多 BATCH_SIZE 只股票一次性发给 LLM，返回 JSON 映射
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")

# Redis 缓存键前缀与 TTL（30 天，行业变动极少）
_INDUSTRY_CACHE_PREFIX = "industry:"
_INDUSTRY_CACHE_TTL = 60 * 60 * 24 * 30

# 每批发给 LLM 的最大股票数（太大 LLM 易超时/返回空，10 比较稳妥）
_BATCH_SIZE = 10


class IndustryService:
    """用大模型识别 A 股行业板块的服务。"""

    def __init__(self) -> None:
        self.db = None

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    async def get_cached_industries(self, codes: List[str]) -> Dict[str, str]:
        """只从 DB / Redis 缓存读取行业（毫秒级），不触发 LLM。

        用于列表加载时快速返回已识别的行业；未命中的由调用方后台异步识别。
        """
        clean_codes: List[str] = []
        seen = set()
        for c in codes or []:
            if not c:
                continue
            code = str(c).strip().zfill(6)
            if code not in seen:
                seen.add(code)
                clean_codes.append(code)
        if not clean_codes:
            return {}

        result: Dict[str, str] = {}

        # 1) 从 stock_basic_info 取已落库的行业
        db = await self._get_db()
        try:
            cursor = db.stock_basic_info.find(
                {"code": {"$in": clean_codes}, "industry": {"$nin": [None, "", "-"]}},
                {"code": 1, "industry": 1, "_id": 0},
            )
            async for doc in cursor:
                code = str(doc.get("code", "")).strip().zfill(6)
                ind = doc.get("industry")
                if ind:
                    result[code] = ind
        except Exception as e:
            logger.warning(f"[行业识别] get_cached 读取 stock_basic_info 失败: {e}")

        # 2) 未命中的查 Redis 缓存
        missing = [c for c in clean_codes if c not in result]
        if missing:
            try:
                from app.core.redis_client import get_redis
                redis = get_redis()
                keys = [f"{_INDUSTRY_CACHE_PREFIX}{c}" for c in missing]
                values = await redis.mget(keys)
                for code, val in zip(missing, values):
                    if val:
                        result[code] = val
            except Exception as e:
                logger.warning(f"[行业识别] get_cached Redis 读取失败: {e}")

        return result

    async def identify_industries(self, codes: List[str], name_map: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """批量获取股票行业。

        Args:
            codes: 6 位 A 股代码列表

        Returns:
            {stock_code: industry_name}，未识别到的返回 "-"
        """
        # 标准化去重
        clean_codes: List[str] = []
        seen = set()
        for c in codes or []:
            if not c:
                continue
            code = str(c).strip().zfill(6)
            if code not in seen:
                seen.add(code)
                clean_codes.append(code)

        if not clean_codes:
            return {}

        result: Dict[str, str] = {}

        # 1) 先从 stock_basic_info 批量取已落库的行业
        db = await self._get_db()
        try:
            cursor = db.stock_basic_info.find(
                {"code": {"$in": clean_codes}, "industry": {"$nin": [None, "", "-"]}},
                {"code": 1, "industry": 1, "_id": 0},
            )
            async for doc in cursor:
                code = str(doc.get("code", "")).strip().zfill(6)
                ind = doc.get("industry")
                if ind:
                    result[code] = ind
        except Exception as e:
            logger.warning(f"[行业识别] 读取 stock_basic_info 失败: {e}")

        # 2) 对仍未命中的代码，查 Redis 缓存
        missing = [c for c in clean_codes if c not in result]
        if missing:
            try:
                from app.core.redis_client import get_redis
                redis = get_redis()
                # 批量 mget
                keys = [f"{_INDUSTRY_CACHE_PREFIX}{c}" for c in missing]
                values = await redis.mget(keys)
                still_missing: List[str] = []
                for code, val in zip(missing, values):
                    if val:
                        result[code] = val
                    else:
                        still_missing.append(code)
                missing = still_missing
            except Exception as e:
                logger.warning(f"[行业识别] Redis 缓存读取失败: {e}")

        # 3) 剩余未命中的，批量调 LLM
        if missing:
            llm_result = await self._batch_identify_via_llm(missing, name_map)
            result.update(llm_result)
            # 写回 DB + Redis
            await self._persist(llm_result)

        # 4) 对始终没结果的代码，填占位
        for c in clean_codes:
            if c not in result or not result[c]:
                result[c] = "-"

        return result

    # ------------------------------------------------------------------
    # LLM 批量识别
    # ------------------------------------------------------------------
    async def _batch_identify_via_llm(self, codes: List[str], name_map: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """分批调用 LLM 识别行业。失败返回空 dict（不抛异常）。"""
        result: Dict[str, str] = {}
        # 分批
        batches = [codes[i : i + _BATCH_SIZE] for i in range(0, len(codes), _BATCH_SIZE)]
        for batch in batches:
            try:
                partial = await self._identify_one_batch(batch, name_map)
                result.update(partial)
            except Exception as e:
                logger.warning(f"[行业识别] LLM 批量识别失败 (batch={batch}): {e}")
        return result

    async def _identify_one_batch(self, codes: List[str], name_map: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """调用一次 LLM 识别一批股票行业，返回 {code: industry}。"""
        llm = await self._build_llm()
        if llm is None:
            return {}

        # 构造股票清单（有名称时带上名称，大幅提升准确率）
        if name_map:
            stock_lines = [f"{c}（{name_map.get(c, '')}）" for c in codes]
            stock_list_str = "、".join(stock_lines)
        else:
            stock_list_str = "、".join(codes)

        prompt = (
            "你是 A 股行业细分赛道专家。下面给你一组 A 股股票，"
            "请判断每只股票主营业务所属的【细分行业赛道】（约等同于申万二级行业或更细的子赛道）。\n"
            "要求：尽量具体，不要笼统归类；但同一类业务要用相同的赛道名，便于归类统计。\n\n"
            "细分赛道参考（非穷举，请按公司实际主业归类，不在此列的可自行给出合适的细分名）：\n"
            "  · 半导体：半导体设备 / 半导体封测 / 半导体硅片 / 半导体材料 / 分立器件 / "
            "存储芯片 / 模拟芯片 / 数字芯片设计 / EDA·IP / MCU / 功率器件(IGBT·SiC)\n"
            "  · 被动元件：MLCC / 电阻电容 / 电感\n"
            "  · 电路板：PCB / 覆铜板 / 铜箔玻纤布\n"
            "  · 显示光电：显示面板 / LED / 光学元件 / 光模块 / 光纤光缆 / 通信设备\n"
            "  · 新能源：锂电池 / 电池材料(正极·负极·电解液·隔膜) / 光伏 / 风电\n"
            "  · 其他：军工电子 / 电子陶瓷 / 券商 / 白酒 / 医疗器械 / 软件开发 等\n\n"
            f"股票：{stock_list_str}\n\n"
            "请严格只返回一个 JSON 对象，键为股票代码(6位数字)，值为细分赛道名（不要带任何额外说明文字），"
            '例如：{"002371":"半导体设备","300750":"锂电池","000636":"MLCC","600183":"PCB"}。'
            '无法判断的填"-"。'
        )

        from langchain_core.messages import HumanMessage

        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)
        if isinstance(content, list):
            # 归一化 typed content blocks
            content = "".join(
                blk.get("text", "") if isinstance(blk, dict) else str(blk)
                for blk in content
            )
        text = str(content).strip()
        logger.info(f"[行业识别] LLM 原始返回长度={len(text)}, 前100字符={text[:100]!r}")

        # 解析 JSON（容错：去掉可能的 markdown 代码块包裹）
        if text.startswith("```"):
            # 去掉 ```json ... ``` 包裹
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            mapping = json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取首个 {...} 片段
            import re

            m = re.search(r"\{.*\}", text, re.S)
            if m:
                try:
                    mapping = json.loads(m.group(0))
                except Exception:
                    logger.warning(f"[行业识别] LLM 返回无法解析为 JSON: {text[:200]}")
                    return {}
            else:
                logger.warning(f"[行业识别] LLM 返回无法解析为 JSON: {text[:200]}")
                return {}

        # 标准化键为 6 位代码
        result: Dict[str, str] = {}
        for k, v in mapping.items():
            code = str(k).strip().zfill(6)
            industry = str(v).strip() if v else "-"
            if industry and industry != "未知":
                result[code] = industry
        logger.info(f"[行业识别] LLM 识别完成 {len(result)}/{len(codes)} 只")
        return result

    async def _build_llm(self):
        """根据系统配置构造一个轻量 LLM 实例；配置缺失返回 None。"""
        try:
            from app.core.unified_config import UnifiedConfigManager
            from app.services.simple_analysis_service import get_provider_and_url_by_model_sync
            from tradingagents.graph.trading_graph import create_llm_by_provider

            config = UnifiedConfigManager()
            model_name = config.get_quick_analysis_model()
            info = get_provider_and_url_by_model_sync(model_name)

            provider = info.get("provider")
            backend_url = info.get("backend_url")
            api_key = info.get("api_key")

            if not provider or not backend_url or not api_key:
                logger.warning(
                    f"[行业识别] LLM 配置不完整: provider={provider}, model={model_name}, "
                    f"has_url={bool(backend_url)}, has_key={bool(api_key)}"
                )
                return None

            llm = create_llm_by_provider(
                provider=provider,
                model=model_name,
                backend_url=backend_url,
                temperature=0.1,
                max_tokens=4096,  # thinking 模型需要较大 max_tokens（reasoning 占用多）
                timeout=60,
                api_key=api_key,
            )
            return llm
        except Exception as e:
            logger.warning(f"[行业识别] 构造 LLM 实例失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    async def _persist(self, mapping: Dict[str, str]) -> None:
        """把识别结果写回 stock_basic_info 和 Redis。"""
        if not mapping:
            return

        # 写 DB（只写非占位的）
        try:
            db = await self._get_db()
            for code, industry in mapping.items():
                if industry and industry != "-":
                    await db.stock_basic_info.update_one(
                        {"code": code},
                        {"$set": {"industry": industry, "updated_at": datetime.now()}},
                    )
        except Exception as e:
            logger.warning(f"[行业识别] 写回 stock_basic_info 失败: {e}")

        # 写 Redis（含占位，避免反复请求 LLM）
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            pipe = redis.pipeline()
            for code, industry in mapping.items():
                pipe.setex(
                    f"{_INDUSTRY_CACHE_PREFIX}{code}",
                    _INDUSTRY_CACHE_TTL,
                    industry,
                )
            await pipe.execute()
        except Exception as e:
            logger.warning(f"[行业识别] 写 Redis 缓存失败: {e}")


# ------------------------------------------------------------------
# 单例
# ------------------------------------------------------------------
_industry_service: Optional[IndustryService] = None


def get_industry_service() -> IndustryService:
    global _industry_service
    if _industry_service is None:
        _industry_service = IndustryService()
    return _industry_service
