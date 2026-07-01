"""
B站 UP 主管理服务

功能：
- UP 主 CRUD（存 user_bili_upmasters 集合，按用户聚合）
- 抓取 UP 主动态（B站 web-dynamic API + WBI 签名 + cookie）
- LLM 提取动态里提到的股票及观点
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.database import get_mongo_db
from app.utils.timezone import now_tz

logger = logging.getLogger(__name__)

_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 36, 25, 24, 30, 48, 51, 40, 52, 4, 34, 7, 0, 55, 20, 17,
    57, 21, 22, 6, 26, 54, 44, 1, 56, 11, 16, 61, 60, 59, 63, 62,
]
_NAV_API = "https://api.bilibili.com/x/web-interface/nav"
_DYNAMIC_API = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
_USER_INFO_API = "https://api.bilibili.com/x/space/wbi/acc/info"

_cached_mixin_key: Optional[str] = None
_cached_mixin_key_expire: float = 0.0
_DYNAMIC_CACHE_TTL = 600
_dynamic_cache: Dict[str, Tuple[float, List[dict]]] = {}


def _get_cookie() -> str:
    return os.getenv("BILI_COOKIE", "").strip()


def _default_headers(cookie: str) -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie,
    }


def _extract_key(url: str) -> str:
    return url.split("/")[-1].split(".")[0]


def _get_mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    result = ""
    for idx in _MIXIN_KEY_ENC_TAB:
        if idx < len(raw):
            result += raw[idx]
        if len(result) >= 32:
            break
    return result


def _sign_params(params: Dict[str, Any], mixin_key: str) -> Dict[str, Any]:
    wts = int(time.time())
    merged = {**params, "wts": wts}
    query = "&".join(f"{k}={merged[k]}" for k in sorted(merged.keys()) if merged[k] != "")
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return {**params, "wts": wts, "w_rid": w_rid}


async def _fetch_mixin_key(cookie: str) -> str:
    global _cached_mixin_key, _cached_mixin_key_expire
    now = time.time()
    if _cached_mixin_key and now < _cached_mixin_key_expire:
        return _cached_mixin_key
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_NAV_API, headers=_default_headers(cookie))
        data = resp.json()
    wbi_img = (data.get("data") or {}).get("wbi_img") or {}
    if not wbi_img.get("img_url") or not wbi_img.get("sub_url"):
        raise RuntimeError(f"nav 接口未返回 wbi_img: code={data.get('code')}")
    mk = _get_mixin_key(_extract_key(wbi_img["img_url"]), _extract_key(wbi_img["sub_url"]))
    _cached_mixin_key = mk
    _cached_mixin_key_expire = now + 50 * 60
    return mk


async def fetch_up_dynamics(mid: str, limit: int = 20) -> List[dict]:
    """抓取某 UP 主的最新动态列表"""
    cached = _dynamic_cache.get(mid)
    if cached and (time.time() - cached[0]) < _DYNAMIC_CACHE_TTL:
        return cached[1][:limit]

    cookie = _get_cookie()
    if not cookie:
        raise RuntimeError("未配置 BILI_COOKIE 环境变量")

    mixin_key = await _fetch_mixin_key(cookie)
    signed = _sign_params({"host_mid": mid, "offset": "", "timezone_offset": -480}, mixin_key)
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(_DYNAMIC_API, params=signed, headers=_default_headers(cookie))
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"B站动态接口报错: code={data.get('code')}, msg={data.get('message')}")

    raw_items = (data.get("data") or {}).get("items") or []
    simplified = [s for s in (_simplify_dynamic(it) for it in raw_items) if s]
    _dynamic_cache[mid] = (time.time(), simplified)
    logger.info(f"[Bili] 抓取 mid={mid} 动态 {len(simplified)} 条")
    return simplified[:limit]


def _simplify_dynamic(it: dict) -> Optional[dict]:
    modules = it.get("modules", {}) or {}
    author = modules.get("module_author", {}) or {}
    dynamic = modules.get("module_dynamic", {}) or {}
    dtype = it.get("type", "")
    pub_ts_raw = author.get("pub_ts") or 0
    try:
        pub_ts = int(pub_ts_raw)
    except (TypeError, ValueError):
        pub_ts = 0

    text = ""
    desc = dynamic.get("desc") or {}
    if desc.get("text"):
        text = desc["text"]
    else:
        nodes = desc.get("rich_text_node") or []
        if nodes:
            text = "".join(n.get("text", "") for n in nodes if n.get("text"))

    title = ""
    major = dynamic.get("major") or {}
    video_bvid = ""
    if major.get("archive"):
        title = major["archive"].get("title", "")
        video_bvid = major["archive"].get("bvid", "")
    elif major.get("opus"):
        title = (major["opus"].get("summary") or {}).get("text", "")
    elif major.get("draw"):
        pics = major["draw"].get("items") or []
        title = f"[图文动态 x{len(pics)}张图]"

    if not text and not title:
        return None

    return {
        "id": it.get("id_str", ""),
        "type": dtype,
        "pub_ts": pub_ts,
        "pub_time": datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M") if pub_ts else "",
        "text": text,
        "title": title,
        "video_bvid": video_bvid,
    }


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
    cookie = _get_cookie()
    if not cookie:
        return None
    try:
        mixin_key = await _fetch_mixin_key(cookie)
        signed = _sign_params({"mid": mid}, mixin_key)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_USER_INFO_API, params=signed, headers=_default_headers(cookie))
            data = resp.json()
        if data.get("code") != 0:
            return None
        d = data.get("data") or {}
        return {
            "mid": str(mid),
            "uname": d.get("name", ""),
            "face": d.get("face", ""),
            "sign": d.get("sign", ""),
        }
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
