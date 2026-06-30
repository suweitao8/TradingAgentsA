"""
股票工具函数
提供股票代码识别、分类和处理功能
本项目仅支持中国A股市场。
"""

import re
from typing import Dict, Tuple
from enum import Enum

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


class StockMarket(Enum):
    """股票市场枚举"""
    CHINA_A = "china_a"      # 中国A股
    UNKNOWN = "unknown"      # 未知


class StockUtils:
    """股票工具类"""

    @staticmethod
    def identify_stock_market(ticker: str) -> StockMarket:
        """识别股票代码所属市场"""
        if not ticker:
            return StockMarket.UNKNOWN

        ticker = str(ticker).strip().upper()

        # 中国A股：6位数字
        if re.match(r'^\d{6}$', ticker):
            return StockMarket.CHINA_A

        return StockMarket.UNKNOWN

    @staticmethod
    def is_china_stock(ticker: str) -> bool:
        """判断是否为中国A股"""
        return StockUtils.identify_stock_market(ticker) == StockMarket.CHINA_A

    @staticmethod
    def is_hk_stock(ticker: str) -> bool:
        """判断是否为港股（本项目不再支持，恒返回 False）"""
        return False

    @staticmethod
    def is_us_stock(ticker: str) -> bool:
        """判断是否为美股（本项目不再支持，恒返回 False）"""
        return False

    @staticmethod
    def get_currency_info(ticker: str) -> Tuple[str, str]:
        """根据股票代码获取货币信息"""
        market = StockUtils.identify_stock_market(ticker)
        if market == StockMarket.CHINA_A:
            return "人民币", "¥"
        else:
            return "未知", "?"

    @staticmethod
    def get_data_source(ticker: str) -> str:
        """根据股票代码获取推荐的数据源"""
        market = StockUtils.identify_stock_market(ticker)
        if market == StockMarket.CHINA_A:
            return "china_unified"
        else:
            return "unknown"

    @staticmethod
    def normalize_hk_ticker(ticker: str) -> str:
        """标准化港股代码格式（本项目不再支持港股，原样返回）"""
        return ticker

    @staticmethod
    def get_market_info(ticker: str) -> Dict:
        """获取股票市场的详细信息"""
        market = StockUtils.identify_stock_market(ticker)
        currency_name, currency_symbol = StockUtils.get_currency_info(ticker)
        data_source = StockUtils.get_data_source(ticker)

        market_names = {
            StockMarket.CHINA_A: "中国A股",
            StockMarket.UNKNOWN: "未知市场"
        }

        return {
            "ticker": ticker,
            "market": market.value,
            "market_name": market_names[market],
            "currency_name": currency_name,
            "currency_symbol": currency_symbol,
            "data_source": data_source,
            "is_china": market == StockMarket.CHINA_A,
            "is_hk": False,
            "is_us": False
        }


# 便捷函数，保持向后兼容
def is_china_stock(ticker: str) -> bool:
    """判断是否为中国A股（向后兼容）"""
    return StockUtils.is_china_stock(ticker)


def is_hk_stock(ticker: str) -> bool:
    """判断是否为港股（恒返回 False）"""
    return False


def is_us_stock(ticker: str) -> bool:
    """判断是否为美股（恒返回 False）"""
    return False


def get_stock_market_info(ticker: str) -> Dict:
    """获取股票市场信息"""
    return StockUtils.get_market_info(ticker)
