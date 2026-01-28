"""
Ollama Provider - Native Ollama API for local models.

Ollama is the easiest way to run local LLMs:
- Simple installation (https://ollama.ai)
- One-command model downloads: `ollama pull llama3.2`
- Runs models optimized for your hardware
- Supports Mac (Metal), Linux (CUDA/ROCm), and Windows

Recommended models for storytelling:
- llama3.2:8b - Fast, good quality (needs ~5GB RAM)
- llama3.2:70b - Excellent quality (needs ~40GB VRAM)
- mistral:7b - Fast and coherent
- mixtral:8x7b - High quality MoE model
- qwen2.5:14b - Strong multilingual model
- nous-hermes-2 - Fine-tuned for roleplay
- mythomist - Creative writing focused
"""

from typing import Any

import httpx

from storyteller.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderConfig,
    ProviderType,
)


# Models known to work well for creative writing/roleplay
OLLAMA_RECOMMENDED = {
    # General purpose - good for both Storyteller and Archivist
    "llama3.2:8b": {
        "description": "Fast and capable, good default choice",
        "vram": "~5GB",
        "quality": "good",
        "speed": "fast",
    },
    "llama3.2:70b": {
        "description": "Excellent quality, needs powerful GPU",
        "vram": "~40GB",
        "quality": "excellent",
        "speed": "slow",
    },
    "qwen2.5:32b": {
        "description": "Strong reasoning and creativity",
        "vram": "~20GB",
        "quality": "excellent",
        "speed": "medium",
    },
    "mistral:7b": {
        "description": "Fast and coherent",
        "vram": "~5GB",
        "quality": "good",
        "speed": "fast",
    },
    "mixtral:8x7b": {
        "description": "MoE architecture, great quality",
        "vram": "~26GB",
        "quality": "excellent",
        "speed": "medium",
    },
    # Roleplay/creative focused
    "nous-hermes-2:10.7b": {
        "description": "Fine-tuned for roleplay and creative writing",
        "vram": "~7GB",
        "quality": "good",
        "speed": "medium",
    },
    # Small/fast for Archivist tasks
    "phi3:mini": {
        "description": "Very fast, good for structured tasks",
        "vram": "~3GB",
        "quality": "moderate",
        "speed": "very fast",
    },
}


class OllamaProvider(LLMProvider):
    """
    Native Ollama provider using Ollama's API.

    Ollama provides an easy way to run local models with automatic
    hardware optimization (Metal on Mac, CUDA on Linux/Windows).
    """

    def __init__(self, config: ProviderConfig):
        """Initialize the Ollama provider."""
        if not config.api_base:
            config.api_base = "http://localhost:11434"

        config.supports_system_prompt = True
        config.supports_json_mode = True  # Ollama supports format: json
        config.supports_tools = False  # Limited tool support

        super().__init__(config)
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_available(self) -> bool:
        """Ollama just needs server to be running."""
        return bool(self.config.api_base)

    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client for Ollama API."""
        return httpx.AsyncClient(
            base_url=self.config.api_base,
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
        Generate a response using Ollama's chat API.

        Args:
            messages: List of chat messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences
            json_mode: If True, request JSON output

        Returns:
            LLMResponse with generated text
        """
        # Format messages for Ollama
        formatted_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        if stop_sequences:
            payload["options"]["stop"] = stop_sequences

        if json_mode:
            payload["format"] = "json"

        # Make the API call
        response = await self.http_client.post("/api/chat", json=payload)
        response.raise_for_status()

        data = response.json()

        # Extract response
        text = data.get("message", {}).get("content", "")

        # Ollama provides some metrics
        metrics = data.get("metrics", {})

        return LLMResponse(
            text=text,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            total_tokens=(
                data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            ),
            model=data.get("model", self.config.model),
            finish_reason=data.get("done_reason", ""),
            raw_response=data,
        )

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List models available in Ollama.

        Returns:
            List of model info dicts with name, size, etc.
        """
        try:
            response = await self.http_client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception:
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull (download) a model from the Ollama library.

        Args:
            model_name: Name of model to pull (e.g., "llama3.2:8b")

        Returns:
            True if successful
        """
        try:
            # This is a streaming endpoint, we just check for success
            response = await self.http_client.post(
                "/api/pull",
                json={"name": model_name, "stream": False},
                timeout=None,  # Model downloads can take a while
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def check_health(self) -> tuple[bool, str]:
        """Check if Ollama is running and responsive."""
        try:
            models = await self.list_models()
            model_names = [m.get("name", "?") for m in models]
            if models:
                return True, f"OK - {len(models)} models: {', '.join(model_names[:3])}"
            return True, "OK - Ollama running but no models installed"
        except httpx.ConnectError:
            return False, "Connection failed - is Ollama running? (try: ollama serve)"
        except Exception as e:
            return False, f"Error: {e}"


def create_ollama_config(
    model: str = "llama3.2:8b",
    api_base: str = "http://localhost:11434",
) -> ProviderConfig:
    """
    Create config for Ollama.

    Args:
        model: Model to use (must be pulled first with `ollama pull <model>`)
        api_base: Ollama server URL

    Returns:
        ProviderConfig for Ollama
    """
    model_info = OLLAMA_RECOMMENDED.get(model, {})

    return ProviderConfig(
        provider_type=ProviderType.OLLAMA,
        api_base=api_base,
        model=model,
        supports_json_mode=True,
        max_context_length=8192,  # Most Ollama models default to 8k
        display_name=f"Ollama {model}",
        description=model_info.get("description", f"Local model via Ollama"),
    )


def get_recommended_models() -> dict[str, dict]:
    """Get recommended Ollama models for storytelling."""
    return OLLAMA_RECOMMENDED
