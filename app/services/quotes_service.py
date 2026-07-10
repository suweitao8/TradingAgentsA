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

# 全局 Session 复用 TCP 连接（避免每次请求都 TLS 握手，29 只并行从 12s 降到 0.7s）
import requests as _requests
_kline_session = _requests.Session()


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
    """根据 ETF 代码生成东方财富 secid（市场前缀+代码）。

    51/56/58 开头 → 沪市(1)，15 开头 → 深市(0)。
    """
    code = str(code).strip().zfill(6)
    if code.startswith(("51", "56", "58")):
        return f"1.{code}"
    elif code.startswith("15"):
        return f"0.{code}"
    return f"1.{code}"  # 默认沪市


def _fetch_kline_closes(code: str, lmt: int = 30) -> list:
    """从东方财富拉取 ETF 1 分钟 K 线的收盘价序列。

    push2delay 延迟域名只有 1 分钟 K 线有数据（5/15/30 分钟返回 0 根），
    所以统一拉 1 分钟 K 线，由调用方本地聚合算其他周期。

    使用全局 requests.Session 复用 TCP 连接，29 只 ETF 并行只需 ~0.7s。

    Args:
        code: 6 位 ETF 代码
        lmt: 返回最近多少根 1 分钟 K 线（30 根足够算 30 分 MA10）

    Returns:
        收盘价列表（按时间正序），失败返回空列表
    """
    try:
        secid = _etf_secid(code)
        url = "https://push2delay.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "1",      # 只拉 1 分钟
            "fqt": "0",
            "end": "20500101",
            "lmt": str(lmt),
        }
        # 用全局 Session 复用连接池（避免每次 TLS 握手）
        resp = _kline_session.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json().get("data") or {}
        klines = data.get("klines") or []
        # 每行格式: "2026-07-01,09:31,5.01,5.02,5.03,5.00,12345,67890"
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
        logger.debug(f"获取 {code} 1分钟K线失败: {e}")
        return []


def _aggregate_closes(closes_1m: list, period: int) -> list:
    """将 1 分钟收盘价序列聚合为更大周期的收盘价序列。

    每 `period` 根 1 分钟 K 线取最后一根的收盘价，
    作为该周期的收盘价。

    Args:
        closes_1m: 1 分钟收盘价列表
        period: 聚合周期（5=5分钟, 15=15分钟, 30=30分钟）

    Returns:
        聚合后的收盘价列表
    """
    if not closes_1m or period <= 1:
        return closes_1m
    result = []
    for i in range(0, len(closes_1m), period):
        chunk = closes_1m[i:i + period]
        if chunk:
            result.append(chunk[-1])  # 取区间最后一根的收盘价
    return result


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

    优化策略：push2delay 只有 1 分钟 K 线有数据，所以每只 ETF 只请求一次
    1 分钟 K 线（240 根），然后本地聚合出 5/15/30 分钟序列再算 MA5/MA10。
    将 N×4 次请求降到 N 次，耗时从 ~10s 降到 ~2s。

    结果 60s 内存缓存（均线斜率不需要实时性，1 分钟更新一次足够）。

    Args:
        codes: ETF 代码列表

    Returns:
        {code: {"ma_slope_1m": {"ma5": int, "ma10": int}, ...}}
        int 含义: 1=上升, -1=下降, 0=走平
    """
    codes = [c.strip().zfill(6) for c in codes if c]
    if not codes:
        return {}

    # 缓存（60s，均线斜率不需要高频更新）
    now = time.time()
    cache_key = ",".join(codes)
    if hasattr(get_etf_ma_slopes, "_cache"):
        cached = get_etf_ma_slopes._cache
        if cached.get("key") == cache_key and (now - cached.get("ts", 0)) < 60:
            return cached["data"]

    async def _fetch_and_calc(code: str) -> tuple:
        """拉取单只 ETF 的 1 分钟 K 线，聚合算 4 个周期的 MA 斜率。"""
        closes_1m = await asyncio.to_thread(_fetch_kline_closes, code)
        if not closes_1m:
            return code, {
                "ma_slope_1m": {"ma5": 0, "ma10": 0},
                "ma_slope_5m": {"ma5": 0, "ma10": 0},
                "ma_slope_15m": {"ma5": 0, "ma10": 0},
                "ma_slope_30m": {"ma5": 0, "ma10": 0},
            }

        # 本地聚合 5/15/30 分钟收盘价序列
        closes_5m = _aggregate_closes(closes_1m, 5)
        closes_15m = _aggregate_closes(closes_1m, 15)
        closes_30m = _aggregate_closes(closes_1m, 30)

        return code, {
            "ma_slope_1m": {"ma5": _calc_ma_slope(closes_1m, 5), "ma10": _calc_ma_slope(closes_1m, 10)},
            "ma_slope_5m": {"ma5": _calc_ma_slope(closes_5m, 5), "ma10": _calc_ma_slope(closes_5m, 10)},
            "ma_slope_15m": {"ma5": _calc_ma_slope(closes_15m, 5), "ma10": _calc_ma_slope(closes_15m, 10)},
            "ma_slope_30m": {"ma5": _calc_ma_slope(closes_30m, 5), "ma10": _calc_ma_slope(closes_30m, 10)},
        }

    # 并行请求：每只 ETF 只 1 次 HTTP 请求
    tasks = [_fetch_and_calc(code) for code in codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 组装结果
    slope_data = {}
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"ETF MA 斜率计算异常: {result}")
            continue
        code, slopes = result
        slope_data[code] = slopes

    # 对失败的 ETF 填充默认值
    for code in codes:
        if code not in slope_data:
            slope_data[code] = {
                "ma_slope_1m": {"ma5": 0, "ma10": 0},
                "ma_slope_5m": {"ma5": 0, "ma10": 0},
                "ma_slope_15m": {"ma5": 0, "ma10": 0},
                "ma_slope_30m": {"ma5": 0, "ma10": 0},
            }

    # 写缓存
    get_etf_ma_slopes._cache = {"key": cache_key, "ts": now, "data": slope_data}
    return slope_data

