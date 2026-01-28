"""Campaign and settings models."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class CampaignStatus(str, Enum):
    """Status of a campaign."""

    DRAFT = "draft"  # Being created/edited
    READY = "ready"  # Ready to play but not started
    ACTIVE = "active"  # Currently in progress
    PAUSED = "paused"  # Temporarily paused
    COMPLETED = "completed"  # Finished
    ARCHIVED = "archived"  # Archived/hidden


class CreativitySettings(BaseModel):
    """Creativity slider settings for the campaign."""

    generation: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much to elaborate during entity/campaign generation (0=minimal, 1=expansive)",
    )
    input_integration: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much to expand player inputs (0=literal, 1=full ghostwrite)",
    )
    npc_autonomy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How proactive NPCs are in taking autonomous actions",
    )
    world_dynamism: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much the world changes between player actions",
    )


class NarrativeSettings(BaseModel):
    """Settings for narrative style and output."""

    max_paragraphs: int = Field(
        default=4, ge=1, le=10, description="Maximum paragraphs per turn"
    )
    perspective: str = Field(
        default="second_person", description="Narrative perspective (second_person, third_person)"
    )
    tense: str = Field(default="present", description="Narrative tense (present, past)")
    content_rating: str = Field(
        default="mature",
        description="Content rating (family, teen, mature, adult)",
    )
    include_internal_responses: bool = Field(
        default=True,
        description="Whether to describe PC's involuntary physical responses",
    )


class SimulationSettings(BaseModel):
    """Settings for world simulation behavior."""

    fog_of_war: bool = Field(
        default=True, description="Enforce information boundaries for NPCs and PC"
    )
    npc_autonomous_actions: bool = Field(
        default=True, description="NPCs take actions for their own reasons"
    )
    consequence_persistence: bool = Field(
        default=True, description="Consequences persist (injuries heal realistically, etc.)"
    )
    time_tracking: bool = Field(
        default=True, description="Track passage of time explicitly"
    )
    difficulty_adjudication: bool = Field(
        default=True, description="Adjudicate action difficulty and outcomes"
    )


class CampaignSettings(BaseModel):
    """All settings for a campaign."""

    creativity: CreativitySettings = Field(default_factory=CreativitySettings)
    narrative: NarrativeSettings = Field(default_factory=NarrativeSettings)
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)


class Campaign(BaseModel):
    """A campaign/story being played."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    description: str = ""
    setting_summary: str = Field(default="", description="Brief description of the setting/world")
    status: CampaignStatus = CampaignStatus.DRAFT

    # The player character
    pc_id: str | None = Field(default=None, description="ID of the player character")

    # Campaign settings
    settings: CampaignSettings = Field(default_factory=CampaignSettings)

    # Initial setup info (used during generation)
    initial_input: str = Field(
        default="",
        description="Original user input used to generate the campaign",
    )
    starting_situation: str = Field(
        default="",
        description="Description of the starting scenario",
    )

    # Metadata
    current_turn: int = Field(default=0, description="Current turn number")
    total_sessions: int = Field(default=0, description="Number of sessions played")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_played: datetime | None = Field(default=None)

    # Summary for context management
    summary: str = Field(
        default="",
        description="Running summary of major events for context compression",
    )
