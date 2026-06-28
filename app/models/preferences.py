"""
用户偏好设置模型

单用户本地部署模式下，偏好设置存储在 system_configs 集合中，
不再绑定用户账户。
"""

from typing import List
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """用户偏好设置"""

    # 分析偏好
    default_market: str = "A股"
    default_depth: str = "3"  # 1-5级，3级为标准分析（推荐）
    default_analysts: List[str] = Field(default_factory=lambda: ["市场分析师", "基本面分析师"])
    auto_refresh: bool = True
    refresh_interval: int = 30  # 秒

    # 外观设置
    ui_theme: str = "light"
    sidebar_width: int = 240

    # 语言和地区
    language: str = "zh-CN"

    # 通知设置
    notifications_enabled: bool = True
    email_notifications: bool = False
    desktop_notifications: bool = True
    analysis_complete_notification: bool = True
    system_maintenance_notification: bool = True
