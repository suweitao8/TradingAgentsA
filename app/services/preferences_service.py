"""
偏好设置服务

单用户本地部署模式下，偏好设置存储在 system_configs 集合中，
以 user_preferences 为键，不再绑定用户账户。
"""

from typing import Optional, Dict, Any
from datetime import datetime

from app.core.database import get_mongo_db_sync
from app.models.preferences import UserPreferences


PREFERENCES_DOC_KEY = "user_preferences"


def get_preferences() -> UserPreferences:
    """获取偏好设置（同步，用于非异步上下文）"""
    try:
        db = get_mongo_db_sync()
        doc = db.system_configs.find_one({"key": PREFERENCES_DOC_KEY})
        if doc and "data" in doc:
            return UserPreferences(**doc["data"])
    except Exception as e:
        print(f"⚠️ [preferences] 从数据库读取偏好设置失败: {e}，使用默认值")

    return UserPreferences()


async def get_preferences_async() -> UserPreferences:
    """获取偏好设置（异步版本）"""
    try:
        from app.core.database import mongo_db
        if mongo_db is not None:
            doc = await mongo_db.system_configs.find_one({"key": PREFERENCES_DOC_KEY})
            if doc and "data" in doc:
                return UserPreferences(**doc["data"])
    except Exception as e:
        print(f"⚠️ [preferences] 异步读取偏好设置失败: {e}，使用默认值")

    return UserPreferences()


async def update_preferences(prefs_update: Dict[str, Any]) -> UserPreferences:
    """更新偏好设置（部分更新，合并已有值）"""
    # 先读取当前值
    current = await get_preferences_async()
    current_dict = current.model_dump()

    # 合并更新
    merged = {**current_dict, **prefs_update}

    # 验证合并后的数据
    validated = UserPreferences(**merged)

    # 写入数据库
    try:
        from app.core.database import mongo_db
        if mongo_db is not None:
            await mongo_db.system_configs.update_one(
                {"key": PREFERENCES_DOC_KEY},
                {
                    "$set": {
                        "key": PREFERENCES_DOC_KEY,
                        "data": validated.model_dump(),
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
    except Exception as e:
        print(f"⚠️ [preferences] 保存偏好设置失败: {e}")

    return validated
