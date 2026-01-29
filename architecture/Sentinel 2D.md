# SENTINEL — Spatial Embodiment & World Map Consolidated Plan

> **Version:** 2.1 (Consolidated)
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

### Phase 0 — Data Foundation (Complete)

- [x] Region positions
- [x] MapState APIs
- [x] Typed route requirements

### Phase 1 — Strategic Map (SVG) ✓

- [x] Render regions and routes
- [x] Travel proposals
- [x] Content markers

### Phase 2 — Safehouse (Canvas) ✓

- [x] Minimal renderer
- [x] Inventory as physical presence
- [x] Quiet reflection space

### Phase 3 — Overworld ✓

- [x] Single region space
- [x] NPCs and hazards
- [x] Commitment enforcement

### Phase 4 — Expansion ✓

- [x] Multi-region overworlds
- [x] Faction pressure visualization
- [x] Combat integration

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

The Kimi world map prototype (`architecture/Kimi_Agent_Astro Map Integration/`) proves the visual layer. This section defines how it connects to the live game.

### 18.1 Data Ownership

The engine is the single source of truth. The map **consumes** — it never stores.

| Data | Owner | Location |
|------|-------|----------|
| Region definitions | Engine | `sentinel-agent/data/regions.json` |
| Region connectivity | Engine | `Campaign.map_state.regions[id].connectivity` |
| Current region | Engine | `Campaign.map_state.current_region` |
| Route requirements | Engine | `regions.json` routes + `schema.py` models |
| Faction standings | Engine | `Campaign.faction_standings` |
| NPCs per region | Engine | Derived from `Campaign.npcs` by location |
| Active jobs/threads | Engine | Derived from `Campaign.jobs` / `Campaign.threads` |

Kimi's static `regions.ts` and `factions.ts` are deleted at integration time. The map component receives all data via props hydrated from the bridge API.

### 18.2 Bridge Map API

New endpoints on the Deno bridge (`localhost:3333`):

#### `GET /map`

Returns the complete map state for the current campaign.

```json
{
  "ok": true,
  "current_region": "rust_corridor",
  "regions": {
    "rust_corridor": {
      "connectivity": "embedded",
      "markers": [
        { "type": "current" },
        { "type": "npc", "count": 3 },
        { "type": "job", "count": 1 }
      ]
    },
    "breadbasket": {
      "connectivity": "connected",
      "markers": [
        { "type": "thread", "count": 1 }
      ]
    },
    "frozen_edge": {
      "connectivity": "disconnected",
      "markers": []
    }
  }
}
```

Content markers are **aggregated server-side** from campaign state:

| Marker | Source |
|--------|--------|
| `current` | `map_state.current_region` |
| `npc` | NPCs whose `location` matches the region |
| `job` | Active jobs assigned to the region |
| `thread` | Dormant threads with region-scoped triggers |
| `locked` | Adjacent region where no route requirements are met |
| `risky` | Adjacent region reachable only via risky alternatives |

#### `GET /map/region/:id`

Returns detailed region info including route feasibility for the current player.

```json
{
  "ok": true,
  "region": {
    "id": "northeast_scar",
    "name": "Northeast Scar",
    "description": "...",
    "primary_faction": "architects",
    "contested_by": ["nexus"],
    "terrain": ["urban", "ruins", "contaminated"],
    "connectivity": "aware",
    "hazards": ["radiation", "structural_collapse"],
    "points_of_interest": ["Manhattan Quarantine Zone", "..."]
  },
  "routes_from_current": [
    {
      "from": "rust_corridor",
      "to": "northeast_scar",
      "requirements": [
        { "type": "faction", "faction": "architects", "min_standing": "neutral", "met": false }
      ],
      "alternatives": [
        { "type": "contact", "faction": "ghost_networks", "description": "Smuggler route through ruins", "available": true },
        { "type": "risky", "description": "Sneak through at night", "cost": { "social_energy": 2 }, "consequence": "architects_noticed" }
      ],
      "traversable": true,
      "best_option": "contact"
    }
  ],
  "content": {
    "npcs": ["Wei", "Kol"],
    "jobs": [],
    "threads": ["architect_credentials"]
  }
}
```

The `met` field on requirements and `available` field on alternatives are resolved server-side against current campaign state (standings, vehicles, contacts, story flags).

#### `POST /command` (existing — travel action)

Travel is proposed through the existing command interface:

```json
{ "cmd": "slash", "command": "travel", "args": ["northeast_scar"] }
```

The engine validates route requirements, consumes the turn, and resolves consequences. No new endpoint needed — travel is a commitment like any other.

### 18.3 Map Event Stream

The existing SSE stream (`GET /events`) gains map-relevant event types:

| Event | Trigger | Data |
|-------|---------|------|
| `region_changed` | Travel resolved | `{ from, to, session }` |
| `connectivity_updated` | NPC met, job done, thread resolved | `{ region, old, new, reason }` |
| `marker_changed` | Job/NPC/thread added or removed in region | `{ region, markers }` |
| `route_status_changed` | Faction standing shift unlocks/locks route | `{ from, to, traversable, reason }` |

The map subscribes to the SSE stream and re-renders on these events. No polling.

### 18.4 Travel Action Sequence

This is the commitment gate (Section 6) made concrete in the UI:

```
1. Player clicks region on map
2. Map calls GET /map/region/:id
3. UI displays region detail panel:
   - Region info, connectivity, content
   - Route feasibility (requirements met/unmet)
   - Available alternatives with costs
4. Player selects travel option (direct, alternative, or cancel)
5. UI shows confirmation dialog:
   "Travel to Northeast Scar via Ghost Networks smuggler route?
    Cost: 1 turn
    Consequence: owes Ghost Networks a favor"
6. Player confirms
7. Map calls POST /command { cmd: "slash", command: "travel", args: ["northeast_scar", "--via", "contact"] }
8. Engine resolves:
   - Validates requirements
   - Consumes turn
   - Updates current_region
   - Applies consequences (favor owed, social energy cost, etc.)
   - Emits region_changed event
9. SSE delivers region_changed to map
10. Map re-renders with new state
```

**Cancellation at any step before 7 has zero side effects.** This is the commitment gate in action — the UI proposes, the engine resolves.

### 18.5 Component Integration

The Kimi prototype is a standalone React + Vite app. Integration path into `sentinel-ui/` (Astro):

#### Strategy: React Island

Astro supports [React component islands](https://docs.astro.build/en/guides/integrations-guide/react/) — interactive React components embedded in otherwise static Astro pages.

```
sentinel-ui/
├── src/
│   ├── components/
│   │   └── map/                    # Extracted from Kimi prototype
│   │       ├── WorldMap.tsx        # Main component (props-driven, no static data)
│   │       ├── RegionNode.tsx
│   │       ├── ConnectionLines.tsx
│   │       ├── MapTooltip.tsx
│   │       ├── MapLegend.tsx
│   │       └── RegionDetail.tsx    # New: detail panel + travel confirmation
│   ├── pages/
│   │   └── index.astro             # Main game view — embeds <WorldMap client:load />
│   └── lib/
│       └── bridge.ts               # Existing bridge client — add map methods
```

#### What migrates from Kimi prototype

| Keep | Discard |
|------|---------|
| `WorldMap.tsx` (refactored to props-only) | `regions.ts` (static data) |
| `RegionNode.tsx` | `factions.ts` (static data) |
| `ConnectionLines.tsx` | `App.tsx` (demo harness) |
| `MapTooltip.tsx` | `ui/` components (use sentinel-ui's existing library) |
| `MapLegend.tsx` | Vite config, Tailwind config (use sentinel-ui's) |
| `types/map.ts` (aligned to engine schema) | |
| CSS variables and faction colors | |

#### Bridge Client Additions

```typescript
// sentinel-ui/src/lib/bridge.ts — new methods

async getMapState(): Promise<MapState>
async getRegionDetail(regionId: string): Promise<RegionDetail>
async travel(regionId: string, via?: string): Promise<CommandResult>
onMapEvent(handler: (event: MapEvent) => void): () => void
```

### 18.6 Data Alignment

The Kimi TypeScript types and engine Python models must stay in sync. The canonical direction is **Python → TypeScript**.

| Python (schema.py) | TypeScript (map.ts) | Notes |
|---------------------|---------------------|-------|
| `Region` enum | `Region` type | Same string values |
| `RegionConnectivity` enum | `RegionConnectivity` type | Same string values |
| `RegionState` model | `RegionState` interface | TS version omits methods |
| `MapState` model | `MapState` interface | TS version is the API response shape |
| `RouteRequirement` model | `RouteRequirement` interface | TS adds `met: boolean` from API |
| `RouteAlternative` model | `RouteAlternative` interface | TS adds `available: boolean` from API |
| `FactionName` enum | `Faction` type | Same string values |

If `schema.py` changes, the bridge must update its serialization and the TypeScript types must follow. The Kimi prototype's types are already close — minor field name casing differences (`minStanding` → `min_standing`) resolve during migration.

### 18.7 What the Map Does Not Do

Restating the invariants from Section 4 in integration terms:

- The map **never writes** to campaign state directly
- The map **never skips** the confirmation step
- The map **never resolves** route requirements client-side (it displays server-resolved `met`/`available` fields)
- The map **never polls** — it subscribes to SSE
- The map **renders correctly with no data** — a new campaign shows 11 disconnected regions and that's it
- If the bridge is down, the map shows last-known state with a connection indicator — the CLI still works

---

> *SENTINEL finally has a body. And a quiet place to count the cost of surviving in it.*