"""
LLM Provider Abstraction Layer.

Supports multiple LLM backends:
- Cloud APIs: Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- Local Models: Ollama, llama.cpp, vLLM, LM Studio, etc.

Most local model servers expose an OpenAI-compatible API, making them
easy to integrate through the OpenAICompatible provider.
"""

from storyteller.providers.base import (
    LLMProvider,
    LLMResponse,
    ProviderConfig,
    ProviderType,
)
from storyteller.providers.registry import (
    get_provider,
    register_provider,
    list_providers,
    get_provider_for_role,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderConfig",
    "ProviderType",
    "get_provider",
    "register_provider",
    "list_providers",
    "get_provider_for_role",
]
