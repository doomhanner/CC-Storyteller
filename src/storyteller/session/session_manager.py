"""
Session Manager - Orchestrates gameplay sessions.

Handles:
- Turn-by-turn gameplay loop
- Coordination between Storyteller and Archivist agents
- State persistence and recovery
- OOC command processing
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from storyteller.agents.archivist import ArchivistAgent, SimulationRequest
from storyteller.agents.storyteller import NarrativeRequest, StorytellerAgent
from storyteller.bible.entity_bible import EntityBible
from storyteller.config import get_settings
from storyteller.models.campaign import Campaign, CampaignStatus
from storyteller.models.session import (
    InputType,
    OOCCommand,
    Session,
    SessionStatus,
    Turn,
    TurnResult,
    parse_ooc_command,
)
from storyteller.models.world_state import WorldState


class SessionManager:
    """
    Manages gameplay sessions and orchestrates the turn loop.
    """

    def __init__(
        self,
        campaign: Campaign,
        bible: EntityBible,
        world_state: WorldState,
        session: Session | None = None,
    ):
        self.campaign = campaign
        self.bible = bible
        self.world_state = world_state

        # Create or use existing session
        if session:
            self.session = session
        else:
            self.session = Session(
                campaign_id=campaign.id,
                session_number=campaign.total_sessions + 1,
                status=SessionStatus.SETUP
                if campaign.status == CampaignStatus.DRAFT
                else SessionStatus.ACTIVE,
            )

        # Initialize agents
        self.storyteller = StorytellerAgent()
        self.archivist = ArchivistAgent()

        # Settings
        self.settings = get_settings()

        # Callbacks for UI integration
        self._on_turn_complete: Callable[[TurnResult], None] | None = None
        self._on_state_change: Callable[[WorldState], None] | None = None

    @property
    def current_turn(self) -> int:
        """Get the current turn number."""
        return self.campaign.current_turn

    @property
    def is_active(self) -> bool:
        """Check if the session is active."""
        return self.session.status == SessionStatus.ACTIVE

    def on_turn_complete(self, callback: Callable[[TurnResult], None]) -> None:
        """Set callback for when a turn completes."""
        self._on_turn_complete = callback

    def on_state_change(self, callback: Callable[[WorldState], None]) -> None:
        """Set callback for when world state changes."""
        self._on_state_change = callback

    # ==================== Session Lifecycle ====================

    def start_session(self) -> str:
        """
        Start the gameplay session.

        Returns:
            Opening narrative or setup instructions
        """
        if self.campaign.status == CampaignStatus.DRAFT:
            return (
                "Campaign is still in draft mode. "
                "Use 'confirm' to finalize and begin play, "
                "or 'generate' to create content."
            )

        # Mark session as active
        self.session.status = SessionStatus.ACTIVE
        self.campaign.status = CampaignStatus.ACTIVE
        self.campaign.last_played = datetime.now()

        # If this is turn 0, generate opening narrative
        if self.campaign.current_turn == 0:
            return self._generate_opening()

        # Otherwise, return recap
        return self._generate_recap()

    def end_session(self) -> None:
        """End the current session."""
        self.session.status = SessionStatus.ENDED
        self.session.ended_at = datetime.now()

        # Calculate duration
        duration = self.session.ended_at - self.session.started_at
        self.session.total_duration_minutes = int(duration.total_seconds() / 60)

        # Update campaign
        self.campaign.total_sessions += 1
        self.campaign.updated_at = datetime.now()

        # Save everything
        self.save()

    def pause_session(self) -> None:
        """Pause the session."""
        self.session.status = SessionStatus.PAUSED
        self.save()

    def resume_session(self) -> str:
        """Resume a paused session."""
        self.session.status = SessionStatus.ACTIVE
        return self._generate_recap()

    # ==================== Turn Processing ====================

    async def process_turn(self, player_input: str) -> TurnResult:
        """
        Process a player turn through the full pipeline.

        1. Parse input
        2. Handle OOC commands if present
        3. Run simulation (Archivist)
        4. Generate narrative (Storyteller)
        5. Update state
        6. Return result

        Args:
            player_input: Raw player input

        Returns:
            TurnResult with narrative and state
        """
        start_time = time.time()

        # Parse input to check for OOC
        parsed = self.archivist.parse_input(player_input)

        # Handle OOC commands
        if parsed.primary_type == InputType.OOC and parsed.ooc_command:
            return self._handle_ooc_command(parsed.ooc_command)

        # Increment turn
        turn_number = self.campaign.current_turn + 1

        # Run simulation
        sim_request = SimulationRequest(
            campaign=self.campaign,
            world_state=self.world_state,
            bible=self.bible,
            player_input=player_input,
            turn_number=turn_number,
        )

        sim_response = await self.archivist.process(sim_request)
        self.session.archivist_calls += 1

        # Update world state
        self.world_state = sim_response.updated_world_state

        # Generate narrative
        narrative_request = NarrativeRequest(
            campaign=self.campaign,
            world_state=self.world_state,
            engine_processing=sim_response.engine_processing,
            turn_number=turn_number,
            player_input=player_input,
        )

        narrative_response = await self.storyteller.process(narrative_request)
        self.session.storyteller_calls += 1

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Create turn record
        turn = Turn(
            number=turn_number,
            player_input=player_input,
            parsed_input=parsed,
            engine_processing=sim_response.engine_processing,
            narrative=narrative_response.narrative,
            tokens_used=sim_response.tokens_used + narrative_response.tokens_used,
            processing_time_ms=processing_time,
        )

        # Update session and campaign
        self.session.add_turn(turn)
        self.campaign.current_turn = turn_number
        self.campaign.updated_at = datetime.now()

        # Create result
        result = TurnResult(
            turn_number=turn_number,
            narrative=narrative_response.narrative,
            world_state_summary=self.world_state.to_summary(),
        )

        # Fire callbacks
        if self._on_turn_complete:
            self._on_turn_complete(result)
        if self._on_state_change:
            self._on_state_change(self.world_state)

        # Auto-save
        self.save()

        return result

    def _handle_ooc_command(self, command_text: str) -> TurnResult:
        """Handle an OOC command."""
        command, arg = parse_ooc_command(command_text)

        if command == OOCCommand.STATUS:
            return self._cmd_status()
        elif command == OOCCommand.INVENTORY:
            return self._cmd_inventory()
        elif command == OOCCommand.RECAP:
            return self._cmd_recap()
        elif command == OOCCommand.NPCS:
            return self._cmd_npcs()
        elif command == OOCCommand.THREADS:
            return self._cmd_threads()
        elif command == OOCCommand.TIME:
            return self._cmd_time()
        elif command == OOCCommand.HELP:
            return self._cmd_help()
        elif command == OOCCommand.SAVE:
            self.save()
            return TurnResult(
                turn_number=self.current_turn,
                narrative="[OOC] Game saved.",
            )
        elif command == OOCCommand.RETCON:
            return self._cmd_retcon(arg)
        elif command == OOCCommand.ADJUST:
            return self._cmd_adjust(arg)
        else:
            return TurnResult(
                turn_number=self.current_turn,
                narrative=f"[OOC] Unknown command: {command_text}. Type ((help)) for available commands.",
            )

    # ==================== OOC Command Implementations ====================

    def _cmd_status(self) -> TurnResult:
        """Return PC status."""
        pc = self.bible.get_pc()
        status = self.world_state.pc_status

        lines = ["[OOC] PC Status:"]
        if pc:
            lines.append(f"Name: {pc.name}")
        lines.append(f"Health: {status.health}")
        if status.conditions:
            lines.append(f"Conditions: {', '.join(status.conditions)}")
        if status.emotional_state:
            lines.append(f"Emotional State: {status.emotional_state}")
        if status.active_goals:
            lines.append(f"Active Goals: {', '.join(status.active_goals)}")

        return TurnResult(
            turn_number=self.current_turn,
            narrative="\n".join(lines),
        )

    def _cmd_inventory(self) -> TurnResult:
        """Return PC inventory."""
        pc = self.bible.get_pc()
        if not pc:
            return TurnResult(
                turn_number=self.current_turn,
                narrative="[OOC] No PC defined.",
            )

        items = self.bible.get_character_inventory(pc.id)
        if not items:
            return TurnResult(
                turn_number=self.current_turn,
                narrative="[OOC] Inventory is empty.",
            )

        lines = ["[OOC] Inventory:"]
        for item in items:
            desc = f"- {item.name}"
            if item.description:
                desc += f": {item.description[:50]}"
            lines.append(desc)

        return TurnResult(
            turn_number=self.current_turn,
            narrative="\n".join(lines),
        )

    def _cmd_recap(self) -> TurnResult:
        """Return a recap of recent events."""
        recap = self._generate_recap()
        return TurnResult(
            turn_number=self.current_turn,
            narrative=f"[OOC] Recap:\n{recap}",
        )

    def _cmd_npcs(self) -> TurnResult:
        """Return info about active NPCs."""
        if not self.world_state.active_npcs:
            return TurnResult(
                turn_number=self.current_turn,
                narrative="[OOC] No NPCs in the current scene.",
            )

        lines = ["[OOC] NPCs Present:"]
        for npc in self.world_state.active_npcs:
            lines.append(f"\n**{npc.name}**")
            lines.append(f"  Disposition: {npc.current_disposition}")
            lines.append(f"  Current Goal: {npc.current_goal}")
            if npc.emotional_state:
                lines.append(f"  Emotional State: {npc.emotional_state}")

        return TurnResult(
            turn_number=self.current_turn,
            narrative="\n".join(lines),
        )

    def _cmd_threads(self) -> TurnResult:
        """Return active plot threads."""
        active_threads = [t for t in self.world_state.plot_threads if t.status == "active"]
        if not active_threads:
            return TurnResult(
                turn_number=self.current_turn,
                narrative="[OOC] No active plot threads.",
            )

        lines = ["[OOC] Active Plot Threads:"]
        for thread in active_threads:
            lines.append(f"\n**{thread.name}** (Priority: {thread.priority})")
            lines.append(f"  {thread.description}")
            if thread.next_beats:
                lines.append(f"  Next: {thread.next_beats[0]}")

        return TurnResult(
            turn_number=self.current_turn,
            narrative="\n".join(lines),
        )

    def _cmd_time(self) -> TurnResult:
        """Return current in-game time."""
        lines = ["[OOC] Time:"]
        if self.world_state.game_time:
            lines.append(f"Current: {self.world_state.game_time}")
        if self.world_state.time_since_start:
            lines.append(f"Elapsed: {self.world_state.time_since_start}")
        lines.append(f"Turn: {self.current_turn}")

        return TurnResult(
            turn_number=self.current_turn,
            narrative="\n".join(lines),
        )

    def _cmd_help(self) -> TurnResult:
        """Return help text."""
        help_text = """[OOC] Available Commands:

**Input Syntax:**
- Plain text: Actions and attempts
- "Quotes": Spoken dialogue
- *Asterisks*: Internal thoughts (private)
- ((Parentheses)): OOC commands
- //: Advance world autonomously

**Commands:**
- ((status)) - View PC status
- ((inventory)) - View inventory
- ((recap)) - Get story recap
- ((npcs)) - View present NPCs
- ((threads)) - View plot threads
- ((time)) - View current time
- ((save)) - Save game
- ((help)) - Show this help
- ((retcon: X)) - Retcon something
- ((adjust: X)) - Adjust settings"""

        return TurnResult(
            turn_number=self.current_turn,
            narrative=help_text,
        )

    def _cmd_retcon(self, what: str) -> TurnResult:
        """Handle retcon request."""
        # This would need LLM assistance to properly implement
        return TurnResult(
            turn_number=self.current_turn,
            narrative=f"[OOC] Retcon requested: {what}\n(Not yet implemented - please describe what you'd like to change)",
            warnings=["Retcon feature not fully implemented"],
        )

    def _cmd_adjust(self, what: str) -> TurnResult:
        """Handle adjustment request."""
        return TurnResult(
            turn_number=self.current_turn,
            narrative=f"[OOC] Adjustment requested: {what}\n(Not yet implemented)",
            warnings=["Adjust feature not fully implemented"],
        )

    # ==================== Narrative Generation ====================

    def _generate_opening(self) -> str:
        """Generate the opening narrative for a new campaign."""
        if not self.world_state.scene_description:
            return "The story begins..."

        # For now, return the scene description
        # In full implementation, this would call the Storyteller
        opening = f"{self.world_state.scene_description}\n\n"

        if self.world_state.current_location:
            opening += f"*{self.world_state.current_location.name}*"
            if self.world_state.game_time:
                opening += f" - {self.world_state.game_time}"

        opening += "\n\n{T: 1}"

        return opening

    def _generate_recap(self) -> str:
        """Generate a recap of recent events."""
        recent_turns = self.session.get_recent_turns(5)

        if not recent_turns:
            return "No events to recap."

        lines = []
        for turn in recent_turns:
            # Truncate narrative for recap
            narrative = turn.narrative[:200]
            if len(turn.narrative) > 200:
                narrative += "..."
            lines.append(f"Turn {turn.number}: {narrative}")

        return "\n\n".join(lines)

    # ==================== Persistence ====================

    def save(self) -> None:
        """Save the current session state."""
        campaign_path = self.settings.campaigns_path / self.campaign.id

        # Save campaign
        with open(campaign_path / "campaign.json", "w") as f:
            json.dump(self.campaign.model_dump(mode="json"), f, indent=2, default=str)

        # Save world state
        state_path = campaign_path / "state"
        state_path.mkdir(exist_ok=True)
        with open(state_path / "world_state.json", "w") as f:
            json.dump(self.world_state.model_dump(mode="json"), f, indent=2, default=str)

        # Save session
        sessions_path = campaign_path / "sessions"
        sessions_path.mkdir(exist_ok=True)
        session_file = sessions_path / f"session_{self.session.session_number}.json"
        with open(session_file, "w") as f:
            json.dump(self.session.model_dump(mode="json"), f, indent=2, default=str)

        # Save bible
        self.bible.save()

    @classmethod
    def load(cls, campaign_id: str) -> "SessionManager":
        """
        Load a session from disk.

        Args:
            campaign_id: The campaign ID to load

        Returns:
            SessionManager with loaded state
        """
        settings = get_settings()
        campaign_path = settings.campaigns_path / campaign_id

        # Load campaign
        with open(campaign_path / "campaign.json") as f:
            campaign_data = json.load(f)
            campaign = Campaign.model_validate(campaign_data)

        # Load bible
        bible = EntityBible(campaign_id, settings.campaigns_path)
        bible.load()

        # Load world state
        state_path = campaign_path / "state" / "world_state.json"
        if state_path.exists():
            with open(state_path) as f:
                world_state_data = json.load(f)
                world_state = WorldState.model_validate(world_state_data)
        else:
            world_state = WorldState(campaign_id=campaign_id)

        # Find most recent session
        sessions_path = campaign_path / "sessions"
        session = None
        if sessions_path.exists():
            session_files = sorted(sessions_path.glob("session_*.json"))
            if session_files:
                with open(session_files[-1]) as f:
                    session_data = json.load(f)
                    session = Session.model_validate(session_data)

        return cls(campaign, bible, world_state, session)
