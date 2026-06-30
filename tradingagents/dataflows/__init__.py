# 导入新闻模块（新路径）
try:
    from .news import getNewsData, fetch_top_from_category
except ImportError:
    # 向后兼容：尝试从旧路径导入
    try:
        from .news.google_news import getNewsData
    except ImportError:
        getNewsData = None
    try:
        from .news.reddit import fetch_top_from_category
    except ImportError:
        fetch_top_from_category = None

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入技术指标模块（新路径）
try:
    from .technical import StockstatsUtils, STOCKSTATS_AVAILABLE
except ImportError as e:
    # 向后兼容：尝试从旧路径导入
    try:
        from .technical.stockstats import StockstatsUtils
        STOCKSTATS_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"⚠️ stockstats模块不可用: {e}")
        StockstatsUtils = None
        STOCKSTATS_AVAILABLE = False

from .interface import (
    # News functions
    get_google_news,
    get_reddit_global_news,
    get_reddit_company_news,
    # Technical analysis functions
    get_stock_stats_indicators_window,
    get_stockstats_indicator,
    # Tushare data functions
    get_china_stock_data_tushare,
    get_china_stock_fundamentals_tushare,
    # Unified China data functions (recommended)
    get_china_stock_data_unified,
    get_china_stock_info_unified,
    switch_china_data_source,
    get_current_china_data_source,
    # Market data functions
    get_stock_data_by_market,
)

__all__ = [
    # News functions
    "get_google_news",
    "get_reddit_global_news",
    "get_reddit_company_news",
    # Technical analysis functions
    "get_stock_stats_indicators_window",
    "get_stockstats_indicator",
    # Tushare data functions
    "get_china_stock_data_tushare",
    "get_china_stock_fundamentals_tushare",
    # Unified China data functions
    "get_china_stock_data_unified",
    "get_china_stock_info_unified",
    "switch_china_data_source",
    "get_current_china_data_source",
    # Market data functions
    "get_stock_data_by_market",
]
