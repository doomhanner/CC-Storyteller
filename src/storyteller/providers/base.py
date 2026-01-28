"""
Base LLM Provider - Abstract interface for all LLM backends.

This abstraction allows CC-Storyteller to work with any LLM,
whether cloud-hosted or running locally.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    # Cloud Providers
    ANTHROPIC = "anthropic"  # Claude models
    OPENAI = "openai"  # GPT models
    GOOGLE = "google"  # Gemini models

    # Local/Self-hosted (OpenAI-compatible API)
    OPENAI_COMPATIBLE = "openai_compatible"  # Generic OpenAI-compatible server
    OLLAMA = "ollama"  # Ollama local models
    LLAMACPP = "llamacpp"  # llama.cpp server
    VLLM = "vllm"  # vLLM server
    LMSTUDIO = "lmstudio"  # LM Studio
    TABBY = "tabby"  # TabbyAPI
    KOBOLD = "kobold"  # KoboldCpp

    # Special
    MOCK = "mock"  # For testing


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    provider_type: ProviderType
    api_key: str = ""
    api_base: str = ""  # Base URL for API (required for local models)
    model: str = ""  # Model identifier
    organization: str = ""  # For OpenAI org ID

    # Model capabilities (helps with prompt formatting)
    supports_system_prompt: bool = True
    supports_json_mode: bool = False
    supports_tools: bool = False
    max_context_length: int = 8192

    # Connection settings
    timeout: int = 120
    max_retries: int = 3

    # Optional metadata
    display_name: str = ""  # Human-friendly name
    description: str = ""

    def __post_init__(self):
        if not self.display_name:
            self.display_name = f"{self.provider_type.value}:{self.model}"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    finish_reason: str = ""
    raw_response: Any = None  # Original response object

    @property
    def tokens_used(self) -> int:
        """Total tokens used (input + output)."""
        return self.total_tokens or (self.input_tokens + self.output_tokens)


@dataclass
class ChatMessage:
    """A message in a chat conversation."""

    role: str  # "system", "user", "assistant"
    content: str
    name: str | None = None  # Optional name for the message author


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement the core methods for text generation.
    The abstraction handles differences in API formats, authentication,
    and capabilities across different LLM backends.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self._client: Any = None

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return self.config.display_name

    @property
    def model(self) -> str:
        """The model being used."""
        return self.config.model

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (API key set, server running, etc.)."""
        pass

    @abstractmethod
    def _create_client(self) -> Any:
        """Create the underlying API client."""
        pass

    @property
    def client(self) -> Any:
        """Get or create the API client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of chat messages (system, user, assistant)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-2.0)
            stop_sequences: Optional sequences that stop generation
            json_mode: If True, request JSON output (if supported)

        Returns:
            LLMResponse with generated text and metadata
        """
        pass

    def generate_sync(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Synchronous wrapper for generate().

        Args:
            Same as generate()

        Returns:
            LLMResponse with generated text and metadata
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.generate(messages, max_tokens, temperature, stop_sequences, json_mode)
        )

    def format_system_prompt(self, system: str, messages: list[ChatMessage]) -> list[ChatMessage]:
        """
        Format system prompt for providers that handle it differently.

        Some providers (like older local models) don't support system prompts
        directly and need them prepended to the first user message.

        Args:
            system: The system prompt
            messages: The conversation messages

        Returns:
            Modified messages list with system prompt handled appropriately
        """
        if self.config.supports_system_prompt:
            # Provider supports system prompt natively
            return [ChatMessage(role="system", content=system)] + messages
        else:
            # Prepend system prompt to first user message
            if messages and messages[0].role == "user":
                modified_first = ChatMessage(
                    role="user",
                    content=f"{system}\n\n---\n\n{messages[0].content}",
                )
                return [modified_first] + messages[1:]
            return messages

    async def check_health(self) -> tuple[bool, str]:
        """
        Check if the provider is healthy and responsive.

        Returns:
            Tuple of (is_healthy, status_message)
        """
        try:
            # Try a minimal generation
            response = await self.generate(
                messages=[ChatMessage(role="user", content="Hi")],
                max_tokens=5,
                temperature=0,
            )
            return True, f"OK - {self.name} responding"
        except Exception as e:
            return False, f"Error: {e}"
