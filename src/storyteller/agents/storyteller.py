"""
Storyteller Agent - Handles narrative generation and prose.

The Storyteller is responsible for:
- Converting simulation results into engaging narrative prose
- Ghostwriting player inputs into vivid descriptions
- Maintaining consistent voice, tone, and style
- Handling character dialogue and descriptions
"""

from dataclasses import dataclass

from storyteller.agents.base import BaseAgent
from storyteller.config import get_settings
from storyteller.models.campaign import Campaign, NarrativeSettings
from storyteller.models.session import EngineProcessing, OutcomeType
from storyteller.models.world_state import WorldState


@dataclass
class NarrativeRequest:
    """Request for narrative generation."""

    campaign: Campaign
    world_state: WorldState
    engine_processing: EngineProcessing
    turn_number: int
    player_input: str
    expanded_input: str | None = None  # If input integration is enabled


@dataclass
class NarrativeResponse:
    """Response from narrative generation."""

    narrative: str
    tokens_used: int


STORYTELLER_SYSTEM_PROMPT = """You are the Storyteller—the narrative voice of a living world simulation. Your role is to transform simulation results into vivid, engaging prose.

## Your Voice

Write in {perspective}, {tense} tense. Be visceral and sensory—engage fully with violence, intimacy, consequence. Describe the PC's involuntary physical responses (racing heart, clenched jaw, the taste of copper) but NOT their emotional interpretations—let the reader feel, don't tell them what to feel.

## Your Constraints

- Maximum {max_paragraphs} paragraphs per turn
- End on a beat that invites response—a question, a tension, a choice
- Never add major actions the player didn't indicate
- Never assume success before the simulation adjudicates
- Enhance HOW, never change WHAT the player intended
- The world exists independently of the PC—NPCs have their own lives, goals, tensions

## Ghostwriting

When expanding player input:
- At LOW creativity: Stay close to literal input, minimal embellishment
- At MEDIUM creativity: Add sensory details, body language, environmental reactions
- At HIGH creativity: Full prose transformation—the player's intent becomes a scene

The player wrote: "{player_input}"

## The Current Scene

Location: {location}
Time: {time}
Present: {npcs_present}

## What Happened (from simulation)

{simulation_results}

## Your Task

Transform the simulation results into narrative prose. {ghostwrite_instruction}

Tag your response with the turn number at the end: {{T: {turn_number}}}"""


class StorytellerAgent(BaseAgent):
    """
    The Storyteller agent - generates narrative prose from simulation results.
    """

    def __init__(self, model: str | None = None):
        super().__init__(model)
        self._settings_cache: NarrativeSettings | None = None

    @property
    def model(self) -> str:
        """The model this agent uses (creative model)."""
        if self._model:
            return self._model
        return get_settings().models.storyteller_model

    @property
    def system_prompt(self) -> str:
        """Base system prompt - will be customized per request."""
        return "You are the Storyteller for an interactive narrative simulation."

    def _build_narrative_prompt(self, request: NarrativeRequest) -> str:
        """Build the customized prompt for narrative generation."""
        settings = request.campaign.settings.narrative
        creativity = request.campaign.settings.creativity.input_integration

        # Determine perspective text
        perspective_map = {
            "second_person": "second person",
            "third_person": "third person limited",
        }
        perspective = perspective_map.get(settings.perspective, "second person")

        # Build NPCs present string
        npcs_present = "No one else"
        if request.world_state.active_npcs:
            npc_names = [npc.name for npc in request.world_state.active_npcs]
            npcs_present = ", ".join(npc_names)

        # Build simulation results summary
        sim_results = self._format_simulation_results(request.engine_processing)

        # Ghostwrite instruction based on creativity level
        if creativity < 0.3:
            ghostwrite_instruction = "Stay close to the player's literal input with minimal embellishment."
        elif creativity < 0.7:
            ghostwrite_instruction = "Enhance the player's input with sensory details and environmental reactions while preserving their intent."
        else:
            ghostwrite_instruction = "Transform the player's input into vivid, immersive prose that captures their intent through rich description and atmosphere."

        # Location and time
        location = "Unknown"
        time = "Unknown"
        if request.world_state.current_location:
            location = request.world_state.current_location.name
            if request.world_state.current_location.atmosphere:
                location += f" ({request.world_state.current_location.atmosphere})"
        if request.world_state.game_time:
            time = request.world_state.game_time

        prompt = STORYTELLER_SYSTEM_PROMPT.format(
            perspective=perspective,
            tense=settings.tense,
            max_paragraphs=settings.max_paragraphs,
            player_input=request.player_input,
            location=location,
            time=time,
            npcs_present=npcs_present,
            simulation_results=sim_results,
            ghostwrite_instruction=ghostwrite_instruction,
            turn_number=request.turn_number,
        )

        return prompt

    def _format_simulation_results(self, processing: EngineProcessing) -> str:
        """Format engine processing results for the storyteller."""
        parts = []

        # Input analysis
        if processing.input_analysis:
            parts.append(f"Player Intent: {processing.input_analysis.primary_type.value}")
            if processing.input_analysis.action_text:
                parts.append(f"Action: {processing.input_analysis.action_text}")
            if processing.input_analysis.dialogue_text:
                parts.append(f"Dialogue: \"{processing.input_analysis.dialogue_text}\"")

        # Feasibility and outcome
        if processing.feasibility:
            if processing.feasibility.outcome_type != OutcomeType.NOT_APPLICABLE:
                outcome_descriptions = {
                    OutcomeType.CLEAR_SUCCESS: "The action succeeds clearly.",
                    OutcomeType.SUCCESS_WITH_COST: "The action succeeds, but at a cost.",
                    OutcomeType.PARTIAL_SUCCESS: "Partial success—some of the intent achieved.",
                    OutcomeType.FAILURE_WITH_OPPORTUNITY: "The action fails, but creates an opportunity.",
                    OutcomeType.FAILURE_WITH_CONSEQUENCE: "The action fails with consequences.",
                    OutcomeType.SIMPLE_FAILURE: "The action simply fails.",
                }
                parts.append(
                    f"Outcome: {outcome_descriptions.get(processing.feasibility.outcome_type, 'Unknown')}"
                )
                if processing.feasibility.outcome_description:
                    parts.append(f"Details: {processing.feasibility.outcome_description}")

        # World simulation
        ws = processing.world_simulation
        if ws.time_elapsed and ws.time_elapsed != "moments":
            parts.append(f"Time Passes: {ws.time_elapsed}")

        if ws.environmental_changes:
            parts.append(f"Environment: {'; '.join(ws.environmental_changes)}")

        if ws.ambient_details:
            parts.append(f"Ambient: {'; '.join(ws.ambient_details)}")

        # NPC actions
        for npc_action in ws.npc_actions:
            action_type = "autonomously" if npc_action.is_autonomous else "in response"
            parts.append(f"{npc_action.npc_name} ({action_type}): {npc_action.action}")

        # State changes
        if processing.state_changes:
            parts.append(f"Changes: {'; '.join(processing.state_changes)}")

        return "\n".join(parts) if parts else "A quiet moment passes."

    async def process(self, request: NarrativeRequest) -> NarrativeResponse:
        """
        Generate narrative from simulation results.

        Args:
            request: The narrative generation request

        Returns:
            NarrativeResponse with the generated prose
        """
        # Build the customized system prompt
        system_prompt = self._build_narrative_prompt(request)

        # Build user message with context
        user_message = f"""Generate the narrative for turn {request.turn_number}.

The player's input was: "{request.player_input}"

Write engaging prose that brings this moment to life. Remember:
- Show, don't tell
- End on a beat that invites response
- Stay within {request.campaign.settings.narrative.max_paragraphs} paragraphs"""

        # Make the API call
        messages = self._build_messages(user_message)

        # Override system prompt for this call
        original_system = self._system_prompt_override
        self._system_prompt_override = system_prompt

        narrative, tokens = self._call_api(
            messages,
            max_tokens=get_settings().models.max_tokens_narrative,
            temperature=self._get_temperature(request.campaign.settings.creativity.input_integration),
        )

        self._system_prompt_override = original_system

        return NarrativeResponse(narrative=narrative.strip(), tokens_used=tokens)

    def _get_temperature(self, creativity: float) -> float:
        """Map creativity slider to temperature."""
        # Range from 0.7 (low creativity) to 1.0 (high creativity)
        return 0.7 + (creativity * 0.3)

    @property
    def _system_prompt_override(self) -> str | None:
        return getattr(self, "_sys_override", None)

    @_system_prompt_override.setter
    def _system_prompt_override(self, value: str | None) -> None:
        self._sys_override = value

    # Synchronous version for simpler use cases
    def generate_narrative(self, request: NarrativeRequest) -> NarrativeResponse:
        """
        Synchronous narrative generation.

        Args:
            request: The narrative generation request

        Returns:
            NarrativeResponse with the generated prose
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.process(request))

    def ghostwrite(
        self, player_input: str, pc_voice: dict | None = None, creativity: float = 0.5
    ) -> tuple[str, int]:
        """
        Expand player input into richer prose.

        Args:
            player_input: The raw player input
            pc_voice: Optional PC voice characteristics
            creativity: How much to elaborate (0-1)

        Returns:
            Tuple of (expanded text, tokens used)
        """
        voice_context = ""
        if pc_voice:
            voice_context = f"""
The PC's voice characteristics:
- Speech patterns: {pc_voice.get('patterns', 'normal')}
- Habits: {pc_voice.get('habits', 'none noted')}
- Typical expressions: {pc_voice.get('expressions', 'none noted')}
"""

        if creativity < 0.3:
            instruction = "Make minimal changes—just clean up the phrasing while preserving the exact intent."
        elif creativity < 0.7:
            instruction = "Enhance with sensory details and body language while keeping the core action/dialogue intact."
        else:
            instruction = "Transform into vivid, immersive prose that captures the spirit of the input with rich description."

        prompt = f"""Ghostwrite this player input into narrative-appropriate prose.

Player input: "{player_input}"
{voice_context}
Instructions: {instruction}

Return ONLY the ghostwritten text, nothing else."""

        messages = self._build_messages(prompt)
        text, tokens = self._call_api(
            messages,
            max_tokens=512,
            temperature=self._get_temperature(creativity),
        )

        return text.strip(), tokens
