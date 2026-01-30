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

Phase 2: Frontend Exploration Loop (Local Maps) — Completed ✓

Goal: Real-time character movement within small, intentional spaces

Tasks:

[x] 1. Local map template system (tiles, walls, exits)


[x] 2. Character controller (WASD/click movement)


[x] 3. Collision detection (walls, NPCs, objects)


[x] 4. Interaction zones (proximity without auto-commit)


[x] 5. Exit handling between local maps and region hub


[x] 6. Local game clock (pauses during dialogue)


[x] 7. Explicit separation between observation and commitment



Success Criteria:

[x] Smooth movement in a bounded space

[x] Player immediately understands where they are

[x] NPC density feels intentional, not crowded

[x] Leaving a location can quietly advance unresolved threads


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

Phase 2.5: Spatial Negative Space (Completed ✓)

Goal: Teach the game to refuse resolution

Tasks:

[x] 1. Define cold spaces:

NPCs visible but unavailable

Objects present but unusable (for now)

Dialogue intentionally disabled



[x] 2. Time-based awareness:

NPC posture/routes shift if player lingers

Idle time advances hidden clocks



[x] 3. Non-feedback feedback:

Glances, pauses, ambient changes




Success Criteria:

[x] Player can spend 30–60 seconds in a space with no prompts

[x] Tension is felt without UI feedback

[x] Player leaves due to discomfort or uncertainty, not broken flow

Implementation Notes:
- Awareness module: sentinel-ui/src/components/localmap/awareness.ts
- useNpcAwareness hook tracks proximity, glance behavior, linger detection
- ColdZone system (bounds-based) suppresses interaction prompts and dialogue
- NPCBehaviorState enum: idle, busy, unavailable, aware, alert
- Idle time advances game clock when player lingers (>5s idle)
- Ambient light shifts based on awareness state



---

Phase 3: Patrol AI System (Local Scope) (Completed ✓)

Goal: NPC movement that supports readable, authored spaces

Tasks:

[x] 1. Patrol routes defined per local map (not global)

[x] 2. TypeScript patrol simulation tuned for ~10 NPCs

[x] 3. Faction behavior patterns expressed spatially:

Lattice: coordinated sweeps across chokepoints

Ember: loose, wandering solo paths

Ghost: static presence → sudden relocation

Covenant: ritualized, time-bound circuits


[x] 4. Line-of-sight calculations

[x] 5. Alert states (patrolling → investigating → combat)

[x] 6. Python validates outcomes on commit



Success Criteria:

[x] Patrol patterns are learnable within minutes

[x] Player reads space before reading UI

[x] Combat triggers feel spatially fair (requires Phase 5)

Implementation Notes:
- Patrol engine: sentinel-ui/src/components/localmap/patrol.ts (327 lines)
- Alert system: sentinel-ui/src/components/localmap/alertSystem.ts (138 lines)
- Simulation hook: sentinel-ui/src/components/localmap/usePatrolSimulation.ts (100 lines)
- Faction behaviors: SweepPatrol (Lattice/Steel Syndicate), WanderPatrol (Ember),
  StaticWatch (Ghost), RitualCircuit (Covenant)
- Detection cone rendering with time-of-day range modifiers
- Alert state indicators ('!' marker, color tints) on canvas
- 60fps requestAnimationFrame loop decoupled from React render



---

Phase 4: LLM Dialogue Integration (Completed ✓)

Goal: Dialogue reframes space, not replaces it

Tasks:

[x] 1. Dialogue UI component

[x] 2. API call: Frontend → Python → LLM → dialogue tree

[x] 3. Faction/disposition-aware responses

[x] 4. Social energy cost calculated server-side

[x] 5. Dialogue updates NPC memory and faction standing



Constraints:

Some conversations yield less clarity than silence

NPCs may end dialogue autonomously


Success Criteria:

[x] Dialogue meaningfully alters interpretation of space

[x] Social energy can be spent with minimal payoff

[x] NPCs remember timing, not just words (requires backend integration)

Implementation Notes:
- DialogueOverlay component: sentinel-ui/src/components/localmap/DialogueOverlay.tsx
- Game API client: sentinel-ui/src/lib/gameApi.ts (talks to FastAPI at localhost:8000)
- Mock fallback when backend unavailable — allows UI testing without Python running
- Typing effect (30ms/char), tone-colored response options
- Social energy bar with color gradient (green/yellow/red)
- Disposition shifts accumulated during dialogue, applied on close
- Map dims during dialogue to focus attention
- Clock pauses during dialogue, advances by spent minutes on close
- Cold zones suppress dialogue initiation



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

[x] 1. Combat state machine (initiative, turns, escalation)

[x] 2. Overlay UI (dimmed map, locked camera)

[x] 3. Action selection UI (small, explicit choices)

[x] 4. Python resolves outcomes; frontend animates

[x] 5. Injury, fear, and reputation consequences propagate immediately


---

Success Criteria:

[x] Combat feels avoidable

[x] Retreat feels like survival, not failure

[x] Positioning and preparation matter more than raw stats

[x] Combat leaves lasting marks on the world and the character

Implementation Notes:
- Combat engine: sentinel-ui/src/components/localmap/combat.ts (495 lines)
- Combat hook: sentinel-ui/src/components/localmap/useCombat.ts (547 lines)
- Overlay UI: sentinel-ui/src/components/localmap/CombatOverlay.tsx (221 lines)
- Triggered when AlertState reaches COMBAT from patrol simulation
- Actions: Move, Fire, Strike, Suppress, Interact, Talk, Flee
- InjuryType enum: grazed, impaired_movement, reduced_accuracy, gear_damaged, bleeding
- NPC AI: fire if visible, seek cover if not, flee if injured
- Backend API: sentinel-agent/src/api/routes.py - combat resolution with injury system
- Faction reputation changes on combat outcome (victory, defeat, fled, negotiated)
- Deterministic hit resolution based on action type and positioning


---

Phase 6: Consequence Propagation (Completed ✓)

Goal: World state visibly changes while player is absent

Tasks:

[x] 1. Faction pressure visualization

[x] 2. NPC disposition alters movement/avoidance

[x] 3. Dormant threads manifest as spatial events

[x] 4. Hinge moments lock world state

[x] 5. Notifications for off-screen consequences



Success Criteria:

[x] Player can see pressure rising

[x] World reacts without asking permission

[x] Absence is treated as a choice

Implementation Notes:
- Consequence engine: sentinel-ui/src/components/localmap/consequences.ts (275 lines)
- Consequence hook: sentinel-ui/src/components/localmap/useConsequences.ts (285 lines)
- FactionPressureOverlay: canvas-based pressure visualization
- NotificationSystem: toast notifications with auto-dismiss, faction-colored borders
- Backend API: sentinel-agent/src/api/routes.py - faction pressure with leverage demands
- NPC patrol behavior varies by faction (sweep, wander, static, ritual patterns)
- Dormant thread checking with spatial triggers and age-based activation
- Combat consequences propagate faction reputation changes


---

Phase 7: Polish & Tuning (Completed ✓)

Goal: The game feels worth returning to

Tasks:

[x] 1. Animation and transition polish

[x] 2. Audio (ambient, footsteps, subtle cues)

[x] 3. Performance optimization

[x] 4. Save/load refinement

[x] 5. Tutorial that teaches hesitation, not mechanics



Success Criteria:

[x] Controls feel responsive

[x] Performance stable (60fps target)

[x] New player learns by observing

[x] The game tolerates silence

Implementation Notes:
- Audio system: sentinel-ui/src/components/localmap/audio.ts (315 lines)
- All sounds procedurally generated via Web Audio API — zero audio file dependencies
- Ambient drones per atmosphere type, footstep variations, alert cues
- Tutorial: sentinel-ui/src/components/localmap/tutorial.ts (160 lines)
- Observation-based teaching: movement first, then prompts, then hints
- OffscreenCanvas tile caching, dust particles, exit pulse animation
- Smooth panel slide-in animations, HUD transitions
- Backend API: Full state persistence via campaign manager
- Game clock with pause/resume for dialogue and menu interactions



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