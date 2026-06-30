"""
QuotesService: 提供A股批量实时快照获取（AKShare东方财富 spot 接口），带内存TTL缓存。
- 不使用通达信（TDX）作为兜底数据源。
- 仅用于筛选返回前对 items 进行行情富集。
"""
from __future__ import annotations

import asyncio
import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        # 处理字符串中的逗号/百分号/空白
        if isinstance(v, str):
            s = v.strip().replace(",", "")
            if s.endswith("%"):
                s = s[:-1]
            if s == "-" or s == "":
                return None
            return float(s)
        # 处理 pandas/numpy 数值
        return float(v)
    except Exception:
        return None


class QuotesService:
    def __init__(self, ttl_seconds: int = 30) -> None:
        self._ttl = ttl_seconds
        self._cache_ts: float = 0.0
        self._cache: Dict[str, Dict[str, Optional[float]]] = {}
        self._lock = asyncio.Lock()

    async def get_quotes(self, codes: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
        """获取一批股票的近实时快照（最新价、涨跌幅、成交额）。
        - 优先使用缓存；缓存超时或为空则刷新一次全市场快照。
        - 返回仅包含请求的 codes。
        """
        codes = [c.strip() for c in codes if c]
        now = time.time()
        async with self._lock:
            if self._cache and (now - self._cache_ts) < self._ttl:
                return {c: q for c, q in self._cache.items() if c in codes and q}
            # 刷新缓存（阻塞IO放到线程）
            data = await asyncio.to_thread(self._fetch_spot_akshare)
            self._cache = data
            self._cache_ts = time.time()
            return {c: q for c, q in self._cache.items() if c in codes and q}

    def _fetch_spot_akshare(self) -> Dict[str, Dict[str, Optional[float]]]:
        """通过东方财富全市场快照接口拉取行情，并标准化为字典。

        直接用小 pz 分页请求东方财富 API（每页 20 条），避免 AKShare
        stock_zh_a_spot_em() 的 pz=100 大请求被东方财富断连的问题。
        字段：最新价、涨跌幅、成交额、换手率、量比。
        """
        try:
            import requests

            # 使用延迟行情域名（push2delay），实时域名 push2 在容器内易被限流断连
            url = "https://82.push2delay.eastmoney.com/api/qt/clist/get"
            # fields: f2=最新价 f3=涨跌幅 f6=成交额 f8=换手率 f10=量比 f12=代码
            base_params = {
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f12",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
                "fields": "f2,f3,f6,f8,f10,f12",
            }

            result: Dict[str, Dict[str, Optional[float]]] = {}
            page_size = 20  # 小 pz 避免被东方财富断连
            page_no = 1
            total = None
            while True:
                params = {**base_params, "pn": str(page_no), "pz": str(page_size)}
                resp = requests.get(url, params=params, timeout=8)
                if resp.status_code != 200:
                    logger.warning(f"东方财富 spot 第{page_no}页 HTTP {resp.status_code}")
                    break
                data = resp.json().get("data") or {}
                if total is None:
                    total = data.get("total", 0)
                diff = data.get("diff") or []
                if not diff:
                    break
                for item in diff:
                    code = str(item.get("f12", "")).strip().zfill(6)
                    if not code:
                        continue
                    result[code] = {
                        "close": _safe_float(item.get("f2")),
                        "pct_chg": _safe_float(item.get("f3")),
                        "amount": _safe_float(item.get("f6")),
                        "turnover_rate": _safe_float(item.get("f8")),
                        "volume_ratio": _safe_float(item.get("f10")),
                    }
                # 已拉完全部
                if total and len(result) >= total:
                    break
                page_no += 1
                # 安全上限，避免死循环（A 股约 5500 只 / 20 = 275 页）
                if page_no > 400:
                    break

            logger.info(f"东方财富 spot 拉取完成: {len(result)} 条")
            return result
        except Exception as e:
            logger.error(f"获取东方财富实时快照失败: {e}")
            return {}


_quotes_service: Optional[QuotesService] = None


def get_quotes_service() -> QuotesService:
    global _quotes_service
    if _quotes_service is None:
        _quotes_service = QuotesService(ttl_seconds=30)
    return _quotes_service

