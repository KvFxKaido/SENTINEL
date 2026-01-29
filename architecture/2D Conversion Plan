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

Phase 0: Foundation (Completed ✓)

[x] Region data structure

[x] MapState APIs

[x] 2D visualization components built

[x] Commitment model prototyped



---

Phase 1: Backend API Refactor (Est: 2–3 weeks)

Goal: Python becomes stateful REST/WebSocket service

Tasks:

1. Create FastAPI layer wrapping Python engine


2. Endpoints:

GET /state – Full game state snapshot

POST /action – Commit player action

POST /dialogue – Crystallize meaning via LLM

WS /updates – Real-time state stream



3. Refactor agent to be request-response, not loop-driven


4. Test harness for API endpoints


5. Preserve existing test coverage



Success Criteria:

Python tests still pass

Can drive game entirely via HTTP/WebSocket

State persists between requests



---

Phase 2: Frontend Exploration Loop (Est: 2–3 weeks)

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

Phase 3: Patrol AI System (Est: 1–2 weeks)

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

Phase 5: Combat Overlay (Est: 2 weeks)

Goal: Tactical combat with narrative consequence

Tasks:

1. Combat state machine (initiative, turns, actions)


2. Action selection UI


3. Targeting system


4. Python resolves outcomes; frontend animates


5. Reputation and injury consequences propagate



Success Criteria:

Combat rewards preparation and positioning

Stealth vs violence meaningfully diverge

Fleeing or negotiating is always possible



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

Godot Migration Path (Fallback)

(unchanged — architecture remains compatible)


---

Final Note: The remaining work is not about responsiveness or content. It is about withholding. The 2D layer must sometimes stare back and say nothing.