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

### NPC Rules Extraction
**Date:** 2026-01-04

Extracted NPC behavior logic to pure functions:

| File | Purpose |
|------|---------|
| `src/rules/__init__.py` | Module exports |
| `src/rules/npc.py` | Pure functions for NPC behavior |

**Functions extracted:**
- `get_disposition_modifier(npc)` — Get modifier for current disposition
- `apply_disposition_shift(npc, delta)` — Shift disposition by steps
- `check_triggers(npc, tags)` — Check and fire memory triggers

**Approach:** NPC methods delegate to pure functions for backward compatibility.
Callers can use either `npc.check_triggers()` or `check_triggers(npc, ...)`.

**Tests added:** 16 new tests in `test_npc_rules.py`

**Total test count:** 77 tests passing

---

## Implementation Order

All priorities from the council review are now complete:

```
1. Extract CampaignStore ✅ DONE
   └── Enables: MemoryCampaignStore for testing

2. Inject LLMClient ✅ DONE
   └── Enables: MockLLMClient for testing

3. Add focused tests ✅ DONE
   └── Uses: MemoryCampaignStore, MockLLMClient (61 tests)

4. Extract NPC rules ✅ DONE
   └── 16 additional tests (77 total)
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
