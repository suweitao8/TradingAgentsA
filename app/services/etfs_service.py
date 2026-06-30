"""
ETF 自选服务层

复制自 favorites_service.py 的模式，集合名 user_etfs，嵌套数组名 etfs。
行情富集使用 quotes_service.get_etf_quotes（东方财富 ETF 专用接口）。
不需要 stock_basic_info 板块查询和 industry_service 行业识别（ETF 本身代表行业/主题）。
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.core.database import get_mongo_db
from app.services.quotes_service import get_quotes_service

logger = logging.getLogger(__name__)


class EtfsService:
    """ETF 自选管理服务（单用户本地部署模式）"""

    def __init__(self):
        self.db = None

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    def _format_etf(self, etf: Dict) -> Dict:
        """格式化 ETF 基础字段，附加行情占位 None。"""
        return {
            "fund_code": etf.get("fund_code", ""),
            "fund_name": etf.get("fund_name", ""),
            "fund_type": etf.get("fund_type", "主题"),
            "added_at": etf.get("added_at"),
            "tags": etf.get("tags", []),
            "notes": etf.get("notes", ""),
            "alert_price_high": etf.get("alert_price_high"),
            "alert_price_low": etf.get("alert_price_low"),
            # 行情占位（后续富集填充）
            "current_price": None,
            "change_percent": None,
            "turnover_rate": None,
            "volume_ratio": None,
        }

    async def get_user_etfs(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户 ETF 列表，并批量拉取实时行情进行富集。"""
        db = await self._get_db()

        doc = await db.user_etfs.find_one({"user_id": user_id})
        etfs = (doc or {}).get("etfs", [])

        items = [self._format_etf(e) for e in etfs]
        if not items:
            return items

        codes = [it["fund_code"] for it in items if it.get("fund_code")]
        if not codes:
            return items

        # 批量拉取 ETF 实时行情
        try:
            svc = get_quotes_service()
            quotes = await svc.get_etf_quotes(codes)
            for it in items:
                code = it.get("fund_code")
                q = quotes.get(code)
                if q:
                    it["current_price"] = q.get("close")
                    it["change_percent"] = q.get("pct_chg")
                    it["turnover_rate"] = q.get("turnover_rate")
                    it["volume_ratio"] = q.get("volume_ratio")
        except Exception as e:
            logger.warning(f"ETF 行情富集失败: {e}")

        return items

    async def add_etf(
        self,
        user_id: str,
        fund_code: str,
        fund_name: str,
        fund_type: str = "主题",
        tags: List[str] = None,
        notes: str = "",
        alert_price_high: float = None,
        alert_price_low: float = None,
    ) -> bool:
        """添加 ETF 到用户自选。"""
        db = await self._get_db()

        etf_doc = {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "fund_type": fund_type,
            "added_at": datetime.utcnow(),
            "tags": tags or [],
            "notes": notes,
            "alert_price_high": alert_price_high,
            "alert_price_low": alert_price_low,
        }

        result = await db.user_etfs.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()},
                "$push": {"etfs": etf_doc},
                "$set": {"updated_at": datetime.utcnow()},
            },
            upsert=True,
        )
        return bool(result.upserted_id or result.modified_count)

    async def remove_etf(self, user_id: str, fund_code: str) -> bool:
        """从用户自选中移除 ETF。"""
        db = await self._get_db()
        result = await db.user_etfs.update_one(
            {"user_id": user_id},
            {
                "$pull": {"etfs": {"fund_code": fund_code}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    async def update_etf(
        self,
        user_id: str,
        fund_code: str,
        tags: List[str] = None,
        notes: str = None,
        alert_price_high: float = None,
        alert_price_low: float = None,
    ) -> bool:
        """更新用户自选 ETF 的标签/备注/价格提醒。"""
        db = await self._get_db()

        set_fields: Dict[str, Any] = {}
        if tags is not None:
            set_fields["etfs.$.tags"] = tags
        if notes is not None:
            set_fields["etfs.$.notes"] = notes
        if alert_price_high is not None:
            set_fields["etfs.$.alert_price_high"] = alert_price_high
        if alert_price_low is not None:
            set_fields["etfs.$.alert_price_low"] = alert_price_low

        if not set_fields:
            return False

        set_fields["updated_at"] = datetime.utcnow()

        result = await db.user_etfs.update_one(
            {"user_id": user_id, "etfs.fund_code": fund_code},
            {"$set": set_fields},
        )
        return result.modified_count > 0

    async def is_etf(self, user_id: str, fund_code: str) -> bool:
        """检查 ETF 是否已在用户自选中。"""
        db = await self._get_db()
        doc = await db.user_etfs.find_one(
            {"user_id": user_id, "etfs.fund_code": fund_code},
            {"_id": 1},
        )
        return doc is not None

    async def get_user_tags(self, user_id: str) -> List[str]:
        """获取用户所有 ETF 标签（去重）。"""
        db = await self._get_db()
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$unwind": "$etfs"},
            {"$unwind": "$etfs.tags"},
            {"$group": {"_id": "$etfs.tags"}},
        ]
        cursor = db.user_etfs.aggregate(pipeline)
        docs = await cursor.to_list(length=None)
        return [d["_id"] for d in (docs or []) if d.get("_id")]


etfs_service = EtfsService()
