# CC-Storyteller Architecture

## Overview

CC-Storyteller is an LLM-powered narrative simulation engine designed for deep roleplaying sessions with robust world-simulation logic. It uses a dual-agent architecture to separate creative storytelling from data management and procedural logic.

## Core Philosophy

1. **Simulation over Narration**: The world exists independently of the player. NPCs have their own goals, knowledge, and agency.
2. **Diegetic Neutrality**: The world is neither adversary nor ally - it simply *is*.
3. **Fog of War**: Information is bounded. NPCs only know what they've witnessed or been told.
4. **Emergent Outcomes**: Results come from honest simulation, not predetermined story beats.

---

## Dual-Agent Architecture

### Storyteller Agent
**Purpose**: Creative narrative generation, prose, atmosphere, dialogue
**Model**: Claude Sonnet (creative, expressive)
**Responsibilities**:
- Generate narrative prose from simulation outcomes
- Ghostwrite player inputs into vivid prose
- Maintain consistent voice and tone
- Handle dialogue and character voice
- Create atmospheric descriptions

### Archivist Agent
**Purpose**: Data extraction, logic, consistency, world state management
**Model**: Claude Haiku (fast, structured) with JSON mode
**Responsibilities**:
- Extract entities from narrative and user inputs
- Maintain the Entity Bible
- Track relationships and their changes
- Perform consistency checks
- Handle turn-indexed state management
- Process feasibility checks for player actions

---

## Entity Bible System

### Entity Types

| Type | Description | Key Attributes |
|------|-------------|----------------|
| **Character** | NPCs and the PC | Physical, Psychology, Relationships, Information State |
| **Location** | Places in the world | Description, Connections, Current Occupants, Events |
| **Item** | Objects of significance | Description, Properties, Owner/Location, History |
| **Faction** | Groups and organizations | Goals, Resources, Members, Relationships, Territory |
| **Lore** | World knowledge/codex | Category, Content, Related Entities, Visibility |

### Relationship System

Relationships are first-class entities with:
- **Source** and **Target** entities
- **Type** (owns, knows, located_at, member_of, allied_with, hostile_to, etc.)
- **Attributes** (strength, trust, respect, affection, utility - for interpersonal)
- **Turn Established** and **Turn Modified**
- **Notes** (context, history)

### Turn Indexing

All state changes are indexed by turn number:
- `{T: 12}` - Established on turn 12
- `{T: 3, 8*}` - Created turn 3, modified turn 8
- `{T: 5+}` - Unchanged since turn 5

---

## Session Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SESSION MODES                             │
├─────────────────────────────────────────────────────────────┤
│  NEW GAME MODE          │  IN-PROGRESS MODE                 │
│  ─────────────────      │  ────────────────────             │
│  1. Intake              │  1. Load Campaign State           │
│  2. Generation          │  2. Resume at Last Turn           │
│  3. Entity Expansion    │  3. Process Player Input          │
│  4. User Review         │  4. Simulate World Response       │
│  5. Confirmation        │  5. Update Entity Bible           │
│  6. Begin Play (T:1)    │  6. Generate Narrative            │
└─────────────────────────────────────────────────────────────┘
```

### Turn Processing Pipeline

```
Player Input
     │
     ▼
┌─────────────────┐
│  Parse Input    │  ← Detect type: action, dialogue, thought, OOC, continue
│  (Script)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Archivist:     │  ← Feasibility check, NPC knowledge check
│  Analyze Intent │     What can NPCs perceive? What do they know?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Archivist:     │  ← Time passage, off-screen events, NPC autonomous actions
│  World Sim      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Archivist:     │  ← Determine outcome based on capability, circumstance, friction
│  Adjudicate     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Storyteller:   │  ← Turn simulation results into narrative prose
│  Narrate        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Archivist:     │  ← Update Bible, track changes, maintain consistency
│  Record State   │
└─────────────────┘
```

---

## Creativity Slider System

### Generation Creativity (0.0 - 1.0)

Controls how much the system elaborates on user input during entity/campaign generation:

| Level | Behavior | Example: "a cat" |
|-------|----------|------------------|
| 0.0-0.3 | Minimal | A common street cat, no special details |
| 0.4-0.6 | Moderate | A grey tabby that frequents the market, locals call it "Shadow" |
| 0.7-1.0 | Expansive | The PC's childhood companion, a one-eyed calico named Whisper with a distinctive crooked tail, known to bring "gifts" at inopportune moments |

### Input Integration Creativity (0.0 - 1.0)

Controls how player action inputs are expanded:

| Level | Behavior | Example: "I tell him to go away" |
|-------|----------|-----------------------------------|
| 0.0 | Literal | "Go away." |
| 0.5 | Enhanced | You wave a dismissive hand. "Leave me be." |
| 1.0 | Full Ghostwrite | Your jaw tightens as you turn to face him, voice dropping to that dangerous quiet your crew knows well. "You have exactly three seconds to remove yourself from my presence before I help you leave—through the window." |

---

## Data Storage

### Directory Structure

```
campaigns/
  {campaign_id}/
    campaign.json       # Campaign metadata
    bible/
      characters.json   # Character entities
      locations.json    # Location entities
      items.json        # Item entities
      factions.json     # Faction entities
      lore.json         # Lore/codex entries
      relationships.json # All relationships
    sessions/
      session_{n}.json  # Session history
    state/
      world_state.json  # Current world state
      turn_log.json     # Turn-by-turn changes
```

### Entity Schema (Example: Character)

```json
{
  "id": "char_001",
  "type": "character",
  "name": "Marcus Ashford",
  "aliases": ["The Merchant", "Old Ash"],
  "created_turn": 1,
  "modified_turn": 5,
  "is_pc": false,

  "physical": {
    "appearance": "Weathered face, deep-set grey eyes, salt-and-pepper beard",
    "build": "Tall, once-powerful frame now slightly stooped",
    "capability": {
      "strength": "diminished",
      "agility": "average",
      "health": "chronic back pain",
      "limitations": ["poor night vision", "arthritic hands"]
    }
  },

  "psychology": {
    "wants": {
      "immediate": "Close the deal with the northern traders",
      "long_term": "Secure his daughter's future before he dies"
    },
    "fears": ["dying in poverty", "his past catching up"],
    "wounds": ["betrayed by former partner", "lost his wife to plague"],
    "blindspots": ["trusts anyone who flatters him", "underestimates women"],
    "voice": {
      "patterns": ["speaks slowly, deliberately", "uses merchant metaphors"],
      "habits": ["strokes beard when lying", "avoids eye contact when sincere"],
      "expressions": ["A fair trade benefits all parties", "Trust is expensive"]
    }
  },

  "information_state": {
    "knows": ["PC helped save his shipment", "the northern pass is blocked"],
    "believes": ["his daughter is safe at the academy"],
    "suspects": ["someone is sabotaging his business"]
  },

  "tags": ["merchant", "quest_giver", "morally_grey"]
}
```

---

## API Design

### Core Endpoints

```
POST /campaigns                    # Create new campaign
GET  /campaigns/{id}               # Get campaign state
POST /campaigns/{id}/generate      # Generate/expand entities

POST /sessions                     # Start new session
POST /sessions/{id}/turn           # Process player turn
GET  /sessions/{id}/state          # Get current world state

GET  /bible/{campaign_id}/entities # List all entities
POST /bible/{campaign_id}/entities # Add entity
GET  /bible/{campaign_id}/entities/{id}
PUT  /bible/{campaign_id}/entities/{id}

GET  /bible/{campaign_id}/relationships
POST /bible/{campaign_id}/relationships
```

---

## Technology Stack

- **Language**: Python 3.11+
- **LLM**: Anthropic Claude API (Sonnet for Storyteller, Haiku for Archivist)
- **Storage**: SQLite + JSON files (simple, portable)
- **API**: FastAPI (async, modern, auto-docs)
- **CLI**: Rich + Typer (beautiful terminal interface)
- **Frontend**: (Future) React + TypeScript

---

## Future Enhancements

1. **Relationship Graph Visualization** - Interactive entity relationship browser
2. **Voice Consistency Checker** - Ensure NPC dialogue matches their voice profile
3. **Timeline View** - Visual timeline of events and state changes
4. **Import from Other Systems** - D&D, World Anvil, etc.
5. **Multiplayer Support** - Multiple PCs with separate knowledge states
6. **Memory Compression** - Summarize old turns to manage context window
