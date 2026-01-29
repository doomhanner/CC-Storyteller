"""
YAML configuration loader for CC-Storyteller.

Handles loading and saving of config.yaml (non-secrets) while
keeping API keys in .env file.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from storyteller.config import ProviderTypeEnum


class ProviderYamlConfig(BaseModel):
    """Provider configuration as stored in YAML."""

    type: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"


class LocalYamlConfig(BaseModel):
    """Local model server configuration."""

    url: str = "http://localhost:11434"
    type: str = "ollama"


class PathsYamlConfig(BaseModel):
    """Path configuration."""

    data_dir: str = "~/.cc-storyteller"
    campaigns_dir: str = "campaigns"


class UIYamlConfig(BaseModel):
    """UI preferences."""

    theme: str = "chronicle"


class DebugYamlConfig(BaseModel):
    """Debug settings."""

    enabled: bool = False
    log_prompts: bool = False
    log_responses: bool = False


class ProvidersYamlConfig(BaseModel):
    """Provider configuration per role."""

    storyteller: ProviderYamlConfig = Field(default_factory=ProviderYamlConfig)
    archivist: ProviderYamlConfig = Field(default_factory=ProviderYamlConfig)


class YamlConfig(BaseModel):
    """Complete YAML configuration structure."""

    providers: ProvidersYamlConfig = Field(default_factory=ProvidersYamlConfig)
    local: LocalYamlConfig = Field(default_factory=LocalYamlConfig)
    paths: PathsYamlConfig = Field(default_factory=PathsYamlConfig)
    ui: UIYamlConfig = Field(default_factory=UIYamlConfig)
    debug: DebugYamlConfig = Field(default_factory=DebugYamlConfig)


DEFAULT_CONFIG = """# CC-Storyteller Configuration
# API keys should be stored in .env file, not here

# Provider configuration per role
providers:
  storyteller:
    type: anthropic       # anthropic, openai, ollama, local
    model: claude-sonnet-4-20250514
  archivist:
    type: anthropic
    model: claude-sonnet-4-20250514

# Local model settings (for ollama, llama.cpp, etc.)
local:
  url: http://localhost:11434
  type: ollama            # ollama, llamacpp, lmstudio, vllm

# Paths
paths:
  data_dir: ~/.cc-storyteller
  campaigns_dir: campaigns

# UI preferences
ui:
  theme: chronicle

# Debug settings (advanced)
debug:
  enabled: false
  log_prompts: false
  log_responses: false
"""


class ConfigLoader:
    """Loads and saves YAML configuration."""

    def __init__(self, config_path: Path | str | None = None):
        """
        Initialize the config loader.

        Args:
            config_path: Path to config.yaml. Defaults to ./config.yaml
        """
        if config_path is None:
            config_path = Path.cwd() / "config.yaml"
        self.config_path = Path(config_path)
        self._config: YamlConfig | None = None

    def load(self) -> YamlConfig:
        """
        Load configuration from YAML file.

        Creates default config if file doesn't exist.

        Returns:
            YamlConfig instance
        """
        if not self.config_path.exists():
            self._create_default()

        with open(self.config_path) as f:
            data = yaml.safe_load(f) or {}

        self._config = YamlConfig(**data)
        return self._config

    def save(self, config: YamlConfig | None = None) -> None:
        """
        Save configuration to YAML file.

        Args:
            config: Config to save. Uses current config if not provided.
        """
        if config is not None:
            self._config = config

        if self._config is None:
            self._config = YamlConfig()

        data = self._config.model_dump()
        yaml_str = self._to_yaml_with_comments(data)

        with open(self.config_path, "w") as f:
            f.write(yaml_str)

    def _create_default(self) -> None:
        """Create default config file."""
        with open(self.config_path, "w") as f:
            f.write(DEFAULT_CONFIG)

    def _to_yaml_with_comments(self, data: dict[str, Any]) -> str:
        """Convert config dict to YAML with comments."""
        lines = ["# CC-Storyteller Configuration", "# API keys should be stored in .env file, not here", ""]

        # Providers section
        lines.append("# Provider configuration per role")
        lines.append("providers:")
        lines.append("  storyteller:")
        lines.append(f"    type: {data['providers']['storyteller']['type']}       # anthropic, openai, ollama, local")
        lines.append(f"    model: {data['providers']['storyteller']['model']}")
        lines.append("  archivist:")
        lines.append(f"    type: {data['providers']['archivist']['type']}")
        lines.append(f"    model: {data['providers']['archivist']['model']}")
        lines.append("")

        # Local section
        lines.append("# Local model settings (for ollama, llama.cpp, etc.)")
        lines.append("local:")
        lines.append(f"  url: {data['local']['url']}")
        lines.append(f"  type: {data['local']['type']}            # ollama, llamacpp, lmstudio, vllm")
        lines.append("")

        # Paths section
        lines.append("# Paths")
        lines.append("paths:")
        lines.append(f"  data_dir: {data['paths']['data_dir']}")
        lines.append(f"  campaigns_dir: {data['paths']['campaigns_dir']}")
        lines.append("")

        # UI section
        lines.append("# UI preferences")
        lines.append("ui:")
        lines.append(f"  theme: {data['ui']['theme']}")
        lines.append("")

        # Debug section
        lines.append("# Debug settings (advanced)")
        lines.append("debug:")
        lines.append(f"  enabled: {str(data['debug']['enabled']).lower()}")
        lines.append(f"  log_prompts: {str(data['debug']['log_prompts']).lower()}")
        lines.append(f"  log_responses: {str(data['debug']['log_responses']).lower()}")
        lines.append("")

        return "\n".join(lines)

    @property
    def config(self) -> YamlConfig:
        """Get current config, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config  # type: ignore

    def update(self, updates: dict[str, Any]) -> YamlConfig:
        """
        Update configuration with partial data.

        Args:
            updates: Partial config dict to merge

        Returns:
            Updated YamlConfig
        """
        current = self.config.model_dump()
        self._deep_merge(current, updates)
        self._config = YamlConfig(**current)
        self.save()
        return self._config

    def _deep_merge(self, base: dict, updates: dict) -> None:
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


# Global config loader instance
_loader: ConfigLoader | None = None


def get_config_loader(config_path: Path | str | None = None) -> ConfigLoader:
    """Get the global config loader instance."""
    global _loader
    if _loader is None or (config_path and _loader.config_path != Path(config_path)):
        _loader = ConfigLoader(config_path)
    return _loader


def get_yaml_config() -> YamlConfig:
    """Get the current YAML configuration."""
    return get_config_loader().config
