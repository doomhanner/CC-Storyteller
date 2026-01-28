"""
Campaign Generator - Creates and expands campaigns from user input.

Handles:
- New campaign generation from minimal to detailed input
- Entity expansion based on creativity settings
- Import of user notes and conversion to structured data
- Integration of new entities into existing campaigns
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from storyteller.agents.archivist import ArchivistAgent, EntityExtractionResult
from storyteller.bible.entity_bible import EntityBible
from storyteller.config import get_settings
from storyteller.models.campaign import Campaign, CampaignSettings, CampaignStatus
from storyteller.models.entities import (
    Character,
    EntityType,
    Faction,
    Item,
    Location,
    Lore,
    LoreCategory,
    PhysicalAttributes,
    Psychology,
    CharacterVoice,
    TurnReference,
)
from storyteller.models.relationships import Relationship, RelationshipType
from storyteller.models.world_state import WorldState, LocationState, PCStatus


@dataclass
class GenerationInput:
    """Input for campaign generation."""

    # User-provided content
    setting_description: str = ""
    pc_description: str = ""
    starting_situation: str = ""
    additional_notes: str = ""

    # Generation settings
    creativity: float = 0.5
    campaign_name: str = ""


@dataclass
class GenerationResult:
    """Result of campaign generation."""

    campaign: Campaign
    bible: EntityBible
    world_state: WorldState
    expansion_summary: str = ""
    tokens_used: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class EntityImportResult:
    """Result of importing entities into an existing campaign."""

    entities_added: int = 0
    relationships_added: int = 0
    integration_notes: str = ""
    tokens_used: int = 0


CAMPAIGN_EXPANSION_PROMPT = """You are expanding a campaign setting for a narrative simulation game.

## User Input
Setting: {setting_description}
Player Character: {pc_description}
Starting Situation: {starting_situation}
Additional Notes: {additional_notes}

## Creativity Level: {creativity_level}
{creativity_instruction}

## Your Task

Expand this into a rich, playable campaign. Generate:

1. **Setting Expansion**: Flesh out the world, its rules, atmosphere, and tone
2. **Key Locations**: 3-5 important locations with atmosphere and features
3. **Important NPCs**: 3-7 characters with full psychological profiles
4. **The Player Character**: Full profile based on the description
5. **Starting Factions**: Any organizations or groups relevant to the story
6. **Essential Lore**: World rules, history, or knowledge the PC would have
7. **Plot Threads**: 2-4 potential storylines seeded in the starting situation
8. **Opening Scene**: Where and how the story begins

## Output Format (JSON)

{{
    "setting_summary": "Expanded description of the setting and its tone",
    "opening_scene": {{
        "location_name": "Where the story begins",
        "description": "What the PC sees/experiences",
        "time": "When it is",
        "present_npcs": ["Names of NPCs present"]
    }},
    "pc": {{
        "name": "PC's name",
        "physical": {{
            "appearance": "What they look like",
            "build": "Body type and presence",
            "capability": {{"strength": "level", "agility": "level", "health": "state"}},
            "limitations": ["Any physical limitations"]
        }},
        "psychology": {{
            "wants_immediate": "Current goal",
            "wants_long_term": "Life goal",
            "fears": ["What they fear"],
            "wounds": ["Past experiences that shaped them"],
            "blindspots": ["Self-deceptions or biases"]
        }},
        "voice": {{
            "patterns": ["How they speak"],
            "habits": ["Verbal/physical habits"],
            "expressions": ["Characteristic phrases"]
        }},
        "inventory": ["Starting items"],
        "capabilities": ["Skills and abilities"],
        "tags": ["Character tags"]
    }},
    "npcs": [
        {{
            "name": "Name",
            "aliases": ["Other names"],
            "description": "Brief description",
            "physical": {{...}},
            "psychology": {{...}},
            "voice": {{...}},
            "relationship_to_pc": {{
                "type": "how they relate",
                "trust": 0.0, "respect": 0.0, "affection": 0.0, "utility": 0.0
            }},
            "tags": ["Tags"]
        }}
    ],
    "locations": [
        {{
            "name": "Name",
            "description": "What it looks like",
            "atmosphere": "How it feels",
            "notable_features": ["Key features"],
            "connected_to": ["Names of connected locations"],
            "tags": ["Tags"]
        }}
    ],
    "factions": [
        {{
            "name": "Name",
            "description": "What they are",
            "goals": ["Their objectives"],
            "public_reputation": "How they're seen",
            "secret_nature": "Hidden aspects",
            "tags": ["Tags"]
        }}
    ],
    "lore": [
        {{
            "name": "Entry name",
            "category": "history/magic/culture/etc",
            "content": "The lore",
            "is_common_knowledge": true/false
        }}
    ],
    "plot_threads": [
        {{
            "name": "Thread name",
            "description": "What this storyline is about",
            "related_npcs": ["NPC names involved"],
            "next_beats": ["Potential upcoming events"],
            "priority": 5
        }}
    ],
    "additional_relationships": [
        {{
            "source": "Entity name",
            "target": "Entity name",
            "type": "relationship type",
            "notes": "Context"
        }}
    ]
}}

Make it specific, evocative, and immediately playable. Create tensions, secrets, and hooks."""


class CampaignGenerator:
    """
    Generates and expands campaigns from user input.
    """

    def __init__(self):
        self.archivist = ArchivistAgent()
        self.settings = get_settings()

    async def generate_campaign(self, input_data: GenerationInput) -> GenerationResult:
        """
        Generate a complete campaign from user input.

        Args:
            input_data: The generation input with user's descriptions

        Returns:
            GenerationResult with campaign, bible, and world state
        """
        total_tokens = 0
        warnings = []

        # Determine creativity instruction
        if input_data.creativity < 0.3:
            creativity_instruction = "Stay close to the user's input. Add only essential details needed for play. Keep it minimal and focused."
            creativity_level = "LOW"
        elif input_data.creativity < 0.7:
            creativity_instruction = "Flesh out the user's input with reasonable additions. Add depth while respecting the core vision."
            creativity_level = "MEDIUM"
        else:
            creativity_instruction = "Richly elaborate on the user's input. Create deep characterization, hidden connections, and layered complexity."
            creativity_level = "HIGH"

        # Build the expansion prompt
        prompt = CAMPAIGN_EXPANSION_PROMPT.format(
            setting_description=input_data.setting_description or "Not specified",
            pc_description=input_data.pc_description or "Not specified",
            starting_situation=input_data.starting_situation or "Not specified",
            additional_notes=input_data.additional_notes or "None",
            creativity_level=creativity_level,
            creativity_instruction=creativity_instruction,
        )

        # Call the LLM for expansion
        messages = [{"role": "user", "content": prompt}]

        # Use the archivist's client for the API call
        response = self.archivist.client.messages.create(
            model=self.archivist.model,
            max_tokens=8192,
            system="You are a creative worldbuilder and game master. Generate rich, playable campaign content in valid JSON format.",
            messages=messages,
            temperature=0.7 + (input_data.creativity * 0.3),
        )

        # Extract and parse response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        total_tokens += response.usage.input_tokens + response.usage.output_tokens

        # Parse JSON
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            expansion_data = json.loads(text.strip())
        except json.JSONDecodeError as e:
            warnings.append(f"JSON parse error: {e}")
            expansion_data = {}

        # Create the campaign
        campaign_name = input_data.campaign_name or self._generate_campaign_name(
            input_data.setting_description
        )
        campaign = Campaign(
            name=campaign_name,
            description=input_data.setting_description,
            setting_summary=expansion_data.get("setting_summary", input_data.setting_description),
            status=CampaignStatus.DRAFT,
            settings=CampaignSettings(),
            initial_input=self._combine_inputs(input_data),
            starting_situation=input_data.starting_situation,
        )

        # Apply creativity settings
        campaign.settings.creativity.generation = input_data.creativity
        campaign.settings.creativity.input_integration = input_data.creativity

        # Create the bible
        bible = EntityBible(campaign.id, self.settings.campaigns_path)

        # Populate the bible from expansion data
        self._populate_bible(bible, expansion_data, campaign, warnings)

        # Create initial world state
        world_state = self._create_initial_world_state(
            campaign, bible, expansion_data, warnings
        )

        # Generate expansion summary
        expansion_summary = self._generate_expansion_summary(expansion_data)

        return GenerationResult(
            campaign=campaign,
            bible=bible,
            world_state=world_state,
            expansion_summary=expansion_summary,
            tokens_used=total_tokens,
            warnings=warnings,
        )

    def _generate_campaign_name(self, setting: str) -> str:
        """Generate a campaign name from the setting description."""
        if not setting:
            return f"Campaign_{uuid4().hex[:6]}"

        # Take first few significant words
        words = setting.split()[:3]
        return " ".join(words).title() + " Campaign"

    def _combine_inputs(self, input_data: GenerationInput) -> str:
        """Combine all inputs into a single string for storage."""
        parts = []
        if input_data.setting_description:
            parts.append(f"Setting: {input_data.setting_description}")
        if input_data.pc_description:
            parts.append(f"PC: {input_data.pc_description}")
        if input_data.starting_situation:
            parts.append(f"Start: {input_data.starting_situation}")
        if input_data.additional_notes:
            parts.append(f"Notes: {input_data.additional_notes}")
        return "\n".join(parts)

    def _populate_bible(
        self,
        bible: EntityBible,
        data: dict,
        campaign: Campaign,
        warnings: list[str],
    ) -> None:
        """Populate the bible from expansion data."""
        entity_id_map = {}  # name -> id for relationship linking

        # Create PC
        pc_data = data.get("pc", {})
        if pc_data:
            pc = self._create_character_from_data(pc_data, is_pc=True)
            bible.add_entity(pc)
            campaign.pc_id = pc.id
            entity_id_map[pc.name.lower()] = pc.id

        # Create NPCs
        for npc_data in data.get("npcs", []):
            try:
                npc = self._create_character_from_data(npc_data, is_pc=False)
                bible.add_entity(npc)
                entity_id_map[npc.name.lower()] = npc.id

                # Create relationship to PC if specified
                rel_to_pc = npc_data.get("relationship_to_pc")
                if rel_to_pc and campaign.pc_id:
                    rel = Relationship(
                        source_id=npc.id,
                        target_id=campaign.pc_id,
                        relationship_type=RelationshipType.KNOWS,
                        label=rel_to_pc.get("type", ""),
                        notes=f"Trust: {rel_to_pc.get('trust', 0)}, Respect: {rel_to_pc.get('respect', 0)}",
                    )
                    bible.add_relationship(rel)
            except Exception as e:
                warnings.append(f"Failed to create NPC: {e}")

        # Create locations
        location_connections = []  # Store for later linking
        for loc_data in data.get("locations", []):
            try:
                location = Location(
                    name=loc_data.get("name", "Unknown Location"),
                    description=loc_data.get("description", ""),
                    atmosphere=loc_data.get("atmosphere", ""),
                    notable_features=loc_data.get("notable_features", []),
                    tags=loc_data.get("tags", []),
                )
                bible.add_entity(location)
                entity_id_map[location.name.lower()] = location.id

                # Store connections for later
                for connected_name in loc_data.get("connected_to", []):
                    location_connections.append((location.name, connected_name))
            except Exception as e:
                warnings.append(f"Failed to create location: {e}")

        # Link location connections
        for source_name, target_name in location_connections:
            source_id = entity_id_map.get(source_name.lower())
            target_id = entity_id_map.get(target_name.lower())
            if source_id and target_id:
                # Add to connected_locations
                source_loc = bible.get_entity_typed(source_id, Location)
                if source_loc and target_id not in source_loc.connected_locations:
                    source_loc.connected_locations.append(target_id)
                    bible.update_entity(source_loc)

        # Create factions
        for faction_data in data.get("factions", []):
            try:
                faction = Faction(
                    name=faction_data.get("name", "Unknown Faction"),
                    description=faction_data.get("description", ""),
                    goals=faction_data.get("goals", []),
                    public_reputation=faction_data.get("public_reputation", ""),
                    secret_nature=faction_data.get("secret_nature", ""),
                    tags=faction_data.get("tags", []),
                )
                bible.add_entity(faction)
                entity_id_map[faction.name.lower()] = faction.id
            except Exception as e:
                warnings.append(f"Failed to create faction: {e}")

        # Create lore
        for lore_data in data.get("lore", []):
            try:
                category_str = lore_data.get("category", "other").lower()
                try:
                    category = LoreCategory(category_str)
                except ValueError:
                    category = LoreCategory.OTHER

                lore = Lore(
                    name=lore_data.get("name", "Unknown Lore"),
                    category=category,
                    content=lore_data.get("content", ""),
                    is_common_knowledge=lore_data.get("is_common_knowledge", True),
                    tags=lore_data.get("tags", []),
                )
                bible.add_entity(lore)
                entity_id_map[lore.name.lower()] = lore.id
            except Exception as e:
                warnings.append(f"Failed to create lore: {e}")

        # Create additional relationships
        for rel_data in data.get("additional_relationships", []):
            try:
                source_id = entity_id_map.get(rel_data.get("source", "").lower())
                target_id = entity_id_map.get(rel_data.get("target", "").lower())

                if source_id and target_id:
                    rel_type_str = rel_data.get("type", "related_to").lower()
                    try:
                        rel_type = RelationshipType(rel_type_str)
                    except ValueError:
                        rel_type = RelationshipType.RELATED_TO

                    rel = Relationship(
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=rel_type,
                        notes=rel_data.get("notes", ""),
                    )
                    bible.add_relationship(rel)
            except Exception as e:
                warnings.append(f"Failed to create relationship: {e}")

        # Save the bible
        bible.save()

    def _create_character_from_data(self, data: dict, is_pc: bool) -> Character:
        """Create a Character entity from expansion data."""
        physical_data = data.get("physical", {})
        psych_data = data.get("psychology", {})
        voice_data = data.get("voice", {})

        physical = PhysicalAttributes(
            appearance=physical_data.get("appearance", ""),
            build=physical_data.get("build", ""),
            capability=physical_data.get("capability", {}),
            limitations=physical_data.get("limitations", []),
        )

        voice = CharacterVoice(
            patterns=voice_data.get("patterns", []),
            habits=voice_data.get("habits", []),
            expressions=voice_data.get("expressions", []),
        )

        psychology = Psychology(
            wants_immediate=psych_data.get("wants_immediate", ""),
            wants_long_term=psych_data.get("wants_long_term", ""),
            fears=psych_data.get("fears", []),
            wounds=psych_data.get("wounds", []),
            blindspots=psych_data.get("blindspots", []),
            voice=voice,
        )

        return Character(
            name=data.get("name", "Unknown"),
            aliases=data.get("aliases", []),
            description=data.get("description", ""),
            is_pc=is_pc,
            physical=physical,
            psychology=psychology,
            inventory=data.get("inventory", []),
            tags=data.get("tags", []),
        )

    def _create_initial_world_state(
        self,
        campaign: Campaign,
        bible: EntityBible,
        data: dict,
        warnings: list[str],
    ) -> WorldState:
        """Create the initial world state from expansion data."""
        opening = data.get("opening_scene", {})

        # Find the starting location
        starting_location = None
        loc_name = opening.get("location_name", "")
        if loc_name:
            locations = bible.find_by_name(loc_name)
            if locations:
                loc = locations[0]
                if isinstance(loc, Location):
                    starting_location = LocationState(
                        id=loc.id,
                        name=loc.name,
                        description=opening.get("description", loc.description),
                        time_of_day=opening.get("time", ""),
                        atmosphere=loc.atmosphere,
                    )

        # Set up PC status
        pc = bible.get_pc()
        pc_status = PCStatus()
        if pc:
            pc_data = data.get("pc", {})
            pc_status.capabilities = pc_data.get("capabilities", [])

        # Find present NPCs
        from storyteller.models.world_state import ActiveNPC

        active_npcs = []
        for npc_name in opening.get("present_npcs", []):
            chars = bible.find_by_name(npc_name)
            if chars:
                char = chars[0]
                if isinstance(char, Character):
                    active_npcs.append(
                        ActiveNPC(
                            id=char.id,
                            name=char.name,
                            current_disposition="neutral",
                            current_goal=char.psychology.wants_immediate,
                            emotional_state="neutral",
                        )
                    )

        # Create plot threads
        from storyteller.models.world_state import PlotThread

        plot_threads = []
        for thread_data in data.get("plot_threads", []):
            plot_threads.append(
                PlotThread(
                    id=str(uuid4())[:8],
                    name=thread_data.get("name", "Unknown Thread"),
                    description=thread_data.get("description", ""),
                    related_npcs=thread_data.get("related_npcs", []),
                    next_beats=thread_data.get("next_beats", []),
                    priority=thread_data.get("priority", 5),
                )
            )

        return WorldState(
            campaign_id=campaign.id,
            current_turn=0,
            current_location=starting_location,
            game_time=opening.get("time", ""),
            pc_status=pc_status,
            pc_inventory=data.get("pc", {}).get("inventory", []),
            active_npcs=active_npcs,
            scene_description=opening.get("description", ""),
            plot_threads=plot_threads,
        )

    def _generate_expansion_summary(self, data: dict) -> str:
        """Generate a human-readable summary of what was created."""
        lines = []

        lines.append("## Campaign Generated\n")

        if data.get("setting_summary"):
            lines.append(f"**Setting:** {data['setting_summary'][:200]}...\n")

        if data.get("pc"):
            lines.append(f"**Player Character:** {data['pc'].get('name', 'Unknown')}")

        npcs = data.get("npcs", [])
        if npcs:
            npc_names = [n.get("name", "?") for n in npcs]
            lines.append(f"**NPCs:** {', '.join(npc_names)}")

        locations = data.get("locations", [])
        if locations:
            loc_names = [l.get("name", "?") for l in locations]
            lines.append(f"**Locations:** {', '.join(loc_names)}")

        threads = data.get("plot_threads", [])
        if threads:
            thread_names = [t.get("name", "?") for t in threads]
            lines.append(f"**Plot Threads:** {', '.join(thread_names)}")

        opening = data.get("opening_scene", {})
        if opening:
            lines.append(f"\n**Opening Scene:** {opening.get('location_name', 'Unknown')}")
            lines.append(f"_{opening.get('description', '')[:200]}_")

        return "\n".join(lines)

    async def import_entities(
        self,
        campaign: Campaign,
        bible: EntityBible,
        text: str,
        creativity: float = 0.5,
    ) -> EntityImportResult:
        """
        Import new entities from text into an existing campaign.

        Args:
            campaign: The campaign to import into
            bible: The existing bible
            text: The text to extract entities from
            creativity: How much to elaborate

        Returns:
            EntityImportResult with import statistics
        """
        # Extract entities from text
        extraction = await self.archivist.extract_entities(text, creativity)

        entities_added = 0
        relationships_added = 0
        entity_id_map = {}

        # Add characters
        for char_data in extraction.characters:
            try:
                char = self._create_character_from_data(char_data, is_pc=False)
                char.turn_ref = TurnReference(created=campaign.current_turn)
                bible.add_entity(char)
                entity_id_map[char.name.lower()] = char.id
                entities_added += 1
            except Exception:
                pass

        # Add locations
        for loc_data in extraction.locations:
            try:
                location = Location(
                    name=loc_data.get("name", "Unknown"),
                    description=loc_data.get("description", ""),
                    atmosphere=loc_data.get("atmosphere", ""),
                    notable_features=loc_data.get("notable_features", []),
                    tags=loc_data.get("tags", []),
                    turn_ref=TurnReference(created=campaign.current_turn),
                )
                bible.add_entity(location)
                entity_id_map[location.name.lower()] = location.id
                entities_added += 1
            except Exception:
                pass

        # Add items
        for item_data in extraction.items:
            try:
                item = Item(
                    name=item_data.get("name", "Unknown"),
                    description=item_data.get("description", ""),
                    properties=item_data.get("properties", {}),
                    is_unique=item_data.get("is_unique", False),
                    tags=item_data.get("tags", []),
                    turn_ref=TurnReference(created=campaign.current_turn),
                )
                bible.add_entity(item)
                entity_id_map[item.name.lower()] = item.id
                entities_added += 1
            except Exception:
                pass

        # Add relationships
        for rel_data in extraction.relationships:
            try:
                source_name = rel_data.get("source_name", "").lower()
                target_name = rel_data.get("target_name", "").lower()

                # Look up in new entities first, then existing bible
                source_id = entity_id_map.get(source_name)
                if not source_id:
                    existing = bible.find_by_name(source_name)
                    if existing:
                        source_id = existing[0].id

                target_id = entity_id_map.get(target_name)
                if not target_id:
                    existing = bible.find_by_name(target_name)
                    if existing:
                        target_id = existing[0].id

                if source_id and target_id:
                    rel_type_str = rel_data.get("type", "related_to").lower()
                    try:
                        rel_type = RelationshipType(rel_type_str)
                    except ValueError:
                        rel_type = RelationshipType.RELATED_TO

                    rel = Relationship(
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=rel_type,
                        notes=rel_data.get("notes", ""),
                        turn_ref=TurnReference(created=campaign.current_turn),
                    )
                    bible.add_relationship(rel)
                    relationships_added += 1
            except Exception:
                pass

        # Save updated bible
        bible.save()

        return EntityImportResult(
            entities_added=entities_added,
            relationships_added=relationships_added,
            integration_notes=f"Imported {entities_added} entities and {relationships_added} relationships.",
            tokens_used=extraction.tokens_used,
        )
