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

The agent supports multiple backends:

### LM Studio (Recommended for local play)
1. Download [LM Studio](https://lmstudio.ai/)
2. Load a model (Mistral, Llama, Qwen recommended)
3. Start the local server (Server tab)
4. Run the CLI — it auto-detects LM Studio at localhost:1234

### Claude API (Optional)
```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY=your-key
python -m src.interface.cli
```

The agent auto-detects available backends, preferring LM Studio (free) over Claude.

## Architecture

```
sentinel-agent/
├── src/
│   ├── agent.py           # Main agent orchestration
│   ├── state/
│   │   ├── schema.py      # Pydantic models (Campaign, Character, NPC, etc.)
│   │   └── manager.py     # Campaign lifecycle (create/load/save)
│   ├── tools/
│   │   └── dice.py        # Dice rolling with advantage/disadvantage
│   └── interface/
│       └── cli.py         # Rich-based CLI interface
├── prompts/
│   ├── core.md            # Agent identity and principles
│   ├── mechanics.md       # 50-line rules reference
│   ├── gm_guidance.md     # Scene and NPC guidance
│   └── examples/          # Example transcripts
├── campaigns/             # Saved game states (JSON)
└── tests/                 # Test suites
```

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
