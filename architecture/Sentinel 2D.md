# SENTINEL — Spatial Embodiment & World Map Consolidated Plan

> **Version:** 2.2 (Consolidated + Integration Architecture)
> **Date:** January 28, 2026
> **Author:** Shawn Montgomery
> **Status:** Design-binding + Implementation roadmap

---

## 1. Purpose of This Document

This document defines a single, coherent source of truth for SENTINEL's spatial embodiment layer.

It establishes **what** the spatial layer is, **why** it exists, and **how** it is implemented — without compromising the core engine.

If any part of this document conflicts with implementation convenience or UI smoothness:

- **Design invariants win**
- **Determinism and turn authority win**

---

## 2. Core Problem (Restated)

SENTINEL already models:

- Irreversible decisions
- Long-tail consequences
- Faction memory and leverage
- Avoidance as a choice

But it is experienced through abstract interfaces.

**Players operate SENTINEL. They do not inhabit it.**

The missing element is **presence**.

---

## 3. Design North Star

> *Presence is felt when the player quietly accounts for what they still have, in a place that is only temporarily safe.*

This refactor prioritizes:

- **Reflection** over spectacle
- **Aftermath** over action
- **Ownership** over optimization

The spatial layer is not a simulation engine. It is a lens through which decisions are framed.

---

## 4. Non-Negotiable Design Invariants

The spatial layer must not compromise:

- **Determinism**
- **Turn authority**
- **Consequence integrity**
- **Replayability**
- **System truthfulness**
- **LLM optionality**

If the spatial UI, web UI, or LLM is removed, the game must still function correctly.

---

## 5. Key Principle

### Movement Creates Presence, Not Progress

- Real-time movement is **cosmetic**
- Movement does not advance time
- Movement does not mutate state
- Proximity alone never commits the player

All meaningful change passes through the **Commitment Gate**.

---

## 6. The Commitment Gate (Authoritative Rule)

All meaningful actions:

1. Consume exactly **one turn**
2. Are resolved **deterministically**
3. Apply consequences **immediately**
4. May trigger optional narrative reaction

### Commitments Include

- Travel between regions
- Initiating combat
- Accepting or completing jobs
- Calling favors
- Advancing faction or narrative threads

**No interface may bypass this gate.**

---

## 7. Spatial Layers Overview

SENTINEL uses two complementary spatial surfaces.

### 7.1 Strategic World Map (Authoritative Proposal Surface)

**Purpose:**

- Decide what matters next
- Visualize social reach and pressure
- Propose intent for the turn

**Properties:**

- SVG-based (web UI)
- Turn-scoped
- No free movement
- No state mutation

> The map **proposes** actions. The engine **resolves** them.

### 7.2 Local Spatial Layer (Embodiment Surface)

**Purpose:**

- Make proximity, exposure, and absence legible
- Provide emotional grounding

**Properties:**

- Canvas-based
- Real-time movement
- Non-authoritative
- Zero state mutation without confirmation

---

## 8. The Safehouse (Anchor Space)

The safehouse is the emotional and mechanical anchor of the spatial layer.

### Purpose

- Quiet accounting of consequences
- Inventory as history, not loot
- Temporary safety without permanence

### Characteristics

- No time pressure
- No surprise state changes
- No forced interactions
- Minimal ambient motion

### Inventory as Presence

Inventory is physically placed in the room:

- Gear on tables or shelves
- Vehicles visible
- Favors pinned on boards
- Empty spaces where things used to be

**Absence is information.**

---

## 9. Overworld Model (Non-Authoritative)

The overworld exists to make:

- Distance
- Exposure
- Hesitation

…legible.

### Properties

- Top-down or isometric
- Player moves freely
- NPCs occupy visible positions
- Hazards are visible

### Critical Constraint

Movement does **not**:

- Consume turns
- Advance time
- Mutate state

### Interaction Pattern

```
Proximity → Prompt → Explicit Confirmation → Commitment Gate → Resolution
```

---

## 10. Combat Model (Hybrid)

Combat is always a **commitment**.

- Overworld movement freezes
- Combat resolves fully turn-based
- Consequences cascade into campaign state
- Control returns to spatial layer after resolution

**There is no real-time combat resolution.**

---

## 11. World Map Design Philosophy

### Social Connectivity (Not Fog of War)

Connectivity represents **who you know**, not where you've been.

| State | Meaning |
|---|---|
| **Disconnected** | No contacts or intel |
| **Aware** | You've heard of it |
| **Connected** | Reliable contacts exist |
| **Embedded** | Deep network and leverage |

Exploration is social investment, not checklist completion.

---

## 12. Negotiable Gates

Routes are not locks. They are **risk and resource multipliers**.

Every blocked route offers:

- Standing solutions
- Contact solutions
- Resource solutions
- Risky traversal

> The question is never "can I go?". It is **"what does it cost?"**.

---

## 13. Map as Proposal, Not Control

### Turn Loop

1. Turn start
2. Map renders current state
3. Player selects one map action
4. Action is confirmed
5. Engine resolves deterministically
6. Map updates after resolution

**No optimistic updates. No free movement.**

---

## 14. Data Model Summary

Key additions:

- `RegionConnectivity` enum
- Typed route requirements
- `RegionState` (per-campaign)
- `MapState` attached to `Campaign`

Connectivity advances via:

- NPCs met
- Threads resolved
- Significant jobs
- Faction standing

---

## 15. Implementation Phases (Condensed)

### Phase 0 — Data Foundation

- Region positions
- MapState APIs
- Typed route requirements

### Phase 1 — Strategic Map (SVG)

- Render regions and routes
- Travel proposals
- Content markers

### Phase 2 — Safehouse (Canvas)

- Minimal renderer
- Inventory as physical presence
- Quiet reflection space

### Phase 3 — Overworld

- Single region space
- NPCs and hazards
- Commitment enforcement

### Phase 4 — Expansion

- Multi-region overworlds
- Faction pressure visualization
- Combat integration

---

## 16. What This Is Not

- Not a simulation engine
- Not a real-time game
- Not a replacement for the CLI

The CLI becomes a debug and inspection surface. The engine remains authoritative.

---

## 17. Success Criteria

This refactor succeeds if:

- Players feel grounded in space
- Inventory feels like history
- Decisions feel costly and irreversible
- The game is playable without LLMs
- The system remains deterministic

---

## 18. Integration Architecture

Sections 1–17 define the philosophy, invariants, and spatial model. This section specifies the **contract** between the engine and the map component — the concrete work required to close the gap between what exists and what the design demands.

### 18.1 Current State

**Engine side (Python + Deno bridge):**

- `schema.py` already has `Region`, `RegionConnectivity`, `MapState`, `RegionState`, `RouteRequirement`, `RouteAlternative` — all wired into `Campaign`
- `regions.json` has all 11 regions with routes, requirements, alternatives, factions
- Bridge at `localhost:3333` exposes `POST /command`, `GET /state`, `GET /events` (SSE)

**Map side (React + Vite standalone):**

- `WorldMap` component takes `currentRegion`, `regionStates`, `markers`, `onRegionClick`
- Own copies of region data, faction data, and types
- Demo states only — no live connection to anything

### 18.2 The Six Gaps

| # | Gap | Problem |
|---|-----|---------|
| 1 | **No map API endpoint** | Bridge has `/state` and `/command` but nothing returns region connectivity, current region, or content markers |
| 2 | **Duplicated data** | Map's `regions.ts` and `factions.ts` are static copies of what's already in `regions.json` and `schema.py` — two sources of truth |
| 3 | **No map events** | SSE stream doesn't emit `region_changed`, `connectivity_updated`, or `travel_proposed` |
| 4 | **No travel action flow** | `onRegionClick` has nowhere to go — no path from "click region" through the commitment gate to engine resolution |
| 5 | **No content marker aggregation** | Engine tracks NPCs, jobs, threads per campaign, but nothing rolls those up into "what's in each region" for map display |
| 6 | **Tech stack mismatch** | Map is React/Vite standalone. The actual UI is Astro (`sentinel-ui/`). Needs integration strategy |

### 18.3 Bridge Map API

A new endpoint the map component consumes.

**`GET /map`** returns:

```json
{
  "current_region": "haven",
  "regions": [
    {
      "id": "haven",
      "name": "Haven",
      "position": { "x": 0.5, "y": 0.3 },
      "controlling_faction": "covenant",
      "connectivity": "embedded",
      "content_markers": {
        "npcs": 3,
        "active_jobs": 1,
        "active_threads": 2,
        "points_of_interest": ["safehouse", "job_board"]
      },
      "routes": [
        {
          "to": "crossroads",
          "accessible": true,
          "requirements": [],
          "alternatives": []
        },
        {
          "to": "rustfield",
          "accessible": false,
          "requirements": [
            { "type": "standing", "faction": "lattice", "minimum": 1 }
          ],
          "alternatives": [
            { "type": "risky_traversal", "risk": "moderate" }
          ]
        }
      ]
    }
  ]
}
```

The bridge constructs this by reading `Campaign.map_state`, `regions.json`, and aggregating per-region content from campaign state. No new engine logic — just a read-only projection.

### 18.4 Data Contract

**`Campaign.map_state`** → **`WorldMapProps`**

| Engine (Python) | Bridge (Deno) | Map (React) |
|-----------------|---------------|-------------|
| `MapState.current_region` | `response.current_region` | `currentRegion` prop |
| `MapState.region_states[id].connectivity` | `response.regions[].connectivity` | `regionStates[id].connectivity` |
| `MapState.region_states[id].discovered_routes` | `response.regions[].routes` | `regionStates[id].routes` |
| Aggregated from NPCs, jobs, threads | `response.regions[].content_markers` | `markers[id]` |

The bridge is a **read-only projection layer**. It does not cache, transform, or enrich — it maps Python state to the JSON shape the component expects.

### 18.5 Event Flow

The map subscribes to the existing SSE stream at `GET /events`. New event types:

| Event | Trigger | Payload |
|-------|---------|---------|
| `region_changed` | Player completes travel | `{ region: string, previous: string }` |
| `connectivity_updated` | NPC met, thread resolved, standing changed | `{ region: string, connectivity: string }` |
| `content_markers_updated` | Job posted, NPC moved, thread activated | `{ region: string, markers: ContentMarkers }` |
| `travel_proposed` | Player clicks region on map | `{ from: string, to: string, route: Route }` |
| `travel_resolved` | Engine resolves travel commitment | `{ success: boolean, region: string, consequences: [] }` |

On receiving an event, the map re-fetches `GET /map` or applies the delta directly. No optimistic updates — the map waits for engine confirmation before reflecting changes.

### 18.6 Travel Action Sequence

```
Player clicks region
  → Map emits travel proposal
  → Bridge forwards: POST /command { type: "travel", to: "region_id" }
  → Engine checks route requirements
  → IF requirements unmet:
      → Bridge returns requirement details + alternatives
      → Map displays route options (standing, contact, resource, risky)
      → Player selects approach or cancels
  → IF requirements met (or alternative chosen):
      → Confirmation UI: "Travel to [region]? This will use your turn."
      → Player confirms
      → Commitment Gate: engine resolves deterministically
      → Consequences applied immediately
      → SSE emits region_changed
      → Map updates to new state
```

This sequence enforces the invariant from Section 6: **no interface may bypass the commitment gate.** The map proposes; the engine resolves.

### 18.7 Data Ownership

**The engine is the single source of truth.**

| Data | Owner | Consumers |
|------|-------|-----------|
| Region definitions | `regions.json` | Engine, Bridge |
| Faction definitions | `sentinel-campaign/data/factions/` | Engine, Bridge |
| Campaign state | `Campaign` (schema.py) | Engine, Bridge |
| Map state | `Campaign.map_state` | Engine, Bridge |
| Route requirements | `regions.json` + `Campaign.map_state` | Engine, Bridge |

The map component's static copies of region and faction data (`regions.ts`, `factions.ts`) are **deleted** once the bridge API is live. The component receives all data via `GET /map` — no local state files.

### 18.8 Astro Embedding Strategy

The map component is embedded in `sentinel-ui/` as a **React island** inside the existing Astro layout.

```
sentinel-ui/
  src/
    components/
      WorldMap.tsx        ← React component (moved from standalone)
    pages/
      index.astro         ← Main game view, includes <WorldMap client:load />
    lib/
      bridge.ts           ← Already exists; add fetchMap() and subscribeMapEvents()
```

**Steps:**

1. Move `WorldMap` component and its dependencies into `sentinel-ui/src/components/`
2. Remove standalone Vite app scaffolding (own `index.html`, `main.tsx`, dev server config)
3. Add `@astrojs/react` integration if not already present
4. Import as `<WorldMap client:load />` in the game page
5. Wire props through `bridge.ts` — `fetchMap()` on mount, SSE subscription for updates

The component remains a pure React component. Astro handles hydration. No framework coupling beyond the island boundary.

---

> *SENTINEL finally has a body. And a quiet place to count the cost of surviving in it.*
