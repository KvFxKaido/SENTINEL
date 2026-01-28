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

> *SENTINEL finally has a body. And a quiet place to count the cost of surviving in it.*
