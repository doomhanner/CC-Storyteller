"""
Archivist Agent - Handles data extraction, logic, and world simulation.

The Archivist is responsible for:
- Parsing player inputs into structured components
- Running feasibility checks on player actions
- Simulating world state changes
- Extracting entities from narrative
- Maintaining consistency and the Entity Bible
"""

import json
import re
from dataclasses import dataclass, field

from storyteller.agents.base import BaseAgent
from storyteller.bible.entity_bible import EntityBible
from storyteller.config import get_settings
from storyteller.models.campaign import Campaign
from storyteller.models.entities import Character, EntityType
from storyteller.models.session import (
    EngineProcessing,
    FeasibilityCheck,
    InputType,
    NPCAction,
    OutcomeType,
    ParsedInput,
    WorldSimulation,
)
from storyteller.models.world_state import ActiveNPC, WorldState


@dataclass
class SimulationRequest:
    """Request for world simulation."""

    campaign: Campaign
    world_state: WorldState
    bible: EntityBible
    player_input: str
    turn_number: int


@dataclass
class SimulationResponse:
    """Response from world simulation."""

    engine_processing: EngineProcessing
    updated_world_state: WorldState
    tokens_used: int


@dataclass
class EntityExtractionResult:
    """Result of entity extraction from text."""

    characters: list[dict] = field(default_factory=list)
    locations: list[dict] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    factions: list[dict] = field(default_factory=list)
    lore: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    tokens_used: int = 0


ARCHIVIST_SYSTEM_PROMPT = """You are the Archivist—the logic engine and memory keeper for a narrative simulation. You maintain absolute fidelity to established facts and enforce the rules of the simulation.

## Your Core Duties

1. **Parse Inputs**: Identify what the player is attempting (action, dialogue, thought, command)
2. **Check Feasibility**: Assess whether actions are possible given PC capabilities and circumstances
3. **Simulate World**: Determine what happens in the world, including NPC autonomous actions
4. **Track State**: Record all changes to entities, relationships, and world state
5. **Enforce Fog of War**: NPCs only know what they've witnessed or been told

## Information Boundaries (FOG OF WAR)

This is CRITICAL. NPCs cannot:
- Know the PC's internal thoughts (marked with *asterisks*)
- React to OOC commands (marked with ((parentheses)))
- Know about events they didn't witness
- Act on player/narrator knowledge they don't possess

Always ask: "How would this NPC know this information?"

## Feasibility Assessment

For each player action, evaluate:
- **Capability**: Does the PC have the skills, tools, and condition to attempt this?
- **Circumstances**: Is the environment, timing, and positioning favorable?
- **Friction**: What difficulty, risk, or cost is involved?

Then determine outcome:
- CLEAR_SUCCESS: Action succeeds without complication
- SUCCESS_WITH_COST: Action succeeds but costs something (time, resources, attention)
- PARTIAL_SUCCESS: Some of the intent achieved
- FAILURE_WITH_OPPORTUNITY: Fails but creates a new opening
- FAILURE_WITH_CONSEQUENCE: Fails and makes things worse
- SIMPLE_FAILURE: Just doesn't work, no major consequence

## NPC Autonomous Actions

Each turn, consider what NPCs do for their OWN reasons—not just reacting to PC. Ask:
- What does this NPC want right now?
- What do they know (from their information state)?
- What emotional state are they in?
- What action serves their goals?

## Output Format

Always respond in valid JSON matching the requested schema. Be precise and consistent."""


class ArchivistAgent(BaseAgent):
    """
    The Archivist agent - handles simulation logic and data management.
    """

    def __init__(self, model: str | None = None):
        super().__init__(model)

    @property
    def model(self) -> str:
        """The model this agent uses (logic-focused model)."""
        if self._model:
            return self._model
        return get_settings().models.archivist_model

    @property
    def system_prompt(self) -> str:
        """The system prompt for the Archivist."""
        return ARCHIVIST_SYSTEM_PROMPT

    # ==================== Input Parsing ====================

    def parse_input(self, raw_input: str) -> ParsedInput:
        """
        Parse player input into structured components.

        This is done with regex for speed—no LLM call needed.

        Input syntax:
        - Plain text: Actions/attempts
        - "Quotes": Spoken dialogue
        - *Asterisks*: Internal thoughts (private)
        - ((Parentheses)): OOC commands
        - //: Advance world autonomously
        """
        # Check for continue command
        if raw_input.strip() in ["//", "//continue"]:
            return ParsedInput(
                raw_input=raw_input, primary_type=InputType.CONTINUE
            )

        # Extract components
        dialogue_matches = re.findall(r'"([^"]*)"', raw_input)
        thought_matches = re.findall(r"\*([^*]*)\*", raw_input)
        ooc_matches = re.findall(r"\(\(([^)]*)\)\)", raw_input)

        # Remove extracted parts to get action text
        action_text = raw_input
        for match in dialogue_matches:
            action_text = action_text.replace(f'"{match}"', "")
        for match in thought_matches:
            action_text = action_text.replace(f"*{match}*", "")
        for match in ooc_matches:
            action_text = action_text.replace(f"(({match}))", "")

        action_text = action_text.strip()

        # Determine primary type
        if ooc_matches and not action_text and not dialogue_matches:
            primary_type = InputType.OOC
        elif thought_matches and not action_text and not dialogue_matches:
            primary_type = InputType.THOUGHT
        elif dialogue_matches and not action_text:
            primary_type = InputType.DIALOGUE
        elif action_text and (dialogue_matches or thought_matches):
            primary_type = InputType.MIXED
        elif action_text:
            primary_type = InputType.ACTION
        else:
            primary_type = InputType.ACTION  # Default

        return ParsedInput(
            raw_input=raw_input,
            primary_type=primary_type,
            action_text=action_text if action_text else None,
            dialogue_text=" ".join(dialogue_matches) if dialogue_matches else None,
            thought_text=" ".join(thought_matches) if thought_matches else None,
            ooc_command=" ".join(ooc_matches) if ooc_matches else None,
        )

    # ==================== Feasibility Check ====================

    async def check_feasibility(
        self,
        parsed_input: ParsedInput,
        pc: Character,
        world_state: WorldState,
        bible: EntityBible,
    ) -> FeasibilityCheck:
        """
        Check if the player's intended action is feasible.

        Args:
            parsed_input: The parsed player input
            pc: The player character
            world_state: Current world state
            bible: The entity bible for context

        Returns:
            FeasibilityCheck with assessment and outcome
        """
        # Skip feasibility for non-action inputs
        if parsed_input.primary_type in [InputType.OOC, InputType.THOUGHT, InputType.CONTINUE]:
            return FeasibilityCheck(outcome_type=OutcomeType.NOT_APPLICABLE)

        # Build context for the check
        pc_context = self._build_pc_context(pc, world_state)
        scene_context = self._build_scene_context(world_state, bible)

        prompt = f"""Assess the feasibility of this player action.

## Player Intent
{parsed_input.action_text or parsed_input.dialogue_text or "No clear action"}

## PC Status
{pc_context}

## Current Scene
{scene_context}

## Assessment Required

Evaluate and respond with JSON:
{{
    "capability": "Brief assessment of PC's relevant skills, condition, tools",
    "circumstances": "Brief assessment of environment, opposition, positioning",
    "friction": "What difficulty, risk, or cost is involved",
    "outcome_type": "One of: CLEAR_SUCCESS, SUCCESS_WITH_COST, PARTIAL_SUCCESS, FAILURE_WITH_OPPORTUNITY, FAILURE_WITH_CONSEQUENCE, SIMPLE_FAILURE",
    "outcome_description": "Brief description of what happens"
}}

Be fair but honest. The world is neither adversary nor servant—it simply is."""

        messages = self._build_messages(prompt)
        result, tokens = self._call_api_json(messages, max_tokens=1024, temperature=0.3)

        if "error" in result:
            # Fallback to simple success if parsing fails
            return FeasibilityCheck(
                capability="Assessment unavailable",
                circumstances="Assessment unavailable",
                friction="Unknown",
                outcome_type=OutcomeType.CLEAR_SUCCESS,
                outcome_description="The action proceeds.",
            )

        # Parse outcome type
        outcome_str = result.get("outcome_type", "CLEAR_SUCCESS").upper()
        try:
            outcome_type = OutcomeType(outcome_str.lower())
        except ValueError:
            outcome_type = OutcomeType.CLEAR_SUCCESS

        return FeasibilityCheck(
            capability=result.get("capability", ""),
            circumstances=result.get("circumstances", ""),
            friction=result.get("friction", ""),
            outcome_type=outcome_type,
            outcome_description=result.get("outcome_description", ""),
        )

    def _build_pc_context(self, pc: Character, world_state: WorldState) -> str:
        """Build context string about the PC."""
        parts = [f"Name: {pc.name}"]

        if pc.physical.capability:
            caps = [f"{k}: {v}" for k, v in pc.physical.capability.items()]
            parts.append(f"Physical: {', '.join(caps)}")

        if pc.physical.limitations:
            parts.append(f"Limitations: {', '.join(pc.physical.limitations)}")

        if world_state.pc_status.conditions:
            parts.append(f"Current conditions: {', '.join(world_state.pc_status.conditions)}")

        if world_state.pc_status.capabilities:
            parts.append(f"Known skills: {', '.join(world_state.pc_status.capabilities)}")

        return "\n".join(parts)

    def _build_scene_context(self, world_state: WorldState, bible: EntityBible) -> str:
        """Build context string about the current scene."""
        parts = []

        if world_state.current_location:
            loc = world_state.current_location
            parts.append(f"Location: {loc.name}")
            if loc.description:
                parts.append(f"Description: {loc.description}")
            if loc.atmosphere:
                parts.append(f"Atmosphere: {loc.atmosphere}")

        if world_state.game_time:
            parts.append(f"Time: {world_state.game_time}")

        if world_state.active_npcs:
            npc_lines = []
            for npc in world_state.active_npcs:
                npc_lines.append(
                    f"- {npc.name}: {npc.current_disposition}, wants: {npc.current_goal}"
                )
            parts.append(f"Present NPCs:\n" + "\n".join(npc_lines))

        return "\n".join(parts) if parts else "No scene context available."

    # ==================== World Simulation ====================

    async def simulate_world(
        self,
        parsed_input: ParsedInput,
        feasibility: FeasibilityCheck,
        world_state: WorldState,
        bible: EntityBible,
        campaign: Campaign,
    ) -> WorldSimulation:
        """
        Simulate world response to player action.

        Includes:
        - Time passage
        - Environmental changes
        - NPC autonomous actions
        - Off-screen events

        Args:
            parsed_input: The parsed player input
            feasibility: The feasibility check results
            world_state: Current world state
            bible: The entity bible
            campaign: The campaign settings

        Returns:
            WorldSimulation with all changes
        """
        # For OOC commands, no world simulation
        if parsed_input.primary_type == InputType.OOC:
            return WorldSimulation()

        # Build NPC context
        npc_context = self._build_npc_simulation_context(world_state, bible)

        prompt = f"""Simulate the world's response to this moment.

## What Just Happened
Player action: {parsed_input.action_text or parsed_input.dialogue_text or "Waiting/observing"}
Outcome: {feasibility.outcome_type.value if feasibility.outcome_type != OutcomeType.NOT_APPLICABLE else "No action taken"}
{feasibility.outcome_description}

## Current Scene
Location: {world_state.current_location.name if world_state.current_location else "Unknown"}
Time: {world_state.game_time or "Unknown"}

## NPCs Present (with their knowledge and goals)
{npc_context}

## Simulation Settings
NPC Autonomy Level: {campaign.settings.creativity.npc_autonomy} (0=reactive only, 1=highly proactive)
World Dynamism: {campaign.settings.creativity.world_dynamism} (0=static, 1=constantly changing)

## CRITICAL: Fog of War
NPCs can ONLY react to:
- What they SEE (actions, expressions, visible items)
- What they HEAR (dialogue in "quotes")

They CANNOT know:
- PC's thoughts (in *asterisks*)
- OOC information (in ((parentheses)))
- Events they didn't witness

## Required Output (JSON)

{{
    "time_elapsed": "How much time passes (moments, minutes, hours)",
    "environmental_changes": ["List of environmental changes, if any"],
    "ambient_details": ["Sensory details: sounds, smells, lighting changes"],
    "npc_actions": [
        {{
            "npc_id": "ID of the NPC",
            "npc_name": "Name",
            "action": "What they do",
            "motivation": "Why (from their perspective)",
            "is_autonomous": true/false
        }}
    ],
    "offscreen_events": ["Events happening elsewhere that might matter later"]
}}"""

        messages = self._build_messages(prompt)
        result, tokens = self._call_api_json(messages, max_tokens=2048, temperature=0.5)

        if "error" in result:
            return WorldSimulation(time_elapsed="moments")

        # Parse NPC actions
        npc_actions = []
        for npc_data in result.get("npc_actions", []):
            npc_actions.append(
                NPCAction(
                    npc_id=npc_data.get("npc_id", "unknown"),
                    npc_name=npc_data.get("npc_name", "Unknown"),
                    action=npc_data.get("action", ""),
                    motivation=npc_data.get("motivation", ""),
                    is_autonomous=npc_data.get("is_autonomous", False),
                )
            )

        return WorldSimulation(
            time_elapsed=result.get("time_elapsed", "moments"),
            environmental_changes=result.get("environmental_changes", []),
            ambient_details=result.get("ambient_details", []),
            npc_actions=npc_actions,
            offscreen_events=result.get("offscreen_events", []),
        )

    def _build_npc_simulation_context(
        self, world_state: WorldState, bible: EntityBible
    ) -> str:
        """Build context for NPC simulation."""
        if not world_state.active_npcs:
            return "No NPCs present."

        lines = []
        for active_npc in world_state.active_npcs:
            # Get full character data if available
            char = bible.get_entity_typed(active_npc.id, Character)

            lines.append(f"\n### {active_npc.name}")
            lines.append(f"Current disposition: {active_npc.current_disposition}")
            lines.append(f"Current goal: {active_npc.current_goal}")
            lines.append(f"Emotional state: {active_npc.emotional_state}")

            # Information state (what they know)
            info = active_npc.information_state
            if info.knows:
                lines.append(f"KNOWS: {', '.join(info.knows)}")
            if info.believes:
                lines.append(f"BELIEVES: {', '.join(info.believes)}")
            if info.suspects:
                lines.append(f"SUSPECTS: {', '.join(info.suspects)}")

            # Psychology if available from bible
            if char:
                if char.psychology.wants_immediate:
                    lines.append(f"Wants (immediate): {char.psychology.wants_immediate}")
                if char.psychology.blindspots:
                    lines.append(f"Blindspots: {', '.join(char.psychology.blindspots)}")

        return "\n".join(lines)

    # ==================== Entity Extraction ====================

    async def extract_entities(
        self, text: str, creativity: float = 0.5
    ) -> EntityExtractionResult:
        """
        Extract entities from narrative or user input text.

        Used during campaign generation and when processing new content.

        Args:
            text: The text to extract entities from
            creativity: How much to elaborate on minimal descriptions

        Returns:
            EntityExtractionResult with all extracted entities
        """
        creativity_instruction = ""
        if creativity < 0.3:
            creativity_instruction = "Extract only explicitly mentioned entities with minimal elaboration."
        elif creativity < 0.7:
            creativity_instruction = "Extract mentioned entities and add reasonable details to flesh them out."
        else:
            creativity_instruction = "Extract entities and richly elaborate them with deep characterization and connections."

        prompt = f"""Extract all significant entities from this text.

## Text to Analyze
{text}

## Instructions
{creativity_instruction}

## Output Format (JSON)

{{
    "characters": [
        {{
            "name": "Name",
            "aliases": ["Any other names"],
            "description": "Physical and notable traits",
            "is_pc": false,
            "psychology": {{
                "wants_immediate": "Current goal",
                "wants_long_term": "Life goal",
                "fears": ["What they fear"],
                "wounds": ["Past trauma"],
                "blindspots": ["Self-deceptions"]
            }},
            "voice": {{
                "patterns": ["Speech patterns"],
                "habits": ["Verbal habits"],
                "expressions": ["Characteristic phrases"]
            }},
            "tags": ["Relevant tags"]
        }}
    ],
    "locations": [
        {{
            "name": "Name",
            "description": "What it looks like",
            "atmosphere": "The feel/mood",
            "notable_features": ["Key features"],
            "tags": ["Relevant tags"]
        }}
    ],
    "items": [
        {{
            "name": "Name",
            "description": "What it is",
            "properties": {{"key": "value"}},
            "is_unique": true/false,
            "tags": ["Relevant tags"]
        }}
    ],
    "factions": [
        {{
            "name": "Name",
            "description": "What the faction is",
            "goals": ["Their objectives"],
            "public_reputation": "How they're perceived",
            "tags": ["Relevant tags"]
        }}
    ],
    "lore": [
        {{
            "name": "Title/name of the lore entry",
            "category": "history/magic/religion/culture/etc",
            "content": "The lore content",
            "is_common_knowledge": true/false,
            "tags": ["Relevant tags"]
        }}
    ],
    "relationships": [
        {{
            "source_name": "Name of source entity",
            "target_name": "Name of target entity",
            "type": "relationship type (knows, owns, member_of, etc.)",
            "notes": "Context about the relationship"
        }}
    ]
}}

Only include entities that are meaningfully present in the text."""

        messages = self._build_messages(prompt)
        result, tokens = self._call_api_json(messages, max_tokens=4096, temperature=0.3)

        if "error" in result:
            return EntityExtractionResult(tokens_used=tokens)

        return EntityExtractionResult(
            characters=result.get("characters", []),
            locations=result.get("locations", []),
            items=result.get("items", []),
            factions=result.get("factions", []),
            lore=result.get("lore", []),
            relationships=result.get("relationships", []),
            tokens_used=tokens,
        )

    # ==================== Full Turn Processing ====================

    async def process(self, request: SimulationRequest) -> SimulationResponse:
        """
        Process a full turn through the simulation pipeline.

        1. Parse input
        2. Check feasibility
        3. Simulate world
        4. Return processing results

        Args:
            request: The simulation request

        Returns:
            SimulationResponse with all processing results
        """
        total_tokens = 0

        # 1. Parse input (no LLM call)
        parsed_input = self.parse_input(request.player_input)

        # 2. Get PC for feasibility check
        pc = request.bible.get_pc()
        if not pc:
            # Create a minimal PC if none exists
            pc = Character(name="Protagonist", is_pc=True)

        # 3. Check feasibility
        feasibility = await self.check_feasibility(
            parsed_input, pc, request.world_state, request.bible
        )

        # 4. Simulate world
        world_sim = await self.simulate_world(
            parsed_input,
            feasibility,
            request.world_state,
            request.bible,
            request.campaign,
        )

        # 5. Determine state changes
        state_changes = self._determine_state_changes(
            parsed_input, feasibility, world_sim, request.world_state
        )

        # 6. Build narrative queue (projected beats)
        narrative_queue = self._build_narrative_queue(
            request.world_state, feasibility, world_sim
        )

        # Create engine processing record
        engine_processing = EngineProcessing(
            input_analysis=parsed_input,
            feasibility=feasibility,
            world_simulation=world_sim,
            narrative_queue=narrative_queue,
            state_changes=state_changes,
        )

        # Update world state
        updated_world_state = self._apply_world_changes(
            request.world_state, world_sim, request.turn_number
        )

        return SimulationResponse(
            engine_processing=engine_processing,
            updated_world_state=updated_world_state,
            tokens_used=total_tokens,
        )

    def _determine_state_changes(
        self,
        parsed_input: ParsedInput,
        feasibility: FeasibilityCheck,
        world_sim: WorldSimulation,
        world_state: WorldState,
    ) -> list[str]:
        """Determine what state changes occurred this turn."""
        changes = []

        if feasibility.outcome_description:
            changes.append(f"Action result: {feasibility.outcome_description}")

        for npc_action in world_sim.npc_actions:
            changes.append(f"{npc_action.npc_name}: {npc_action.action}")

        if world_sim.environmental_changes:
            changes.extend(world_sim.environmental_changes)

        return changes

    def _build_narrative_queue(
        self,
        world_state: WorldState,
        feasibility: FeasibilityCheck,
        world_sim: WorldSimulation,
    ) -> list[str]:
        """Build the queue of upcoming narrative beats."""
        queue = []

        # Add immediate consequences
        if feasibility.outcome_description:
            queue.append(f"Immediate: {feasibility.outcome_description}")

        # Add NPC reactions/actions
        for npc_action in world_sim.npc_actions:
            queue.append(f"NPC: {npc_action.npc_name} - {npc_action.action}")

        # Add from plot threads
        for thread in world_state.plot_threads:
            if thread.status == "active" and thread.next_beats:
                queue.append(f"Thread ({thread.name}): {thread.next_beats[0]}")

        return queue[:5]  # Keep to 3-5 beats

    def _apply_world_changes(
        self, world_state: WorldState, world_sim: WorldSimulation, turn: int
    ) -> WorldState:
        """Apply simulation results to world state."""
        # Update turn
        world_state.update_turn(turn)

        # Update NPC states based on their actions
        for npc_action in world_sim.npc_actions:
            active_npc = world_state.get_active_npc(npc_action.npc_id)
            if active_npc:
                # Update their turn reference
                active_npc.turn_ref.modified = turn
                active_npc.notes = f"Last action: {npc_action.action}"

        # Add to recent events
        for change in world_sim.environmental_changes:
            world_state.add_event(change)

        return world_state
