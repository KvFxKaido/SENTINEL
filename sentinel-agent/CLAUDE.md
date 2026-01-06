# CLAUDE.md

Context for AI assistants working on this project.

## Project Overview

SENTINEL Agent is an AI Game Master for a tactical TTRPG. It runs narrative sessions, tracks game state, and uses tools to handle mechanics (dice, reputation, consequences).

**Core philosophy:** The agent is a storyteller who knows the rules, not a rules engine that tells stories.

## Architecture

```
src/
├── agent.py              # Orchestrates LLM, tools, and state
├── state/
│   ├── schema.py         # Pydantic models — the source of truth
│   ├── manager.py        # CRUD operations on campaign state
│   └── memvid_adapter.py # Campaign memory via memvid (optional)
├── tools/
│   ├── dice.py           # Game mechanics (rolls, tactical reset)
│   └── hinge_detector.py # Detects irreversible choices in player input
├── interface/
│   ├── cli.py            # Player-facing terminal UI
│   ├── glyphs.py         # Visual indicators (Unicode/ASCII)
│   └── choices.py        # Multiple choice system
├── llm/
│   ├── base.py           # Abstract LLM client
│   ├── lmstudio.py       # Local LM Studio backend
│   ├── claude.py         # Claude API backend
│   ├── openrouter.py     # OpenRouter API backend
│   └── cli_wrapper.py    # Gemini/Codex CLI wrappers
└── lore/
    ├── retriever.py      # Context-aware lore lookup
    └── chunker.py        # Document chunking

prompts/                  # Hot-reloadable prompt modules
├── advisors/             # Faction advisor prompts (for /consult)
campaigns/                # JSON save files (gitignored)
```

## Key Design Decisions

### State is JSON, not SQLite
We chose JSON files for MVP simplicity. The schema is designed to migrate to SQLite later if needed. All state files are versioned with `_version` field.

### Prompts are modular and hot-reloadable
The `PromptLoader` class watches file modification times. Edit `prompts/*.md` and changes take effect on next API call without restart.

### Tools return dicts, not Pydantic models
Tool handlers return plain dicts for JSON serialization to the API. Pydantic models are for internal state only.

### NPCs have agendas, not just names
Every NPC must have: `wants`, `fears`, `leverage`, `owes`, `lie_to_self`. This drives realistic behavior.

### NPCs have disposition modifiers
Each NPC can define behavior per disposition level (hostile→wary→neutral→warm→loyal):
- `tone` — How they speak
- `reveals` — What they'll share at this level
- `withholds` — What they keep hidden
- `tells` — Behavioral cues players might notice

### NPCs have memory triggers
NPCs react to tagged events. When `check_triggers(["helped_ember"])` is called, any NPC with a matching trigger fires (e.g., Lattice contact becomes wary). Faction shifts auto-generate tags.

### Social energy is narrative, not just numeric
When querying social energy, always include a `narrative_hint` that describes the state in fiction ("running on fumes").

### Memvid is optional campaign memory
The `MemvidAdapter` provides semantic search over campaign history (hinges, NPC interactions, faction shifts). It's append-only and complements JSON saves. Key principles:
- **Graceful degradation**: All ops are no-ops if `memvid-sdk` not installed
- **Evidence, not memory**: Raw frames are GM-only; player queries go through faction bias
- **Auto-hooks**: Manager automatically saves hinges, faction shifts, and dormant threads

Query with `/timeline` command or `manager.query_campaign_history()`.

## File Purposes

| File | Purpose | When to modify |
|------|---------|----------------|
| `schema.py` | Data models | Adding new state fields |
| `manager.py` | State operations | Adding new CRUD operations |
| `memvid_adapter.py` | Campaign memory | Adding new frame types or queries |
| `agent.py` | API orchestration | Adding new tools, changing prompts |
| `cli.py` | User interface | Adding commands, changing display |
| `glyphs.py` | Visual indicators | Adding new symbols, context meter |
| `hinge_detector.py` | Choice detection | Adding hinge patterns |
| `dice.py` | Game mechanics | Changing roll logic |
| `prompts/core.md` | Agent identity | Changing GM personality |
| `prompts/mechanics.md` | Rules reference | Changing game rules |
| `prompts/gm_guidance.md` | Scene guidance | Changing narrative style |
| `prompts/advisors/*.md` | Faction voices | Changing /consult responses |

## Code Conventions

### Pydantic Models
```python
class Example(BaseModel):
    id: str = Field(default_factory=generate_id)  # Always have an ID
    name: str  # Required fields first
    optional_field: str | None = None  # Optional fields with defaults
```

### Tool Handlers
```python
def _handle_tool_name(self, **kwargs) -> dict:
    """Handle tool_name tool call."""
    # Validate inputs
    # Perform operation
    # Return dict (not Pydantic model)
    return {"result": "value", "narrative_hint": "..."}
```

### CLI Commands
```python
def cmd_name(manager: CampaignManager, args: list[str]):
    """Docstring becomes help text."""
    # Use Rich console for output
    # Use Prompt.ask for input
```

## Common Tasks

### Adding a new tool

1. Define the schema in `agent.py` → `get_tools()`
2. Add handler method `_handle_<tool_name>` in `SentinelAgent`
3. Register in `self.tools` dict in `__init__`
4. Add to `prompts/mechanics.md` if player-facing

### Adding a new state field

1. Add to appropriate model in `schema.py`
2. Bump `_version` in `Campaign` model
3. Add migration logic in `manager.py` if needed
4. Update `prompts/` if it affects gameplay

### Adding a CLI command

1. Add `cmd_<name>` function in `cli.py`
2. Add to `COMMANDS` dict
3. Update help text in `show_help()`

### Modifying GM behavior

1. Edit relevant prompt in `prompts/`
2. Changes are hot-reloaded automatically
3. Test with actual gameplay, not unit tests

## Testing Strategy

### Golden Transcripts (primary)
Record ideal GM responses in `tests/golden/`. Format:
```json
{
  "input": "player message",
  "expected_tools": ["tool_name"],
  "expected_state_changes": {...},
  "quality_criteria": ["NPC had clear agenda", "consequence was queued"]
}
```

### Boundary Tests
Test edge cases in `tests/boundary/`:
- Social energy at 0%
- Faction at Hostile
- Enhancement leverage called

### State Tests
Test CRUD operations in `tests/integration/`:
- Save/load roundtrip
- Schema validation
- Manager operations

## Game Rules Quick Reference

- **Rolls:** d20 + 5 (trained) vs DC 10/14/18/22
- **Social Energy:** 100→0, affects roll modifiers
- **Factions:** Hostile→Unfriendly→Neutral→Friendly→Allied
- **Hinge Moments:** Irreversible choices, always log
- **Dormant Threads:** Delayed consequences, queue then surface later

## What NOT to do

- Don't put game logic in the CLI — it belongs in tools or manager
- Don't hardcode prompts in Python — use the prompts/ directory
- Don't return Pydantic models from tool handlers — return dicts
- Don't skip the narrative_hint — state should always have flavor
- Don't queue dormant threads for minor things — save for real consequences

## Dependencies

```
pydantic>=2.0.0     # State validation
rich>=13.0.0        # Terminal UI
prompt-toolkit>=3.0 # Input handling
anthropic>=0.40.0   # Claude API (optional, pip install -e ".[claude]")
memvid-sdk>=0.1.0   # Campaign memory (optional, pip install -e ".[memvid]")
```

## Environment

- Python 3.10+
- **LM Studio** at localhost:1234 (free, local) — preferred backend
- OR `ANTHROPIC_API_KEY` for Claude API
- CLI works without any LLM for state management testing

## Backend Selection

The agent auto-detects backends in this order:
1. **LM Studio** (localhost:1234) — free, local
2. **Claude API** — requires `ANTHROPIC_API_KEY`
3. **OpenRouter** — requires `OPENROUTER_API_KEY`, multi-model
4. **Gemini CLI** — requires `gemini` command installed
5. **Codex CLI** — requires `codex` command installed

Use `/backend <name>` in the CLI to switch manually. Note: CLI backends (Gemini, Codex) don't support tool calling.

## Related Files

- `../core/SENTINEL Playbook — Core Rules.md` — The full game rules
- `../lore/` — Canon bible, characters, session logs (indexed by lore retriever)
- `../architecture/AGENT_ARCHITECTURE.md` — Design document
- `../architecture/memvid_integration_design.md` — Memvid philosophy and integration design
- `../sentinel-campaign/README.md` — Campaign MCP server (factions, history, tools)
