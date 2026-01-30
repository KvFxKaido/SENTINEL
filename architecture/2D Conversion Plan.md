SENTINEL 2D Conversion Plan

Current State → Target State

What We Have Now

CLI-driven game loop: Python agent controls flow, player types commands

2D visualization layer: Companion views (map, safehouse, overworld, combat)

LLM as game master: Constant narrative, handles all game flow

Commitment model: All actions go through CLI confirmation


Player Experience: Type commands → LLM narrates → 2D shows what happened

What We Want

2D exploration as primary loop: Player moves character in real-time

Python as game logic backend: State manager + consequence engine

LLM as meaning crystallizer: Invoked only when pressure collapses into dialogue or narrative beats

Spatial commitment model: Move freely, confirm when actions matter


Player Experience: Move/explore in 2D → hesitate/observe → commit to actions → LLM crystallizes meaning → see consequences


---

Architecture Shift


---

Spatial Structure (New)


---

Camera & Perspective — Locked: Isometric View

SENTINEL 2D uses a fixed isometric camera for all local maps. This is a design-binding decision.

Rationale:

Preserves distance without removing presence

Improves legibility of patrols, cover, and chokepoints

Reinforces observation → hesitation → commitment loop

Supports room-scale tactical combat without spectacle



---

Hard Constraints:

Fixed isometric angle (no camera rotation)

Limited zoom range (no tactical zoom-outs)

Small, authored rooms only

Clear occlusion rules (walls fade when blocking the player)

Minimal animation set (idle, move, combat actions only)

UI must never compete with the world view


Non-Goals:

Open-world scale

Cinematic camera motion

Physics-driven interactions


Isometric is a tool for weight and legibility, not visual flourish.


---

Before

Player → CLI → Python Agent → LLM (always) → State Update → 2D Visualization

After

Player → 2D Frontend ──┬→ State Query (constant)
                       │
                       └→ Commit Action → Python Backend ──┬→ Resolve Mechanics
                                                            │
                                                            └→ LLM (selective) → Update State
                                           
Frontend ← State Stream ← Python Backend


---

What Stays (Core Assets)

✅ Game Systems (Python):

Faction reputation tracking

Social energy (Pistachios) system

NPC agenda system (wants, fears, leverage, owes, lie_to_self)

Consequence engine (hinge moments, dormant threads)

Mission structure

Equipment/inventory logic

Enhancement temptation mechanics


✅ Data:

11 faction definitions + philosophies

Region/geography data

Canon lore for RAG retrieval

197 tests covering mechanics


✅ Infrastructure:

Deno bridge architecture

Multiple LLM backend support

State serialization (JSON)



---

What Changes (Orchestration)


---

UI Authority Shift (New)

Main View → Tactical Pause Menu

The current primary UI view (chat log, faction standings, gear, social energy, consequences, etc.) is no longer a live gameplay surface.

It is redefined as a pause-layer interface with strict constraints.

Design Intent:

Preserve legibility without breaking presence

Prevent the UI from competing with spatial play

Centralize reflection, not action


The Pause Menu Is Used For:

At-a-glance information:

Faction standings

Social energy state

Inventory and gear (management, equip/unequip)

Known consequences and dormant threads


Inventory management:

Equip / unequip gear

Reorder loadout

Inspect items and condition

Discard or stash items only if a valid stash exists in the world


Messaging NPC contacts already met in the playthrough

Reviewing past decisions, not making new ones


Design Constraint: Inventory changes do not advance time, but they do respect physical plausibility (you cannot equip what you are not carrying).

The Pause Menu Is Explicitly NOT Used For:

Initiating new world actions

Triggering missions

Forcing dialogue with nearby NPCs

Advancing time


Hard Rule: If something can be done while unpaused, it must not be possible in the pause menu.

This keeps the player body authoritative and prevents menu-driven play from re-emerging.


---

1. Game Loop Authority

From: Python drives turn-based loop
To: Frontend drives real-time exploration, Python responds only to commits

Work:

Remove CLI command parser as primary interface

Python becomes REST/WebSocket API

Frontend maintains local game clock



---

2. State Exposure

From: State hidden behind agent, queried via commands
To: Frontend has direct read access to permitted state

Work:

API endpoints for: NPC positions, faction pressure, patrol routes, POIs

WebSocket for real-time state updates

Frontend caching with invalidation


Constraint: Backend remains source of truth; frontend may optimistically render but must reconcile


---

3. LLM Invocation

From: LLM always in the loop, narrating everything
To: LLM invoked only when ambiguity collapses into meaning

Work:

Separate dialogue/narrative endpoint from game logic

Cache common crystallization responses

Generate dialogue trees only on pressure points, not idle exploration


Design Rule: Silence is a valid (and often preferred) outcome


---

4. Patrol AI

From: Conceptual (not implemented yet)
To: Real-time simulation emphasizing predictability before surprise

Work:

TypeScript patrol behavior engine

Faction-specific movement patterns

Line-of-sight calculations

State sync with Python for consequence tracking


Constraint: Patrols should not be the first source of tension; player vulnerability comes first


---

Conversion Phases

> Structural Note: SENTINEL is not an open world. It is a network of curated locations connected by a strategic layer. This dramatically reduces scope while increasing authorial control.



Phase 0: Foundation (Completed ✓)

[x] Region data structure

[x] MapState APIs

[x] 2D visualization components built

[x] Commitment model prototyped



---

Phase 1: Backend API Refactor (Completed ✓)

Goal: Python becomes stateful REST/WebSocket service

Tasks:

[x] Create FastAPI layer wrapping Python engine


[x] Endpoints:

GET /state – Full game state snapshot

POST /action – Commit player action

POST /dialogue – Crystallize meaning via LLM

WS /updates – Real-time state stream



[x] Refactor agent to be request-response, not loop-driven


[x] Test harness for API endpoints (25 new tests)


[x] Preserve existing test coverage (454 tests still passing)



Success Criteria: ✓

[x] Python tests still pass

[x] Can drive game entirely via HTTP/WebSocket

[x] State persists between requests


Implementation Notes:
- API module: sentinel-agent/src/api/
- Extended endpoints for map, NPCs, patrols, factions, game clock
- WebSocket with subscription management and patrol simulation scaffolding
- State versioning for optimistic update conflict detection



---

Phase 2: Frontend Exploration Loop (Local Maps) — In Progress

Goal: Real-time character movement within small, intentional spaces

Tasks:

[x] 1. Local map template system (tiles, walls, exits)


[x] 2. Character controller (WASD/click movement)


[x] 3. Collision detection (walls, NPCs, objects)


[x] 4. Interaction zones (proximity without auto-commit)


[x] 5. Exit handling between local maps and region hub


[x] 6. Local game clock (pauses during dialogue)


[ ] 7. Explicit separation between observation and commitment



Success Criteria:

[x] Smooth movement in a bounded space

[x] Player immediately understands where they are

[ ] NPC density feels intentional, not crowded

[ ] Leaving a location can quietly advance unresolved threads


Implementation Notes:
- Local map module: sentinel-ui/src/components/localmap/
- Tile-based collision with smooth movement (swept AABB)
- Sample maps: safehouse, market, street (Rust Corridor)
- Game clock with auto-advance, pauses during interaction/menus
- Map transitions with directional animations
- Test page: /localmap?map=safehouse_main


--- (Est: 2–3 weeks)

Goal: Real-time character movement with spatial hesitation

Tasks:

1. Character controller (WASD/click movement)


2. Collision detection (walls, NPCs, objects)


3. Interaction zones (proximity without auto-commit)


4. Local game clock (pauses during dialogue)


5. Explicit separation between observation and commitment



Success Criteria:

Smooth character movement

Player can observe without triggering systems

Player can miss opportunities by moving too slowly

Leaving a space can quietly advance unresolved threads



---

Phase 2.5: Spatial Negative Space (Est: 1 week)

Goal: Teach the game to refuse resolution

Tasks:

1. Define cold spaces:

NPCs visible but unavailable

Objects present but unusable (for now)

Dialogue intentionally disabled



2. Time-based awareness:

NPC posture/routes shift if player lingers

Idle time advances hidden clocks



3. Non-feedback feedback:

Glances, pauses, ambient changes




Success Criteria:

Player can spend 30–60 seconds in a space with no prompts

Tension is felt without UI feedback

Player leaves due to discomfort or uncertainty, not broken flow



---

Phase 3: Patrol AI System (Local Scope)

Goal: NPC movement that supports readable, authored spaces

Tasks:

1. Patrol routes defined per local map (not global)


2. TypeScript patrol simulation tuned for ~10 NPCs


3. Faction behavior patterns expressed spatially:

Lattice: coordinated sweeps across chokepoints

Ember: loose, wandering solo paths

Ghost: static presence → sudden relocation

Covenant: ritualized, time-bound circuits



4. Line-of-sight calculations


5. Alert states (patrolling → investigating → combat)


6. Python validates outcomes on commit



Success Criteria:

Patrol patterns are learnable within minutes

Player reads space before reading UI

Combat triggers feel spatially fair


--- (Est: 1–2 weeks)

Goal: Dynamic NPC movement with readable intent

Tasks:

1. Patrol route generation (TypeScript simulation)


2. Faction behavior patterns:

Lattice: coordinated sweeps

Ember: unpredictable solo paths

Ghost: static presence → sudden relocation

Covenant: ritualized, time-bound routes



3. Line-of-sight calculations


4. Alert states (patrolling → investigating → combat)


5. Python validates outcomes on commit



Success Criteria:

NPC behavior is learnable before it is dangerous

Player plans around patterns, not surprises

Combat triggers feel earned, not random



---

Phase 4: LLM Dialogue Integration (Est: 1–2 weeks)

Goal: Dialogue reframes space, not replaces it

Tasks:

1. Dialogue UI component


2. API call: Frontend → Python → LLM → dialogue tree


3. Faction/disposition-aware responses


4. Social energy cost calculated server-side


5. Dialogue updates NPC memory and faction standing



Constraints:

Some conversations yield less clarity than silence

NPCs may end dialogue autonomously


Success Criteria:

Dialogue meaningfully alters interpretation of space

Social energy can be spent with minimal payoff

NPCs remember timing, not just words



---

Phase 5: Combat Overlay — Locked: Room-Scale Tactical Combat (Est: 2 weeks)

Combat Model (Design-Binding):

> Room-scale tactical resolution
Turn-based, spatial, short-lived, and consequence-forward.



Combat is not a separate game mode. It is an escalation of presence in the same space where failure occurred.


---

Core Characteristics:

Turn-based, alternating initiative

Occurs in the current local map (overlay, not scene switch)

3–6 total combatants maximum

Gridless or micro-grid (room-scale only)

Average duration: 3–6 total rounds



---

Design Rules (Hard Locks):

1. Combat Is a Consequence, Not a Goal
Combat is triggered by detection, escalation, or failed restraint — never as a primary objective loop.


2. Positioning > Abilities
Actions are limited and legible:

Move (expose / reposition)

Fire / Strike (commit violence)

Suppress (buy time)

Interact (doors, cover, environment)

Talk (rare, risky)

Flee (always available)



3. Retreat Is First-Class
Fleeing is always possible unless the player explicitly chose to trap themselves. Retreat carries social and faction consequences, not mechanical punishment.


4. Injuries > HP
Damage creates persistent conditions:

Impaired movement

Reduced accuracy

Gear damage

Visible scars remembered by NPCs


HP exists only as a short-term survival buffer.


5. Fast Resolution or Spiral
Prepared encounters resolve quickly. Unprepared encounters deteriorate rapidly. Long, attritional fights are a failure state.




---

Tasks:

1. Combat state machine (initiative, turns, escalation)


2. Overlay UI (dimmed map, locked camera)


3. Action selection UI (small, explicit choices)


4. Python resolves outcomes; frontend animates


5. Injury, fear, and reputation consequences propagate immediately




---

Success Criteria:

Combat feels avoidable

Retreat feels like survival, not failure

Positioning and preparation matter more than raw stats

Combat leaves lasting marks on the world and the character



---

Phase 6: Consequence Propagation (Est: 1–2 weeks)

Goal: World state visibly changes while player is absent

Tasks:

1. Faction pressure visualization


2. NPC disposition alters movement/avoidance


3. Dormant threads manifest as spatial events


4. Hinge moments lock world state


5. Notifications for off-screen consequences



Success Criteria:

Player can see pressure rising

World reacts without asking permission

Absence is treated as a choice



---

Phase 7: Polish & Tuning (Est: 2–3 weeks)

Goal: The game feels worth returning to

Tasks:

1. Animation and transition polish


2. Audio (ambient, footsteps, subtle cues)


3. Performance optimization


4. Save/load refinement


5. Tutorial that teaches hesitation, not mechanics



Success Criteria:

Controls feel responsive

Performance stable (60fps target)

New player learns by observing

The game tolerates silence



---

Ego Check (Revised)

"Would I accept not knowing for 10 minutes in this version?"

If no, the 2D layer is still ornamental.


---

Art Asset Strategy (New)

Constraint-First Asset Pipeline

Art production for SENTINEL 2D prioritizes consistency, legibility, and constraint over expressiveness or volume. LLMs are treated as junior production tools, not creative directors.


---

Core Principle

> Do not describe vibes. Enforce rules.



Art direction is defined through fixed grammars that the asset generator must comply with. Any output that violates constraints is discarded without iteration.


---

Asset Grammar (Design-Binding)

Camera & Scale

Fixed isometric perspective

Consistent tile ratio across all maps

Character height expressed in tiles (locked)

Doors, walls, and props snap to tile grid


Palette

Muted, desaturated colors only

No pure whites or neons

Metals skew blue-gray

Fabrics skew brown/olive

Blood and damage indicators are dark and restrained


Detail Budget

No micro-texture noise

No decorative clutter

Silhouette clarity > surface detail

Fewer props with clearer purpose



---

Production Stages

1. Blockout Phase (Mandatory)

Flat colors only

No textures

No lighting effects

Focus on proportion, silhouette, and scale


LLM prompts at this stage must request blockouts only. Any textured or stylized output is rejected.

2. Texture & Material Pass (Selective)

Applied only after blockout approval

Limited palette overlays

No additional geometry introduced



---

Shape Before Style

LLMs are never permitted to invent:

Proportions

Silhouettes

Camera framing


These are locked by specification before generation. Texture and color are applied only after shapes are approved.


---

Role-Based Asset Definition

Assets are defined by role, not appearance.

Example:

Guard NPC:

Tall vertical silhouette

Weapon visible at isometric angle

Readable posture at 6 tiles distance



Behavior and placement provide personality; art provides readability.


---

Reuse & Variation Strategy

Single base body per NPC class

Palette swaps for faction identity

One accessory variation maximum per role


Visual variety emerges from behavior, context, and consequence — not bespoke sprites.


---

Reference-Driven Prompting

When generating assets:

Provide 2–4 reference images

Explicitly state what to copy (angle, scale, restraint)

Explicitly state what to ignore (lighting, flourish, detail)


LLMs are better at subtraction than invention.


---

SENTINEL-Specific Allowances

Because the game emphasizes observation and hesitation:

Lower texture fidelity is acceptable

Strong silhouettes are preferred

Heavy shadowing and occlusion are encouraged


This reduces asset load while reinforcing tone.


---

Enforcement Rule

Any asset that requires explanation to be understood is invalid. If it does not read at a glance in motion, it is discarded.


---

Godot Migration Path (Fallback)

(unchanged — architecture remains compatible)