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
        # A 股缓存
        self._cache_ts: float = 0.0
        self._cache: Dict[str, Dict[str, Optional[float]]] = {}
        self._lock = asyncio.Lock()
        # ETF 缓存（独立，不污染 A 股缓存）
        self._etf_cache_ts: float = 0.0
        self._etf_cache: Dict[str, Dict[str, Optional[float]]] = {}
        self._etf_lock = asyncio.Lock()

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

    # ------------------------------------------------------------------
    # ETF 行情（独立缓存，不污染 A 股缓存）
    # ------------------------------------------------------------------

    async def get_etf_quotes(self, codes: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
        """获取一批 ETF 的近实时快照（最新价、涨跌幅、换手率、量比）。

        东方财富的 ETF 和 A 股是不同的市场分类（fs 参数不同），不能用 A 股的
        _fetch_spot_akshare 拉取。本方法使用独立的 ETF 缓存。
        """
        codes = [c.strip() for c in codes if c]
        now = time.time()
        async with self._etf_lock:
            if self._etf_cache and (now - self._etf_cache_ts) < self._ttl:
                return {c: q for c, q in self._etf_cache.items() if c in codes and q}
            data = await asyncio.to_thread(self._fetch_etf_spot)
            self._etf_cache = data
            self._etf_cache_ts = time.time()
            return {c: q for c, q in self._etf_cache.items() if c in codes and q}

    def _fetch_etf_spot(self) -> Dict[str, Dict[str, Optional[float]]]:
        """通过东方财富 ETF 行情接口拉取全市场 ETF 快照。

        ETF 的 fs 参数为 ``b:MK002``（沪深 ETF 基金），与 A 股的
        ``m:0 t:6,...`` 不同。字段映射相同（f2/f3/f6/f8/f10/f12）。
        """
        try:
            import requests

            url = "https://82.push2delay.eastmoney.com/api/qt/clist/get"
            base_params = {
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f12",
                "fs": "b:MK0021",  # 沪深 ETF 基金
                "fields": "f2,f3,f6,f8,f10,f12",
            }

            result: Dict[str, Dict[str, Optional[float]]] = {}
            page_size = 20
            page_no = 1
            total = None
            while True:
                params = {**base_params, "pn": str(page_no), "pz": str(page_size)}
                resp = requests.get(url, params=params, timeout=8)
                if resp.status_code != 200:
                    logger.warning(f"东方财富 ETF spot 第{page_no}页 HTTP {resp.status_code}")
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
                if total and len(result) >= total:
                    break
                page_no += 1
                if page_no > 100:  # ETF 约 900 只 / 20 = 45 页，安全上限 100
                    break

            logger.info(f"东方财富 ETF spot 拉取完成: {len(result)} 条")
            return result
        except Exception as e:
            logger.error(f"获取东方财富 ETF 实时快照失败: {e}")
            return {}


_quotes_service: Optional[QuotesService] = None


def get_quotes_service() -> QuotesService:
    global _quotes_service
    if _quotes_service is None:
        _quotes_service = QuotesService(ttl_seconds=30)
    return _quotes_service


# ---------------------------------------------------------------------------
# ETF 分时均线斜率（MA5/MA10）
# ---------------------------------------------------------------------------

def _etf_secid(code: str) -> str:
    """根据 ETF 代码生成东方财富 secid（市场前缀+代码）。

    51/56/58 开头 → 沪市(1)，15 开头 → 深市(0)。
    """
    code = str(code).strip().zfill(6)
    if code.startswith(("51", "56", "58")):
        return f"1.{code}"
    elif code.startswith("15"):
        return f"0.{code}"
    return f"1.{code}"  # 默认沪市


def _fetch_kline_closes(code: str, klt: str, lmt: int = 15) -> list:
    """从东方财富拉取 ETF 分时 K 线的收盘价序列。

    Args:
        code: 6 位 ETF 代码
        klt: K 线周期（1=1分钟, 5=5分钟, 15=15分钟, 30=30分钟）
        lmt: 返回最近多少根 K 线

    Returns:
        收盘价列表（按时间正序），失败返回空列表
    """
    import requests

    try:
        secid = _etf_secid(code)
        url = "https://push2delay.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": klt,
            "fqt": "0",
            "end": "20500101",
            "lmt": str(lmt),
        }
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json().get("data") or {}
        klines = data.get("klines") or []
        # 每行格式: "2026-07-01,09:31,5.01,5.02,5.03,5.00,12345,67890"
        # f51=时间, f52=开, f53=收, f54=高, f55=低, f56=量, f57=额
        closes = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    closes.append(float(parts[2]))  # f53=收盘价
                except (ValueError, IndexError):
                    continue
        return closes
    except Exception as e:
        logger.debug(f"获取 {code} klt={klt} K线失败: {e}")
        return []


def _calc_ma_slope(closes: list, window: int) -> int:
    """计算 MA(window) 的斜率方向。

    斜率 = 最后一个 MA 值 - 倒数第二个 MA 值。
    返回 1(上升)/-1(下降)/0(走平或数据不足)。
    """
    if len(closes) < window + 1:
        return 0
    # 计算 MA 序列的最后两个值
    ma_now = sum(closes[-window:]) / window
    ma_prev = sum(closes[-window - 1:-1]) / window
    diff = ma_now - ma_prev
    if diff > 0.0001:
        return 1
    elif diff < -0.0001:
        return -1
    return 0


async def get_etf_ma_slopes(codes: list) -> dict:
    """批量获取 ETF 的分时 MA5/MA10 斜率方向。

    对每只 ETF 请求 4 个周期（1分/5分/15分/30分）的 K 线，
    计算 MA5 和 MA10 的斜率方向。结果 30s 内存缓存。

    Args:
        codes: ETF 代码列表

    Returns:
        {code: {"ma5": int, "ma10": int, ...}} 每个周期一组
        int 含义: 1=上升, -1=下降, 0=走平
    """
    codes = [c.strip().zfill(6) for c in codes if c]
    if not codes:
        return {}

    # 缓存
    now = time.time()
    cache_key = ",".join(codes)
    if hasattr(get_etf_ma_slopes, "_cache"):
        cached = get_etf_ma_slopes._cache
        if cached.get("key") == cache_key and (now - cached.get("ts", 0)) < 30:
            return cached["data"]

    periods = [("1m", "1"), ("5m", "5"), ("15m", "15"), ("30m", "30")]

    async def _fetch_one_period(code: str, klt: str) -> tuple:
        closes = await asyncio.to_thread(_fetch_kline_closes, code, klt)
        return code, {
            "ma5": _calc_ma_slope(closes, 5),
            "ma10": _calc_ma_slope(closes, 10),
        }

    # 并行请求：每只 ETF × 4 周期
    tasks = []
    for code in codes:
        for period_label, klt in periods:
            tasks.append((code, period_label, _fetch_one_period(code, klt)))

    results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

    # 组装结果
    slope_data = {code: {} for code in codes}
    for (code, period_label, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            slope_data[code][f"ma_slope_{period_label}"] = {"ma5": 0, "ma10": 0}
        else:
            _, slopes = result
            slope_data[code][f"ma_slope_{period_label}"] = slopes

    # 写缓存
    get_etf_ma_slopes._cache = {"key": cache_key, "ts": now, "data": slope_data}
    return slope_data

