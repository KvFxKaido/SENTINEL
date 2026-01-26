# SENTINEL Agent

[![CI](https://github.com/KvFxKaido/SENTINEL/actions/workflows/ci.yml/badge.svg)](https://github.com/KvFxKaido/SENTINEL/actions/workflows/ci.yml)

AI Game Master for [SENTINEL](../core/SENTINEL%20Playbook%20—%20Core%20Rules.md), a tactical TTRPG about navigating political tension, ethical tradeoffs, and survival under fractured systems.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the CLI
python -m src.interface.cli
```

## LLM Backends

SENTINEL supports both local and cloud backends.

### Local Backends (Recommended)

#### LM Studio
1. Download [LM Studio](https://lmstudio.ai/)
2. Load a model (Mistral, Llama, Qwen recommended)
3. Start the local server (Server tab)
4. Run the CLI — it auto-detects LM Studio at localhost:1234

#### Ollama
1. Install [Ollama](https://ollama.ai/)
2. Pull a model: `ollama pull llama3.2`
3. Ollama runs automatically after install
4. Run the CLI — it auto-detects Ollama at localhost:11434

### Cloud Backends: Gemini CLI, Codex CLI & Claude Code

All cloud backends work the same way: we invoke the official CLI tools and let them handle authentication through your existing subscription.

| Backend | Install | Switch Command |
|---------|---------|----------------|
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | See GitHub for install | `/backend gemini` |
| [Codex CLI](https://github.com/openai/codex) | `npm i -g @openai/codex` | `/backend codex` |
| [Claude Code](https://claude.ai/code) | Download from website | `/backend claude` |
| [Kimi CLI](https://github.com/MoonshotAI/kimi-cli) | `pip install kimi-cli` | `/backend kimi` |
| [Mistral Vibe](https://github.com/mistralai/mistral-vibe) | `pip install mistral-vibe` | `/backend vibe` |

**No API keys needed.** If you're logged into the CLI, SENTINEL just works — using whatever plan you're already paying for (Gemini Pro, ChatGPT Plus, Claude Pro, etc.).

#### Gemini CLI Features
- **1M token context** — Can hold entire campaigns in memory
- **Free tier available** — 60 requests/minute, 1000/day
- **Native MCP support** — Can use sentinel-campaign tools directly
- **GEMINI.md context** — Auto-reads project context for GM role

#### Codex CLI Features
- **Agentic capabilities** — Built for autonomous operation
- **Model selection** — o3, gpt-4o, gpt-4o-mini
- **Sandbox modes** — read-only, workspace-write, full-access
- **AGENTS.md context** — Auto-reads project context for GM role

#### Claude Code Features
- **Best narrative quality** — Excels at NPC interactions, faction politics
- **Model selection** — `/model sonnet`, `/model opus`, `/model haiku`
- **Long-term memory** — Remembers details across sessions

#### Kimi CLI Features
- **32K-128K context** — moonshot-v1-32k (default), moonshot-v1-128k available
- **Moonshot AI authentication** — Uses existing Kimi CLI login
- **Chinese language support** — Native bilingual capabilities

#### Mistral Vibe Features
- **Agentic capabilities** — Built for autonomous coding tasks
- **Codestral models** — Code-optimized Mistral models
- **Auto-approve mode** — Non-interactive operation for GM use

### Backend Detection

The agent auto-detects backends in this order:
1. **LM Studio** (localhost:1234) — free, local, native tool support
2. **Ollama** (localhost:11434) — free, local, native tool support
3. **Gemini CLI** — free tier, 1M context, native MCP support
4. **Codex CLI** — agentic, uses your existing OpenAI authentication
5. **Claude Code CLI** — uses your existing Anthropic authentication
6. **Kimi CLI** — uses your existing Moonshot AI authentication
7. **Mistral Vibe CLI** — uses your existing Mistral AI authentication

Local backends are preferred for privacy, cost, and predictable context handling. Use `/backend <name>` to switch manually.

### Which Backend Should I Use?

| Priority | Recommendation |
|----------|----------------|
| Best narrative quality | Claude (via Claude Code) |
| Best agentic capability | Codex CLI (OpenAI o3/gpt-4o) |
| Free + huge context | Gemini CLI (1M tokens, 60 req/min free) |
| Free + private | LM Studio or Ollama with 14B+ model |
| Offline play | Local only |
| Potato PC | Claude, Codex, or Gemini (offload compute to cloud) |

Local models are fully playable — the mechanics work identically. Claude shines in nuanced NPC interactions, faction politics, and long-term consequence tracking. Think of it as a GM skill slider: local 7B models might forget context mid-scene, while Claude Opus will remember that throwaway comment you made three sessions ago and weave it into the plot.

## Architecture

```
sentinel-agent/
├── src/
│   ├── agent.py           # Main agent orchestration
│   ├── state/
│   │   ├── schema.py      # Pydantic models (Campaign, Character, NPC, etc.)
│   │   ├── manager.py     # Campaign lifecycle (create/load/save)
│   │   ├── wiki_adapter.py    # Obsidian wiki integration
│   │   ├── wiki_watcher.py    # Bi-directional sync (file watcher)
│   │   ├── templates.py       # Jinja2 template engine
│   │   └── memvid_adapter.py  # Optional semantic memory (memvid)
│   ├── llm/               # LLM backend abstraction
│   │   ├── base.py        # Abstract client interface
│   │   ├── lmstudio.py    # LM Studio backend
│   │   ├── ollama.py      # Ollama backend
│   │   ├── claude_code.py # Claude Code CLI backend
│   │   ├── gemini_cli.py  # Gemini CLI backend (1M context)
│   │   ├── codex_cli.py   # Codex CLI backend (OpenAI agentic)
│   │   ├── kimi.py        # Kimi CLI backend (Moonshot AI)
│   │   ├── mistral_vibe.py # Mistral Vibe CLI backend
│   │   └── skills.py      # Skill-based tool invocation for CLI backends
│   ├── context/           # Engine-owned context control
│   │   ├── packer.py      # Prompt packing with token budgets
│   │   ├── window.py      # Rolling window with priority trimming
│   │   ├── tokenizer.py   # Token counting (tiktoken + fallback)
│   │   └── digest.py      # Campaign memory compression
│   ├── tools/
│   │   └── dice.py        # Dice rolling with advantage/disadvantage
│   ├── lore/
│   │   ├── chunker.py     # Parse markdown → tagged chunks
│   │   ├── retriever.py   # Multi-directory keyword retrieval
│   │   └── unified.py     # Combined lore + wiki + campaign history
│   └── interface/
│       └── cli.py         # Rich-based CLI interface
├── prompts/
│   ├── core.md            # Agent identity and principles
│   ├── mechanics.md       # Compact rules reference
│   └── rules/             # Two-layer rules system
│       ├── core_logic.md      # Decision triggers (always loaded)
│       └── narrative_guidance.md  # Flavor (cut under strain)
├── campaigns/             # Saved game states (JSON)
└── tests/                 # Test suites
```

### Two-Layer Rules

Rules are split for survivable truncation under memory strain:

| Layer | Content | Behavior |
|-------|---------|----------|
| `core_logic.md` | If/then decision triggers | Always loaded, never cut |
| `narrative_guidance.md` | Flavor, examples, tone | Cut under Strain II+ |

When context pressure exceeds 85%, narrative guidance is dropped (~925 tokens saved) while core decision logic survives. The GM can still make correct decisions; it just loses the "how to phrase it beautifully" guidance.

## Obsidian Integration

SENTINEL auto-generates a campaign wiki as you play, designed for [Obsidian](https://obsidian.md/).

### What Gets Generated

| Content | Location | Trigger |
|---------|----------|---------|
| Session notes | `sessions/{date}/{date}.md` | `/debrief` command |
| Game log | `sessions/{date}/_game_log.md` | Live during play |
| NPC pages | `NPCs/{name}.md` | First encounter |
| Timeline | `_events.md` | Hinge moments, faction shifts |
| Index pages | `_index.md`, `NPCs/_index.md`, `sessions/_index.md` | `/debrief` |

### Features

- **Obsidian callouts** — Hinge moments, faction shifts, and threads render as styled callouts
- **Wikilinks** — NPCs, factions, and sessions are cross-linked automatically
- **Frontmatter** — All pages have YAML frontmatter for Dataview queries
- **Content separation** — Game log is separate from your notes (via transclusion)
- **Bi-directional sync** — Edit NPC disposition in Obsidian → game state updates
- **Custom templates** — Override any page template in `wiki/templates/`

### Setup

1. Point SENTINEL at your vault: set `wiki_dir` in config or use `--wiki` flag
2. Create a `canon/` folder with core lore (factions, locations, rules)
3. Campaign overlays go to `campaigns/{campaign_id}/`

### Directory Structure

```
your-vault/
├── canon/                    # Core lore (read-only reference)
│   ├── Factions/
│   ├── NPCs/
│   └── Locations/
├── campaigns/
│   └── {campaign_id}/        # Auto-generated per campaign
│       ├── _index.md         # Campaign MOC
│       ├── _events.md        # Timeline
│       ├── NPCs/
│       │   ├── _index.md     # NPC index by faction
│       │   └── {name}.md     # NPC overlay pages
│       └── sessions/
│           ├── _index.md     # Session index
│           └── {date}/
│               ├── {date}.md     # Session summary
│               └── _game_log.md  # Live updates
└── templates/                # Optional custom templates
```

Wiki features include live session updates, NPC page auto-creation, bi-directional sync, and Dataview-ready frontmatter. See `src/state/wiki_adapter.py` for implementation.

## CLI Commands

| Command | Description |
|---------|-------------|
| `/new <name>` | Create a new campaign |
| `/load` | Load an existing campaign |
| `/save` | Save current campaign |
| `/list` | List all campaigns |
| `/status` | Show current status |
| `/char` | Create a character |
| `/roll <skill> <dc>` | Roll a skill check |
| `/mission` | Start a new mission |
| `/backend [name]` | Show or switch LLM backend |
| `/model [name]` | Show or switch model |
| `/endgame` | View campaign readiness and status |
| `/endgame begin` | Begin epilogue (final session) |
| `/retire` | Graceful alias for `/endgame begin` |
| `/quit` | Exit the game |

## State Schema

All game state is stored as versioned JSON files:

- **Campaign** — The root container
- **Character** — Player characters with background, gear, social energy
- **NPC** — Non-player characters with agendas and memory
- **FactionStanding** — Reputation with each of the eleven factions
- **DormantThread** — Delayed consequences waiting to trigger
- **HistoryEntry** — Chronicle and canon records
- **EndgameReadiness** — Multi-factor score tracking campaign conclusion readiness

## Tools

The agent has access to these tools:

| Tool | Description |
|------|-------------|
| `roll_check` | d20 + modifier vs DC |
| `tactical_reset` | Spend social energy for advantage |
| `update_character` | Modify credits, social energy |
| `update_faction` | Shift faction standing |
| `log_hinge_moment` | Record irreversible choice |
| `queue_dormant_thread` | Schedule delayed consequence |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## MVP Status

### Phase 1: Playable Single Session
- [x] State schema with versioning
- [x] Core tools: roll_check, update_character, update_faction
- [x] NPC structure with agendas
- [x] Prompt loader with hot-reload
- [x] 50-line mechanical reference
- [x] CLI interface
- [x] NPC memory triggers and disposition modifiers
- [x] Test suite (380 tests)
- [x] CI/CD with GitHub Actions
- [ ] One complete mission playable end-to-end
- [ ] 3 golden transcripts for regression

### Phase 2: Campaign Continuity
- [x] Full tool suite (chronicle, dormant threads, leverage)
- [x] Save/load with migration support
- [x] NPC memory across sessions
- [x] Dormant thread triggering
- [x] Obsidian wiki integration (auto-generated campaign notes)
- [x] Bi-directional sync (wiki edits update game state)
- [x] Endgame system (readiness tracking, epilogue sessions)
- [ ] Between-missions phase
- [ ] 10 golden transcripts
- [ ] Boundary test suite

### Phase 3: Polish
- [ ] Mission generator from templates
- [ ] Faction AI (proactive demands)
- [ ] Discord interface
- [ ] Multiplayer state management

## License

CC BY-NC 4.0
