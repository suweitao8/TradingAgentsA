#!/usr/bin/env python3
"""
初始化大模型厂家数据脚本

厂家元数据（canonical_name / display_name / default_url / 是否启用）统一从
tradingagents.llm_clients.provider_keys.PROVIDER_REGISTRY 派生，本脚本不再
硬编码重复的 URL 和名称，新增 provider 只需在注册表追加一条。

如需补充 provider 的展示描述（description/website/api_doc_url），在下方
_PROVIDER_EXTRA_INFO 字典维护。
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database import init_db, get_mongo_db
from tradingagents.llm_clients.provider_keys import PROVIDER_REGISTRY, canonical_aliases

# 展示性补充信息（非协议必需，仅用于前端展示）
_PROVIDER_EXTRA_INFO = {
    "jdcloud": {
        "description": "京东云言犀模型服务，提供 Kimi K2.5 等大模型，OpenAI 兼容接口。本项目默认渠道。",
        "website": "https://modelservice.jdcloud.com/",
        "api_doc_url": "https://modelservice.jdcloud.com/coding/openai/v1",
    },
    "openai": {
        "description": "OpenAI 是人工智能领域的领先公司，提供 GPT 系列模型",
        "website": "https://openai.com",
        "api_doc_url": "https://platform.openai.com/docs",
    },
    "anthropic": {
        "description": "Anthropic 专注于 AI 安全研究，提供 Claude 系列模型",
        "website": "https://anthropic.com",
        "api_doc_url": "https://docs.anthropic.com",
    },
    "google": {
        "description": "Google 的人工智能平台，提供 Gemini 系列模型",
        "website": "https://ai.google.dev",
        "api_doc_url": "https://ai.google.dev/docs",
    },
    "glm": {
        "description": "智谱 AI 提供 GLM 系列中文大模型",
        "website": "https://zhipuai.cn",
        "api_doc_url": "https://open.bigmodel.cn/doc",
    },
    "deepseek": {
        "description": "DeepSeek 提供高性能的 AI 推理服务",
        "website": "https://www.deepseek.com",
        "api_doc_url": "https://platform.deepseek.com/api-docs",
    },
    "qwen": {
        "description": "阿里云百炼大模型服务平台，提供通义千问等模型",
        "website": "https://bailian.console.aliyun.com",
        "api_doc_url": "https://help.aliyun.com/zh/dashscope/",
    },
    "siliconflow": {
        "description": "硅基流动提供高性价比的 AI 推理服务，支持多种开源模型",
        "website": "https://siliconflow.cn",
        "api_doc_url": "https://docs.siliconflow.cn",
    },
    "aihubmix": {
        "description": "AIHubMix 深度适配全球顶级模型，多模型交叉验证，无限并发按量计费。",
        "website": "https://aihubmix.com",
        "api_doc_url": "https://docs.aihubmix.com/cn/quick-start",
    },
    "openrouter": {
        "description": "OpenRouter 提供 300+ 大模型的统一 API 接口",
        "website": "https://openrouter.ai",
        "api_doc_url": "https://openrouter.ai/docs",
    },
    "ollama": {
        "description": "Ollama 本地大模型运行环境，无需联网即可使用",
        "website": "https://ollama.com",
        "api_doc_url": "https://github.com/ollama/ollama/blob/main/docs/api.md",
    },
    "qianfan": {
        "description": "百度千帆大模型平台，提供文心一言等模型",
        "website": "https://qianfan.cloud.baidu.com",
        "api_doc_url": "https://cloud.baidu.com/doc/WENXINWORKSHOP/index",
    },
    "custom_openai": {
        "description": "自定义 OpenAI 兼容接口，适用于自建或第三方兼容服务",
        "website": "",
        "api_doc_url": "",
    },
}


async def init_providers():
    """初始化大模型厂家数据。

    从 PROVIDER_REGISTRY 派生所有 provider，default_active=True 的写入为
    is_active=True，其余写入为 is_active=False（前端可手动启用）。
    """
    print("🚀 开始初始化大模型厂家数据（从 PROVIDER_REGISTRY 派生）...")

    await init_db()
    db = get_mongo_db()
    providers_collection = db.llm_providers

    # 从注册表派生种子数据
    providers_data = []
    for canonical_name, meta in PROVIDER_REGISTRY.items():
        extra = _PROVIDER_EXTRA_INFO.get(canonical_name, {})
        entry = {
            "name": canonical_name,
            "display_name": meta.display_name or canonical_name,
            "description": extra.get("description", f"{meta.display_name} LLM 服务"),
            "website": extra.get("website", ""),
            "api_doc_url": extra.get("api_doc_url", meta.default_url or ""),
            "default_base_url": meta.default_url or "",
            "is_active": meta.default_active,
            "supported_features": ["chat", "completion", "function_calling", "streaming"],
        }
        aliases = canonical_aliases(canonical_name)
        if aliases:
            entry["aliases"] = aliases
        providers_data.append(entry)

    # 清除现有数据
    await providers_collection.delete_many({})
    print("🧹 清除现有厂家数据")

    # 插入新数据
    active_count = 0
    for provider_data in providers_data:
        provider_data["created_at"] = datetime.utcnow()
        provider_data["updated_at"] = datetime.utcnow()
        result = await providers_collection.insert_one(provider_data)
        status = "✅ 启用" if provider_data["is_active"] else "⬜ 未启用"
        print(f"  {status} {provider_data['display_name']} ({provider_data['name']})")
        if provider_data["is_active"]:
            active_count += 1

    print(f"🎉 成功初始化 {len(providers_data)} 个厂家（其中 {active_count} 个默认启用）")


if __name__ == "__main__":
    asyncio.run(init_providers())
