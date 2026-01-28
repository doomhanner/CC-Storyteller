"""Relationship models for entity connections."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from storyteller.models.entities import RelationshipAxes, TurnReference


class RelationshipType(str, Enum):
    """Types of relationships between entities."""

    # Character relationships
    KNOWS = "knows"  # Characters know each other
    FAMILY = "family"  # Family relationship
    FRIEND = "friend"  # Friendship
    RIVAL = "rival"  # Rivalry
    ENEMY = "enemy"  # Enmity
    ROMANTIC = "romantic"  # Romantic relationship
    EMPLOYER = "employer"  # Employment (source employs target)
    EMPLOYEE = "employee"  # Employment (source works for target)
    MENTOR = "mentor"  # Mentorship (source mentors target)
    STUDENT = "student"  # Student (source learns from target)
    ALLY = "ally"  # Alliance

    # Possession/location relationships
    OWNS = "owns"  # Character owns item
    LOCATED_AT = "located_at"  # Entity is at location
    CONTAINS = "contains"  # Location contains another location

    # Faction relationships
    MEMBER_OF = "member_of"  # Character is member of faction
    LEADS = "leads"  # Character leads faction
    ALLIED_WITH = "allied_with"  # Factions are allied
    HOSTILE_TO = "hostile_to"  # Factions are hostile
    CONTROLS = "controls"  # Faction controls location

    # Knowledge relationships
    KNOWS_ABOUT = "knows_about"  # Character knows about lore/entity
    CREATED = "created"  # Character created item/faction
    DISCOVERED = "discovered"  # Character discovered location/lore

    # Generic
    RELATED_TO = "related_to"  # Generic relationship


class Relationship(BaseModel):
    """A relationship between two entities."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    source_id: str = Field(description="ID of the source entity")
    target_id: str = Field(description="ID of the target entity")
    relationship_type: RelationshipType

    # Optional detailed attributes for interpersonal relationships
    axes: RelationshipAxes | None = Field(
        default=None,
        description="Detailed relationship axes (trust, respect, affection, utility)",
    )

    # Metadata
    label: str = Field(default="", description="Custom label for the relationship")
    notes: str = Field(default="", description="Additional context or history")
    is_mutual: bool = Field(
        default=False,
        description="Whether the relationship is reciprocal (creates implicit reverse)",
    )
    is_secret: bool = Field(
        default=False,
        description="Whether this relationship is hidden from most characters",
    )

    # Turn tracking
    turn_ref: TurnReference = Field(default_factory=lambda: TurnReference(created=0))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def update_turn(self, turn: int) -> None:
        """Mark relationship as modified on given turn."""
        self.turn_ref.modified = turn
        self.turn_ref.unchanged_since = None
        self.updated_at = datetime.now()

    def describe(self) -> str:
        """Generate a human-readable description of the relationship."""
        type_descriptions = {
            RelationshipType.KNOWS: "knows",
            RelationshipType.FAMILY: "is family of",
            RelationshipType.FRIEND: "is friends with",
            RelationshipType.RIVAL: "is a rival of",
            RelationshipType.ENEMY: "is an enemy of",
            RelationshipType.ROMANTIC: "has a romantic relationship with",
            RelationshipType.EMPLOYER: "employs",
            RelationshipType.EMPLOYEE: "works for",
            RelationshipType.MENTOR: "mentors",
            RelationshipType.STUDENT: "studies under",
            RelationshipType.ALLY: "is allied with",
            RelationshipType.OWNS: "owns",
            RelationshipType.LOCATED_AT: "is located at",
            RelationshipType.CONTAINS: "contains",
            RelationshipType.MEMBER_OF: "is a member of",
            RelationshipType.LEADS: "leads",
            RelationshipType.ALLIED_WITH: "is allied with",
            RelationshipType.HOSTILE_TO: "is hostile to",
            RelationshipType.CONTROLS: "controls",
            RelationshipType.KNOWS_ABOUT: "knows about",
            RelationshipType.CREATED: "created",
            RelationshipType.DISCOVERED: "discovered",
            RelationshipType.RELATED_TO: "is related to",
        }

        base = type_descriptions.get(self.relationship_type, "is connected to")
        if self.label:
            return f"{base} ({self.label})"
        return base
