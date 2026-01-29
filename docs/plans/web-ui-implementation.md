# CC-Storyteller: Web UI Implementation Plan

## User Decisions (Confirmed)

1. **Config storage**: Separate `config.yaml` file (not .env for non-secrets)
2. **Settings scope**: MVP + advanced dropdown (defaults, debug, paths)
3. **UI direction**: **Full SPA with Svelte** - most powerful option
4. **Architecture**: Separated frontend/backend (FastAPI + Svelte SPA)
5. **Deployment**: Flexible - local-first but cloud/SaaS ready
6. **Theme system**: Built from start with CSS variables, begin with one "Chronicle" theme
7. **TUI**: Keep existing for later as alternative interface option

---

## Chosen Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              SPA (React/Vue/Svelte)                   │  │
│  │  - Theme system (CSS variables)                       │  │
│  │  - Settings UI                                        │  │
│  │  - Campaign management                                │  │
│  │  - Gameplay (Chronicle)                               │  │
│  │  - Entity browser (Codex)                             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ REST API / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Routes    │ │   Services  │ │   Storage   │           │
│  │  /api/...   │ │  (existing) │ │  Abstraction│           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Anthropic│   │  OpenAI  │   │  Ollama  │
        │   API    │   │   API    │   │  Local   │
        └──────────┘   └──────────┘   └──────────┘
```

---

## Theme/Skin System Design

### CSS Custom Properties Approach
```css
:root {
  --primary-bg: #1a1410;      /* Parchment dark */
  --primary-text: #d4c4a8;    /* Aged paper */
  --accent: #8b7355;          /* Leather brown */
  --border: #3d3429;          /* Worn edge */
  --font-display: 'Cinzel';   /* Medieval display */
  --font-body: 'Crimson Pro'; /* Readable serif */
}

[data-theme="eldritch"] {
  --primary-bg: #0d0d1a;
  --accent: #4a0080;
  /* ... */
}
```

### Theme Components
- Color palette (backgrounds, text, accents)
- Typography (display font, body font)
- Decorative elements (borders, dividers, icons)
- Optional: Background textures, custom scrollbars

### AI-Generated Elements (Future)
- Generate themed icons/decorations per campaign genre
- Create custom "illuminated manuscript" borders
- Generate thematic loading screens
- **Note**: This is enhancement, not MVP

---

## Config File Format

### config.yaml (non-secrets)
```yaml
# Provider configuration per role
providers:
  storyteller:
    type: anthropic       # anthropic, openai, ollama, local
    model: claude-sonnet-4-20250514
  archivist:
    type: anthropic
    model: claude-sonnet-4-20250514

# Local model settings
local:
  url: http://localhost:11434
  type: ollama            # ollama, llamacpp, lmstudio, vllm

# Paths
paths:
  data_dir: ~/.cc-storyteller
  campaigns_dir: campaigns

# UI preferences
ui:
  theme: chronicle

# Debug settings (advanced)
debug:
  enabled: false
  log_prompts: false
  log_responses: false
```

### .env (secrets only)
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

---

## Streaming Support

Add `generate_stream()` to providers for real-time narrative display:

```python
# In providers/base.py
async def generate_stream(
    self,
    messages: list[ChatMessage],
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Yield text chunks as they arrive."""
    ...
```

WebSocket endpoint streams chunks to frontend:
```
WS /api/sessions/{id}/stream
← {"type": "chunk", "text": "The door creaks..."}
← {"type": "chunk", "text": " open slowly."}
← {"type": "done", "tokens_used": 150}
```

---

## Implementation Phases

### Phase 1: Foundation (Current Focus)

**Backend (FastAPI)**
1. Create `src/storyteller/api/` package structure
2. Implement core API routes:
   - `GET/POST /api/settings` - Read/write config
   - `POST /api/settings/test-provider` - Test LLM connection
   - `GET /api/campaigns` - List campaigns
   - `GET /api/providers` - List available providers
3. Add WebSocket endpoint for streaming LLM responses
4. Create `config.yaml` loader (separate from .env secrets)

**Frontend (Svelte)**
1. Initialize Svelte project in `frontend/` directory
2. Set up theme system with CSS custom properties
3. Create Settings page with provider configuration UI
4. Implement connection test functionality

### Phase 1.5: Launcher Scripts & First-Run (Current Focus)

- Create install.bat/sh with prerequisite checking
- Create start.bat/sh with auto-browser-open
- Configure FastAPI to serve built frontend static files
- Add first-run setup wizard at `/setup`
- Add setup status API endpoint

### Phase 2: Feature Parity

- Port Chronicle (gameplay) screen to web
- Port Codex (entity browser) to web
- Add relationship graph visualization (D3.js or similar)

### Phase 3: Enhancements

- Additional themes
- Advanced visualizations
- AI-generated UI elements (future)

---

## File Structure

```
CC-Storyteller/
├── src/storyteller/
│   ├── api/                    # FastAPI backend (NEW)
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI app entry point
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── campaigns.py    # Campaign CRUD
│   │   │   ├── sessions.py     # Gameplay sessions + WebSocket
│   │   │   ├── settings.py     # Config management
│   │   │   └── codex.py        # Entity Bible API
│   │   ├── deps.py             # Dependency injection
│   │   └── schemas.py          # Pydantic request/response models
│   ├── config_loader.py        # YAML config loader (NEW)
│   ├── providers/              # (existing - add streaming)
│   ├── agents/                 # (existing)
│   ├── bible/                  # (existing)
│   └── gui/                    # (existing TUI - preserved)
├── frontend/                   # Svelte SPA (NEW)
│   ├── src/
│   │   ├── App.svelte
│   │   ├── main.js
│   │   ├── lib/
│   │   │   ├── api.js          # API client
│   │   │   ├── stores.js       # Svelte stores
│   │   │   └── theme.js        # Theme management
│   │   ├── routes/
│   │   │   ├── Settings.svelte
│   │   │   ├── Campaigns.svelte
│   │   │   ├── Chronicle.svelte
│   │   │   └── Codex.svelte
│   │   └── components/
│   │       ├── ProviderConfig.svelte
│   │       └── ThemeSelector.svelte
│   ├── static/
│   │   └── themes/
│   │       └── chronicle.css   # Default "Chronicle" theme
│   ├── package.json
│   └── vite.config.js
├── config.yaml                 # User config (non-secrets)
├── .env                        # Secrets only (API keys)
└── pyproject.toml              # (existing - add deps)
```

---

## API Routes Specification

### Settings (`/api/settings`)
```
GET  /api/settings              # Get current config
POST /api/settings              # Update config
POST /api/settings/test         # Test provider connection
GET  /api/providers             # List available provider types
GET  /api/providers/{type}/models  # List models for provider
```

### Campaigns (`/api/campaigns`)
```
GET    /api/campaigns           # List all campaigns
POST   /api/campaigns           # Create campaign
GET    /api/campaigns/{id}      # Get campaign details
DELETE /api/campaigns/{id}      # Delete campaign
```

### Sessions (`/api/sessions`)
```
POST   /api/sessions            # Start new session
GET    /api/sessions/{id}       # Get session state
WS     /api/sessions/{id}/stream  # WebSocket for gameplay
```

### Codex (`/api/codex`)
```
GET    /api/codex/{campaign}/entities      # List entities
GET    /api/codex/{campaign}/entities/{id} # Get entity
GET    /api/codex/{campaign}/relationships # Get relationship graph
```

---

## Critical Files to Modify

### Existing files:
- `pyproject.toml` - Add fastapi, uvicorn, pyyaml dependencies
- `src/storyteller/providers/base.py` - Add `generate_stream()` method
- `src/storyteller/cli.py` - Add `serve` command

### New files (Phase 1):
- `src/storyteller/api/app.py` - FastAPI application
- `src/storyteller/api/routes/settings.py` - Settings endpoints
- `src/storyteller/config_loader.py` - YAML config management
- `frontend/` - Entire Svelte project

---

## Launcher Scripts (Phase 1.5)

### Goal
Make the app user-friendly with simple batch/shell scripts. Users run one script to install, one to start.

### Architecture Change
- Build Svelte frontend to static files (`npm run build` → `frontend/dist/`)
- FastAPI serves static files directly
- **Single server** - users just run `start.bat` and open browser

### Scripts to Create

```
scripts/
├── install.bat          # Windows installer
├── install.sh           # Linux/Mac installer
├── start.bat            # Windows launcher
├── start.sh             # Linux/Mac launcher
└── dev.bat / dev.sh     # Development mode (optional)
```

### install.bat / install.sh
1. **Check prerequisites**
   - Python 3.10+ installed? If not, show download link
   - Node.js 18+ installed? If not, show download link
2. **Create virtual environment**
   - `python -m venv .venv`
3. **Install Python dependencies**
   - `.venv\Scripts\pip install -e .`
4. **Install Node dependencies**
   - `cd frontend && npm install`
5. **Build frontend**
   - `npm run build`
6. **Create .env template** (if not exists)
   - Copy `.env.example` to `.env`
7. **Success message**
   - "Installation complete! Run start.bat to launch."

### start.bat / start.sh
1. **Activate venv**
2. **Check if first run** (no API keys configured)
   - If first run, open browser to `/setup` (first-run wizard)
   - Otherwise, open browser to `/`
3. **Start server**
   - `storyteller serve --host 127.0.0.1 --port 8000`
4. **Open browser automatically**
   - Windows: `start http://localhost:8000`
   - Linux/Mac: `xdg-open` / `open`

### First-Run Setup Wizard
**Purpose:** Technical setup only (not campaign creation)

**Route:** `/setup` (redirects here if no API keys configured)

**Steps:**
1. **Welcome** - Brief intro to CC-Storyteller
2. **Provider Selection** - Choose primary provider (Anthropic/OpenAI/Ollama)
3. **API Key Entry** - Enter key, with "Get API Key" links
4. **Connection Test** - Verify it works
5. **Model Selection** - Choose models for Storyteller/Archivist roles
6. **Complete** - "Setup complete! Start your first chronicle."

**Technical:** Wizard saves to `.env` (secrets) and `config.yaml` (preferences)

### Files to Modify

**Backend:**
- `src/storyteller/api/app.py` - Add static file serving from `frontend/dist/`
- `src/storyteller/api/routes/settings.py` - Add `/api/setup/status` endpoint

**Frontend:**
- `frontend/src/routes/Setup.svelte` - New first-run wizard component
- `frontend/src/App.svelte` - Add `/setup` route
- `frontend/vite.config.js` - Configure build output

---

## Verification Plan

After Phase 1:
1. Run `storyteller serve` to start web server
2. Open browser to `http://localhost:8000`
3. Navigate to Settings, configure provider (Anthropic API key)
4. Click "Test Connection", verify success/error feedback
5. Save settings, restart server, verify persistence in `config.yaml`
6. Verify "Chronicle" theme renders correctly
7. Check API endpoints work: `curl http://localhost:8000/api/settings`

After Phase 1.5 (Launcher Scripts):
1. Run `install.bat` on fresh system - verify prerequisites check works
2. Run `start.bat` - verify server starts and browser opens
3. On first run, verify redirect to `/setup` wizard
4. Complete wizard, verify `.env` and `config.yaml` created
5. Restart with `start.bat` - verify goes to home page (not setup)
