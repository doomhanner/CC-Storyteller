# CC-Storyteller

LLM-powered narrative simulation engine for deep roleplaying sessions with robust world-simulation logic.

## Features

- **Dual-Agent Architecture**: Storyteller for creative narrative, Archivist for data and logic
- **Entity Bible**: Track all characters, locations, items, factions, and lore with relationships
- **World Simulation**: NPCs act on their own motivations with fog-of-war information boundaries
- **Campaign Generation**: Create rich campaigns from minimal descriptions or detailed notes
- **Creativity Sliders**: Control how much the AI elaborates on your input
- **Turn-Indexed State**: Track all changes by turn number for consistency

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/CC-Storyteller.git
cd CC-Storyteller

# Install with pip
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and add your Anthropic API key:

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

### The Chronicle (GUI)

Launch the graphical terminal interface:

```bash
chronicle
```

This opens **The Chronicle**, a beautiful terminal UI featuring:
- **Hall of Chronicles**: Browse and select your campaigns
- **The Scriptorium**: Guided campaign creation wizard
- **The Codex**: Browse the Entity Bible (characters, locations, items, factions, lore)
- **Chronicle View**: Main gameplay screen with narrative display

### CLI Commands

For command-line usage:

```bash
# Create a new campaign (interactive wizard)
storyteller new

# Create with options
storyteller new --name "Dark Fantasy" --creativity 0.7

# List campaigns
storyteller list

# Play a specific campaign
storyteller play <campaign_id>

# View Entity Bible
storyteller bible <campaign_id>
storyteller bible <campaign_id> --type character
```

## Input Syntax

During play, use these formats:

| Format | Meaning |
|--------|---------|
| Plain text | Actions and attempts |
| "Quotes" | Spoken dialogue (audible to NPCs) |
| *Asterisks* | Internal thoughts (private) |
| ((Parentheses)) | OOC commands |
| // | Advance world autonomously |

### OOC Commands

- `((status))` - View PC status
- `((inventory))` - View inventory
- `((recap))` - Get story recap
- `((npcs))` - View present NPCs
- `((threads))` - View plot threads
- `((time))` - View current time
- `((save))` - Save game
- `((help))` - Show help

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

### Key Components

- **Storyteller Agent**: Creative narrative generation
- **Archivist Agent**: Data extraction, feasibility checks, world simulation
- **Entity Bible**: Graph-based entity and relationship management
- **Session Manager**: Turn processing and state persistence

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/storyteller

# Linting
ruff check src/
```

## License

MIT
