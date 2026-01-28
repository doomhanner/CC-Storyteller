"""Session and turn models for gameplay."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class InputType(str, Enum):
    """Types of player input."""

    ACTION = "action"  # Plain text - actions/attempts
    DIALOGUE = "dialogue"  # "Quotes" - spoken words
    THOUGHT = "thought"  # *Asterisks* - internal thoughts (private)
    OOC = "ooc"  # ((Parentheses)) - out of character commands
    CONTINUE = "continue"  # // - advance world autonomously
    MIXED = "mixed"  # Contains multiple input types


class OutcomeType(str, Enum):
    """Types of action outcomes."""

    CLEAR_SUCCESS = "clear_success"
    SUCCESS_WITH_COST = "success_with_cost"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE_WITH_OPPORTUNITY = "failure_with_opportunity"
    FAILURE_WITH_CONSEQUENCE = "failure_with_consequence"
    SIMPLE_FAILURE = "simple_failure"
    NOT_APPLICABLE = "not_applicable"  # For non-action inputs


class ParsedInput(BaseModel):
    """Parsed player input with detected components."""

    raw_input: str
    primary_type: InputType
    action_text: str | None = None
    dialogue_text: str | None = None
    thought_text: str | None = None
    ooc_command: str | None = None


class FeasibilityCheck(BaseModel):
    """Assessment of whether an action is feasible."""

    capability: str = Field(default="", description="PC's relevant skills, condition, tools")
    circumstances: str = Field(
        default="", description="Environment, opposition, time pressure"
    )
    friction: str = Field(default="", description="Difficulty, risk, cost")
    outcome_type: OutcomeType = OutcomeType.NOT_APPLICABLE
    outcome_description: str = ""


class NPCAction(BaseModel):
    """An action taken by an NPC during a turn."""

    npc_id: str
    npc_name: str
    action: str
    motivation: str = Field(default="", description="Why the NPC took this action")
    is_autonomous: bool = Field(
        default=False, description="Whether this was autonomous vs reactive"
    )


class WorldSimulation(BaseModel):
    """World simulation results for a turn."""

    time_elapsed: str = Field(default="moments", description="How much time passed")
    environmental_changes: list[str] = Field(default_factory=list)
    offscreen_events: list[str] = Field(
        default_factory=list, description="Events happening elsewhere"
    )
    ambient_details: list[str] = Field(default_factory=list)
    npc_actions: list[NPCAction] = Field(default_factory=list)


class EngineProcessing(BaseModel):
    """
    The Archivist's reasoning for a turn.
    This is the 'Engine Processing' artifact from the prompt.
    """

    input_analysis: ParsedInput | None = None
    feasibility: FeasibilityCheck | None = None
    world_simulation: WorldSimulation = Field(default_factory=WorldSimulation)
    narrative_queue: list[str] = Field(
        default_factory=list, description="This turn's events + next 3-5 projected beats"
    )
    state_changes: list[str] = Field(
        default_factory=list, description="Updates to PC, NPCs, world, threads"
    )


class Turn(BaseModel):
    """A single turn in the game."""

    number: int
    timestamp: datetime = Field(default_factory=datetime.now)

    # Input
    player_input: str
    parsed_input: ParsedInput | None = None

    # Processing
    engine_processing: EngineProcessing | None = None

    # Output
    narrative: str = ""
    integrated_input: str | None = Field(
        default=None, description="Player input expanded by ghostwriting (if enabled)"
    )

    # Metadata
    tokens_used: int = Field(default=0, description="Total tokens used this turn")
    processing_time_ms: int = Field(default=0)


class TurnResult(BaseModel):
    """Result of processing a turn, returned to the player."""

    turn_number: int
    narrative: str
    world_state_summary: str = ""
    warnings: list[str] = Field(
        default_factory=list, description="Any warnings or notes for the player"
    )


class SessionStatus(str, Enum):
    """Status of a session."""

    SETUP = "setup"  # Campaign generation phase
    ACTIVE = "active"  # Currently playing
    PAUSED = "paused"  # Temporarily paused
    ENDED = "ended"  # Session ended


class Session(BaseModel):
    """A play session within a campaign."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    campaign_id: str
    session_number: int = 1
    status: SessionStatus = SessionStatus.SETUP

    # Turn tracking
    turns: list[Turn] = Field(default_factory=list)
    current_turn: int = Field(default=0)

    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None
    total_duration_minutes: int = 0

    # Statistics
    total_tokens_used: int = 0
    storyteller_calls: int = 0
    archivist_calls: int = 0

    def add_turn(self, turn: Turn) -> None:
        """Add a completed turn to the session."""
        self.turns.append(turn)
        self.current_turn = turn.number
        self.total_tokens_used += turn.tokens_used

    def get_recent_turns(self, count: int = 5) -> list[Turn]:
        """Get the most recent turns."""
        return self.turns[-count:] if self.turns else []


class OOCCommand(str, Enum):
    """Recognized OOC commands."""

    STATUS = "status"
    INVENTORY = "inventory"
    RECAP = "recap"
    NPCS = "npcs"
    THREADS = "threads"
    TIME = "time"
    RETCON = "retcon"
    ADJUST = "adjust"
    HELP = "help"
    SAVE = "save"
    QUIT = "quit"


def parse_ooc_command(text: str) -> tuple[OOCCommand | None, str]:
    """Parse an OOC command and its argument."""
    text = text.strip().lower()

    # Check for commands with arguments
    for cmd in [OOCCommand.RETCON, OOCCommand.ADJUST]:
        if text.startswith(f"{cmd.value}:"):
            return cmd, text[len(cmd.value) + 1 :].strip()

    # Check for simple commands
    for cmd in OOCCommand:
        if text == cmd.value:
            return cmd, ""

    return None, text
