"""Dependency injection for FastAPI routes."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from storyteller.config import Settings, get_settings
from storyteller.config_loader import ConfigLoader, YamlConfig, get_config_loader


def get_app_settings() -> Settings:
    """Get application settings (includes API keys from .env)."""
    return get_settings()


def get_yaml_config_loader() -> ConfigLoader:
    """Get the YAML config loader."""
    return get_config_loader()


def get_yaml_config(loader: Annotated[ConfigLoader, Depends(get_yaml_config_loader)]) -> YamlConfig:
    """Get current YAML configuration."""
    return loader.config


# Type aliases for dependency injection
AppSettings = Annotated[Settings, Depends(get_app_settings)]
YamlConfigLoader = Annotated[ConfigLoader, Depends(get_yaml_config_loader)]
CurrentYamlConfig = Annotated[YamlConfig, Depends(get_yaml_config)]
