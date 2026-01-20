# Sentinel Cross-Platform Implementation Plan

## Purpose

This plan outlines a **phased, low-risk path** from the current Sentinel CLI proof-of-concept to a polished, cross-platform experience (desktop + mobile) **without rewriting the engine or compromising architectural sovereignty**.

Sentinel remains the authoritative engine. All other layers are bridges, shells, or observers.

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

## Phase 3 — Persistence Upgrade (Optional, Turso)

**Goal:** Enable durable, portable state without central servers

### Tasks

1. **Abstract Persistence Layer**
   - File-based (default)
   - Turso-backed (optional)

2. **Local-First Writes**
   - All writes happen locally first
   - Sync is asynchronous and optional

3. **Conflict Policy**
   - Sentinel state always wins
   - Sync conflicts surfaced, not hidden

4. **Offline Guarantees**
   - No feature requires connectivity

**Exit condition:** Campaigns survive restarts and can sync across devices

---

## Phase 4 — Polished UI Layer (Astro)

**Status:** 🚧 In Progress (scaffold complete)

**Goal:** Visual clarity without architectural gravity

### Tasks

1. ✅ **Read-Only First UI** — `sentinel-ui/src/components/`
   - Header with connection status
   - Narrative log for GM conversation
   - Side panel with state, factions, events

2. ✅ **Interactive Islands (Minimal)** — Vanilla JS
   - Command input with form submission
   - Quick command buttons
   - SSE subscription for live events

3. ✅ **State as Projection**
   - UI renders Sentinel output via bridge API
   - No local derivation of truth

4. ✅ **Performance Constraints**
   - Zero framework JS (vanilla only)
   - Astro static-first with minimal hydration

### Setup

```bash
# Start the full stack
cd sentinel-bridge && deno task dev   # Terminal 1
cd sentinel-ui && npm run dev         # Terminal 2

# Open http://localhost:4321
```

**Exit condition:** In progress — needs live testing with Sentinel

---

## Phase 5 — Desktop Packaging (Optional)

**Goal:** Native feel without native rewrites

### Options

- Tauri (recommended)
- Minimal WebView shell

### Tasks

- Bundle Deno + Sentinel
- Embed Astro UI
- Ensure filesystem access is explicit

**Exit condition:** One-click desktop app, offline-capable

---

## Phase 6 — Mobile Shell (Optional, Later)

**Goal:** Mobile access without redefining Sentinel

### Tasks

- WebView-based mobile shell
- Local Deno bridge
- Touch-friendly UI adjustments
- Background suspension handling

**Non-goals**
- Rewriting Sentinel in JS
- Real-time multiplayer
- Always-online requirements

**Exit condition:** Sentinel sessions playable on mobile devices

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

