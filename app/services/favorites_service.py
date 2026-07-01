"""
自选股服务
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.database import get_mongo_db
from app.models.common import FavoriteStock
from app.services.quotes_service import get_quotes_service

logger = logging.getLogger(__name__)


class FavoritesService:
    """自选股服务类"""
    
    def __init__(self):
        self.db = None
    
    async def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    def _is_valid_object_id(self, user_id: str) -> bool:
        """
        检查是否是有效的ObjectId格式
        注意：这里只检查格式，不代表数据库中实际存储的是ObjectId类型
        为了兼容性，我们统一使用 user_favorites 集合存储自选股
        """
        # 强制返回 False，统一使用 user_favorites 集合
        return False

    def _format_favorite(self, favorite: Dict[str, Any]) -> Dict[str, Any]:
        """格式化收藏条目（仅基础信息，不包含实时行情）。
        行情将在 get_user_favorites 中批量富集。
        """
        added_at = favorite.get("added_at")
        if isinstance(added_at, datetime):
            added_at = added_at.isoformat()
        return {
            "stock_code": favorite.get("stock_code"),
            "stock_name": favorite.get("stock_name"),
            "market": favorite.get("market", "A股"),
            "added_at": added_at,
            "tags": favorite.get("tags", []),
            "notes": favorite.get("notes", ""),
            "alert_price_high": favorite.get("alert_price_high"),
            "alert_price_low": favorite.get("alert_price_low"),
            # 行情占位，稍后填充
            "current_price": None,
            "change_percent": None,
            "turnover_rate": None,
            "volume_ratio": None,
            "industry": "-",
        }

    async def get_user_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户自选股列表，并批量拉取实时行情进行富集。"""
        db = await self._get_db()

        # 单用户本地部署模式：直接从 user_favorites 集合读取
        doc = await db.user_favorites.find_one({"user_id": user_id})
        favorites = (doc or {}).get("favorites", [])

        # 先格式化基础字段
        items = [self._format_favorite(fav) for fav in favorites]

        # 批量获取股票基础信息（板块等）
        codes = [it.get("stock_code") for it in items if it.get("stock_code")]
        if codes:
            try:
                # 🔥 获取数据源优先级配置
                from app.core.unified_config import UnifiedConfigManager
                config = UnifiedConfigManager()
                data_source_configs = await config.get_data_source_configs_async()

                # 提取启用的数据源，按优先级排序
                enabled_sources = [
                    ds.type.lower() for ds in data_source_configs
                    if ds.enabled and ds.type.lower() in ['tushare', 'akshare', 'baostock']
                ]

                if not enabled_sources:
                    enabled_sources = ['tushare', 'akshare', 'baostock']

                preferred_source = enabled_sources[0] if enabled_sources else 'tushare'

                # 从 stock_basic_info 获取板块信息（只查询优先级最高的数据源）
                basic_info_coll = db["stock_basic_info"]
                cursor = basic_info_coll.find(
                    {"code": {"$in": codes}, "source": preferred_source},  # 🔥 添加数据源筛选
                    {"code": 1, "sse": 1, "market": 1, "_id": 0}
                )
                basic_docs = await cursor.to_list(length=None)
                basic_map = {str(d.get("code")).zfill(6): d for d in (basic_docs or [])}

                for it in items:
                    code = it.get("stock_code")
                    basic = basic_map.get(code)
                    if basic:
                        # market 字段表示板块（主板、创业板、科创板等）
                        it["board"] = basic.get("market", "-")
                        # sse 字段表示交易所（上海证券交易所、深圳证券交易所等）
                        it["exchange"] = basic.get("sse", "-")
                    else:
                        it["board"] = "-"
                        it["exchange"] = "-"
            except Exception as e:
                # 查询失败时设置默认值
                for it in items:
                    it["board"] = "-"
                    it["exchange"] = "-"

        # 批量获取行情（优先使用入库的 market_quotes，6分钟更新）
        if codes:
            try:
                coll = db["market_quotes"]
                cursor = coll.find(
                    {"code": {"$in": codes}},
                    {"code": 1, "close": 1, "pct_chg": 1, "amount": 1, "turnover_rate": 1, "volume_ratio": 1},
                )
                docs = await cursor.to_list(length=None)
                quotes_map = {str(d.get("code")).zfill(6): d for d in (docs or [])}
                for it in items:
                    code = it.get("stock_code")
                    q = quotes_map.get(code)
                    if q:
                        it["current_price"] = q.get("close")
                        it["change_percent"] = q.get("pct_chg")
                        it["turnover_rate"] = q.get("turnover_rate")
                        it["volume_ratio"] = q.get("volume_ratio")
                # 兜底：当 market_quotes 缺价格、换手率或量比时，后台异步补齐（不阻塞当前请求）。
                # 根因：入库任务（Tushare rt_k）不返回换手率/量比，market_quotes 里这两个字段可能为空。
                # 改为后台触发：先立即返回已有数据（前端先渲染），补齐后前端轮询刷新拿到新值。
                missing_codes = [
                    it.get("stock_code") for it in items
                    if it.get("stock_code") and (
                        it.get("current_price") is None
                        or it.get("turnover_rate") is None
                        or it.get("volume_ratio") is None
                    )
                ]
                if missing_codes:
                    import asyncio
                    asyncio.create_task(self._backfill_quotes_async(db, missing_codes))
            except Exception:
                # 查询失败时保持占位 None，避免影响基础功能
                pass

        # 批量识别行业（用大模型细分赛道）
        # 策略：先同步从 DB 取已识别的行业（毫秒级），未命中的后台异步 LLM 识别，
        # 不阻塞当前请求（下次刷新时填充）。这样列表加载不会被 LLM 耗时拖慢。
        if codes:
            try:
                from app.services.industry_service import get_industry_service
                svc = get_industry_service()
                # 同步层：只从 DB 快速取（不触发 LLM）
                industry_map = await svc.get_cached_industries(codes)
                missing_codes = [c for c in codes if c not in industry_map or not industry_map[c] or industry_map[c] == "-"]
                for it in items:
                    code = it.get("stock_code")
                    it["industry"] = industry_map.get(code, "-")
                # 后台异步识别未命中的（不 await，不阻塞）
                if missing_codes:
                    import asyncio
                    # 带上股票名称，提升 LLM 识别准确率
                    name_map = {it.get("stock_code"): it.get("stock_name", "") for it in items}
                    asyncio.create_task(svc.identify_industries(missing_codes, name_map=name_map))
            except Exception as e:
                # 行业识别失败不阻塞列表加载
                for it in items:
                    if "industry" not in it:
                        it["industry"] = "-"

        return items

    async def _backfill_quotes_async(self, db, codes: list) -> None:
        """后台异步补齐：从东方财富延迟快照取行情，写入 market_quotes 集合。

        - 不阻塞调用方（由 asyncio.create_task 触发）
        - 写入 market_quotes 后，前端的轮询刷新接口自然能拿到新值
        - QuotesService 有 30 秒缓存，多个并发请求只触发一次全市场拉取
        """
        try:
            quotes_online = await get_quotes_service().get_quotes(codes)
            if not quotes_online:
                return
            # 只回填有值的字段，避免覆盖已有的价格数据
            from pymongo import UpdateOne
            ops = []
            for code, q in quotes_online.items():
                if not q:
                    continue
                set_fields = {}
                if q.get("close") is not None:
                    set_fields["close"] = q.get("close")
                if q.get("pct_chg") is not None:
                    set_fields["pct_chg"] = q.get("pct_chg")
                if q.get("turnover_rate") is not None:
                    set_fields["turnover_rate"] = q.get("turnover_rate")
                if q.get("volume_ratio") is not None:
                    set_fields["volume_ratio"] = q.get("volume_ratio")
                if set_fields:
                    ops.append(UpdateOne({"code": code}, {"$set": set_fields}))
            if ops:
                await db["market_quotes"].bulk_write(ops, ordered=False)
                logger.info(f"🔄 [后台补齐] 已回填 {len(ops)} 只股票的行情字段到 market_quotes")
        except Exception as e:
            logger.warning(f"⚠️ [后台补齐] 行情补齐失败: {e}")

    async def get_user_quotes(self, user_id: str) -> List[Dict[str, Any]]:
        """轻量查询：只返回用户自选股的行情字段（供前端轮询刷新用，毫秒级）。

        比 get_user_favorites 快：跳过基础信息、行业识别等富集，只查 market_quotes。
        """
        db = await self._get_db()
        doc = await db.user_favorites.find_one({"user_id": user_id}, {"favorites.stock_code": 1, "_id": 0})
        favorites = (doc or {}).get("favorites", [])
        codes = [str(f.get("stock_code")).zfill(6) for f in favorites if f.get("stock_code")]
        if not codes:
            return []
        cursor = db["market_quotes"].find(
            {"code": {"$in": codes}},
            {"code": 1, "close": 1, "pct_chg": 1, "turnover_rate": 1, "volume_ratio": 1, "_id": 0},
        )
        docs = await cursor.to_list(length=None)
        result = []
        for d in (docs or []):
            result.append({
                "stock_code": str(d.get("code")).zfill(6),
                "current_price": d.get("close"),
                "change_percent": d.get("pct_chg"),
                "turnover_rate": d.get("turnover_rate"),
                "volume_ratio": d.get("volume_ratio"),
            })
        return result

    async def add_favorite(
        self,
        user_id: str,
        stock_code: str,
        stock_name: str,
        market: str,
        tags: Optional[List[str]] = None,
        notes: str = "",
        alert_price_high: Optional[float] = None,
        alert_price_low: Optional[float] = None
    ) -> bool:
        """添加股票到自选股"""
        import logging
        logger = logging.getLogger("webapi")

        try:
            logger.info(f"🔧 [add_favorite] 开始添加自选股: user_id={user_id}, stock_code={stock_code}")

            db = await self._get_db()
            logger.info(f"🔧 [add_favorite] 数据库连接获取成功")

            favorite_stock = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market": market,
                "added_at": datetime.utcnow(),
                "tags": tags or [],
                "notes": notes,
                "alert_price_high": alert_price_high,
                "alert_price_low": alert_price_low
            }

            logger.info(f"🔧 [add_favorite] 自选股数据构建完成: {favorite_stock}")

            result = await db.user_favorites.update_one(
                {"user_id": user_id},
                {
                    "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()},
                    "$push": {"favorites": favorite_stock},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True
            )
            logger.info(f"🔧 [add_favorite] 更新结果: matched_count={result.matched_count}, modified_count={result.modified_count}, upserted_id={result.upserted_id}")
            logger.info(f"🔧 [add_favorite] 返回结果: True")
            return True
        except Exception as e:
            logger.error(f"❌ [add_favorite] 添加自选股异常: {type(e).__name__}: {str(e)}", exc_info=True)
            raise

    async def remove_favorite(self, user_id: str, stock_code: str) -> bool:
        """从自选股中移除股票"""
        db = await self._get_db()

        result = await db.user_favorites.update_one(
            {"user_id": user_id},
            {
                "$pull": {"favorites": {"stock_code": stock_code}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    async def update_favorite(
        self,
        user_id: str,
        stock_code: str,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        alert_price_high: Optional[float] = None,
        alert_price_low: Optional[float] = None
    ) -> bool:
        """更新自选股信息"""
        db = await self._get_db()

        prefix = "favorites.$."
        update_fields: Dict[str, Any] = {}
        if tags is not None:
            update_fields[prefix + "tags"] = tags
        if notes is not None:
            update_fields[prefix + "notes"] = notes
        if alert_price_high is not None:
            update_fields[prefix + "alert_price_high"] = alert_price_high
        if alert_price_low is not None:
            update_fields[prefix + "alert_price_low"] = alert_price_low

        if not update_fields:
            return True

        result = await db.user_favorites.update_one(
            {
                "user_id": user_id,
                "favorites.stock_code": stock_code
            },
            {
                "$set": {
                    **update_fields,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    async def is_favorite(self, user_id: str, stock_code: str) -> bool:
        """检查股票是否在自选股中"""
        import logging
        logger = logging.getLogger("webapi")

        try:
            logger.info(f"🔧 [is_favorite] 检查自选股: user_id={user_id}, stock_code={stock_code}")

            db = await self._get_db()

            doc = await db.user_favorites.find_one(
                {
                    "user_id": user_id,
                    "favorites.stock_code": stock_code
                }
            )
            result = doc is not None
            logger.info(f"🔧 [is_favorite] 查询结果: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ [is_favorite] 检查自选股异常: {type(e).__name__}: {str(e)}", exc_info=True)
            raise

    async def get_user_tags(self, user_id: str) -> List[str]:
        """获取用户使用的所有标签"""
        db = await self._get_db()

        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$unwind": "$favorites"},
            {"$unwind": "$favorites.tags"},
            {"$group": {"_id": "$favorites.tags"}},
            {"$sort": {"_id": 1}}
        ]
        result = await db.user_favorites.aggregate(pipeline).to_list(None)

        return [item["_id"] for item in result if item.get("_id")]

    def _get_mock_price(self, stock_code: str) -> float:
        """获取模拟股价"""
        # 基于股票代码生成模拟价格
        base_price = hash(stock_code) % 100 + 10
        return round(base_price + (hash(stock_code) % 1000) / 100, 2)
    
    def _get_mock_change(self, stock_code: str) -> float:
        """获取模拟涨跌幅"""
        # 基于股票代码生成模拟涨跌幅
        change = (hash(stock_code) % 2000 - 1000) / 100
        return round(change, 2)
    
    def _get_mock_volume(self, stock_code: str) -> int:
        """获取模拟成交量"""
        # 基于股票代码生成模拟成交量
        return (hash(stock_code) % 10000 + 1000) * 100


# 创建全局实例
favorites_service = FavoritesService()
