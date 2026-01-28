"""
Anthropic Provider - Claude models via the Anthropic API.

Supports all Claude models including:
- claude-opus-4-20250514 (most capable)
- claude-sonnet-4-20250514 (balanced)
- claude-haiku-3-5-20241022 (fast and efficient)
"""

from typing import Any

import anthropic

from storyteller.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderConfig,
    ProviderType,
)


# Default models for each role
ANTHROPIC_MODELS = {
    "storyteller": "claude-sonnet-4-20250514",  # Creative, expressive
    "archivist": "claude-sonnet-4-20250514",  # Logical, structured
    "default": "claude-sonnet-4-20250514",
}


class AnthropicProvider(LLMProvider):
    """
    Provider for Anthropic's Claude models.

    Claude excels at:
    - Long-form creative writing
    - Complex reasoning
    - Following nuanced instructions
    - Maintaining character voice
    """

    def __init__(self, config: ProviderConfig):
        """Initialize the Anthropic provider."""
        # Set defaults for Anthropic
        if not config.model:
            config.model = ANTHROPIC_MODELS["default"]

        config.supports_system_prompt = True
        config.supports_json_mode = False  # Claude uses prompt-based JSON
        config.supports_tools = True
        config.max_context_length = 200000  # Claude 3 has 200k context

        super().__init__(config)

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)

    def _create_client(self) -> anthropic.Anthropic:
        """Create the Anthropic client."""
        kwargs: dict[str, Any] = {"api_key": self.config.api_key}

        if self.config.api_base:
            kwargs["base_url"] = self.config.api_base

        if self.config.timeout:
            kwargs["timeout"] = self.config.timeout

        return anthropic.Anthropic(**kwargs)

    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Generate a response using Claude.

        Args:
            messages: List of chat messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences
            json_mode: If True, append JSON instruction to prompt

        Returns:
            LLMResponse with generated text
        """
        # Separate system message from conversation
        system_prompt = ""
        conversation = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        # Build request
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "messages": conversation,
            "temperature": temperature,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        # For JSON mode, we append instruction (Claude doesn't have native JSON mode)
        if json_mode and conversation:
            last_msg = conversation[-1]
            if last_msg["role"] == "user":
                last_msg["content"] += "\n\nRespond with valid JSON only, no other text."

        # Make the API call
        response = self.client.messages.create(**kwargs)

        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        return LLMResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            model=response.model,
            finish_reason=response.stop_reason or "",
            raw_response=response,
        )


def create_anthropic_config(
    api_key: str,
    model: str | None = None,
    role: str = "default",
) -> ProviderConfig:
    """
    Create an Anthropic provider config.

    Args:
        api_key: Anthropic API key
        model: Model to use (or None for role-based default)
        role: Agent role for default model selection

    Returns:
        ProviderConfig for Anthropic
    """
    return ProviderConfig(
        provider_type=ProviderType.ANTHROPIC,
        api_key=api_key,
        model=model or ANTHROPIC_MODELS.get(role, ANTHROPIC_MODELS["default"]),
        display_name=f"Claude ({model or ANTHROPIC_MODELS.get(role, 'default')})",
        description="Anthropic Claude - excellent for creative writing and complex reasoning",
    )
