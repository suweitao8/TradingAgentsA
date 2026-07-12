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
                        "name": item.get("f14", ""),
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

        优先读 Redis 缓存（后台定时任务刷新），未命中再查内存缓存，
        都没有才实时拉取。避免 API 请求时因全市场拉取导致超长等待。
        """
        import json as _json

        codes = [c.strip() for c in codes if c]
        if not codes:
            return {}

        # 1) 优先从 Redis 读（后台任务每分钟刷新的全市场快照）
        redis_key = "etf_spot_all"
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            cached = await redis.get(redis_key)
            if cached:
                all_quotes = _json.loads(cached)
                return {c: all_quotes[c] for c in codes if c in all_quotes and all_quotes[c]}
        except Exception as e:
            logger.debug(f"ETF spot Redis 读取跳过: {e}")

        # 2) 内存缓存（30s TTL，Redis 不可用时的降级）
        now = time.time()
        async with self._etf_lock:
            if self._etf_cache and (now - self._etf_cache_ts) < self._ttl:
                return {c: q for c, q in self._etf_cache.items() if c in codes and q}
            # 3) 实时拉取（最后的降级手段）
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
                "fields": "f2,f3,f6,f8,f10,f12,f14",  # f14=名称
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
                        "name": item.get("f14", ""),
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


def fetch_etf_detail(code: str) -> dict:
    """从东方财富个股实时接口获取单只 ETF 的价格/涨跌幅/换手率/量比/名称。

    用于 spot 全市场快照（b:MK0021）中找不到的 ETF（如港股通 ETF）兜底。
    返回 {"close", "pct_chg", "turnover_rate", "volume_ratio", "name"}，失败返回 {}。
    """
    try:
        secid = _etf_secid(code)
        url = "https://push2delay.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fields": "f43,f58,f170,f8,f10",
        }
        resp = _kline_session.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            return {}
        data = resp.json().get("data") or {}
        # f43=最新价(×1000) f170=涨跌幅(×100) f58=名称 f8=换手率 f10=量比
        price = data.get("f43")
        pct = data.get("f170")
        name = data.get("f58", "")
        turnover = data.get("f8")
        vol_ratio = data.get("f10")
        result = {}
        if price is not None and price != "-":
            result["close"] = float(price) / 1000
        if pct is not None and pct != "-":
            result["pct_chg"] = float(pct) / 100
        if turnover is not None and turnover != "-":
            result["turnover_rate"] = float(turnover)
        if vol_ratio is not None and vol_ratio != "-":
            result["volume_ratio"] = float(vol_ratio)
        if name:
            result["name"] = name
        return result
    except Exception as e:
        logger.debug(f"获取 {code} 个股详情失败: {e}")
        return {}


def _fetch_kline_closes(code: str, lmt: int = 30) -> list:
    """从东方财富拉取 ETF 1 分钟 K 线的收盘价序列。

    Returns:
        收盘价列表（按时间正序），失败返回空列表
    """
    result = _fetch_kline_raw(code, lmt)
    return result[0] if result else []


def _fetch_kline_raw(code: str, lmt: int = 30) -> tuple:
    """拉取 ETF 1 分钟 K 线，返回 (收盘价列表, ETF名称)。

    K 线接口的 data.name 包含真实 ETF 名称，可用于修正 spot 快照中找不到的名称。

    Returns:
        (closes, name)，失败返回 ([], "")
    """
    try:
        secid = _etf_secid(code)
        url = "https://push2delay.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "1",
            "fqt": "0",
            "end": "20500101",
            "lmt": str(lmt),
        }
        resp = _kline_session.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return [], ""
        data = resp.json().get("data") or {}
        name = data.get("name", "")
        klines = data.get("klines") or []
        closes = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    closes.append(float(parts[2]))
                except (ValueError, IndexError):
                    continue
        return closes, name
    except Exception as e:
        logger.debug(f"获取 {code} 1分钟K线失败: {e}")
        return [], ""


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


def _calc_ma_slope(closes: list, window: int) -> dict:
    """计算 MA(window) 最近 3 个时间点的斜率度数。

    返回 {"prev2": float, "prev": float, "now": float}
    - now:   当前根斜率 = MA(t0) - MA(t-1)
    - prev:  上一根斜率 = MA(t-1) - MA(t-2)
    - prev2: 上上根斜率 = MA(t-2) - MA(t-3)
    分别对应前端表格中 3 列（当前分钟/一分钟前/两分钟前）。
    数据不足时返回 0.0
    """
    import math

    def _slope(vals, offset=0):
        if len(vals) < window + 1 + offset:
            return 0.0
        end_a = len(vals) - offset
        end_b = len(vals) - 1 - offset
        ma_a = sum(vals[end_a - window:end_a]) / window
        ma_b = sum(vals[end_b - window:end_b]) / window
        diff = ma_a - ma_b
        # 转角度：arctan(diff * 100) 放大到有区分度的度数范围
        # 微弱趋势 ±2-3°，明显趋势 ±15-25°，剧烈趋势 ±45°+
        return round(math.degrees(math.atan(diff * 100)), 1)

    return {
        "prev2": _slope(closes, 2),
        "prev": _slope(closes, 1),
        "now": _slope(closes, 0),
    }


# Redis 缓存键前缀和 TTL
_ETF_MA_CACHE_PREFIX = "etf_ma:"
_ETF_MA_CACHE_TTL = 120  # 2 分钟，后台定时任务每分钟刷新


async def get_etf_ma_slopes(codes: list) -> dict:
    """批量获取 ETF 的分时 MA5/MA10 斜率方向。

    数据流：Redis 缓存（后台定时任务每分钟刷新）→ 未命中的实时拉取。
    前端打开页面时大部分数据已在 Redis 里，直接 mget 秒出；
    只有新添加的 ETF 首次访问时需实时拉取（0.7s），之后由后台任务接管。

    Args:
        codes: ETF 代码列表

    Returns:
        {code: {"ma_slope_1m": {"ma5": {"now": int, "prev": int}, "ma10": {"now": int, "prev": int}}, ...}}
        int 含义: 1=上升, -1=下降, 0=走平
    """
    import json as _json

    codes = [c.strip().zfill(6) for c in codes if c]
    if not codes:
        return {}

    result = {}
    missing_codes = []

    # 1) 优先从 Redis 批量读取（后台任务已缓存的）
    try:
        from app.core.redis_client import get_redis
        redis = get_redis()
        keys = [f"{_ETF_MA_CACHE_PREFIX}{c}" for c in codes]
        values = await redis.mget(keys)
        for code, val in zip(codes, values):
            if val:
                try:
                    result[code] = _json.loads(val)
                except Exception:
                    missing_codes.append(code)
            else:
                missing_codes.append(code)
    except Exception as e:
        logger.debug(f"ETF MA Redis 缓存读取跳过: {e}")
        missing_codes = list(codes)

    # 2) 未命中的实时拉取（新添加的 ETF 首次访问）
    if missing_codes:
        fresh_data = await _fetch_and_calc_slopes(missing_codes)
        result.update(fresh_data)

        # 回写 Redis 供后续使用
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            pipe = redis.pipeline()
            for code, slopes in fresh_data.items():
                pipe.setex(f"{_ETF_MA_CACHE_PREFIX}{code}", _ETF_MA_CACHE_TTL, _json.dumps(slopes))
            await pipe.execute()
        except Exception as e:
            logger.debug(f"ETF MA Redis 缓存写入跳过: {e}")

    # 3) 对仍无数据的 ETF 填充默认值（3 个时间点都为 0）
    _zero3 = {"prev2": 0, "prev": 0, "now": 0}
    for code in codes:
        if code not in result:
            result[code] = {
                "ma_slope_1m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
                "ma_slope_5m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
                "ma_slope_15m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
                "ma_slope_30m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
            }

    return result


async def _fetch_and_calc_slopes(codes: list) -> dict:
    """拉取多只 ETF 的 1 分钟 K 线并计算 4 周期 MA 斜率。

    每只 ETF 只请求 1 次 1 分钟 K 线（用全局 Session 复用连接），
    本地聚合算 5/15/30 分钟，再算 MA5/MA10 斜率。
    """
    async def _fetch_one(code: str) -> tuple:
        closes_1m, name = await asyncio.to_thread(_fetch_kline_raw, code)

        # 顺带把名称存到 Redis（供 etfs_service 修正假名）
        if name:
            try:
                from app.core.redis_client import get_redis
                redis = get_redis()
                await redis.setex(f"etf_name:{code}", 86400, name)
            except Exception:
                pass

        if not closes_1m:
            _zero3 = {"prev2": 0, "prev": 0, "now": 0}
            return code, {
                "ma_slope_1m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
                "ma_slope_5m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
                "ma_slope_15m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
                "ma_slope_30m": {"ma5": dict(_zero3), "ma10": dict(_zero3)},
            }

        closes_5m = _aggregate_closes(closes_1m, 5)
        closes_15m = _aggregate_closes(closes_1m, 15)
        closes_30m = _aggregate_closes(closes_1m, 30)

        return code, {
            "ma_slope_1m": {"ma5": _calc_ma_slope(closes_1m, 5), "ma10": _calc_ma_slope(closes_1m, 10)},
            "ma_slope_5m": {"ma5": _calc_ma_slope(closes_5m, 5), "ma10": _calc_ma_slope(closes_5m, 10)},
            "ma_slope_15m": {"ma5": _calc_ma_slope(closes_15m, 5), "ma10": _calc_ma_slope(closes_15m, 10)},
            "ma_slope_30m": {"ma5": _calc_ma_slope(closes_30m, 5), "ma10": _calc_ma_slope(closes_30m, 10)},
        }

    tasks = [_fetch_one(code) for code in codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    slope_data = {}
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"ETF MA 斜率计算异常: {result}")
            continue
        code, slopes = result
        slope_data[code] = slopes

    return slope_data


async def refresh_etf_ma_slopes_cache(codes: list) -> int:
    """后台定时任务：刷新 ETF 均线斜率到 Redis。

    由 APScheduler 每分钟调用，拉取所有用户 ETF 的最新 K 线，
    计算斜率后写入 Redis（TTL=120s）。前端读取时直接命中 Redis 秒出。

    Returns:
        成功刷新的 ETF 数量
    """
    import json as _json

    codes = [c.strip().zfill(6) for c in codes if c]
    if not codes:
        return 0

    # 实时拉取并计算
    fresh_data = await _fetch_and_calc_slopes(codes)
    if not fresh_data:
        return 0

    # 写入 Redis
    try:
        from app.core.redis_client import get_redis
        redis = get_redis()
        pipe = redis.pipeline()
        for code, slopes in fresh_data.items():
            pipe.setex(f"{_ETF_MA_CACHE_PREFIX}{code}", _ETF_MA_CACHE_TTL, _json.dumps(slopes))
        await pipe.execute()
        logger.info(f"[ETF MA] 后台刷新 {len(fresh_data)}/{len(codes)} 只 ETF 均线斜率到 Redis")
        return len(fresh_data)
    except Exception as e:
        logger.warning(f"[ETF MA] Redis 写入失败: {e}")
        return 0


async def refresh_etf_spot_cache() -> int:
    """后台定时任务：刷新全市场 ETF 行情快照到 Redis。

    拉取全市场 ETF spot（约 1200 只），整体序列化为一个 JSON 存入 Redis。
    前端读取时直接命中 Redis 秒出，避免分页拉取导致的偶发性超长等待。
    TTL=90s，由每分钟定时任务刷新。
    """
    import json as _json

    svc = get_quotes_service()
    data = await asyncio.to_thread(svc._fetch_etf_spot)
    if not data:
        return 0

    try:
        from app.core.redis_client import get_redis
        redis = get_redis()
        await redis.setex("etf_spot_all", 90, _json.dumps(data, default=str))
        # 同步更新内存缓存
        svc._etf_cache = data
        svc._etf_cache_ts = time.time()
        logger.info(f"[ETF Spot] 后台刷新 {len(data)} 只 ETF 行情到 Redis")
        return len(data)
    except Exception as e:
        logger.warning(f"[ETF Spot] Redis 写入失败: {e}")
        return 0

