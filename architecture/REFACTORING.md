# SENTINEL Refactoring Roadmap

Council review conducted 2026-01-04 with Gemini and Codex.

---

## Completed

### CLI Module Split
**Date:** 2026-01-04

Split `cli.py` (1160 lines) into focused modules:

| File | Lines | Responsibility |
|------|-------|----------------|
| `cli.py` | 259 | Main loop, argument parsing |
| `renderer.py` | 307 | Theme, console, display helpers |
| `commands.py` | 652 | All `/command` handlers |

**Benefits:**
- Each file has single responsibility
- Commands can be tested independently
- Theme changes isolated to renderer

---

### CampaignStore Extraction
**Date:** 2026-01-04

Separated persistence from domain logic in `manager.py`:

| File | Responsibility |
|------|----------------|
| `store.py` | Storage abstraction (CampaignStore protocol) |
| `manager.py` | Domain operations (create, load, NPC management, etc.) |

**New classes:**
- `CampaignStore` — Protocol defining storage interface
- `JsonCampaignStore` — File-based persistence (production)
- `MemoryCampaignStore` — In-memory storage (testing)

**Benefits:**
- Tests can use `MemoryCampaignStore` — no file I/O
- Storage strategy is pluggable (could add SQLite later)
- Backwards compatible: `CampaignManager("path")` still works

---

### LLMClient Injection
**Date:** 2026-01-04

Added dependency injection for LLM clients:

| Component | Purpose |
|-----------|---------|
| `create_llm_client()` | Factory function for backend creation |
| `detect_backend()` | Auto-detection logic (extracted from agent) |
| `MockLLMClient` | Test double with configurable responses |

**New SentinelAgent signature:**
```python
SentinelAgent(
    manager,
    prompts_dir,
    client=mock_client,  # NEW: optional injected client
    backend="auto",      # Falls back to factory if no client
)
```

**Benefits:**
- Tests can use `MockLLMClient` — no API calls
- Call recording for assertions (`mock.calls`)
- Backwards compatible: `backend` param still works

---

## Remaining Priorities

### 1. Extract NPC Rules to Pure Functions

**Priority:** Medium
**Effort:** 1-2 hours
**Source:** Codex recommendation

**Problem:** NPC behavior logic embedded in Pydantic models makes testing harder.

**Current state:**
```python
class NPC(BaseModel):
    def check_triggers(self, tags: list[str]) -> list[str]:
        # Logic embedded in model
        ...

    def get_current_modifier(self) -> DispositionModifier | None:
        # Logic embedded in model
        ...
```

**Target state:**
```python
# src/rules/npc.py - Pure functions
def check_triggers(npc: NPC, tags: list[str]) -> list[str]:
    """Check and fire memory triggers, return messages."""
    ...

def get_disposition_modifier(npc: NPC) -> DispositionModifier | None:
    """Get current disposition modifier for NPC."""
    ...

def shift_disposition(npc: NPC, delta: int) -> NPC:
    """Return new NPC with shifted disposition."""
    ...

# Model becomes pure data
class NPC(BaseModel):
    name: str
    faction: FactionName | None
    disposition: Disposition
    # ... no methods
```

**Implementation steps:**
1. Create `src/rules/npc.py` with pure functions
2. Move logic from `NPC` methods to functions
3. Update callers (agent, manager) to use functions
4. Test functions in isolation

**Files affected:**
- `src/rules/npc.py` (new)
- `src/state/schema.py` (simplify NPC)
- `src/agent.py` (update calls)
- `src/state/manager.py` (update calls)
- `tests/test_npc_rules.py` (new)

---

### 2. Add Focused Test Coverage

**Priority:** High
**Effort:** 3-4 hours
**Source:** Both consultants agreed

**Problem:** No tests for critical game mechanics.

**Test priorities:**

| Area | Test Cases |
|------|------------|
| Memory triggers | Trigger fires once, disposition shifts correctly, tags match |
| Faction shifts | Standing changes logged, cross-faction effects |
| Chronicle logging | Hinge moments logged, history filters work |
| Disposition modifiers | Correct modifier for each level, tells/reveals accurate |
| Social energy | Bands transition correctly, state names match |

**Example tests:**
```python
# tests/test_memory_triggers.py
def test_trigger_fires_once():
    npc = NPC(
        name="Test",
        memory_triggers=[
            MemoryTrigger(
                condition="helped_ember",
                effect="becomes wary",
                disposition_shift=-1,
                one_shot=True
            )
        ]
    )

    # First trigger
    messages = check_triggers(npc, ["helped_ember"])
    assert len(messages) == 1
    assert npc.disposition == Disposition.WARY

    # Second trigger - should not fire
    messages = check_triggers(npc, ["helped_ember"])
    assert len(messages) == 0

# tests/test_chronicle.py
def test_hinge_moment_logged():
    store = MemoryCampaignStore()
    manager = CampaignManager(store)
    manager.create_campaign("Test")

    manager.log_hinge_moment(
        situation="Player decided to...",
        choice="Betrayed the contact",
        reasoning="Survival over loyalty"
    )

    history = manager.current.history
    assert len(history) == 1
    assert history[0].type == HistoryType.HINGE_MOMENT
```

**Implementation steps:**
1. Set up pytest configuration
2. ~~Implement `MemoryCampaignStore`~~ ✅ Done
3. ~~Implement `MockLLMClient`~~ ✅ Done
4. Write tests for each area
5. Add to CI (when set up)

**Files to create:**
- `tests/conftest.py` (fixtures)
- `tests/test_memory_triggers.py`
- `tests/test_faction_shifts.py`
- `tests/test_chronicle.py`
- `tests/test_disposition.py`
- `tests/test_social_energy.py`

---

## Implementation Order

Recommended sequence (dependencies noted):

```
1. Extract CampaignStore ✅ DONE
   └── Enables: MemoryCampaignStore for testing

2. Inject LLMClient ✅ DONE
   └── Enables: MockLLMClient for testing

3. Add focused tests (#2)
   └── Uses: MemoryCampaignStore, MockLLMClient

4. Extract NPC rules (#1)
   └── Tests already in place, safe refactor
```

---

## Not Prioritized

These were discussed but deemed lower priority:

### Tool Registry Pattern
Extract tool definitions from agent to separate registry. Would help if we add many more tools, but current count (6) is manageable.

### Event Bus for State Changes
Decouple components via events. Adds complexity without clear benefit at current scale.

### Plugin System for Backends
Make LLM backends truly pluggable. Current factory pattern is sufficient.

---

## Notes

- All refactoring should maintain backward compatibility with existing campaigns
- JSON save format must remain unchanged
- CLI interface should be unaffected by internal changes
- Consider feature flags if changes are large
