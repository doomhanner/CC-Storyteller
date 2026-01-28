"""
OpenAI-Compatible Provider - Works with OpenAI API and compatible servers.

This provider works with:
- OpenAI API (GPT-4, GPT-3.5)
- Ollama (with OpenAI compatibility mode)
- llama.cpp server (with --api-key flag)
- vLLM (OpenAI-compatible server)
- LM Studio (local server)
- LocalAI
- text-generation-webui (with OpenAI extension)
- TabbyAPI
- Any other OpenAI-compatible endpoint

This is the most versatile provider for local models since most
local inference servers implement OpenAI's API format.
"""

import json
from typing import Any

import httpx

from storyteller.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderConfig,
    ProviderType,
)


# Common local model presets
LOCAL_MODEL_PRESETS = {
    # Ollama default
    "ollama": {
        "api_base": "http://localhost:11434/v1",
        "models": ["llama3.2", "mistral", "mixtral", "qwen2.5", "deepseek-r1"],
    },
    # llama.cpp server
    "llamacpp": {
        "api_base": "http://localhost:8080/v1",
        "models": ["default"],  # llama.cpp uses loaded model
    },
    # LM Studio
    "lmstudio": {
        "api_base": "http://localhost:1234/v1",
        "models": ["local-model"],  # LM Studio uses loaded model
    },
    # vLLM
    "vllm": {
        "api_base": "http://localhost:8000/v1",
        "models": [],  # Depends on loaded model
    },
    # LocalAI
    "localai": {
        "api_base": "http://localhost:8080/v1",
        "models": [],
    },
    # text-generation-webui
    "textgen": {
        "api_base": "http://localhost:5000/v1",
        "models": [],
    },
}

# Recommended models for roleplay/creative writing
RECOMMENDED_MODELS = {
    # Cloud
    "gpt-4-turbo": "Best GPT for creative writing",
    "gpt-4o": "Fast and capable",
    # Local (via Ollama)
    "llama3.2:70b": "Excellent open model, needs ~40GB VRAM",
    "llama3.2:8b": "Good balance of quality and speed",
    "mistral:7b": "Fast and coherent",
    "mixtral:8x7b": "MoE model, good quality",
    "qwen2.5:32b": "Strong Chinese/English model",
    "deepseek-r1:32b": "Strong reasoning model",
    "nous-hermes-2": "Fine-tuned for roleplay",
    "mythomist": "Creative writing focused",
}


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider for OpenAI API and compatible servers.

    Works with both the official OpenAI API and local servers
    that implement the OpenAI API format.
    """

    def __init__(self, config: ProviderConfig):
        """Initialize the OpenAI-compatible provider."""
        # Set defaults
        if not config.api_base:
            if config.provider_type == ProviderType.OPENAI:
                config.api_base = "https://api.openai.com/v1"
            else:
                config.api_base = "http://localhost:11434/v1"  # Ollama default

        config.supports_system_prompt = True
        config.supports_json_mode = True  # OpenAI has native JSON mode
        config.supports_tools = True

        super().__init__(config)
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_available(self) -> bool:
        """Check if the provider is available."""
        # For OpenAI, need API key
        if self.config.provider_type == ProviderType.OPENAI:
            return bool(self.config.api_key)
        # For local, just need the server to be configured
        return bool(self.config.api_base)

    def _create_client(self) -> httpx.AsyncClient:
        """Create an async HTTP client."""
        headers = {"Content-Type": "application/json"}

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization

        return httpx.AsyncClient(
            base_url=self.config.api_base,
            headers=headers,
            timeout=self.config.timeout,
        )

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = self._create_client()
        return self._http_client

    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Generate a response using the OpenAI-compatible API.

        Args:
            messages: List of chat messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences
            json_mode: If True, request JSON output

        Returns:
            LLMResponse with generated text
        """
        # Format messages for OpenAI API
        formatted_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if stop_sequences:
            payload["stop"] = stop_sequences

        if json_mode and self.config.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Make the API call
        response = await self.http_client.post("/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()

        # Extract response
        choice = data["choices"][0]
        text = choice["message"]["content"]

        # Token usage (may not be available for all local servers)
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=data.get("model", self.config.model),
            finish_reason=choice.get("finish_reason", ""),
            raw_response=data,
        )

    async def list_models(self) -> list[str]:
        """
        List available models from the server.

        Returns:
            List of model IDs
        """
        try:
            response = await self.http_client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
        except Exception:
            return []

    async def check_health(self) -> tuple[bool, str]:
        """Check if the server is responsive."""
        try:
            models = await self.list_models()
            if models:
                return True, f"OK - {len(models)} models available"
            # Some servers don't implement /models, try a generation
            return await super().check_health()
        except httpx.ConnectError:
            return False, "Connection failed - is the server running?"
        except Exception as e:
            return False, f"Error: {e}"


def create_openai_config(
    api_key: str,
    model: str = "gpt-4-turbo",
    organization: str = "",
) -> ProviderConfig:
    """
    Create config for OpenAI API.

    Args:
        api_key: OpenAI API key
        model: Model to use
        organization: Optional organization ID

    Returns:
        ProviderConfig for OpenAI
    """
    return ProviderConfig(
        provider_type=ProviderType.OPENAI,
        api_key=api_key,
        api_base="https://api.openai.com/v1",
        model=model,
        organization=organization,
        supports_json_mode=True,
        max_context_length=128000 if "gpt-4" in model else 16385,
        display_name=f"OpenAI {model}",
        description="OpenAI GPT models",
    )


def create_local_config(
    preset: str = "ollama",
    model: str = "",
    api_base: str = "",
    api_key: str = "",
) -> ProviderConfig:
    """
    Create config for a local model server.

    Args:
        preset: Server preset (ollama, llamacpp, lmstudio, vllm, localai, textgen)
        model: Model to use (or empty for server default)
        api_base: Custom API base URL (overrides preset)
        api_key: API key if required by server

    Returns:
        ProviderConfig for local server
    """
    preset_config = LOCAL_MODEL_PRESETS.get(preset, LOCAL_MODEL_PRESETS["ollama"])

    return ProviderConfig(
        provider_type=ProviderType.OPENAI_COMPATIBLE,
        api_key=api_key,
        api_base=api_base or preset_config["api_base"],
        model=model or (preset_config["models"][0] if preset_config["models"] else ""),
        supports_json_mode=False,  # Most local servers don't support this reliably
        max_context_length=8192,  # Conservative default
        display_name=f"Local ({preset}: {model or 'default'})",
        description=f"Local model via {preset}",
    )
