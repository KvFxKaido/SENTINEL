Sentinel — Map Integration into Turn-Based Play

Purpose

Integrate the existing world map into Sentinel as a turn-scoped decision surface, not a free-navigation UI. The map exists to propose player intent, which the core game loop resolves deterministically.

The map must:

Respect turn-based pacing

Preserve system authority over outcomes

Reduce LLM responsibility to narration only

Core Design Rule (Non‑Negotiable)

The map never mutates state directly.

Map interactions only generate action proposals. State changes occur exclusively during turn resolution.

Revised Turn Loop

Turn Start

World state is loaded

Map renders current connectivity, markers, routes

Present Options (Map Phase)

Player reviews regions, routes, jobs, threads, NPC presence

Map highlights valid and risky actions

Player Chooses ONE Map Action

Travel attempt

Commit attention to a region

Recon / risky probe

Resolution Phase (System Authority)

Validate requirements

Apply costs

Trigger consequences

Mutate campaign state

Narrative Reaction (Optional)

LLM narrates outcome

NPC dialogue, tone, flavor only

Turn End

Updated map state rendered

Map Action Types

1. Travel Attempt

Trigger: Click adjacent region node

Behavior:

Checks route requirements

If unmet, presents alternatives (contact, bribe, risky)

Player selects method

Travel consumes the entire turn

Resolution:

Costs applied (social energy, credits, time)

Possible dormant threads queued

Connectivity updated (aware / connected)

2. Commit Attention (Remote Action)

Trigger: Click region with jobs, threads, or known NPCs

Behavior:

No physical movement

Represents focus, outreach, influence

Possible Outcomes:

Advance or surface a thread

Unlock a job

Receive intel

Establish contact

Increase region connectivity

Resolution:

One turn consumed

Network density updated

3. Recon / Risky Probe

Trigger: Click disconnected or blocked region

Behavior:

Player is warned of uncertainty

Offered a risky attempt

Resolution:

Pay social energy or accept consequence

Region may become aware

Dormant threads may trigger

Map as Proposal, Not Control

InteractionEffectHoverInformation onlyClickAction proposalConfirmLocks intent for this turnEnd TurnResolution fires 

No free movement. No immediate teleportation. No real‑time traversal.

Data Flow

Map → Engine

{ "action": "travel", "from": "rust_corridor", "to": "appalachian_hollows", "method": "risky", "cost": { "social_energy": 1 } } 

or

{ "action": "commit_attention", "region": "gulf_passage", "intent": "thread" } 

Engine Responsibilities

Validate action

Apply deterministic rules

Mutate campaign state

Emit events

UI Responsibilities

Render updated map

Display consequences

Forward events to narrative layer

LLM Boundary (Hard Rule)

The LLM may:

Narrate outcomes

Voice NPC reactions

Describe environments

The LLM may NOT:

Choose actions

Resolve travel

Modify state

Invent mechanics

If the LLM fails or is removed, the turn must still resolve correctly.

UI Integration Phases

Phase 1 — Dispatcher

Map emits typed action proposals

No visual overhaul required

Phase 2 — Confirmation Layer

Action preview modal

Costs and risks shown explicitly

Phase 3 — Feedback Loop

Map updates only after turn resolution

Visual markers reflect new state

Success Criteria

The integration succeeds if:

Every map interaction costs a turn

Players use the map to decide what matters next

Travel feels consequential, not connective

LLM dialogue feels optional, not load‑bearing

The map tells the story of player commitment

Design Summary

You are not adding a map. You are adding commitment pressure.

The map becomes the clearest expression of player intent in Sentinel’s turn economy.

