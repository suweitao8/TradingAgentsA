"""
自选股分析报告数据模型

包含两类报告：
- 每日报告（daily）：复用完整多智能体分析，存入 analysis_reports 集合，标记 report_type="daily"
- 盘中实时报告（realtime）：行情快照 + LLM 简评，存入 realtime_reports 集合
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.utils.timezone import now_tz


class QuotesSnapshot(BaseModel):
    """行情快照（实时报告生成时刻的行情）"""
    current_price: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None
    volume_ratio: Optional[float] = None
    amount: Optional[float] = None  # 成交额（万元）


class RealtimeReport(BaseModel):
    """自选股盘中实时报告（轻量）"""
    id: Optional[str] = None
    stock_code: str = Field(..., description="6位股票代码")
    stock_name: Optional[str] = None
    user_id: str = Field(..., description="所属用户")
    market_type: str = Field(default="A股")

    # 时间维度：哪一天 + 第几小时（9-15）
    trade_date: str = Field(..., description="交易日 YYYY-MM-DD")
    hour_slot: int = Field(..., description="所属小时（9-15）")

    # 行情快照（生成时刻）
    quotes_snapshot: QuotesSnapshot = Field(default_factory=QuotesSnapshot)

    # LLM 简评（单次调用产出）
    commentary: str = Field(default="", description="LLM 简评（约200字）")
    recommendation: Optional[str] = Field(None, description="一句话建议：偏多/中性/偏空")
    risk_level: Optional[str] = Field(None, description="风险等级：低/中/高")
    key_points: List[str] = Field(default_factory=list, description="关键点（最多3条）")

    # 元数据
    status: str = Field(default="completed", description="completed/failed")
    error_message: Optional[str] = None
    model_info: Optional[str] = None
    created_at: datetime = Field(default_factory=now_tz)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class FavoriteReportQuery(BaseModel):
    """查询自选股报告的参数"""
    stock_code: str = Field(..., description="6位股票代码")
    report_type: str = Field(default="all", description="all/daily/realtime")
    trade_date: Optional[str] = Field(None, description="交易日 YYYY-MM-DD，默认当天")
    limit: int = Field(default=20, ge=1, le=100)


class GenerateReportRequest(BaseModel):
    """手动触发生成报告的请求"""
    report_type: str = Field(default="realtime", description="daily/realtime")
    stock_code: Optional[str] = Field(None, description="单只股票代码，为空则对全部自选股生成")
