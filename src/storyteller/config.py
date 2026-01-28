"""Configuration management for CC-Storyteller."""

import os
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    """Configuration for LLM models."""

    storyteller_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model for narrative generation",
    )
    archivist_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model for data extraction and logic",
    )
    max_tokens_narrative: int = Field(
        default=2048, description="Max tokens for narrative responses"
    )
    max_tokens_processing: int = Field(
        default=4096, description="Max tokens for processing/extraction"
    )


class StorageConfig(BaseModel):
    """Configuration for data storage."""

    campaigns_dir: Path = Field(
        default=Path("campaigns"), description="Directory for campaign data"
    )
    database_path: Path = Field(
        default=Path("storyteller.db"), description="SQLite database path"
    )


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # API keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Paths
    data_dir: Path = Field(
        default=Path.home() / ".cc-storyteller", description="Data directory"
    )

    # Model configuration
    models: ModelConfig = Field(default_factory=ModelConfig)

    # Storage configuration
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # Debug settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_prompts: bool = Field(default=False, description="Log prompts to console")
    log_responses: bool = Field(default=False, description="Log responses to console")

    model_config = {
        "env_prefix": "STORYTELLER_",
        "env_file": ".env",
        "env_nested_delimiter": "__",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Also check for ANTHROPIC_API_KEY directly
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def campaigns_path(self) -> Path:
        """Get the full path to campaigns directory."""
        return self.data_dir / self.storage.campaigns_dir

    @property
    def database_path(self) -> Path:
        """Get the full path to the database."""
        return self.data_dir / self.storage.database_path

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.campaigns_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings


def configure(settings: Settings) -> None:
    """Set the global settings instance."""
    global _settings
    _settings = settings
    _settings.ensure_directories()
