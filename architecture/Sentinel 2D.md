SENTINEL  Spatial Embodiment Refactor Plan

Version: 2.1
Date: January 28, 2026
Author: Shawn Montgomery
Status: Design-binding proposal

Executive Summary

SENTINEL is a turn-authoritative game about aftermath.
A deterministic, consequence-driven narrative system that began as a terminal-mediated simulator

The problem is not depth, realism, or narrative quality.

The problem is presence.

Players do not inhabit SENTINEL.
They operate it.

This refactor introduces a minimal 2D spatial layer whose purpose is phenomenological embodiment, not simulation. The spatial layer gives the system a body — most importantly, a place where consequences can be quietly accounted for.

Design North Star

Presence in SENTINEL is felt when the player quietly accounts for what they still have, in a place that is only temporarily safe.

This refactor is designed around reflection, aftermath, and ownership, not action spectacle.

Core Design Invariants (Non-Negotiable)

The refactor must not compromise:

Determinism

Consequence integrity

Turn authority

Replayability

System truthfulness

LLM optionality

If the spatial client, CLI, or LLM is removed, the game must still function correctly.

Any feature that violates this invariant is out of scope.

The Actual Problem (Restated)

SENTINEL already models:

Irreversible decisions

Long-tail consequences

Faction memory and leverage

Avoidance as choice

However, these are currently accessed through abstract interfaces (CLI/TUI), which:

Position the player as an operator, not a body

Obscure proximity, risk, and commitment

Compress reflection into menus and commands

The result is cognitive engagement without embodied presence.

High-Level Solution

Introduce a 2D spatial embodiment layer that:

Provides situational and emotional context

Makes safety, danger, and proximity legible

Creates spaces for reflection (especially the safehouse)

Preserves turn-authoritative gameplay

This layer is not a simulation engine.
It is a lens through which decisions are framed.

Spatial Layer Overview

Key Principle

Movement creates presence, not progress.

Real-time movement is cosmetic and non-authoritative

Time does not advance through movement

State does not mutate through proximity alone

All meaningful change passes through the Commitment Gate.

The Safehouse (Anchor Space)

The safehouse is the emotional and mechanical anchor of the spatial layer.

Purpose

The safehouse exists to:

Allow quiet accounting of consequences

Surface loss, scarcity, and obligation

Frame inventory as history, not loot

Provide temporary safety without permanence

It is not a hub of activity.
It is a place of aftermath.

Safehouse Characteristics

No time pressure

No surprise state changes

No forced interactions

Minimal ambient motion

The player is alone unless they explicitly invite interruption.

Inventory as Presence

Inventory is not just gear. It is what remains.

Inventory may include:

Physical items

Damaged or degraded equipment

Vehicles with condition tags

Favors owed or callable

Compromised intel

NPC access gained or lost

Empty slots where things used to be

Items may carry tags such as:

Promised

Compromised

Will be noticed if used again

Illicit

Last resort

No narration is required.
Absence is itself information.

Overworld Model (Non-Authoritative)

Overworld Properties

2D top-down or isometric space

Player moves freely (WASD or equivalent)

NPCs occupy fixed or patrolled positions

Hazards, exits, and points of interest are visible

Critical Constraint

Overworld movement does not consume turns.

No time advancement

No state mutation

No accidental commitments

The overworld exists to make:

distance

exposure

hesitation
legible.

The Commitment Gate (Authoritative Rule)

All meaningful actions pass through the Commitment Gate.

What Counts as a Commitment

Examples include:

Initiating combat

Accepting or completing a job

Making contact that spends resources

Calling in a favor

Traveling between regions

Advancing faction or narrative threads

Commitment Properties

Every commitment:

Consumes exactly one turn

Is resolved deterministically

Applies consequences immediately

Triggers optional narrative reaction after resolution

No interface may bypass this gate — including the CLI.

Combat Model (Hybrid)

Combat is always a commitment.

When combat is initiated:

Overworld movement freezes

Turn order is established

Combat resolves fully in turn-based mode

Consequences cascade into campaign state

Optional narration reacts

Control returns to overworld or safehouse

There is no real-time combat resolution.

Combat should feel costly, disruptive, and memorable.

Narrative Layer (LLM — Optional)

LLMs are used only for:

Dialogue

Descriptive flavor

Emotional reaction

LLMs may never:

Resolve mechanics

Choose outcomes

Mutate state

If the LLM is removed, the game remains fully playable.

CLI Reclassification (Binding)

The CLI is no longer a primary gameplay surface.

It functions as:

Developer console

Debugging and balance harness

Scenario injector

State inspection tool

The CLI must obey the same Commitment Gate as all other interfaces.

Architecture Overview

[ Spatial Client (2D) ] ↓ [ Commitment Dispatcher ] ↓ [ Turn Resolver (sentinel-agent) ] ↓ [ State + Consequence Engine ] ↓ [ Optional Narrative Layer (LLM) ] 

Phased Implementation Plan

Phase 1 — Safehouse MVP

Single safehouse scene

Inventory view with tags and absences

No NPCs

No combat

One exit leading to a single overworld space

Goal: Validate reflective presence.

Phase 2 — Overworld Embodiment

One small overworld region

One NPC with proximity-based interaction

One visible hazard

One irreversible commitment

Goal: Validate spatial framing of decisions.

Phase 3 — Commitment Enforcement

Lock all state changes behind Commitment Gate

Visual feedback for costs and consequences

Ensure replay determinism

Goal: Validate authority across interfaces.

Phase 4 — Expansion

Additional regions

Faction pressure visualization

Job chains

Cascading consequences

Goal: Validate depth without simulation drift.

Success Criteria

This refactor succeeds if:

Players feel grounded in space

Inventory feels like history, not loot

Decisions feel costly and irreversible

The game is playable without LLMs

The system remains deterministic

Final Note

This is not a pivot away from SENTINEL.

It is SENTINEL finally receiving a body —
and a quiet place to count the cost of surviving in it.
