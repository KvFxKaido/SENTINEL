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

### Focused Test Suite
**Date:** 2026-01-04

Added comprehensive test coverage for core game mechanics:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_memory_triggers.py` | 10 | Trigger firing, one-shot, disposition shifts |
| `test_faction_shifts.py` | 10 | Standing model, manager ops, cross-faction |
| `test_chronicle.py` | 11 | History logging, hinge moments, session end |
| `test_disposition.py` | 10 | Modifier access, content, progression |
| `test_social_energy.py` | 20 | Bands, boundaries, hints, manager ops |

**Total:** 61 tests passing

**Fixtures (conftest.py):**
- `MemoryCampaignStore` — In-memory persistence
- `MockLLMClient` — Recorded responses
- Sample NPCs with triggers and modifiers

**Bug fixed:** `log_hinge_moment` was creating dict instead of `HingeMoment` model.

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

## Implementation Order

Recommended sequence (dependencies noted):

```
1. Extract CampaignStore ✅ DONE
   └── Enables: MemoryCampaignStore for testing

2. Inject LLMClient ✅ DONE
   └── Enables: MockLLMClient for testing

3. Add focused tests ✅ DONE
   └── Uses: MemoryCampaignStore, MockLLMClient (61 tests)

4. Extract NPC rules (next)
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
