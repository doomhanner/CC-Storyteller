"""Entity models for the Entity Bible."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of entities that can exist in the bible."""

    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    FACTION = "faction"
    LORE = "lore"


class TurnReference(BaseModel):
    """Track when an entity or field was created/modified."""

    created: int = Field(description="Turn number when created")
    modified: int | None = Field(default=None, description="Turn number when last modified")
    unchanged_since: int | None = Field(
        default=None, description="Turn number since which no changes occurred"
    )

    def to_tag(self) -> str:
        """Convert to display tag format like {T: 12} or {T: 3, 8*}."""
        if self.modified:
            return f"{{T: {self.created}, {self.modified}*}}"
        elif self.unchanged_since:
            return f"{{T: {self.unchanged_since}+}}"
        return f"{{T: {self.created}}}"


class Entity(BaseModel):
    """Base class for all entities in the bible."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    turn_ref: TurnReference = Field(default_factory=lambda: TurnReference(created=0))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def update_turn(self, turn: int) -> None:
        """Mark entity as modified on given turn."""
        self.turn_ref.modified = turn
        self.turn_ref.unchanged_since = None
        self.updated_at = datetime.now()


# Character-specific models


class PhysicalAttributes(BaseModel):
    """Physical description and capabilities of a character."""

    appearance: str = Field(default="", description="Face, coloring, hair, distinguishing features")
    build: str = Field(default="", description="Height, body type, physical presence")
    capability: dict[str, str] = Field(
        default_factory=lambda: {
            "strength": "average",
            "agility": "average",
            "health": "healthy",
        },
        description="Physical capabilities",
    )
    limitations: list[str] = Field(default_factory=list, description="Physical limitations")


class CharacterVoice(BaseModel):
    """How a character speaks and expresses themselves."""

    patterns: list[str] = Field(default_factory=list, description="Speech patterns")
    habits: list[str] = Field(default_factory=list, description="Verbal/physical habits")
    expressions: list[str] = Field(default_factory=list, description="Characteristic phrases")


class Psychology(BaseModel):
    """Psychological profile of a character."""

    wants_immediate: str = Field(default="", description="Immediate goals")
    wants_long_term: str = Field(default="", description="Long-term goals")
    fears: list[str] = Field(default_factory=list, description="What they avoid or dread")
    wounds: list[str] = Field(default_factory=list, description="Past experiences shaping reactions")
    blindspots: list[str] = Field(
        default_factory=list, description="Self-deceptions, biases, assumptions"
    )
    voice: CharacterVoice = Field(default_factory=CharacterVoice)


class InformationState(BaseModel):
    """What a character knows, believes, and suspects."""

    knows: list[str] = Field(default_factory=list, description="Verified facts they possess")
    believes: list[str] = Field(
        default_factory=list, description="What they think is true (may be false)"
    )
    suspects: list[str] = Field(
        default_factory=list, description="Unconfirmed possibilities they're watching"
    )


class RelationshipAxes(BaseModel):
    """
    The four axes of interpersonal relationships.
    Values range from -1.0 (negative) to 1.0 (positive), with 0 being neutral.
    """

    trust: float = Field(default=0.0, ge=-1.0, le=1.0, description="Do they believe this person?")
    respect: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Do they take this person seriously?"
    )
    affection: float = Field(default=0.0, ge=-1.0, le=1.0, description="Do they like this person?")
    utility: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Is this person useful to their goals?"
    )


class Character(Entity):
    """A character entity (NPC or PC)."""

    type: EntityType = EntityType.CHARACTER
    is_pc: bool = Field(default=False, description="Whether this is the player character")
    physical: PhysicalAttributes = Field(default_factory=PhysicalAttributes)
    psychology: Psychology = Field(default_factory=Psychology)
    information_state: InformationState = Field(default_factory=InformationState)
    inventory: list[str] = Field(
        default_factory=list, description="Item IDs in character's possession"
    )
    current_location: str | None = Field(default=None, description="Location ID")
    faction_memberships: list[str] = Field(default_factory=list, description="Faction IDs")


# Location-specific models


class Location(Entity):
    """A location entity."""

    type: EntityType = EntityType.LOCATION
    parent_location: str | None = Field(
        default=None, description="ID of containing location (e.g., room in building)"
    )
    connected_locations: list[str] = Field(
        default_factory=list, description="IDs of adjacent/accessible locations"
    )
    current_occupants: list[str] = Field(
        default_factory=list, description="Character IDs currently present"
    )
    notable_features: list[str] = Field(default_factory=list)
    atmosphere: str = Field(default="", description="Mood, ambiance, sensory details")
    controlling_faction: str | None = Field(default=None, description="Faction ID")


# Item-specific models


class Item(Entity):
    """An item entity."""

    type: EntityType = EntityType.ITEM
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Item-specific properties (magical, value, etc.)"
    )
    owner_id: str | None = Field(default=None, description="Character ID of owner")
    location_id: str | None = Field(
        default=None, description="Location ID if not owned by character"
    )
    history: list[str] = Field(default_factory=list, description="Notable history of the item")
    is_unique: bool = Field(default=False, description="Whether this is a unique/significant item")


# Faction-specific models


class Faction(Entity):
    """A faction/organization entity."""

    type: EntityType = EntityType.FACTION
    goals: list[str] = Field(default_factory=list, description="Faction objectives")
    resources: list[str] = Field(default_factory=list, description="What the faction controls")
    territory: list[str] = Field(default_factory=list, description="Location IDs controlled")
    leadership: list[str] = Field(default_factory=list, description="Character IDs of leaders")
    members: list[str] = Field(
        default_factory=list, description="Character IDs of known members"
    )
    public_reputation: str = Field(default="", description="How the faction is publicly perceived")
    secret_nature: str = Field(default="", description="Hidden aspects unknown to most")


# Lore-specific models


class LoreCategory(str, Enum):
    """Categories of lore entries."""

    HISTORY = "history"
    MAGIC = "magic"
    RELIGION = "religion"
    CULTURE = "culture"
    TECHNOLOGY = "technology"
    GEOGRAPHY = "geography"
    LANGUAGE = "language"
    LEGEND = "legend"
    OTHER = "other"


class Lore(Entity):
    """A lore/codex entry."""

    type: EntityType = EntityType.LORE
    category: LoreCategory = LoreCategory.OTHER
    content: str = Field(default="", description="The lore content itself")
    related_entities: list[str] = Field(
        default_factory=list, description="IDs of related entities"
    )
    is_common_knowledge: bool = Field(
        default=True, description="Whether this is widely known vs secret"
    )
    known_by: list[str] = Field(
        default_factory=list, description="Character IDs who know this (if not common)"
    )
