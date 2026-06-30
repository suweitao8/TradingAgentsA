"""
自选股服务
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.database import get_mongo_db
from app.models.common import FavoriteStock
from app.services.quotes_service import get_quotes_service


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
                # 兜底：仅当 market_quotes 未覆盖到某些代码（价格为空）时，
                # 才调在线快照补齐 —— 避免每次刷新都拉全市场（58秒）。
                # 换手率/量比已由入库任务写入 market_quotes，不再作为在线兜底触发条件。
                missing_codes = [
                    it.get("stock_code") for it in items
                    if it.get("stock_code") and it.get("current_price") is None
                ]
                if missing_codes:
                    try:
                        quotes_online = await get_quotes_service().get_quotes(missing_codes)
                        for it in items:
                            code = it.get("stock_code")
                            if code not in missing_codes:
                                continue
                            q2 = quotes_online.get(code, {}) if quotes_online else {}
                            if not q2:
                                continue
                            if it.get("current_price") is None:
                                it["current_price"] = q2.get("close")
                            if it.get("change_percent") is None:
                                it["change_percent"] = q2.get("pct_chg")
                            if it.get("turnover_rate") is None and q2.get("turnover_rate") is not None:
                                it["turnover_rate"] = q2.get("turnover_rate")
                            if it.get("volume_ratio") is None and q2.get("volume_ratio") is not None:
                                it["volume_ratio"] = q2.get("volume_ratio")
                    except Exception:
                        pass
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
