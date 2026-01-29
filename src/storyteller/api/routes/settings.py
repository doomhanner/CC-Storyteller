"""Settings API routes."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from storyteller.api.deps import AppSettings, YamlConfigLoader
from storyteller.api.schemas import (
    ProviderInfo,
    ProviderTestRequest,
    ProviderTestResponse,
    ProviderType,
    SettingsResponse,
    SettingsUpdateRequest,
)
from storyteller.providers.base import ChatMessage, ProviderConfig
from storyteller.providers.base import ProviderType as BaseProviderType

router = APIRouter(prefix="/settings", tags=["settings"])


# Known models for each provider
PROVIDER_MODELS = {
    ProviderType.ANTHROPIC: [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
    ProviderType.OPENAI: [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ],
    ProviderType.OLLAMA: [
        "llama3.2",
        "llama3.1",
        "mistral",
        "mixtral",
        "codellama",
        "deepseek-coder",
    ],
    ProviderType.LOCAL: [],
}


@router.get("", response_model=SettingsResponse)
async def get_settings(
    settings: AppSettings,
    config_loader: YamlConfigLoader,
) -> SettingsResponse:
    """Get current settings."""
    config = config_loader.config

    return SettingsResponse(
        providers=config.providers.model_dump(),
        local=config.local.model_dump(),
        paths=config.paths.model_dump(),
        ui=config.ui.model_dump(),
        debug=config.debug.model_dump(),
        available_providers=settings.get_available_providers(),
    )


@router.post("", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    settings: AppSettings,
    config_loader: YamlConfigLoader,
) -> SettingsResponse:
    """Update settings."""
    updates: dict[str, Any] = {}

    if request.providers is not None:
        updates["providers"] = request.providers.model_dump()
    if request.local is not None:
        updates["local"] = request.local.model_dump()
    if request.paths is not None:
        updates["paths"] = request.paths.model_dump()
    if request.ui is not None:
        updates["ui"] = request.ui.model_dump()
    if request.debug is not None:
        updates["debug"] = request.debug.model_dump()

    if updates:
        config_loader.update(updates)

    config = config_loader.config

    return SettingsResponse(
        providers=config.providers.model_dump(),
        local=config.local.model_dump(),
        paths=config.paths.model_dump(),
        ui=config.ui.model_dump(),
        debug=config.debug.model_dump(),
        available_providers=settings.get_available_providers(),
    )


@router.post("/test", response_model=ProviderTestResponse)
async def test_provider(
    request: ProviderTestRequest,
    settings: AppSettings,
) -> ProviderTestResponse:
    """Test a provider connection."""
    start_time = time.time()

    try:
        # Get the appropriate provider
        if request.provider_type == ProviderType.ANTHROPIC:
            if not settings.anthropic_api_key:
                return ProviderTestResponse(
                    success=False,
                    message="Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env file.",
                )
            from storyteller.providers.anthropic_provider import AnthropicProvider

            config = ProviderConfig(
                provider_type=BaseProviderType.ANTHROPIC,
                api_key=settings.anthropic_api_key,
                model=request.model,
            )
            provider = AnthropicProvider(config)

        elif request.provider_type == ProviderType.OPENAI:
            if not settings.openai_api_key:
                return ProviderTestResponse(
                    success=False,
                    message="OpenAI API key not configured. Set OPENAI_API_KEY in .env file.",
                )
            from storyteller.providers.openai_compatible import OpenAICompatibleProvider

            config = ProviderConfig(
                provider_type=BaseProviderType.OPENAI,
                api_key=settings.openai_api_key,
                model=request.model,
            )
            provider = OpenAICompatibleProvider(config)

        elif request.provider_type in (ProviderType.OLLAMA, ProviderType.LOCAL):
            from storyteller.providers.ollama_provider import OllamaProvider

            api_base = request.api_base or settings.local_provider_url
            config = ProviderConfig(
                provider_type=BaseProviderType.OLLAMA,
                api_base=api_base,
                model=request.model,
            )
            provider = OllamaProvider(config)

        else:
            return ProviderTestResponse(
                success=False,
                message=f"Unknown provider type: {request.provider_type}",
            )

        # Test the connection
        is_healthy, message = await provider.check_health()
        latency_ms = (time.time() - start_time) * 1000

        return ProviderTestResponse(
            success=is_healthy,
            message=message,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return ProviderTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            latency_ms=latency_ms,
        )


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(settings: AppSettings) -> list[ProviderInfo]:
    """List available providers and their configuration status."""
    available = settings.get_available_providers()

    providers = [
        ProviderInfo(
            type=ProviderType.ANTHROPIC,
            name="Anthropic",
            description="Claude models (Claude 3.5 Sonnet, Claude 3 Opus, etc.)",
            requires_api_key=True,
            is_configured="anthropic" in available,
            models=PROVIDER_MODELS[ProviderType.ANTHROPIC],
        ),
        ProviderInfo(
            type=ProviderType.OPENAI,
            name="OpenAI",
            description="GPT models (GPT-4, GPT-4 Turbo, etc.)",
            requires_api_key=True,
            is_configured="openai" in available,
            models=PROVIDER_MODELS[ProviderType.OPENAI],
        ),
        ProviderInfo(
            type=ProviderType.OLLAMA,
            name="Ollama",
            description="Local models via Ollama",
            requires_api_key=False,
            is_configured="ollama" in available,
            models=PROVIDER_MODELS[ProviderType.OLLAMA],
        ),
        ProviderInfo(
            type=ProviderType.LOCAL,
            name="Local (OpenAI-compatible)",
            description="Any OpenAI-compatible local server (llama.cpp, vLLM, etc.)",
            requires_api_key=False,
            is_configured="local" in available,
            models=[],
        ),
    ]

    return providers


@router.get("/providers/{provider_type}/models", response_model=list[str])
async def list_models(provider_type: ProviderType) -> list[str]:
    """List available models for a provider."""
    return PROVIDER_MODELS.get(provider_type, [])
