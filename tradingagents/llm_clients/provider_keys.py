"""LLM Provider 元数据注册表（单一数据源）。

本项目历史上 provider 信息散落在 7 处（provider_keys/factory/openai_client/
trading_graph/config/config_service/init_providers），别名/env_key/默认 URL
各自重复定义且已出现不一致（如 siliconflow env_key）。

本模块将其收敛为单一 `PROVIDER_REGISTRY`，其余代码统一查表，新增 provider
只需在此追加一条记录即可。

每个 provider 的 client_type 决定走哪个 LLM 客户端：
  - openai_compat: OpenAI 兼容协议（ChatOpenAI），含 deepseek/qwen/glm/jdcloud 等
  - google: Google AI（ChatGoogleGenerativeAI）
  - anthropic: Anthropic（ChatAnthropic）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProviderMeta:
    """单个 LLM provider 的元数据。"""

    canonical_name: str  # 规范名（如 "qwen"），全仓唯一标识
    aliases: tuple = ()  # 别名列表（含中文），normalize 时映射到 canonical_name
    env_key: Optional[str] = None  # 默认环境变量名（如 "DASHSCOPE_API_KEY"），None 表示无默认 key
    default_url: Optional[str] = None  # 默认 API 地址
    client_type: str = "openai_compat"  # 客户端类型: openai_compat / google / anthropic
    default_active: bool = False  # 是否默认启用（DB 种子用）
    display_name: str = ""  # 展示名（DB 种子用）


# ---------------------------------------------------------------------------
# 唯一权威 Provider 注册表
# ---------------------------------------------------------------------------
# 新增 provider 只需在此追加一条。所有 env_key / default_url / client_type 的
# 消费方（factory / openai_client / trading_graph / config_service / init_providers）
# 统一从此表读取，禁止在消费方硬编码重复值。

PROVIDER_REGISTRY: Dict[str, ProviderMeta] = {
    "openai": ProviderMeta(
        canonical_name="openai",
        aliases=(),
        env_key="OPENAI_API_KEY",
        default_url="https://api.openai.com/v1",
        client_type="openai_compat",
        display_name="OpenAI",
    ),
    "qwen": ProviderMeta(
        canonical_name="qwen",
        aliases=("dashscope", "alibaba", "阿里百炼", "百炼"),
        env_key="DASHSCOPE_API_KEY",
        default_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        client_type="openai_compat",
        display_name="阿里百炼 (Qwen)",
    ),
    "glm": ProviderMeta(
        canonical_name="glm",
        aliases=("zhipu", "智谱", "智谱ai", "智谱AI"),
        env_key="ZHIPU_API_KEY",
        default_url="https://open.bigmodel.cn/api/paas/v4/",
        client_type="openai_compat",
        display_name="智谱 GLM",
    ),
    "deepseek": ProviderMeta(
        canonical_name="deepseek",
        aliases=(),
        env_key="DEEPSEEK_API_KEY",
        default_url="https://api.deepseek.com",
        client_type="openai_compat",
        display_name="DeepSeek",
    ),
    "google": ProviderMeta(
        canonical_name="google",
        aliases=(),
        env_key="GOOGLE_API_KEY",
        default_url="https://generativelanguage.googleapis.com/v1beta",
        client_type="google",
        display_name="Google AI",
    ),
    "anthropic": ProviderMeta(
        canonical_name="anthropic",
        aliases=("claude",),
        env_key="ANTHROPIC_API_KEY",
        default_url="https://api.anthropic.com",
        client_type="anthropic",
        display_name="Anthropic Claude",
    ),
    "openrouter": ProviderMeta(
        canonical_name="openrouter",
        aliases=(),
        env_key="OPENROUTER_API_KEY",
        default_url="https://openrouter.ai/api/v1",
        client_type="openai_compat",
        display_name="OpenRouter",
    ),
    "aihubmix": ProviderMeta(
        canonical_name="aihubmix",
        aliases=(),
        env_key="AIHUBMIX_API_KEY",
        default_url="https://aihubmix.com/v1",
        client_type="openai_compat",
        display_name="AIHubMix",
    ),
    "ollama": ProviderMeta(
        canonical_name="ollama",
        aliases=(),
        env_key=None,  # ollama 无需 api key
        default_url="http://localhost:11434/v1",
        client_type="openai_compat",
        display_name="Ollama (本地)",
    ),
    "qianfan": ProviderMeta(
        canonical_name="qianfan",
        aliases=("baidu", "百度"),
        env_key="QIANFAN_API_KEY",
        default_url="https://qianfan.baidubce.com/v2",
        client_type="openai_compat",
        display_name="百度千帆",
    ),
    "siliconflow": ProviderMeta(
        canonical_name="siliconflow",
        aliases=("硅基流动",),
        env_key="SILICONFLOW_API_KEY",
        default_url="https://api.siliconflow.cn/v1",
        client_type="openai_compat",
        display_name="硅基流动 SiliconFlow",
    ),
    "jdcloud": ProviderMeta(
        canonical_name="jdcloud",
        aliases=("jd", "京东", "京东云", "言犀"),
        env_key="JDCLOUD_API_KEY",
        default_url="https://modelservice.jdcloud.com/coding/openai/v1",
        client_type="openai_compat",
        default_active=True,  # 本项目当前默认渠道
        display_name="京东云",
    ),
    "custom_openai": ProviderMeta(
        canonical_name="custom_openai",
        aliases=(),
        env_key="CUSTOM_OPENAI_API_KEY",
        default_url=None,  # 无固定 URL，由调用方传入
        client_type="openai_compat",
        display_name="自定义 OpenAI 兼容",
    ),
}


# ---------------------------------------------------------------------------
# 从注册表派生的查找索引（模块加载时构建一次）
# ---------------------------------------------------------------------------

def _build_alias_index() -> Dict[str, str]:
    """构建 别名 -> canonical_name 的索引（含 canonical_name 自身和中英文）。"""
    index: Dict[str, str] = {}
    for canonical, meta in PROVIDER_REGISTRY.items():
        index[canonical] = canonical
        index[canonical.lower()] = canonical
        for alias in meta.aliases:
            index[alias] = canonical
            index[alias.lower()] = canonical
    return index


_ALIAS_INDEX = _build_alias_index()


def _build_openai_compat_set() -> frozenset:
    """构建 openai_compat 类型 provider 的 canonical_name 集合。"""
    return frozenset(
        name for name, meta in PROVIDER_REGISTRY.items()
        if meta.client_type == "openai_compat"
    )


_OPENAI_COMPATIBLE_PROVIDERS = _build_openai_compat_set()


# ---------------------------------------------------------------------------
# 公共 API（保持向后兼容，消费方统一用这些函数）
# ---------------------------------------------------------------------------

def normalize_provider_key(provider: str) -> str:
    """将 provider 名称/别名/中文名归一化为 canonical_name。

    >>> normalize_provider_key("dashscope")
    'qwen'
    >>> normalize_provider_key("京东云")
    'jdcloud'
    >>> normalize_provider_key("")
    ''
    """
    if provider is None:
        return ""

    raw = str(provider).strip()
    if not raw:
        return ""

    # 先查别名索引（含中文）
    result = _ALIAS_INDEX.get(raw)
    if result:
        return result

    lowered = raw.lower()
    result = _ALIAS_INDEX.get(lowered)
    if result:
        return result

    # 未知 provider 原样返回（供自定义厂家兜底）
    return lowered


def env_key_for_provider(provider: str) -> str:
    """获取 provider 的默认环境变量名（如 "DASHSCOPE_API_KEY"），无则返回空串。"""
    key = normalize_provider_key(provider)
    meta = PROVIDER_REGISTRY.get(key)
    return meta.env_key if meta and meta.env_key else ""


def default_backend_url(provider: str) -> str:
    """获取 provider 的默认 API 地址，无则返回空串。"""
    key = normalize_provider_key(provider)
    meta = PROVIDER_REGISTRY.get(key)
    return meta.default_url if meta and meta.default_url else ""


def canonical_aliases(provider: str) -> list[str]:
    """获取 provider 的别名列表（不含 canonical_name 自身）。"""
    key = normalize_provider_key(provider)
    meta = PROVIDER_REGISTRY.get(key)
    return list(meta.aliases) if meta else []


def is_openai_compatible(provider: str) -> bool:
    """判断 provider 是否走 OpenAI 兼容协议。"""
    return normalize_provider_key(provider) in _OPENAI_COMPATIBLE_PROVIDERS


def get_provider_meta(provider: str) -> Optional[ProviderMeta]:
    """获取 provider 的完整元数据，不存在返回 None。"""
    key = normalize_provider_key(provider)
    return PROVIDER_REGISTRY.get(key)


def all_provider_names() -> List[str]:
    """返回所有已注册 provider 的 canonical_name 列表。"""
    return list(PROVIDER_REGISTRY.keys())
