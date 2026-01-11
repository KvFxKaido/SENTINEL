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

### Cloud Backend: Claude Code

If you have [Claude Code](https://claude.ai/code) installed and authenticated, SENTINEL can use it as a backend.

```bash
# In the SENTINEL CLI
/backend claude
/model sonnet   # or opus, haiku
```

**How it works:** We invoke the `claude` CLI in print mode (`claude -p "prompt"`), which is a documented, intended use of the tool. No OAuth tokens are extracted, no credentials are stolen, no terms of service are violated. If you're logged into Claude Code, it just works — the same way any CLI tool uses your existing authentication.

This is explicitly *not* an exploit. We're using the CLI the way it was designed to be used.

**Why this matters:** Some projects have extracted OAuth tokens from other tools to make unauthorized API calls. We don't do that. We simply shell out to the official CLI and let it handle authentication through its normal channels.

### Backend Detection

The agent auto-detects backends in this order:
1. **LM Studio** (localhost:1234) — free, local, native tool support
2. **Ollama** (localhost:11434) — free, local, native tool support
3. **Claude Code CLI** — uses your existing authentication

Local backends are preferred for privacy, cost, and predictable context handling. Use `/backend <name>` to switch manually.

### Which Backend Should I Use?

| Priority | Recommendation |
|----------|----------------|
| Best narrative quality | Claude (via Claude Code) |
| Free + private | LM Studio or Ollama with 70B+ model |
| Offline play | Local only |
| Potato PC | Claude (offload compute to cloud) |

Local models are fully playable — the mechanics work identically. Claude shines in nuanced NPC interactions, faction politics, and long-term consequence tracking. Think of it as a GM skill slider: local 7B models might forget context mid-scene, while Claude Opus will remember that throwaway comment you made three sessions ago and weave it into the plot.

## Architecture

```
sentinel-agent/
├── src/
│   ├── agent.py           # Main agent orchestration
│   ├── state/
│   │   ├── schema.py      # Pydantic models (Campaign, Character, NPC, etc.)
│   │   ├── manager.py     # Campaign lifecycle (create/load/save)
│   │   └── memvid_adapter.py  # Optional semantic memory (memvid)
│   ├── llm/               # LLM backend abstraction
│   │   ├── base.py        # Abstract client interface
│   │   ├── lmstudio.py    # LM Studio backend
│   │   ├── ollama.py      # Ollama backend
│   │   ├── claude_code.py # Claude Code CLI backend
│   │   └── skills.py      # Skill-based tool invocation for CLI backends
│   ├── context/           # Engine-owned context control
│   │   ├── packer.py      # Prompt packing with token budgets
│   │   ├── window.py      # Rolling window with priority trimming
│   │   ├── tokenizer.py   # Token counting (tiktoken + fallback)
│   │   └── digest.py      # Campaign memory compression
│   ├── tools/
│   │   └── dice.py        # Dice rolling with advantage/disadvantage
│   ├── lore/
│   │   └── unified.py     # Unified retrieval (lore + history)
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
| `/quit` | Exit the game |

## State Schema

All game state is stored as versioned JSON files:

- **Campaign** — The root container
- **Character** — Player characters with background, gear, social energy
- **NPC** — Non-player characters with agendas and memory
- **FactionStanding** — Reputation with each of the six factions
- **DormantThread** — Delayed consequences waiting to trigger
- **HistoryEntry** — Chronicle and canon records

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
- [x] Test suite (77 tests)
- [x] CI/CD with GitHub Actions
- [ ] One complete mission playable end-to-end
- [ ] 3 golden transcripts for regression

### Phase 2: Campaign Continuity
- [x] Full tool suite (chronicle, dormant threads, leverage)
- [x] Save/load with migration support
- [x] NPC memory across sessions
- [x] Dormant thread triggering
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
