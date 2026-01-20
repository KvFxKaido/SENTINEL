# Sentinel Cross-Platform Implementation Plan

## Purpose

This plan outlines a **phased, low-risk path** from the current Sentinel CLI proof-of-concept to a polished, cross-platform experience (desktop + mobile) **without rewriting the engine or compromising architectural sovereignty**.

Sentinel remains the authoritative engine. All other layers are bridges, shells, or observers.

**Related:** [Visual & Aesthetic Roadmap](sentinel_visual_roadmap.md) — UI polish, portraits, sound, Fallout/MGS feel

---

## Guiding Principles (Non-Negotiable)

1. **Sentinel is the engine**
   - Owns state, rules, consequences, memory, and progression
   - Must run headless and offline
   - Must not depend on UI, network, or model availability

2. **Everything else is optional infrastructure**
   - UI, sync, cloud models, and mobile shells may fail independently
   - Failure must be visible and non-destructive

3. **Local-first always**
   - No required servers
   - No required accounts
   - No required network

4. **Bridges translate, they do not decide**
   - No business logic outside Sentinel
   - No state mutation without Sentinel’s consent

---

## Phase 0 — Baseline (Already Complete)

**Status:** ✅ Done

- Sentinel runs as a standalone Python CLI/TUI
- State is persisted locally (JSON/files)
- Model backends are swappable and non-authoritative
- Offline play works
- Tests validate mechanics and state integrity

**Exit condition:** Sentinel is playable end-to-end with no external dependencies

---

## Phase 1 — Engine Boundary Hardening

**Status:** ✅ Done

**Goal:** Make Sentinel explicitly embeddable without changing behavior

### Tasks

1. ✅ **Define a Stable Command Interface**
   - Commands: `status`, `say`, `slash`, `load`, `save`, `quit`
   - Structured JSON responses with `ok`, `error`, and result fields
   - See: `sentinel-agent/src/interface/headless.py`

2. ✅ **Formalize Engine I/O Contract**
   - Input: JSON commands via stdin (one per line)
   - Output: JSON events + responses via stdout (newline-delimited)
   - Errors: explicit `ok: false` with `error` message

3. ✅ **Headless Execution Mode**
   - `sentinel --headless`
   - Emits `{"type": "ready"}` on startup
   - Subscribes to event bus, emits all game events as JSON

4. ✅ **State Snapshot + Restore**
   - `{"cmd": "save"}` and `{"cmd": "load", "campaign_id": "..."}` commands
   - Campaign manager handles persistence

**Exit condition:** ✅ Sentinel can be driven entirely by another process

---

## Phase 2 — Local Bridge (Deno)

**Status:** ✅ Complete and Tested

**Goal:** Introduce a local orchestration layer without logic leakage

### Responsibilities (Allowed)

- Launch Sentinel as a child process
- Send commands to Sentinel
- Receive and relay structured output
- Expose a local API to UIs
- Coordinate persistence and sync

### Responsibilities (Forbidden)

- Interpreting game rules
- Mutating game state
- Generating narrative
- Making decisions

### Tasks

1. ✅ **Deno Bridge Process** — `sentinel-bridge/src/process.ts`
   - `SentinelProcess` class spawns `sentinel --headless`
   - Manages lifecycle (start, stop, status)
   - Auto-restart on crash (up to 3 attempts with backoff)

2. ✅ **Local API Surface** — `sentinel-bridge/src/api.ts`
   - `POST /command` — Send command to Sentinel
   - `GET /state` — Get bridge + Sentinel state
   - `GET /events` — SSE stream of game events
   - `POST /start` / `POST /stop` — Lifecycle control
   - `GET /health` — Health check

3. ✅ **IPC / HTTP Choice**
   - HTTP over localhost (default port 3333)
   - CORS enabled for local development
   - Transport is internal, swappable if needed

4. ✅ **Graceful Degradation**
   - Crash detection → auto-restart → event broadcast
   - API returns 503 when Sentinel unavailable
   - SSE broadcasts `bridge_state_change` events

### Setup

```bash
# Install Deno (if not installed)
# Windows: irm https://deno.land/install.ps1 | iex
# macOS/Linux: curl -fsSL https://deno.land/install.sh | sh

# Start the bridge
cd sentinel-bridge
deno task dev
```

**Exit condition:** ✅ Sentinel can be controlled programmatically via Deno

---

## Phase 3 — Polished UI Layer (Astro)

**Status:** ✅ Complete

**Goal:** Visual clarity without architectural gravity

### Tasks

1. ✅ **TUI-Style Web Interface** — `sentinel-ui/src/components/`
   - 3-column layout (SELF | NARRATIVE | WORLD)
   - Header with connection status, campaign name, backend info
   - Narrative log with GM/player message styling
   - Side panels with character state, factions, events

2. ✅ **Interactive Islands (Minimal)** — Vanilla JS
   - Command input with form submission
   - Quick command buttons
   - SSE subscription for live events
   - State refresh on commands

3. ✅ **State as Projection**
   - UI renders Sentinel output via bridge API
   - No local derivation of truth
   - Type-safe discriminated unions for responses

4. ✅ **Performance Constraints**
   - Zero framework JS (vanilla only)
   - Astro static-first with minimal hydration
   - AMOLED-optimized dark theme

### Setup

```bash
# Start the full stack
cd sentinel-bridge && deno task dev   # Terminal 1
cd sentinel-ui && npm run dev         # Terminal 2

# Open http://localhost:4321
```

**Exit condition:** ✅ Web UI functional with live Sentinel integration

---

## Future Possibilities

These are potential extensions without a required sequence. Implement as needed.

See also: [Visual & Aesthetic Roadmap](sentinel_visual_roadmap.md) for UI polish, portraits, sound design.

### Desktop Packaging (Tauri)

**Goal:** Native feel without native rewrites

- Bundle Deno + Sentinel into single executable
- Embed Astro UI in WebView
- Ensure filesystem access is explicit
- One-click install, offline-capable

### Mobile Shell

**Goal:** Mobile access without redefining Sentinel

- WebView-based mobile shell (Capacitor or similar)
- Local Deno bridge running on device
- Touch-friendly UI adjustments
- Background suspension handling

**Non-goals:** Rewriting Sentinel in JS, real-time multiplayer, always-online requirements

### Persistence Upgrade (Turso)

**Goal:** Enable durable, portable state without central servers

- Abstract persistence layer (file-based default, Turso optional)
- Local-first writes — sync is asynchronous
- Conflict policy: Sentinel state always wins
- No feature requires connectivity

---

## Tooling & Hygiene

- **Ruff** for Python linting/formatting
- Existing test suite remains authoritative
- CI validates engine behavior, not UI

---

## Success Criteria

- Sentinel runs unchanged in all modes
- UI layers can be deleted without data loss
- Offline play always works
- Failures are visible and recoverable
- No layer silently gains authority

---

## Explicit Non-Goals

- Building a general-purpose game platform
- Hosting user accounts
- Chasing feature parity with web games
- Monetization infrastructure

---

## Final Note

If a step feels like it requires rewriting Sentinel, the step is wrong.

If a layer starts to feel indispensable, it has exceeded its mandate.

Sentinel should always be able to stand alone.

