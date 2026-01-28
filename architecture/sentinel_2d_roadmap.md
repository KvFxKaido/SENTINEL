# SENTINEL — 2D Implementation Roadmap

> **Purpose:** Unified implementation plan for SENTINEL's 2D spatial layer — from strategic map to embodied overworld.
>
> **Status:** Draft
> **Date:** January 28, 2026
> **Synthesizes:** `Sentinel 2D.md`, `Turn Based Map Integration.md`, `world_map_system_plan.md`

---

## What This Document Is

Three design documents define SENTINEL's 2D vision:

| Document | Scope | Focus |
|----------|-------|-------|
| `Sentinel 2D.md` | Spatial embodiment refactor | Presence, safehouse, commitment gate, combat |
| `Turn Based Map Integration.md` | Map as decision surface | Turn-scoped actions, map proposals, system authority |
| `world_map_system_plan.md` | Interactive world map | Social connectivity, negotiable gates, network density |

Each is well-reasoned. None is an implementation roadmap. This document sequences them into buildable phases with concrete technology decisions, dependencies, and exit conditions.

---

## Design Constraints (Inherited)

From the existing documents and design philosophy:

1. **Sentinel is the engine** — No state mutation outside the Python backend
2. **Turn authority is non-negotiable** — All meaningful actions pass through the Commitment Gate
3. **LLM optionality** — Game must function without the narrative layer
4. **Movement creates presence, not progress** — Real-time movement is cosmetic
5. **Boring is correct** — Predictable, explicit, auditable behavior
6. **Fewer features > more coherence** — Every addition must justify its cognitive cost
7. **Local-first, offline-capable** — No required network, no required servers beyond local bridge

---

## Two Tracks, One Roadmap

The 2D layer splits into two distinct rendering problems:

| Track | What | Rendering | Interaction Model |
|-------|------|-----------|-------------------|
| **Strategic Map** | Region graph, social connectivity, travel proposals | SVG (DOM-based) | Click → Propose → Confirm → Resolve |
| **Spatial Embodiment** | Safehouse, overworld, proximity, NPCs | Canvas (pixel-based) | WASD movement → Commitment Gate for actions |

These tracks share the same data model but differ in rendering technology, interaction pattern, and design intent. The strategic map is a **decision tool**. The spatial layer is a **presence system**.

The roadmap interleaves them because they share infrastructure and because the map validates data before the spatial layer depends on it.

---

## Technology Decisions

### Strategic Map: SVG

**Why SVG over Canvas for the map:**
- DOM-native — works with Astro's vanilla JS, no framework needed
- Accessible — screen readers, keyboard navigation, semantic elements
- Interactive — CSS hover states, click handlers, transitions
- Resolution-independent — scales cleanly at any zoom level
- Inspectable — visible in DevTools, debuggable

**What this means in practice:**
- Map nodes are `<g>` groups with `<circle>`, `<text>`, `<path>` elements
- Faction colors applied via CSS variables (already defined in the theme)
- Connectivity states control `opacity`, `fill`, `stroke-dasharray`
- Transitions via CSS (`transition: opacity 0.3s`) — no animation library needed

**Embedded in:** `sentinel-ui` as a new Astro component with a `<script>` island

### Spatial Layer: Canvas + Minimal Custom Renderer

**Why Canvas over SVG for the overworld:**
- Pixel-level control for the safehouse and overworld scenes
- Performant for real-time movement (60fps loop, even if cosmetic)
- Camera/viewport panning without DOM reflows
- Sprite-based NPC and item rendering

**Why custom renderer over Pixi.js/Phaser:**
- SENTINEL's spatial needs are minimal — one room, one overworld area, positioned entities
- No physics, no particle systems, no complex animations
- A game framework would violate "fewer features > coherence"
- Custom code is auditable and has zero dependency risk
- Estimated renderer: ~300-500 lines for the initial scope

**Reconsidering point:** If Phase 4 (overworld expansion) reveals that the custom renderer is accumulating complexity beyond ~1000 lines, evaluate Pixi.js as a targeted replacement. This is a known decision gate, not a surprise.

### Shared: Bridge API Extensions

Both tracks consume data from the same source: the Bridge API. New endpoints needed:

```
GET  /map/state          → MapState (connectivity, current region)
GET  /map/regions        → Full region graph (routes, requirements, alternatives)
POST /map/travel         → Travel proposal (returns options or confirms)
POST /map/action         → Generic map action (commit attention, recon)
```

These are thin wrappers around existing Sentinel commands. No new game logic in the bridge.

---

## Phase 0 — Data Model Validation

**Goal:** Confirm that the existing data model supports both tracks.

### What Exists

| Component | Status | Location |
|-----------|--------|----------|
| `Region` enum (11 regions) | Done | `schema.py` |
| `RegionConnectivity` enum | Done | `schema.py` |
| `RegionState` model | Done | `schema.py` |
| `MapState` model | Done | `schema.py` |
| `regions.json` with routes | Done | `data/regions.json` |
| Negotiable gates (alternatives, risky traversal) | Done | `data/regions.json` |
| `map_state` on Campaign | Done | `schema.py` |

### What Needs Work

1. **Bridge API surface for map data** — Currently `campaign_state` returns `region` as a string. Need dedicated map endpoints that return full `MapState` and route graph.

2. **Region position data** — `regions.json` has no coordinates for visual layout. Add:
   ```json
   "rust_corridor": {
     "position": { "x": 0.55, "y": 0.40 },
     ...
   }
   ```
   Positions are normalized (0-1) and mapped to viewport by the renderer. Rough geographic accuracy, not cartographic precision.

3. **Travel command formalization** — The `/region` slash command handles travel, but the bridge needs a structured travel endpoint that returns requirement checks, alternatives, and costs before confirming.

### Exit Condition

- Bridge returns full MapState via `GET /map/state`
- Bridge returns region graph with positions and routes via `GET /map/regions`
- Bridge accepts travel proposals via `POST /map/travel` and returns options
- All data flows through existing Sentinel commands — no logic in bridge

---

## Phase 1 — Strategic Map (SVG)

**Goal:** An interactive map that shows where you are, what you know, and what it costs to move.

**Depends on:** Phase 0

### 1.1 — Static Map Render

Build the SVG component that renders the 11-region node graph.

**Deliverables:**
- New Astro component: `MapView.astro` with `<script>` island
- SVG render function that takes MapState and region graph data
- Region nodes positioned by coordinates from `regions.json`
- Route lines between adjacent regions
- Faction colors on nodes (using existing CSS variables)
- Connectivity-based visual states:

```
Disconnected:  dim node, name only if adjacent
Aware:         outlined node, "?" marker
Connected:     filled outline, full label
Embedded:      solid fill, glow/pulse
```

- Current location marker (pulsing indicator)
- Legend bar at bottom

**Integration:**
- Fetch data from `GET /map/state` and `GET /map/regions`
- Render into a panel within the existing 3-column layout (replaceable with the WORLD panel, or a dedicated map mode)
- Update on SSE events that affect map state (travel, faction changes)

**Exit Condition:**
- Map renders all 11 regions with correct connectivity states
- Current location is clearly indicated
- Faction control is visible via color
- Route lines distinguish open/conditional/contested passages

### 1.2 — Interactive Travel

Add click interactions that propose travel actions.

**Deliverables:**
- Click region → show travel options panel
- If requirements unmet, show:
  - What's blocking (faction standing, vehicle, contact)
  - Available alternatives (bribe, smuggler route, risky traversal)
  - Costs for each option
- Confirm button locks intent for this turn
- Resolution fires via bridge, map updates after turn resolves
- Cancel option to back out before confirmation

**Interaction flow:**
```
Hover region    → Tooltip: name, faction, connectivity, content count
Click region    → Travel panel: requirements, alternatives, costs
Select method   → Cost confirmation: "This will cost 2 social energy"
Confirm         → POST /map/travel → Sentinel resolves → Map updates
```

**Critical constraint:** No state change on click. Only proposals. State changes on confirmation only, after Sentinel resolves.

**Exit Condition:**
- Player can travel between regions using the map
- Requirements and alternatives are shown before commitment
- Map updates only after turn resolution (not optimistically)
- Travel consumes a turn (visible in UI)

### 1.3 — Content Markers

Show what's happening where.

**Deliverables:**
- Job markers (diamond) on regions with available jobs
- Thread markers (lightning) on regions with anchored dormant threads
- NPC markers (dot with count) on regions with known NPCs
- Hover reveals marker details
- Click marker navigates to relevant detail (job board, thread log, NPC list)

**Depends on:** Content anchoring data — jobs, threads, and NPCs need `region` fields populated. This is partially done (jobs have `region`), but threads and NPCs may need schema work.

**Exit Condition:**
- Active jobs visible on the map by region
- Dormant threads show spatial anchoring
- Known NPCs show where they are
- Map tells the player "what matters where"

---

## Phase 2 — Safehouse (Canvas)

**Goal:** A quiet room where inventory feels like history and safety feels temporary.

**Depends on:** Phase 0 (data model). Independent of Phase 1 (map).

This is the emotional anchor of the spatial layer. See `Sentinel 2D.md` for full design rationale.

### 2.1 — Canvas Renderer Foundation

Build the minimal custom renderer.

**Deliverables:**
- Canvas element embedded in a new Astro component: `SpatialView.astro`
- Render loop (requestAnimationFrame, 60fps target)
- Camera/viewport system (fixed for safehouse, pannable later for overworld)
- Tile-based or free-position entity placement
- Sprite loading from `assets/` directory (PNG)
- Basic entity types: `player`, `item`, `furniture`, `exit`

**Architecture:**
```
SpatialRenderer
├── Camera (position, viewport, zoom)
├── Scene (entity list, sorted by y-position for depth)
├── InputHandler (keyboard state, WASD → velocity)
└── EntityRenderer (sprite + position → canvas draw)
```

No physics engine. No collision detection beyond simple rectangular overlap checks. Movement is cosmetic — the player can walk through walls if they want. This is not a simulation.

**Exit Condition:**
- Canvas renders a scene with positioned entities
- Player entity moves with WASD input
- Frame rate is stable (60fps with <10 entities)
- Renderer is under 500 lines

### 2.2 — Safehouse Scene

The first playable space.

**Deliverables:**
- Single-room scene with sparse furnishing
- Player character (top-down sprite, 4-directional or single facing)
- Inventory items placed physically in the room:
  - Gear on a table/shelf
  - Vehicles visible outside (window or door)
  - Favor tokens / NPC tokens on a board
  - Empty spaces where things used to be
- Item tags visible on proximity (`Promised`, `Compromised`, `Last resort`)
- Exit point leading to overworld (Phase 3) or map (Phase 1)
- No NPCs. No time pressure. No surprise state changes.

**Inventory as Presence:**
Items aren't just listed — they're placed. When you lose something, there's an empty space. This is the core emotional beat of the safehouse.

```
┌──────────────────────────────────────────┐
│                 SAFEHOUSE                 │
│                                          │
│   ┌─────┐         ┌──────────┐           │
│   │BOARD│         │  TABLE   │           │
│   │     │         │ [Knife]  │           │
│   │ ○○  │         │ [Radio]  │           │
│   │ ○_  │ ←empty  │ [      ] │ ←empty   │
│   └─────┘         └──────────┘           │
│                                          │
│              ☺ (you)                     │
│                                          │
│   ┌─────┐                    ┌─────┐     │
│   │SHELF│                    │ EXIT │     │
│   │[Med]│                    │  →   │     │
│   └─────┘                    └─────┘     │
└──────────────────────────────────────────┘
```

**Data flow:**
- Fetch character gear, vehicles, favors from `GET /state`
- Map inventory items to physical positions in the room
- Empty slots derived from gear capacity minus current gear
- Item tags from Sentinel state (no local derivation)

**Exit Condition:**
- Player can walk around the safehouse
- Inventory is physically placed, not listed
- Empty slots are visible (absence is information)
- Item tags are readable on proximity
- The room feels quiet — no urgency, no flashing, no prompts

### 2.3 — Safehouse Polish

After the MVP validates, add texture.

**Deliverables:**
- Ambient details: dim lighting, sparse furniture, salvaged tech aesthetic
- Item interaction: walk to item → see detail panel (description, tags, history)
- Sound integration (if sound roadmap Phase 1 is complete): quiet ambient loop
- Day/session indicator (not a clock — more like "Session 4, Night")
- Exit interaction: walking to exit prompts "Leave safehouse?" → transitions to map or overworld

**Exit Condition:**
- Safehouse feels like a place, not a menu
- Players spend time there without being prompted
- "Presence" validated through playtesting

---

## Phase 3 — Overworld (Canvas)

**Goal:** A small spatial area where distance, exposure, and hesitation become legible.

**Depends on:** Phase 2 (renderer exists), Phase 1 (map provides travel context)

### 3.1 — Single Region Overworld

One region rendered as a traversable space.

**Deliverables:**
- Extend Canvas renderer with a larger scene (camera panning)
- Region terrain rendered as tilemap or stylized background
- Points of interest positioned in the space:
  - Faction HQ
  - Markets
  - Safe houses
  - Job locations
- One NPC placed at a fixed or patrolled position
- One visible hazard (environmental danger, checkpoint, etc.)
- Player can move freely (WASD) — movement does not consume turns

**Critical constraint:** Movement is non-authoritative. Walking near an NPC does not initiate dialogue. Walking through a hazard does not apply damage. All meaningful actions require the Commitment Gate.

**Commitment Gate interaction:**
```
Walk near NPC → Proximity indicator appears
Press [E] or click → "Initiate contact?" confirmation
Confirm → Commitment dispatched to Sentinel → Turn consumed → Resolution
```

**Exit Condition:**
- Player can move through a region space
- NPCs and hazards are visible and positioned
- Meaningful actions require explicit commitment
- Movement feels like exploration, not a loading screen

### 3.2 — Commitment Gate Enforcement

Lock all state changes behind the gate.

**Deliverables:**
- Commitment confirmation UI (modal or inline panel):
  - Action description
  - Known costs (social energy, credits, faction standing)
  - Known risks (dormant thread triggers, attention drawn)
  - Confirm / Cancel
- Commitment resolution feedback:
  - Visual indication during resolution ("Resolving...")
  - Outcome display after Sentinel responds
  - Map/scene updates to reflect new state
- Undo prevention: once confirmed, no take-backs (this is SENTINEL)

**Integration:**
- `POST /map/action` sends typed action proposals
- Bridge forwards to Sentinel as commands
- Sentinel resolves deterministically
- UI updates on resolution event

**Exit Condition:**
- No state change occurs without passing through the gate
- Costs are visible before commitment
- Resolution is deterministic and auditable
- The gate works identically whether triggered from map, overworld, or CLI

### 3.3 — Overworld ↔ Map Transitions

Connect the two tracks.

**Deliverables:**
- From map: click "Enter Region" on connected/embedded region → load overworld scene
- From overworld: walk to region exit → return to map with travel options
- Transition effect (fade, or stylized static/scan line effect matching tactical aesthetic)
- State continuity: overworld position persists per-session (not saved to campaign state)

**Exit Condition:**
- Seamless transition between strategic map and regional overworld
- Player understands which layer they're in (map = strategic, overworld = spatial)
- No state confusion between layers

---

## Phase 4 — Expansion

**Goal:** Fill out the remaining regions and deepen spatial content.

**Depends on:** Phase 3 validated

### 4.1 — Multi-Region Overworld

- Overworld scenes for additional regions (prioritize: Rust Corridor, Breadbasket, Desert Sprawl)
- Each region has distinct terrain tileset and ambient feel
- Region-specific points of interest from `regions.json`

### 4.2 — Faction Pressure Visualization

- Faction territory shown as color gradients or border patrols in overworld
- Contested borders have visual tension (overlapping colors, checkpoint NPCs)
- Nexus presence as overlay indicator (surveillance grid, cameras, data nodes)

### 4.3 — Content Density

- Multiple NPCs per region with patrol or station behavior
- Job locations visible in overworld (walk to location to see job details)
- Dormant thread anchors visible as environmental markers
- Secrets revealed in embedded regions (hidden paths, locked areas that open with network density)

### 4.4 — Combat (Hybrid Model)

Per `Sentinel 2D.md`:
- Combat is always a commitment
- Overworld movement freezes when combat initiates
- Turn order established, resolved in turn-based mode
- Consequences cascade into campaign state
- Control returns to overworld or safehouse after resolution

**Implementation note:** Combat UI could be a separate Canvas scene or an overlay on the overworld. Decision deferred until Phase 3 validates the spatial renderer.

---

## Phase 5 — Advanced Features (Deferred)

These are explicitly deferred and not scheduled. Implement only if earlier phases validate the spatial approach.

| Feature | Rationale for Deferral |
|---------|----------------------|
| Fast travel for embedded regions | Needs embedded status to be meaningful first |
| Dynamic faction territory shifts | Needs baseline faction visualization working |
| Secret regions (hinge-unlocked) | Needs hinge system integrated with map |
| Player map annotations | Nice-to-have, not core to presence |
| Multiplayer map sharing | Out of scope for single-player experience |
| Mobile touch controls | Touch input mapping deferred until desktop validated |

---

## Asset Requirements

### Phase 1 (Strategic Map)
- No external assets — SVG rendered procedurally from data
- Faction colors from existing CSS variables
- Optional: region icon sprites (11 small icons) — not blocking

### Phase 2 (Safehouse)
- Player sprite: 32x32 or 48x48, top-down, minimal animation (idle + 4-directional walk)
- Item sprites: 16x16 or 32x32 per item category (weapon, tool, vehicle, token)
- Furniture sprites: table, shelf, board, cot, exit marker
- Tileset: simple floor + wall tiles (dark, industrial, salvaged)
- Style: pixel art, low-color, consistent with "salvaged post-collapse tech" aesthetic

**Art style constraint:** Not retro-nostalgic. Not cute. Functional, sparse, slightly degraded. Think data terminal, not SNES RPG.

### Phase 3 (Overworld)
- Terrain tilesets per region type (urban, mountain, plains, desert, etc.)
- NPC sprites: 32x32, faction-colored accents
- Hazard sprites: checkpoint barrier, contamination marker, patrol indicator
- Point-of-interest markers: building icons, market icon, HQ icon

### Source Options
- Commission pixel artist (consistent style)
- Generate with AI tools (review for consistency)
- Placeholder rectangles until art direction is locked

---

## File Structure (Proposed)

```
sentinel-ui/
├── src/
│   ├── components/
│   │   ├── MapView.astro          # Strategic map (SVG)
│   │   └── SpatialView.astro      # Overworld/Safehouse (Canvas)
│   ├── lib/
│   │   ├── bridge.ts              # (existing) API client
│   │   ├── map/
│   │   │   ├── renderer.ts        # SVG map rendering
│   │   │   ├── interactions.ts    # Click/hover handlers
│   │   │   └── layout.ts          # Node positioning from data
│   │   └── spatial/
│   │       ├── renderer.ts        # Canvas render loop
│   │       ├── camera.ts          # Viewport/panning
│   │       ├── entities.ts        # Entity types + sprites
│   │       ├── input.ts           # Keyboard/mouse input
│   │       └── scenes/
│   │           ├── safehouse.ts   # Safehouse scene definition
│   │           └── overworld.ts   # Region overworld scene
│   └── assets/
│       ├── sprites/               # Character, item, NPC sprites
│       ├── tiles/                 # Terrain tilesets
│       └── map/                   # Map-specific icons (if any)

sentinel-bridge/
├── src/
│   ├── api.ts                     # (extend) Add /map/* endpoints
│   └── types.ts                   # (extend) Add map-related types

sentinel-agent/
├── data/
│   └── regions.json               # (extend) Add position coordinates
├── src/
│   └── state/
│       └── schema.py              # (existing) MapState, RegionState
```

---

## Bridge API Extensions (Detailed)

### `GET /map/state`

Returns the campaign's current map state.

```typescript
interface MapStateResponse {
  ok: true;
  current_region: string;
  regions: Record<string, {
    connectivity: "disconnected" | "aware" | "connected" | "embedded";
    npcs_met: number;
    threads_active: number;
    jobs_available: number;
    network_density: number;
  }>;
}
```

### `GET /map/regions`

Returns the full region graph for rendering.

```typescript
interface RegionGraphResponse {
  ok: true;
  regions: Record<string, {
    name: string;
    description: string;
    primary_faction: string;
    contested_by: string[];
    terrain: string[];
    position: { x: number; y: number };  // 0-1 normalized
    nexus_presence: string;
    points_of_interest: string[];
  }>;
  routes: Array<{
    from: string;
    to: string;
    requirements: RouteRequirement[];
    alternatives: RouteAlternative[];
    terrain: string[];
    travel_description: string;
  }>;
}
```

### `POST /map/travel`

Propose a travel action. Returns options or confirms.

```typescript
// Request
interface TravelProposal {
  target_region: string;
  method?: "direct" | "alternative" | "risky";
  alternative_index?: number;  // Which alternative to use
}

// Response (options available)
interface TravelOptionsResponse {
  ok: true;
  status: "options";
  blocked_by: RouteRequirement[];
  alternatives: RouteAlternative[];
  risky_option: { cost: Record<string, number>; consequence: string } | null;
}

// Response (travel confirmed)
interface TravelConfirmedResponse {
  ok: true;
  status: "confirmed";
  from: string;
  to: string;
  method: string;
  costs_applied: Record<string, number>;
  consequences: string[];
  turn_consumed: true;
}
```

---

## Decision Log

Decisions made in this roadmap and their rationale.

| Decision | Choice | Rationale | Revisit If |
|----------|--------|-----------|------------|
| Map rendering tech | SVG | DOM-native, accessible, works with Astro vanilla JS | Map needs real-time animation (unlikely) |
| Spatial rendering tech | Custom Canvas | Minimal scope, auditable, zero deps | Renderer exceeds ~1000 lines |
| No game framework | Skip Pixi.js/Phaser | SENTINEL's spatial needs are minimal; framework adds unjustified complexity | Combat or multi-entity scenes need physics/particles |
| Map in web UI only | No TUI map | TUI ASCII map is a separate concern (see Phase 4 of world_map_system_plan) | TUI becomes primary play surface again |
| Safehouse before overworld | Phase 2 before 3 | Safehouse is simpler, validates renderer, tests core emotional beat | Overworld proves more valuable in playtesting |
| No optimistic UI updates | Wait for Sentinel resolution | Design philosophy: "truth over smoothness" | Latency makes the game feel broken |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Custom renderer grows too complex | Scope creep, maintenance burden | Hard cap at 1000 lines; evaluate Pixi.js at that threshold |
| Safehouse doesn't feel meaningful | Core emotional beat fails | Playtest early (Phase 2.2); pivot to map-only if safehouse doesn't land |
| Asset art direction inconsistent | Visual incoherence | Lock art style before commissioning; use placeholders until style guide exists |
| Bridge API latency visible during travel | Breaks immersion | Show explicit "Resolving..." state; design philosophy permits honest latency |
| Spatial layer feels disconnected from narrative | Presence without purpose | Ensure commitment gate routes back to narrative layer; combat/dialogue always involve Sentinel |
| Overworld movement feels pointless | "Walking simulator" criticism | Movement surfaces information (proximity reveals, NPC positions, hazard awareness); if not enough, add environmental storytelling elements |

---

## Success Criteria (Per Phase)

### Phase 0
- [ ] Bridge returns map state and region graph
- [ ] Regions have position coordinates
- [ ] Travel proposals work through bridge

### Phase 1
- [ ] Map renders all 11 regions with correct visual states
- [ ] Player can travel between regions using the map
- [ ] Requirements and alternatives are shown before commitment
- [ ] Content markers (jobs, threads, NPCs) visible on map
- [ ] Map updates only after turn resolution

### Phase 2
- [ ] Player can walk around the safehouse
- [ ] Inventory is physically present in the room
- [ ] Empty slots communicate loss
- [ ] Item tags are readable
- [ ] The room feels quiet

### Phase 3
- [ ] Player moves through a region overworld
- [ ] NPCs and hazards are visible
- [ ] All actions pass through the Commitment Gate
- [ ] Transitions between map and overworld work
- [ ] Movement feels like presence, not progress

### Phase 4
- [ ] Multiple regions have overworld scenes
- [ ] Faction pressure is visually legible
- [ ] Combat resolves through the hybrid model
- [ ] Content density makes regions feel lived-in

---

## Relationship to Existing Roadmaps

| Roadmap | Relationship |
|---------|-------------|
| `sentinel_visual_roadmap.md` | Codec system, portraits, and CRT effects are independent. Sound design (Phases 1-2) integrates with safehouse ambient. World Map entry updated to reference this roadmap. |
| `sentinel_cross_platform_implementation_plan.md` | Phases 0-3 of that plan are complete. The 2D layer lives in the web UI (Phase 3's output). Desktop packaging (Tauri) would bundle the 2D layer automatically. |
| `sentinel_sound_roadmap.md` | Sound Phase 1 (presence & latency) pairs naturally with safehouse. Sound Phase 2 (system telemetry) pairs with map events. No dependency — sound is additive. |
| `design-philosophy.md` | Every phase exit condition should be evaluated against the design principles. Specifically: visibility over convenience, truth over smoothness, fewer features > coherence. |

---

## What This Roadmap Is Not

- **Not a game engine architecture.** SENTINEL's engine is Python. The 2D layer is a projection of engine state, not a parallel authority.
- **Not a timeline.** Phases have dependencies and exit conditions, not dates. Build at the pace that produces quality.
- **Not permanent.** If playtesting reveals that the strategic map alone provides sufficient presence, the spatial embodiment phases can be deferred indefinitely. The map is the higher-confidence bet.

---

## Next Steps

1. **Phase 0:** Add position coordinates to `regions.json`, extend Bridge API with `/map/*` endpoints
2. **Art direction:** Decide pixel art style before any sprite work begins (block on this)
3. **Playtest checkpoint:** After Phase 1.2, evaluate whether the map alone provides enough spatial grounding to defer the safehouse
