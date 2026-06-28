"""
公共数据模型

包含跨模块共享的基础类型定义。
"""

from datetime import datetime
from app.utils.timezone import now_tz
from typing import Optional, Any, Annotated, List
from pydantic import BaseModel, Field, BeforeValidator, PlainSerializer
from bson import ObjectId


def validate_object_id(v: Any) -> ObjectId:
    """验证ObjectId"""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return ObjectId(v)
    raise ValueError("Invalid ObjectId")


def serialize_object_id(v: ObjectId) -> str:
    """序列化ObjectId为字符串"""
    return str(v)


# 创建自定义ObjectId类型
PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
    PlainSerializer(serialize_object_id, return_type=str),
]


class FavoriteStock(BaseModel):
    """自选股信息"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场类型")
    added_at: datetime = Field(default_factory=now_tz, description="添加时间")
    tags: List[str] = Field(default_factory=list, description="用户标签")
    notes: str = Field(default="", description="用户备注")
    alert_price_high: Optional[float] = Field(None, description="价格上限提醒")
    alert_price_low: Optional[float] = Field(None, description="价格下限提醒")
