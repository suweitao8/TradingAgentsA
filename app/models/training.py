"""AI 做 T 训练领域模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.timezone import now_tz


TradeSide = Literal["buy", "sell"]
TrainingMarket = Literal["CN"]


class TrainingSessionCreate(BaseModel):
    """创建训练会话请求。"""

    symbol: str = Field(..., min_length=6, max_length=10, description="股票或 ETF 代码")
    start_date: Optional[str] = Field(default=None, description="训练开始日期，YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="训练结束日期，YYYY-MM-DD")
    initial_cash: float = Field(default=100000, gt=0, description="初始本金")
    total_days: int = Field(default=30, ge=1, le=120, description="训练交易日数")
    market: TrainingMarket = Field(default="CN", description="市场类型")
    note: Optional[str] = Field(default=None, description="训练备注")


class TrainingAction(BaseModel):
    """训练中的一笔模拟交易。"""

    side: TradeSide = Field(..., description="交易方向")
    quantity: int = Field(..., gt=0, description="数量")
    price: float = Field(..., gt=0, description="成交价格")
    trade_date: Optional[str] = Field(default=None, description="交易日期，YYYY-MM-DD")
    reason: Optional[str] = Field(default=None, description="交易理由")


class TrainingPosition(BaseModel):
    """当前持仓。"""

    symbol: str = Field(..., description="标的代码")
    quantity: int = Field(..., ge=0, description="持仓数量")
    avg_cost: float = Field(..., ge=0, description="持仓均价")
    market_value: float = Field(..., ge=0, description="持仓市值")
    unrealized_pnl: float = Field(..., description="未实现盈亏")


class TrainingAdvice(BaseModel):
    """规则教练建议。"""

    trend_strength: str
    volume_change: str
    t_suitability: str
    risk_level: str
    chase_risk: str
    dip_buy_suitability: str
    position_range: str
    reason: str


class TrainingSessionResponse(BaseModel):
    """训练会话摘要。"""

    model_config = ConfigDict(extra="allow")

    session_id: str
    symbol: str
    symbol_name: Optional[str] = None
    market: TrainingMarket = "CN"
    start_date: str
    end_date: str = ""
    current_step: int = 0
    total_days: int = 30
    initial_cash: float = 100000
    cash: float = 100000
    positions: List[TrainingPosition] = Field(default_factory=list)
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    total_equity: float = 100000
    trade_count: int = 0
    status: Literal["active", "finished", "paused"] = "active"
    created_at: datetime = Field(default_factory=now_tz)
    updated_at: datetime = Field(default_factory=now_tz)


class TrainingSessionSummary(BaseModel):
    """璁粌存档摘要銆?"""

    model_config = ConfigDict(extra="allow")

    session_id: str
    symbol: str
    symbol_name: Optional[str] = None
    market: TrainingMarket = "CN"
    start_date: str
    end_date: str = ""
    current_step: int = 0
    total_days: int = 30
    initial_cash: float = 100000
    cash: float = 100000
    total_equity: float = 100000
    trade_count: int = 0
    status: Literal["active", "finished", "paused"] = "active"
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=now_tz)
    updated_at: datetime = Field(default_factory=now_tz)


class TrainingReplayStep(BaseModel):
    """训练回放当前可见窗口。"""

    trade_date: str
    bar_index: int
    visible_bars: List[Dict[str, Any]] = Field(default_factory=list)
    is_finished: bool = False
    current_price: Optional[float] = None
    advice: Optional[TrainingAdvice] = None
    session: Optional[TrainingSessionResponse] = None


class TrainingReport(BaseModel):
    """赛后复盘报告。"""

    session_id: str
    symbol: str
    start_date: str
    end_date: str
    final_cash: float
    final_equity: float
    realized_pnl: float
    unrealized_pnl: float
    active_return: float
    buy_and_hold_return: float
    excess_return: float
    trade_count: int
    max_drawdown: float
    good_trades: List[Dict[str, Any]] = Field(default_factory=list)
    bad_trades: List[Dict[str, Any]] = Field(default_factory=list)
    advice: str
