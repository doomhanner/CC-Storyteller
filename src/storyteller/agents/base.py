"""Base agent class for LLM interactions."""

from abc import ABC, abstractmethod
from typing import Any

import anthropic

from storyteller.config import get_settings


class BaseAgent(ABC):
    """
    Base class for AI agents in the system.

    Provides common functionality for interacting with Claude API,
    prompt management, and response handling.
    """

    def __init__(self, model: str | None = None):
        """
        Initialize the agent.

        Args:
            model: The Claude model to use. If None, uses config default.
        """
        self.settings = get_settings()
        self._model = model
        self._client: anthropic.Anthropic | None = None
        self._total_tokens_used = 0

    @property
    def client(self) -> anthropic.Anthropic:
        """Get or create the Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    @property
    @abstractmethod
    def model(self) -> str:
        """The model this agent uses."""
        pass

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
        self, user_message: str, context: list[dict[str, str]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Build the messages array for an API call.

        Args:
            user_message: The current user message
            context: Optional list of previous messages for context

        Returns:
            List of message dicts for the API
        """
        messages = []

        if context:
            messages.extend(context)

        messages.append({"role": "user", "content": user_message})

        return messages

    def _call_api(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stop_sequences: list[str] | None = None,
    ) -> tuple[str, int]:
        """
        Make an API call to Claude.

        Args:
            messages: The messages to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences

        Returns:
            Tuple of (response text, tokens used)
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": self.system_prompt,
            "messages": messages,
            "temperature": temperature,
        }

        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        if self.settings.log_prompts:
            print(f"\n[PROMPT] System: {self.system_prompt[:200]}...")
            print(f"[PROMPT] Messages: {messages}")

        response = self.client.messages.create(**kwargs)

        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        # Track token usage
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        self._total_tokens_used += tokens_used

        if self.settings.log_responses:
            print(f"\n[RESPONSE] {text[:500]}...")
            print(f"[TOKENS] {tokens_used}")

        return text, tokens_used

    def _call_api_json(
        self,
        messages: list[dict[str, Any]],
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
        import json

        # Append instruction to return JSON
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] += "\n\nRespond with valid JSON only."

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
