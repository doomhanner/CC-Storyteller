"""World state model - the live document tracking current truth."""

from datetime import datetime

from pydantic import BaseModel, Field

from storyteller.models.entities import InformationState, RelationshipAxes, TurnReference


class PCStatus(BaseModel):
    """Current status of the player character."""

    health: str = Field(default="healthy", description="Current health state")
    conditions: list[str] = Field(
        default_factory=list, description="Active conditions (injured, poisoned, etc.)"
    )
    emotional_state: str = Field(default="neutral", description="Current emotional state")
    resources: dict[str, str] = Field(
        default_factory=dict, description="Resources like money, supplies"
    )
    active_goals: list[str] = Field(default_factory=list, description="PC's current objectives")
    capabilities: list[str] = Field(default_factory=list, description="Notable skills/abilities")


class ActiveNPC(BaseModel):
    """
    An NPC currently relevant to the scene.
    Lighter weight than full Character entity for quick reference.
    """

    id: str
    name: str
    current_disposition: str = Field(
        default="neutral", description="How they currently feel toward the PC"
    )
    current_goal: str = Field(default="", description="What they want right now")
    emotional_state: str = Field(default="neutral")
    relationship_to_pc: RelationshipAxes = Field(default_factory=RelationshipAxes)
    information_state: InformationState = Field(default_factory=InformationState)
    turn_ref: TurnReference = Field(default_factory=lambda: TurnReference(created=0))
    notes: str = Field(default="", description="Quick notes about current state")


class PlotThread(BaseModel):
    """An active plot thread or storyline."""

    id: str
    name: str
    description: str
    status: str = Field(default="active", description="active, dormant, resolved")
    related_npcs: list[str] = Field(default_factory=list, description="NPC IDs involved")
    related_locations: list[str] = Field(default_factory=list, description="Location IDs involved")
    next_beats: list[str] = Field(
        default_factory=list, description="Projected next events in this thread"
    )
    turn_ref: TurnReference = Field(default_factory=lambda: TurnReference(created=0))
    priority: int = Field(default=5, ge=1, le=10, description="1=background, 10=urgent")


class LocationState(BaseModel):
    """Current state of a location."""

    id: str
    name: str
    description: str = ""
    time_of_day: str = Field(default="", description="Current time at this location")
    weather: str = Field(default="", description="Current weather/atmosphere")
    present_npcs: list[str] = Field(default_factory=list, description="NPC IDs currently here")
    recent_events: list[str] = Field(
        default_factory=list, description="Recent notable events at this location"
    )


class WorldState(BaseModel):
    """
    The World State document - current truth of the simulation.
    Overwritten each turn to reflect current state.
    """

    campaign_id: str
    current_turn: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

    # Time and place
    current_location: LocationState | None = None
    game_time: str = Field(default="", description="In-game date/time")
    time_since_start: str = Field(default="", description="Time elapsed since campaign start")

    # PC state
    pc_status: PCStatus = Field(default_factory=PCStatus)
    pc_inventory: list[str] = Field(default_factory=list, description="Item IDs")

    # Active scene
    active_npcs: list[ActiveNPC] = Field(
        default_factory=list, description="NPCs in current scene"
    )
    scene_description: str = Field(default="", description="Current scene summary")

    # Plot tracking
    plot_threads: list[PlotThread] = Field(default_factory=list)
    recent_events: list[str] = Field(
        default_factory=list, description="Recent significant events (last few turns)"
    )

    # Faction states (summary)
    faction_states: dict[str, str] = Field(
        default_factory=dict, description="Faction ID -> current state summary"
    )

    # Narrative queue
    projected_beats: list[str] = Field(
        default_factory=list, description="Next 3-5 projected narrative beats"
    )

    def update_turn(self, turn: int) -> None:
        """Update the world state for a new turn."""
        self.current_turn = turn
        self.last_updated = datetime.now()

    def add_event(self, event: str) -> None:
        """Add a recent event, keeping only the last 10."""
        self.recent_events.insert(0, event)
        self.recent_events = self.recent_events[:10]

    def get_active_npc(self, npc_id: str) -> ActiveNPC | None:
        """Get an active NPC by ID."""
        for npc in self.active_npcs:
            if npc.id == npc_id:
                return npc
        return None

    def get_thread(self, thread_id: str) -> PlotThread | None:
        """Get a plot thread by ID."""
        for thread in self.plot_threads:
            if thread.id == thread_id:
                return thread
        return None

    def to_summary(self) -> str:
        """Generate a concise summary for context."""
        parts = []

        if self.current_location:
            parts.append(f"Location: {self.current_location.name}")
        if self.game_time:
            parts.append(f"Time: {self.game_time}")

        if self.pc_status.conditions:
            parts.append(f"PC Conditions: {', '.join(self.pc_status.conditions)}")

        if self.active_npcs:
            npc_names = [npc.name for npc in self.active_npcs]
            parts.append(f"Present: {', '.join(npc_names)}")

        active_threads = [t for t in self.plot_threads if t.status == "active"]
        if active_threads:
            thread_names = [t.name for t in active_threads[:3]]
            parts.append(f"Active threads: {', '.join(thread_names)}")

        return " | ".join(parts)
