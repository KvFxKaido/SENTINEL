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

SENTINEL runs on local LLM backends. Hosted-API support is planned as a follow-up.

### LM Studio
1. Download [LM Studio](https://lmstudio.ai/)
2. Load a model (Mistral, Llama, Qwen recommended)
3. Start the local server (Server tab)
4. Run the CLI — it auto-detects LM Studio at localhost:1234

### Ollama
1. Install [Ollama](https://ollama.ai/)
2. Pull a model: `ollama pull llama3.2`
3. Ollama runs automatically after install
4. Run the CLI — it auto-detects Ollama at localhost:11434

### Backend Detection

The agent auto-detects backends in this order:
1. **LM Studio** (localhost:1234) — free, local, native tool support
2. **Ollama** (localhost:11434) — free, local, native tool support

Use `/backend <name>` to switch manually (`lmstudio`, `ollama`, `auto`).

### Model Sizing

Local models are fully playable — the mechanics work identically. Larger models (14B+) hold context better across long campaigns and produce richer NPC voicing; smaller models (7B-12B) work well with `--local` mode, which trims prompts and uses phase-specific tool subsets.

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
│   │   └── skills.py      # Skill-based tool invocation (fallback for models without native tools)
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
