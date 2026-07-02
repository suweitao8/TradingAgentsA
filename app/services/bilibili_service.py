"""
B站 UP 主管理服务

通过 RSSHub（自建 docker 容器）抓取 UP 主动态，规避 B站反爬/风控。
RSSHub 用 Playwright 无头浏览器模拟真人访问，处理 buvid3/wbi/cookie/重试。

依赖：
- RSSHub 容器（docker-compose 里配置，http://rsshub:1200）
- RSSHub 的 B站动态路由：/bilibili/user/dynamic/{mid}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

import httpx

from app.core.database import get_mongo_db
from app.utils.timezone import now_tz

logger = logging.getLogger(__name__)


def _rsshub_base() -> str:
    """RSSHub 地址（容器内通过服务名访问，本地开发用 localhost）"""
    return os.getenv("RSSHUB_BASE_URL", "http://rsshub:1200")


# 动态抓取内存缓存：{ mid: (timestamp, items) }，10 分钟内不重复拉
_DYNAMIC_CACHE_TTL = 600
_dynamic_cache: Dict[str, Tuple[float, List[dict]]] = {}


async def fetch_up_dynamics(mid: str, limit: int = 20) -> List[dict]:
    """通过 RSSHub 抓取某 UP 主的最新动态

    RSSHub 返回 RSS XML，解析出每条动态的标题/描述/时间/链接。
    """
    cached = _dynamic_cache.get(mid)
    if cached and (datetime.now().timestamp() - cached[0]) < _DYNAMIC_CACHE_TTL:
        return cached[1][:limit]

    url = f"{_rsshub_base()}/bilibili/user/dynamic/{mid}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as e:
        raise RuntimeError(f"RSSHub 请求失败: {e}")

    items = _parse_rss(xml_text)
    _dynamic_cache[mid] = (datetime.now().timestamp(), items)
    logger.info(f"[Bili] 通过RSSHub抓取 mid={mid} 动态 {len(items)} 条")
    return items[:limit]


def _parse_rss(xml_text: str) -> List[dict]:
    """解析 RSSHub 返回的 RSS XML，提取动态列表"""
    items: List[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.error(f"[Bili] RSS XML 解析失败: {e}")
        return items

    channel = root.find("channel")
    if channel is None:
        return items

    for idx, item in enumerate(channel.findall("item")):
        title = (item.findtext("title") or "").strip()
        desc_raw = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        link = (item.findtext("link") or "").strip()

        # description 是 HTML，去掉标签得到纯文本
        text = _strip_html(desc_raw) if desc_raw else title

        pub_ts = _parse_pub_date(pub_date)
        pub_time = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M") if pub_ts else pub_date

        video_bvid = ""
        bvid_match = re.search(r"(BV[a-zA-Z0-9]{10})", link)
        if bvid_match:
            video_bvid = bvid_match.group(1)

        items.append({
            "id": link or f"dyn_{idx}",
            "type": "DYNAMIC_TYPE_AV" if video_bvid else "DYNAMIC_TYPE_WORD",
            "pub_ts": pub_ts,
            "pub_time": pub_time,
            "text": text,
            "title": title if title != text else "",
            "video_bvid": video_bvid,
        })
    return items


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_pub_date(pub_date: str) -> int:
    if not pub_date:
        return 0
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_date)
        return int(dt.timestamp())
    except Exception:
        return 0


async def extract_stocks_from_dynamics(dynamics: List[dict]) -> List[dict]:
    """用 LLM 从多条动态里提取提到的股票及 UP 主观点"""
    if not dynamics:
        return []
    combined = ""
    for d in dynamics:
        snippet = d.get("text") or d.get("title") or ""
        if snippet:
            combined += f"[{d.get('pub_time','')}] {snippet}\n"
    combined = combined[:3000]
    if not combined.strip():
        return []

    llm, _ = await _get_llm()
    if llm is None:
        return _regex_extract_stocks(dynamics)

    prompt = (
        "你是 A 股分析助手。请从以下 B 站 UP 主的动态内容中，提取出所有被提及的 A 股股票，"
        "并判断 UP 主对每只股票的观点倾向。\n\n"
        f"动态内容：\n{combined}\n\n"
        "请严格按以下 JSON 数组格式返回（不要任何额外文字、不要 markdown 代码块）：\n"
        '[{"stock_name":"股票名称","stock_code":"6位代码(不确定可留空)","sentiment":"看多/看空/中性/观望",'
        '"mention":"原文中提到这只股票的关键句（原样摘录）"}]\n'
        "如果没有提到任何股票，返回空数组 []"
    )
    try:
        from langchain_core.messages import HumanMessage
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)
        return _parse_llm_stocks(content, dynamics)
    except Exception as e:
        logger.error(f"[Bili] LLM 提取股票失败: {e}")
        return _regex_extract_stocks(dynamics)


def _parse_llm_stocks(content: str, dynamics: List[dict]) -> List[dict]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        arr = json.loads(text)
    except Exception:
        return []
    pub_time = dynamics[0].get("pub_time", "") if dynamics else ""
    dyn_id = dynamics[0].get("id", "") if dynamics else ""
    result = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        name = str(item.get("stock_name", "")).strip()
        if not name:
            continue
        result.append({
            "stock_name": name,
            "stock_code": str(item.get("stock_code", "")).strip(),
            "sentiment": str(item.get("sentiment", "中性")).strip(),
            "mention": str(item.get("mention", "")).strip(),
            "dynamic_id": dyn_id,
            "pub_time": pub_time,
        })
    return result


def _regex_extract_stocks(dynamics: List[dict]) -> List[dict]:
    result = []
    code_pat = re.compile(r"\b([036]\d{5})\b")
    for d in dynamics:
        text = (d.get("text") or "") + " " + (d.get("title") or "")
        for m in code_pat.finditer(text):
            result.append({
                "stock_name": m.group(1), "stock_code": m.group(1),
                "sentiment": "中性", "mention": "",
                "dynamic_id": d.get("id", ""), "pub_time": d.get("pub_time", ""),
            })
    return result


async def _get_llm() -> Tuple[Any, str]:
    try:
        from tradingagents.graph.trading_graph import create_llm_by_provider
        from app.services.favorite_report_service import FavoriteReportService
        svc = FavoriteReportService()
        model_name = svc._get_quick_model_name()
        if not model_name:
            return None, "未配置模型"
        from app.services.simple_analysis_service import get_provider_and_url_by_model_sync
        info = get_provider_and_url_by_model_sync(model_name)
        if not info.get("provider"):
            return None, "未找到 provider"
        llm = create_llm_by_provider(
            provider=info["provider"], model=model_name,
            backend_url=info.get("backend_url"), temperature=0.1,
            max_tokens=2048, timeout=30, api_key=info.get("api_key"),
        )
        return llm, f"{info['provider']}/{model_name}"
    except Exception as e:
        logger.error(f"[Bili] 获取 LLM 失败: {e}")
        return None, f"错误: {e}"


async def fetch_up_info(mid: str) -> Optional[dict]:
    """查询 UP 主基本信息（通过 RSSHub 用户名路由）"""
    url = f"{_rsshub_base()}/bilibili/user/name/{mid}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            xml_text = resp.text
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return None
        uname = (channel.findtext("title") or "").strip()
        desc = (channel.findtext("description") or "").strip()
        return {"mid": str(mid), "uname": uname, "face": "", "sign": desc}
    except Exception as e:
        logger.warning(f"[Bili] 查询 UP 主信息失败 mid={mid}: {e}")
        return None


class BilibiliService:
    def __init__(self) -> None:
        self.db = None

    async def _get_db(self):
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def get_upmasters(self, user_id: str) -> List[Dict[str, Any]]:
        db = await self._get_db()
        doc = await db.user_bili_upmasters.find_one({"user_id": user_id})
        return (doc or {}).get("upmasters", [])

    async def add_upmaster(self, user_id, mid, uname="", category="", notes="") -> Dict[str, Any]:
        db = await self._get_db()
        existing = await db.user_bili_upmasters.find_one({"user_id": user_id, "upmasters.mid": mid}, {"_id": 1})
        if existing:
            return {"added": False, "message": "该 UP 主已添加"}
        if not uname:
            info = await fetch_up_info(mid)
            if info:
                uname = info.get("uname", "")
        await db.user_bili_upmasters.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {"created_at": now_tz()},
                "$set": {"updated_at": now_tz()},
                "$push": {"upmasters": {"mid": mid, "uname": uname or mid, "category": category, "notes": notes, "added_at": now_tz()}},
            },
            upsert=True,
        )
        return {"added": True, "uname": uname or mid}

    async def remove_upmaster(self, user_id, mid) -> Dict[str, Any]:
        db = await self._get_db()
        await db.user_bili_upmasters.update_one({"user_id": user_id}, {"$pull": {"upmasters": {"mid": mid}}})
        return {"removed": True}

    async def get_upmasters_with_dynamics(self, user_id: str) -> List[Dict[str, Any]]:
        upmasters = await self.get_upmasters(user_id)
        if not upmasters:
            return []
        sem = asyncio.Semaphore(3)

        async def _enrich(up):
            mid = up.get("mid", "")
            dynamics, stocks, error = [], [], None
            try:
                async with sem:
                    dynamics = await fetch_up_dynamics(mid, limit=15)
                stocks = await extract_stocks_from_dynamics(dynamics)
            except Exception as e:
                error = str(e)
            return {**up, "dynamics": dynamics, "stocks": stocks, "fetch_error": error}

        return await asyncio.gather(*[_enrich(u) for u in upmasters])


bilibili_service = BilibiliService()
