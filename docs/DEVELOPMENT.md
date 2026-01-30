# CC-Storyteller Development Guide

> **For AI Assistants**: This document is your primary reference when working on this project.
> Read this file FIRST before making any changes. Update it when you complete features or make architectural decisions.

---

## How to Use This Document

### Starting a New Session
1. **Read this entire file** to understand project state and architecture
2. **Check the Feature Status** section to see what's done, in progress, or pending
3. **Review Recent Changes** to understand recent modifications
4. **Check the Current Sprint** for active priorities

### During Development
- Update feature status checkboxes as you work
- Add entries to the changelog when completing features
- Document any architectural decisions in the Decisions Log
- Note any blockers or issues in the Known Issues section

### Ending a Session
1. Update feature checkboxes to reflect current state
2. Add changelog entries for completed work
3. Document any incomplete work in "Handoff Notes"
4. Commit this file with your other changes

### Using Plan Files
For complex features, create detailed plans in `docs/plans/`:
1. Create a new file: `docs/plans/<feature-name>.md`
2. Document architecture decisions, API designs, implementation steps
3. Reference the plan file from Feature Status section below
4. Keep plans updated as implementation progresses

**Existing Plans:**
| Plan File | Covers |
|-----------|--------|
| [`web-ui-implementation.md`](plans/web-ui-implementation.md) | Phases 1, 1.5, 2, 3 - Web UI architecture |

---

## Project Overview

**CC-Storyteller** is an LLM-powered narrative simulation engine for deep roleplaying experiences.

### Core Concept
- **Dual-agent architecture**: Storyteller (creative narrative) + Archivist (logic/data)
- **Entity Bible**: Track NPCs, items, locations, factions, lore with relationship links
- **World simulation**: NPCs with fog-of-war, autonomous actions, psychological profiles
- **Turn-indexed state**: All changes tracked with `{T: N}` notation

### Tech Stack
| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, FastAPI, Pydantic |
| Frontend | Svelte, Vite |
| LLM Providers | Anthropic, OpenAI, Ollama (local) |
| Storage | JSON files (local), SQLite (planned) |
| CLI | Typer, Rich |
| TUI | Textual (preserved, not primary) |

### Project Structure
```
CC-Storyteller/
├── src/storyteller/
│   ├── api/                 # FastAPI backend
│   │   ├── app.py           # Main FastAPI application
│   │   ├── routes/          # API endpoints
│   │   │   ├── settings.py  # Settings + Setup wizard API
│   │   │   ├── campaigns.py # Campaign CRUD
│   │   │   ├── sessions.py  # Gameplay + WebSocket
│   │   │   └── codex.py     # Entity Bible API
│   │   ├── deps.py          # Dependency injection
│   │   └── schemas.py       # Pydantic models
│   ├── agents/              # LLM agents
│   │   ├── storyteller.py   # Narrative generation
│   │   ├── archivist.py     # Data extraction
│   │   └── base.py          # Base agent class
│   ├── bible/               # Entity Bible system
│   │   └── entity_bible.py  # Graph-based entity management
│   ├── generation/          # Campaign generation
│   │   └── campaign_generator.py
│   ├── models/              # Data models
│   │   ├── entities.py      # Character, Location, Item, etc.
│   │   ├── relationships.py # Entity relationships
│   │   ├── campaign.py      # Campaign model
│   │   └── session.py       # Session model
│   ├── providers/           # LLM provider abstraction
│   │   ├── base.py          # Abstract provider interface
│   │   ├── anthropic_provider.py
│   │   ├── openai_compatible.py
│   │   ├── ollama_provider.py
│   │   └── registry.py      # Provider registration
│   ├── session/             # Gameplay session management
│   │   └── session_manager.py
│   ├── gui/                 # Textual TUI (preserved)
│   ├── cli.py               # CLI commands
│   ├── config.py            # Settings (pydantic-settings)
│   └── config_loader.py     # YAML config management
├── frontend/                # Svelte SPA
│   ├── src/
│   │   ├── App.svelte       # Main app with routing
│   │   ├── lib/
│   │   │   ├── api.js       # API client
│   │   │   └── stores.js    # Svelte stores
│   │   ├── routes/
│   │   │   ├── Home.svelte
│   │   │   ├── Settings.svelte
│   │   │   ├── Campaigns.svelte
│   │   │   ├── Chronicle.svelte  # Gameplay
│   │   │   ├── Codex.svelte      # Entity browser
│   │   │   └── Setup.svelte      # First-run wizard
│   │   └── components/
│   ├── static/themes/       # CSS theme files
│   └── package.json
├── scripts/                 # User-facing scripts
│   ├── install.bat/sh       # Installation
│   └── start.bat/sh         # Launch app
├── docs/
│   ├── DEVELOPMENT.md       # THIS FILE - start here
│   └── plans/               # Detailed feature plans
│       └── web-ui-implementation.md  # Web UI phases 1-3
└── pyproject.toml
```

---

## Feature Status

### Phase 1: Foundation ✅ COMPLETE
> 📄 **Plan:** [`web-ui-implementation.md`](plans/web-ui-implementation.md)

- [x] FastAPI backend structure
- [x] API routes (settings, campaigns, codex, sessions)
- [x] Pydantic schemas for API
- [x] config_loader.py for YAML config
- [x] Svelte frontend scaffold
- [x] Theme system (CSS custom properties)
- [x] Chronicle theme implemented
- [x] Settings page with provider config
- [x] Campaigns page
- [x] Chronicle (gameplay) page
- [x] Codex (entity browser) page
- [x] WebSocket endpoint for streaming

### Phase 1.5: Launcher Scripts ✅ COMPLETE
> 📄 **Plan:** [`web-ui-implementation.md`](plans/web-ui-implementation.md#launcher-scripts-phase-15)

- [x] install.bat with Python/Node detection
- [x] install.sh for Linux/Mac
- [x] start.bat with auto-browser-open
- [x] start.sh for Linux/Mac
- [x] FastAPI serves built frontend (frontend/dist/)
- [x] First-run setup wizard (/setup route)
- [x] Setup status API endpoint
- [x] API key save endpoint

### Phase 2: Feature Parity 🔄 IN PROGRESS
> 📄 **Plan:** [`web-ui-implementation.md`](plans/web-ui-implementation.md#phase-2-feature-parity)

- [ ] Streaming LLM responses (generate_stream in providers)
- [ ] Real WebSocket streaming in Chronicle
- [ ] Relationship graph visualization (D3.js)
- [ ] Campaign import from notes
- [ ] Creativity sliders for generation

### Phase 3: Enhancements 📋 PLANNED
> 📄 **Plan:** [`web-ui-implementation.md`](plans/web-ui-implementation.md#phase-3-enhancements)

- [ ] Additional themes (Eldritch, etc.)
- [ ] AI-generated UI elements
- [ ] Advanced entity editing in Codex
- [ ] Session history/replay
- [ ] Export campaigns

### Infrastructure 📋 PLANNED
- [ ] SQLite storage backend
- [ ] User authentication (for SaaS)
- [ ] Multi-tenant support
- [ ] Docker deployment

---

## Recent Changes (Changelog)

### 2026-01-30
- **fix**: Keep install.bat window open on errors (cmd /k wrapper)
- **fix**: Improve Python detection in install.bat (try py, python, python3)
- **feat**: Add launcher scripts (install.bat/sh, start.bat/sh)
- **feat**: Add first-run setup wizard at /setup
- **feat**: FastAPI serves built frontend from frontend/dist/
- **feat**: Add setup status and API key save endpoints
- **docs**: Add Phase 1.5 launcher scripts plan

### 2026-01-29 (Initial Implementation)
- **feat**: Implement Phase 1 web UI - FastAPI backend + Svelte frontend
- **feat**: Add provider abstraction layer (Anthropic, OpenAI, Ollama)
- **feat**: Create Entity Bible system
- **feat**: Implement Storyteller and Archivist agents
- **feat**: Add CLI with new, play, list, bible, config commands
- **feat**: Create Textual TUI (preserved for later)

---

## Architecture Decisions

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-30 | Svelte over React | Smaller bundle, better streaming, simpler state |
| 2026-01-30 | Separate config.yaml and .env | Security (keys in .env), preferences in YAML |
| 2026-01-30 | FastAPI serves frontend | Single server for users, simpler deployment |
| 2026-01-29 | Dual-agent architecture | Separation of concerns: creative vs analytical |
| 2026-01-29 | Provider abstraction | Support multiple LLM backends uniformly |

### Key Patterns

**Provider Pattern**: All LLM providers implement `LLMProvider` interface
```python
class LLMProvider(ABC):
    async def generate(self, messages, max_tokens, temperature) -> LLMResponse
    async def generate_stream(self, messages, max_tokens) -> AsyncIterator[str]
    async def check_health(self) -> tuple[bool, str]
```

**Config Pattern**: Two-file config system
- `.env` - Secrets only (API keys)
- `config.yaml` - All other preferences (loaded by config_loader.py)

**API Pattern**: RESTful with WebSocket for streaming
- `/api/settings` - Config management
- `/api/campaigns` - Campaign CRUD
- `/api/sessions` - Gameplay (POST /turn for sync, WS for stream)
- `/api/codex/{campaign_id}` - Entity Bible

---

## API Reference

### Settings
```
GET  /api/settings              # Get current config
POST /api/settings              # Update config
POST /api/settings/test         # Test provider connection
GET  /api/settings/providers    # List available providers
```

### Setup (First-Run)
```
GET  /api/setup/status          # Check if configured
POST /api/setup/api-key         # Save API key to .env
```

### Campaigns
```
GET    /api/campaigns           # List all
POST   /api/campaigns           # Create new
GET    /api/campaigns/{id}      # Get details
DELETE /api/campaigns/{id}      # Delete
```

### Sessions
```
POST   /api/sessions            # Start session
GET    /api/sessions/{id}       # Get state
POST   /api/sessions/{id}/turn  # Process turn (sync)
WS     /api/sessions/{id}/stream # WebSocket streaming
POST   /api/sessions/{id}/save  # Save session
DELETE /api/sessions/{id}       # End session
```

### Codex
```
GET /api/codex/{campaign}/entities      # List entities
GET /api/codex/{campaign}/entities/{id} # Get entity
GET /api/codex/{campaign}/relationships # Get graph
GET /api/codex/{campaign}/stats         # Get statistics
```

---

## Theme System

Themes use CSS custom properties defined in `frontend/src/app.css`:

```css
:root {
  --color-bg-primary: #1a1410;
  --color-bg-secondary: #241d17;
  --color-text-primary: #d4c4a8;
  --color-accent-primary: #8b7355;
  --font-display: 'Cinzel', serif;
  --font-body: 'Crimson Pro', serif;
  /* ... more variables */
}

[data-theme="eldritch"] {
  --color-bg-primary: #0d0d1a;
  /* ... override variables */
}
```

To add a new theme:
1. Add CSS variables in `app.css` under `[data-theme="themename"]`
2. Add option in Settings.svelte theme selector
3. Theme is applied via `document.documentElement.setAttribute('data-theme', theme)`

---

## Testing Checklist

### After Backend Changes
- [ ] `curl http://localhost:8000/health` returns healthy
- [ ] `curl http://localhost:8000/api/settings` returns config
- [ ] Provider test endpoint works with valid API key

### After Frontend Changes
- [ ] `npm run build` succeeds in frontend/
- [ ] App loads at http://localhost:8000
- [ ] Navigation works between all pages
- [ ] Theme applies correctly

### After Script Changes
- [ ] install.bat/sh runs on clean system
- [ ] Prerequisites check shows helpful errors
- [ ] start.bat/sh launches server and opens browser
- [ ] First-run redirects to /setup

---

## Known Issues

| Issue | Severity | Workaround |
|-------|----------|------------|
| WebSocket streaming not implemented | Medium | Uses chunked REST fallback |
| generate_stream not in providers | Medium | Falls back to generate() |
| No input validation on campaign creation | Low | None |

---

## Handoff Notes

*Use this section to document incomplete work for the next session*

### Current State
- Phase 1 and 1.5 complete
- Launcher scripts working (Windows tested)
- Setup wizard implemented but not fully tested end-to-end

### Next Priority
1. Test full install → setup → play flow on Windows
2. Implement `generate_stream()` in providers
3. Wire up real WebSocket streaming in Chronicle

### Blocked On
- Nothing currently blocked

### Questions for User
- None pending

---

## Naming Conventions

### Literary Theme (User-Facing)
| Internal | User-Facing |
|----------|-------------|
| Home page | Hall of Chronicles |
| Campaign | Chronicle |
| Entity Bible | Codex |
| Campaign creation | Scriptorium |
| Storyteller agent | The Storyteller |
| Archivist agent | The Archivist |

### Code Style
- Python: snake_case, type hints everywhere
- Svelte: PascalCase components, camelCase functions
- CSS: kebab-case with BEM-like patterns
- API: snake_case in JSON

---

## Quick Commands

```bash
# Development
cd frontend && npm run dev          # Start Vite dev server
storyteller serve --reload          # Start FastAPI with reload

# Production
./scripts/install.sh                # Full installation
./scripts/start.sh                  # Launch app

# Testing
curl http://localhost:8000/health   # Health check
curl http://localhost:8000/api      # API info

# Building
cd frontend && npm run build        # Build frontend
pip install -e .                    # Install Python package
```

---

## File Quick Reference

| Need to... | File(s) |
|------------|---------|
| Add API endpoint | `src/storyteller/api/routes/` |
| Add API schema | `src/storyteller/api/schemas.py` |
| Modify config options | `src/storyteller/config_loader.py` |
| Add frontend route | `frontend/src/App.svelte` + `frontend/src/routes/` |
| Add API client method | `frontend/src/lib/api.js` |
| Modify theme colors | `frontend/src/app.css` |
| Add LLM provider | `src/storyteller/providers/` |
| Modify entity types | `src/storyteller/models/entities.py` |
| Change CLI commands | `src/storyteller/cli.py` |

---

*Last updated: 2026-01-30 by Claude*
