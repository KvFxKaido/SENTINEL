# Sovwren → SENTINEL Salvage Map

Components from Sovwren that can be adapted for the SENTINEL agent.
Updated to track implementation status.

---

## Completed

### 1. Session/Campaign Management ✅
**Source:** `core/session_manager.py` + `persistence.py`
**Implemented:** `src/state/manager.py`

| Sovwren | SENTINEL | Status |
|---------|----------|--------|
| `create_session()` | `create_campaign()` | ✅ |
| `resume_session()` | `load_campaign()` | ✅ |
| `list_sessions()` | `list_campaigns()` | ✅ |
| `name_session()` | `name_campaign()` | ✅ |
| `delete_session()` | `delete_campaign()` | ✅ |
| `update_current_session()` | `save_campaign()` | ✅ |

Uses JSON persistence with Pydantic models. Relative timestamps ("Today", "Yesterday") in CLI.

---

### 2. Event Logging Schema ✅
**Source:** `core/database.py` (protocol_events table)
**Implemented:** `src/state/schema.py` → `HistoryEntry`, `HistoryType`

SENTINEL event types:
```
hinge_moment, faction_shift, mission_complete,
phase_change, consequence, canon
```

Features:
- ✅ Structured metadata approach
- ✅ `is_permanent` flag for canon vs chronicle
- ✅ `severity` field on dormant threads

---

### 3. NPC Agenda System ✅
**Source:** `profiles/sovwren.json`
**Implemented:** `src/state/schema.py` → `NPC`, `NPCAgenda`

```python
class NPCAgenda(BaseModel):
    wants: str       # "Protect her daughter's future"
    fears: str       # "Being seen as a collaborator"
    leverage: str | None = None
    owes: str | None = None
    lie_to_self: str | None = None  # "It's temporary..."
```

---

### 4. Mission Phase System ✅
**Source:** `config.py` (Mode/Lens)
**Implemented:** `src/state/schema.py` → `MissionPhase`

```python
class MissionPhase(str, Enum):
    BRIEFING = "briefing"
    PLANNING = "planning"
    EXECUTION = "execution"
    RESOLUTION = "resolution"
    DEBRIEF = "debrief"
    BETWEEN = "between"
```

---

### 5. Social Energy with Narrative Bands ✅
**Source:** `persistence.py` (bandwidth bands)
**Implemented:** `src/state/schema.py` → `SocialEnergy`

```python
@property
def state(self) -> str:
    if self.current >= 51: return "Centered"
    elif self.current >= 26: return "Frayed"
    elif self.current >= 1: return "Overloaded"
    else: return "Shutdown"
```

---

### 6. CLI Architecture ✅
**Source:** `cli/interface.py`, `cli/commands.py`, `cli/themes.py`
**Implemented:** `src/interface/cli.py`

Features:
- ✅ Command parsing with prompt_toolkit
- ✅ Theme/color management (Rich)
- ✅ Animated ASCII banner
- ✅ Game-specific displays (character sheet, faction standings, energy bar)

---

### 7. Glyph System ✅
**Source:** `glyphs.py`
**Implemented:** `src/interface/glyphs.py`

Unicode glyphs with ASCII fallbacks for:
- Faction standings (◆◇○●★)
- Social energy states
- Mission phases
- Events and moments (⬡ hinge, ◌ thread)
- Actions (✓ success, ✗ failure)

---

### 8. LLM Client Abstraction ✅
**Source:** `llm/ollama_client.py`, `llm/lmstudio_client.py`, `llm/council_client.py`
**Implemented:** `src/llm/` directory

Backends:
- ✅ LM Studio (local, free)
- ✅ Claude API
- ✅ OpenRouter (multi-model)
- ✅ Gemini CLI wrapper
- ✅ Codex CLI wrapper
- ✅ Auto-detection with fallback chain

---

### 9. Hinge Moment Detection ✅
**Source:** `config.py` (self_focus_guardrail pattern)
**Implemented:** `src/tools/hinge_detector.py`

Detects irreversible choices via regex patterns:
- Violence: "I kill...", "I destroy..."
- Betrayal: "I betray...", "I sell out..."
- Commitment: "I promise...", "I swear..."
- Enhancement: "I accept the enhancement..."
- Disclosure: "I tell [faction] about..."

Integrated into `agent.respond()` - injects context when detected.

---

### 10. Context Meter ✅
**Source:** `persistence.py` (bandwidth tracking)
**Implemented:** `src/interface/glyphs.py`

Features:
- ✅ Token estimation from text length
- ✅ Visual context bar
- ✅ Narrative bands (shallow → critical)
- ✅ Warning when context is full

---

### 11. Council/Consult System ✅
**Source:** `llm/council_client.py`
**Implemented:** `src/agent.py` → `consult()` method

Features:
- ✅ Parallel queries to multiple advisors
- ✅ Faction-flavored advisor prompts (Nexus, Ember, Witness)
- ✅ Context injection from campaign state
- ✅ CLI `/consult` command with themed panels

---

### 12. Lore Retrieval ✅
**Implemented:** `src/lore/retriever.py`

Features:
- ✅ Chunk-based document indexing
- ✅ Keyword matching with boost factors
- ✅ Context-aware retrieval (faction, mission type)
- ✅ Integration with agent respond loop

---

### 13. NPC Disposition Modifiers ✅
**Implemented:** `src/state/schema.py` → `DispositionModifier`, `NPC.disposition_modifiers`

```python
class DispositionModifier(BaseModel):
    tone: str              # "clipped and formal" / "warm but cautious"
    reveals: list[str]     # What they'll share at this disposition
    withholds: list[str]   # What they keep hidden
    tells: list[str]       # Behavioral cues player might notice
```

Features:
- ✅ `NPC.get_current_modifier()` returns modifier for current disposition
- ✅ Agent state summary includes disposition guidance for active NPCs
- ✅ `update_npc` tool allows GM to change disposition

---

### 14. NPC Memory Triggers ✅
**Implemented:** `src/state/schema.py` → `MemoryTrigger`, `NPC.memory_triggers`

```python
class MemoryTrigger(BaseModel):
    condition: str         # "helped_ember", "betrayed_lattice"
    effect: str            # "disposition shifts to wary"
    disposition_shift: int # -2 to +2
    one_shot: bool         # Only fires once
    triggered: bool        # Has this fired?
```

Features:
- ✅ `NPC.check_triggers(tags)` checks and fires matching triggers
- ✅ `CampaignManager.check_npc_triggers(tags)` checks all active NPCs
- ✅ Faction shifts auto-generate tags (`helped_ember`, `betrayed_lattice`, etc.)
- ✅ `trigger_npc_memory` tool allows GM to fire triggers manually

---

### 15. Faction MCP Server ✅
**Implemented:** `sentinel-campaign/` package

External MCP server providing faction lore, NPC archetypes, and campaign tracking.

**Resources:**
- `faction://{id}/lore` — History, ideology, structure
- `faction://{id}/npcs` — NPC archetypes with wants/fears/speech
- `faction://{id}/operations` — Goals, methods, tensions
- `faction://relationships` — Inter-faction dynamics

**Tools:**
- `get_faction_standing` — Player's standing + history
- `get_faction_interactions` — Past encounters this campaign
- `log_faction_event` — Record faction-related event
- `get_faction_intel` — What does faction know about topic?
- `query_faction_npcs` — NPCs by faction in campaign

Features:
- ✅ All 11 factions with detailed lore, archetypes, operations
- ✅ Intel domains for knowledge queries (each faction knows different things)
- ✅ Campaign state tracking via JSON files
- ✅ Configured for Claude Code via `.mcp.json`

---

### 16. Chronicle Logging Integration ✅
**Implemented:** `src/state/manager.py`, `src/interface/cli.py`

Features:
- ✅ Hinge moments auto-logged when detected and player proceeds
- ✅ Faction shifts auto-logged (via `shift_faction()`)
- ✅ Mission completions logged via `/debrief` → `manager.end_session()`
- ✅ `/history` command shows chronicle with filtering by type
- ✅ `SessionReflection` model stores player debrief answers
- ✅ Reflections stored in `MissionOutcome` within history entries

---

### 17. Leverage Escalation UI ✅
**Implemented:** `src/state/schema.py` → `LeverageDemand`, `src/state/manager.py`

Rich demand modeling for when factions call in enhancement debt:

```python
class LeverageDemand(BaseModel):
    faction: FactionName
    enhancement_id: str
    enhancement_name: str      # Denormalized for display
    demand: str                # What they're asking
    threat_basis: list[str]    # Why leverage works (info OR functional)
    deadline: str | None       # Human-facing ("Before the convoy leaves")
    deadline_session: int | None  # Authoritative for overdue calc
    consequences: list[str]    # What happens if ignored
    weight: LeverageWeight
```

Features:
- ✅ `get_pending_demands()` returns demands sorted by urgency (critical > urgent > pending)
- ✅ `check_demand_deadlines()` returns overdue/urgent demands for GM attention
- ✅ `escalate_demand()` with three escalation types: queue_consequence, increase_weight, faction_action
- ✅ `[DEMAND DEADLINE ALERT]` injection in agent context
- ✅ State summary shows pending demands with urgency markers
- ✅ GM guidance in `prompts/gm_guidance.md`

**Use case:** "We need you to delay the Ember shipment. We know about Sector 7. You have until the convoy leaves."

---

### 18. Phase-Based GM Guidance ✅
**Implemented:** `src/agent.py` → `PromptLoader`, `prompts/phases/`

Phase-specific GM guidance injected based on current mission phase:

```
prompts/phases/
├── briefing.md    # Present situation, competing truths
├── planning.md    # Support player strategy, don't lead
├── execution.md   # Complications arise from choices
├── resolution.md  # Land consequences, don't rush
├── debrief.md     # Four questions, close with intention
└── between.md     # Downtime is character time
```

Features:
- ✅ `PromptLoader.load_phase()` with hot-reload caching
- ✅ `assemble_system_prompt()` includes phase guidance when session active
- ✅ `set_phase` tool for GM to advance mission phase
- ✅ Phase transitions logged to history
- ✅ Narrative hints for each phase transition

---

### 19. Campaign History Search ✅
**Implemented:** `sentinel-campaign/` package (MCP tools and resources)

Keyword-based campaign history search (not embedding-based RAG - works with local models):

**Resources:**
- `campaign://{id}/sessions` — Session summaries grouped by session
- `campaign://{id}/hinges` — All hinge moments in chronological order
- `campaign://{id}/npc/{name}` — All history related to a specific NPC

**Tools:**
- `search_history` — Keyword search with filters (NPC, faction, type, session range)
- `get_npc_timeline` — Chronological timeline of events involving an NPC
- `get_session_summary` — Condensed summary of a specific session

Features:
- ✅ Keyword extraction with boost factors for exact matches
- ✅ Filters: NPC, faction, entry type, session range
- ✅ Searches both history entries and character hinge_history
- ✅ Results sorted by relevance score, then by session

---

## All Salvage Items Complete

All 19 items from the Sovwren salvage map have been implemented.

---

## File Structure Reference

```
sovwren/                          sentinel-agent/
├── core/                         ├── src/
│   ├── session_manager.py   →   │   ├── state/
│   ├── database.py          →   │   │   ├── manager.py      ✅
│   └── ...                       │   │   └── schema.py       ✅
├── persistence.py           →   │   │
├── config.py                →   │   ├── prompts/
│                                 │   │   ├── core.md          ✅
│                                 │   │   └── mechanics.md     ✅
├── profiles/                →   │   ├── npcs/
│   └── sovwren.json         →   │   │   └── templates/       ⏳
├── cli/                     →   │   └── interface/
│   ├── interface.py         →   │       └── cli.py           ✅
│   ├── commands.py          →   │
│   └── themes.py            →   │
├── llm/                     →   │   ├── llm/
│   └── *_client.py          →   │   │   ├── base.py          ✅
│                                 │   │   ├── lmstudio.py      ✅
│                                 │   │   ├── claude.py        ✅
│                                 │   │   ├── openrouter.py    ✅
│                                 │   │   └── cli_wrapper.py   ✅
├── glyphs.py                →   │   └── interface/
│                                 │       └── glyphs.py        ✅
└── rag/                     →   └── lore/
                                      ├── retriever.py         ✅
                                      └── chunker.py           ✅
```

---

## Recommended Implementation Order

1. ~~**NPC Disposition Modifiers** (#13)~~ ✅ Complete
2. ~~**NPC Memory Triggers** (#14)~~ ✅ Complete
3. ~~**Faction MCP Server** (#15)~~ ✅ Complete
4. ~~**Chronicle Logging Integration** (#16)~~ ✅ Complete
5. ~~**Leverage Escalation UI** (#17)~~ ✅ Complete
6. ~~**Phase-Based GM Guidance** (#18)~~ ✅ Complete
7. ~~**Campaign History Search** (#19)~~ ✅ Complete

---

## Open Questions

### Storage: Resolved ✅
Chose **Option 3**: Pydantic models that serialize to JSON but structured like tables. Migration to SQLite possible later.

### NPC Templates
Should we create JSON template files for common NPC archetypes?
```
npcs/templates/
├── faction_contact.json
├── information_broker.json
├── reluctant_ally.json
└── hidden_enemy.json
```
