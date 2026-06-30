from typing import Optional

from .base_client import BaseLLMClient
from .provider_keys import normalize_provider_key, is_openai_compatible


def create_llm_client(
    provider: str,
    model: str,
    base_url: Optional[str] = None,
    **kwargs,
) -> BaseLLMClient:
    """根据 provider 创建对应的 LLM 客户端。

    provider 类型和默认配置统一从 PROVIDER_REGISTRY 查表，不再在本文件硬编码。
    """
    canonical = normalize_provider_key(provider)

    if is_openai_compatible(canonical):
        from .openai_client import OpenAIClient

        return OpenAIClient(model, base_url, provider=canonical, **kwargs)

    if canonical == "google":
        from .google_client import GoogleClient

        return GoogleClient(model, base_url, **kwargs)

    if canonical == "anthropic":
        from .anthropic_client import AnthropicClient

        return AnthropicClient(model, base_url, **kwargs)

    raise ValueError(f"Unsupported LLM provider: {provider}")
