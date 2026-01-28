"""
Provider Registry - Manages LLM provider instances and configuration.

Allows users to:
- Register custom providers
- Configure different providers for different roles (Storyteller, Archivist)
- Switch providers at runtime
- Discover available providers and models
"""

from typing import Callable

from storyteller.providers.base import (
    LLMProvider,
    ProviderConfig,
    ProviderType,
)


# Type alias for provider factory functions
ProviderFactory = Callable[[ProviderConfig], LLMProvider]

# Registry of provider factories
_provider_factories: dict[ProviderType, ProviderFactory] = {}

# Active provider instances by role
_active_providers: dict[str, LLMProvider] = {}

# Default role configurations
_role_configs: dict[str, ProviderConfig] = {}


def register_provider(provider_type: ProviderType, factory: ProviderFactory) -> None:
    """
    Register a provider factory.

    Args:
        provider_type: The type of provider
        factory: Function that creates a provider from config
    """
    _provider_factories[provider_type] = factory


def _ensure_default_providers_registered() -> None:
    """Register default providers if not already registered."""
    if ProviderType.ANTHROPIC not in _provider_factories:
        from storyteller.providers.anthropic_provider import AnthropicProvider

        register_provider(ProviderType.ANTHROPIC, AnthropicProvider)

    if ProviderType.OPENAI not in _provider_factories:
        from storyteller.providers.openai_compatible import OpenAICompatibleProvider

        register_provider(ProviderType.OPENAI, OpenAICompatibleProvider)

    if ProviderType.OPENAI_COMPATIBLE not in _provider_factories:
        from storyteller.providers.openai_compatible import OpenAICompatibleProvider

        register_provider(ProviderType.OPENAI_COMPATIBLE, OpenAICompatibleProvider)

    if ProviderType.OLLAMA not in _provider_factories:
        from storyteller.providers.ollama_provider import OllamaProvider

        register_provider(ProviderType.OLLAMA, OllamaProvider)


def get_provider(config: ProviderConfig) -> LLMProvider:
    """
    Get a provider instance for the given config.

    Args:
        config: Provider configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider type is not registered
    """
    _ensure_default_providers_registered()

    factory = _provider_factories.get(config.provider_type)
    if not factory:
        raise ValueError(f"Unknown provider type: {config.provider_type}")

    return factory(config)


def configure_role(role: str, config: ProviderConfig) -> None:
    """
    Configure a provider for a specific role.

    Args:
        role: The role (e.g., "storyteller", "archivist")
        config: Provider configuration for this role
    """
    _role_configs[role] = config
    # Clear cached provider for this role
    if role in _active_providers:
        del _active_providers[role]


def get_provider_for_role(role: str) -> LLMProvider:
    """
    Get the configured provider for a role.

    Args:
        role: The role (e.g., "storyteller", "archivist")

    Returns:
        LLMProvider instance configured for this role

    Raises:
        ValueError: If role is not configured
    """
    # Return cached provider if available
    if role in _active_providers:
        return _active_providers[role]

    # Get config for role
    config = _role_configs.get(role)
    if not config:
        raise ValueError(
            f"No provider configured for role '{role}'. "
            f"Call configure_role('{role}', config) first."
        )

    # Create and cache provider
    provider = get_provider(config)
    _active_providers[role] = provider
    return provider


def list_providers() -> list[ProviderType]:
    """List all registered provider types."""
    _ensure_default_providers_registered()
    return list(_provider_factories.keys())


def list_configured_roles() -> dict[str, str]:
    """
    List all configured roles and their providers.

    Returns:
        Dict mapping role name to provider display name
    """
    return {role: config.display_name for role, config in _role_configs.items()}


def clear_providers() -> None:
    """Clear all cached providers (useful for testing or reconfiguration)."""
    _active_providers.clear()


def setup_from_settings() -> None:
    """
    Configure providers from application settings.

    This reads the settings and sets up the appropriate providers
    for each role based on user configuration.
    """
    from storyteller.config import get_settings

    settings = get_settings()

    # Check what's configured
    has_anthropic = bool(settings.anthropic_api_key)
    has_openai = bool(getattr(settings, "openai_api_key", ""))
    has_local = bool(getattr(settings, "local_model_url", ""))

    # Default to Anthropic if available
    if has_anthropic:
        from storyteller.providers.anthropic_provider import create_anthropic_config

        # Storyteller - creative model
        storyteller_config = create_anthropic_config(
            api_key=settings.anthropic_api_key,
            model=settings.models.storyteller_model,
            role="storyteller",
        )
        configure_role("storyteller", storyteller_config)

        # Archivist - logical model
        archivist_config = create_anthropic_config(
            api_key=settings.anthropic_api_key,
            model=settings.models.archivist_model,
            role="archivist",
        )
        configure_role("archivist", archivist_config)

    # If local model URL is configured, allow override
    if has_local:
        from storyteller.providers.openai_compatible import create_local_config

        local_url = getattr(settings, "local_model_url", "")
        local_model = getattr(settings, "local_model_name", "")

        if getattr(settings, "use_local_for_storyteller", False):
            local_storyteller = create_local_config(
                api_base=local_url,
                model=local_model,
            )
            configure_role("storyteller", local_storyteller)

        if getattr(settings, "use_local_for_archivist", False):
            local_archivist = create_local_config(
                api_base=local_url,
                model=local_model,
            )
            configure_role("archivist", local_archivist)


# ==================== Convenience Functions ====================


def quick_setup_anthropic(api_key: str) -> None:
    """
    Quick setup using Anthropic Claude for both roles.

    Args:
        api_key: Anthropic API key
    """
    from storyteller.providers.anthropic_provider import create_anthropic_config

    configure_role(
        "storyteller",
        create_anthropic_config(api_key, role="storyteller"),
    )
    configure_role(
        "archivist",
        create_anthropic_config(api_key, role="archivist"),
    )


def quick_setup_openai(api_key: str, model: str = "gpt-4-turbo") -> None:
    """
    Quick setup using OpenAI for both roles.

    Args:
        api_key: OpenAI API key
        model: Model to use
    """
    from storyteller.providers.openai_compatible import create_openai_config

    config = create_openai_config(api_key, model)
    configure_role("storyteller", config)
    configure_role("archivist", config)


def quick_setup_ollama(model: str = "llama3.2:8b") -> None:
    """
    Quick setup using Ollama for both roles.

    Args:
        model: Ollama model to use (must be pulled first)
    """
    from storyteller.providers.ollama_provider import create_ollama_config

    config = create_ollama_config(model)
    configure_role("storyteller", config)
    configure_role("archivist", config)


def quick_setup_hybrid(
    anthropic_key: str = "",
    local_storyteller: str = "",
    local_url: str = "http://localhost:11434/v1",
) -> None:
    """
    Hybrid setup: Claude for Archivist (logic), local model for Storyteller (creativity).

    This is cost-effective: the Archivist does structured work that benefits from
    Claude's reliability, while the Storyteller can use a local model fine-tuned
    for creative writing.

    Args:
        anthropic_key: Anthropic API key for Archivist
        local_storyteller: Local model name for Storyteller
        local_url: URL for local model server
    """
    from storyteller.providers.anthropic_provider import create_anthropic_config
    from storyteller.providers.openai_compatible import create_local_config

    # Archivist: Claude for reliable structured output
    if anthropic_key:
        configure_role(
            "archivist",
            create_anthropic_config(anthropic_key, role="archivist"),
        )

    # Storyteller: Local model for creative writing
    if local_storyteller:
        configure_role(
            "storyteller",
            create_local_config(api_base=local_url, model=local_storyteller),
        )
