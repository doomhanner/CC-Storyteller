"""Pydantic schemas for API requests and responses."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ==================== Settings Schemas ====================


class ProviderType(str, Enum):
    """Available provider types."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LOCAL = "local"


class ProviderConfigSchema(BaseModel):
    """Provider configuration for a role."""

    type: ProviderType = ProviderType.ANTHROPIC
    model: str = "claude-sonnet-4-20250514"


class LocalConfigSchema(BaseModel):
    """Local model server configuration."""

    url: str = "http://localhost:11434"
    type: str = "ollama"


class PathsConfigSchema(BaseModel):
    """Paths configuration."""

    data_dir: str = "~/.cc-storyteller"
    campaigns_dir: str = "campaigns"


class UIConfigSchema(BaseModel):
    """UI configuration."""

    theme: str = "chronicle"


class DebugConfigSchema(BaseModel):
    """Debug configuration."""

    enabled: bool = False
    log_prompts: bool = False
    log_responses: bool = False


class ProvidersConfigSchema(BaseModel):
    """Providers configuration."""

    storyteller: ProviderConfigSchema = Field(default_factory=ProviderConfigSchema)
    archivist: ProviderConfigSchema = Field(default_factory=ProviderConfigSchema)


class SettingsResponse(BaseModel):
    """Complete settings response."""

    providers: ProvidersConfigSchema
    local: LocalConfigSchema
    paths: PathsConfigSchema
    ui: UIConfigSchema
    debug: DebugConfigSchema
    available_providers: list[str] = []


class SettingsUpdateRequest(BaseModel):
    """Partial settings update request."""

    providers: ProvidersConfigSchema | None = None
    local: LocalConfigSchema | None = None
    paths: PathsConfigSchema | None = None
    ui: UIConfigSchema | None = None
    debug: DebugConfigSchema | None = None


class ProviderTestRequest(BaseModel):
    """Request to test a provider connection."""

    provider_type: ProviderType
    model: str
    api_base: str | None = None


class ProviderTestResponse(BaseModel):
    """Response from provider test."""

    success: bool
    message: str
    latency_ms: float | None = None


class ProviderInfo(BaseModel):
    """Information about an available provider."""

    type: ProviderType
    name: str
    description: str
    requires_api_key: bool
    is_configured: bool
    models: list[str] = []


# ==================== Campaign Schemas ====================


class CampaignSummary(BaseModel):
    """Summary of a campaign for listing."""

    id: str
    name: str
    status: str
    current_turn: int
    total_sessions: int
    setting_summary: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class CampaignListResponse(BaseModel):
    """Response for campaign list."""

    campaigns: list[CampaignSummary]
    total: int


class CampaignCreateRequest(BaseModel):
    """Request to create a new campaign."""

    name: str
    setting_description: str = ""
    pc_description: str = ""
    starting_situation: str = ""
    additional_notes: str = ""
    creativity: float = Field(default=0.5, ge=0.0, le=1.0)


class CampaignCreateResponse(BaseModel):
    """Response from campaign creation."""

    campaign: CampaignSummary
    expansion_summary: str
    bible_stats: dict[str, int]
    tokens_used: int
    warnings: list[str] = []


# ==================== Entity/Codex Schemas ====================


class EntityType(str, Enum):
    """Entity types in the bible."""

    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    FACTION = "faction"
    LORE = "lore"


class EntitySummary(BaseModel):
    """Summary of an entity."""

    id: str
    name: str
    type: EntityType
    description: str = ""
    tags: list[str] = []


class EntityDetail(BaseModel):
    """Full entity details."""

    id: str
    name: str
    type: EntityType
    description: str = ""
    attributes: dict[str, Any] = {}
    tags: list[str] = []
    relationships: list["RelationshipSummary"] = []
    turn_created: int = 0
    turn_modified: int = 0


class RelationshipSummary(BaseModel):
    """Summary of a relationship."""

    id: str
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str
    description: str = ""


class CodexResponse(BaseModel):
    """Response with entity list."""

    entities: list[EntitySummary]
    total: int


class RelationshipGraphResponse(BaseModel):
    """Response with relationship graph data."""

    nodes: list[EntitySummary]
    edges: list[RelationshipSummary]


# ==================== Session Schemas ====================


class SessionInfo(BaseModel):
    """Session information."""

    id: str
    campaign_id: str
    started_at: str
    current_turn: int
    is_active: bool


class SessionStartRequest(BaseModel):
    """Request to start a new session."""

    campaign_id: str


class SessionStartResponse(BaseModel):
    """Response from starting a session."""

    session: SessionInfo
    opening_narrative: str


class TurnRequest(BaseModel):
    """Request to process a turn."""

    player_input: str


class TurnResponse(BaseModel):
    """Response from processing a turn."""

    narrative: str
    turn_number: int
    bible_updates: list[str] = []
    warnings: list[str] = []


# ==================== WebSocket Messages ====================


class WSMessageType(str, Enum):
    """WebSocket message types."""

    CHUNK = "chunk"
    DONE = "done"
    ERROR = "error"
    TURN_START = "turn_start"
    BIBLE_UPDATE = "bible_update"


class WSMessage(BaseModel):
    """WebSocket message."""

    type: WSMessageType
    data: dict[str, Any] = {}


# Forward reference resolution
EntityDetail.model_rebuild()
