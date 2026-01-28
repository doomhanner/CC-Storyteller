"""Base agent class for LLM interactions."""

import json
from abc import ABC, abstractmethod
from typing import Any

from storyteller.config import get_settings
from storyteller.providers.base import ChatMessage, LLMProvider


class BaseAgent(ABC):
    """
    Base class for AI agents in the system.

    Provides common functionality for interacting with LLM providers,
    prompt management, and response handling.

    Agents can use any configured LLM provider (Anthropic, OpenAI, Ollama, etc.)
    through the provider abstraction layer.
    """

    def __init__(self, provider: LLMProvider | None = None, role: str = "default"):
        """
        Initialize the agent.

        Args:
            provider: LLM provider to use. If None, uses configured provider for role.
            role: Agent role for provider lookup (e.g., "storyteller", "archivist")
        """
        self.settings = get_settings()
        self._provider = provider
        self._role = role
        self._total_tokens_used = 0

    @property
    def provider(self) -> LLMProvider:
        """Get the LLM provider for this agent."""
        if self._provider is not None:
            return self._provider

        # Get provider from registry based on role
        from storyteller.providers.registry import get_provider_for_role

        try:
            return get_provider_for_role(self._role)
        except ValueError:
            # Fall back to creating a default Anthropic provider
            from storyteller.providers.anthropic_provider import (
                AnthropicProvider,
                create_anthropic_config,
            )

            config = create_anthropic_config(
                api_key=self.settings.anthropic_api_key,
                role=self._role,
            )
            self._provider = AnthropicProvider(config)
            return self._provider

    @property
    def model(self) -> str:
        """The model this agent uses."""
        return self.provider.model

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt for this agent."""
        pass

    @property
    def total_tokens_used(self) -> int:
        """Total tokens used by this agent."""
        return self._total_tokens_used

    def _build_messages(
        self,
        user_message: str,
        context: list[dict[str, str]] | None = None,
        system: str | None = None,
    ) -> list[ChatMessage]:
        """
        Build the messages array for an API call.

        Args:
            user_message: The current user message
            context: Optional list of previous messages for context
            system: Optional system prompt override

        Returns:
            List of ChatMessage objects for the provider
        """
        messages = []

        # Add system prompt
        sys_prompt = system or self.system_prompt
        if sys_prompt:
            messages.append(ChatMessage(role="system", content=sys_prompt))

        # Add context messages
        if context:
            for msg in context:
                messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

        # Add current user message
        messages.append(ChatMessage(role="user", content=user_message))

        return messages

    def _call_api(
        self,
        messages: list[ChatMessage] | list[dict[str, Any]],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
    ) -> tuple[str, int]:
        """
        Make an API call to the LLM provider.

        Args:
            messages: The messages to send (ChatMessage list or dict list for backward compat)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences

        Returns:
            Tuple of (response text, tokens used)
        """
        # Convert dict messages to ChatMessage if needed
        if messages and isinstance(messages[0], dict):
            messages = [
                ChatMessage(role=m["role"], content=m["content"]) for m in messages
            ]

        if self.settings.log_prompts:
            print(f"\n[PROMPT] Provider: {self.provider.name}")
            print(f"[PROMPT] Messages: {messages}")

        response = self.provider.generate_sync(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences,
        )

        # Track token usage
        self._total_tokens_used += response.tokens_used

        if self.settings.log_responses:
            print(f"\n[RESPONSE] {response.text[:500]}...")
            print(f"[TOKENS] {response.tokens_used}")

        return response.text, response.tokens_used

    async def _call_api_async(
        self,
        messages: list[ChatMessage] | list[dict[str, Any]],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
    ) -> tuple[str, int]:
        """
        Make an async API call to the LLM provider.

        Args:
            messages: The messages to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences

        Returns:
            Tuple of (response text, tokens used)
        """
        # Convert dict messages to ChatMessage if needed
        if messages and isinstance(messages[0], dict):
            messages = [
                ChatMessage(role=m["role"], content=m["content"]) for m in messages
            ]

        if self.settings.log_prompts:
            print(f"\n[PROMPT] Provider: {self.provider.name}")
            print(f"[PROMPT] Messages: {messages}")

        response = await self.provider.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences,
        )

        # Track token usage
        self._total_tokens_used += response.tokens_used

        if self.settings.log_responses:
            print(f"\n[RESPONSE] {response.text[:500]}...")
            print(f"[TOKENS] {response.tokens_used}")

        return response.text, response.tokens_used

    def _call_api_json(
        self,
        messages: list[ChatMessage] | list[dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> tuple[dict[str, Any], int]:
        """
        Make an API call expecting JSON response.

        Wraps the response in JSON parsing with error handling.

        Args:
            messages: The messages to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Tuple of (parsed JSON dict, tokens used)
        """
        # Convert to ChatMessage if needed
        if messages and isinstance(messages[0], dict):
            messages = [
                ChatMessage(role=m["role"], content=m["content"]) for m in messages
            ]

        # Append instruction to return JSON
        if messages and messages[-1].role == "user":
            messages[-1] = ChatMessage(
                role="user",
                content=messages[-1].content + "\n\nRespond with valid JSON only.",
            )

        text, tokens = self._call_api(
            messages, max_tokens=max_tokens, temperature=temperature
        )

        # Try to parse JSON
        try:
            # Handle potential markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip()), tokens
        except json.JSONDecodeError as e:
            # Return error info if parsing fails
            return {"error": f"JSON parse error: {e}", "raw_text": text}, tokens

    async def _call_api_json_async(
        self,
        messages: list[ChatMessage] | list[dict[str, Any]],
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> tuple[dict[str, Any], int]:
        """
        Make an async API call expecting JSON response.

        Args:
            messages: The messages to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Tuple of (parsed JSON dict, tokens used)
        """
        # Convert to ChatMessage if needed
        if messages and isinstance(messages[0], dict):
            messages = [
                ChatMessage(role=m["role"], content=m["content"]) for m in messages
            ]

        # Append instruction to return JSON
        if messages and messages[-1].role == "user":
            messages[-1] = ChatMessage(
                role="user",
                content=messages[-1].content + "\n\nRespond with valid JSON only.",
            )

        text, tokens = await self._call_api_async(
            messages, max_tokens=max_tokens, temperature=temperature
        )

        # Try to parse JSON
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip()), tokens
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse error: {e}", "raw_text": text}, tokens

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Process input and return output.

        This is the main entry point for agent functionality.
        Subclasses must implement this method.

        Args:
            input_data: The input to process (type depends on agent)

        Returns:
            The processed output (type depends on agent)
        """
        pass
