# SENTINEL: Close Contact — Core Design Spec

**Status: Proposal** — combat system spec for the 1v1 fighting layer;
cite as intent, not law. Moved into this repo 2026-07-30 from the
standalone SCC workspace (`C:\dev\SCC`), text unchanged apart from
markdown headers. The playable Godot prototype lives at
[`prototypes/close-contact/`](../prototypes/close-contact/).

Where the Circuit design (`sentinel_circuit_design.md`) is the
*institution* — cards, purses, witnesses, the showrunner — Close Contact
is the fight at the scale where you can see someone decide to commit a
limb. The institution wraps this game the way it wraps the squad layer;
nothing here redefines it.

---

## 1. Design Pillars

Physical Intent Over Abstraction
Every button corresponds to a limb. Actions should feel like committing a body part, not selecting a move from a list.

Low Move Count, High Readability
Fewer attacks, clearer animations, stronger consequences. The game should be legible at a glance.

Active Defense
Defense requires timing and decision-making. Passive blocking is intentionally weak.

Solo-Dev Realism
All systems must be buildable, testable, and tunable by one developer without bespoke tooling.

## 2. Control Scheme

Face Buttons (Limb Mapping)

A – Left Kick (LK)

B – Right Kick (RK)

X – Left Punch (LP)

Y – Right Punch (RP)

Each button always triggers the same limb. No remapping by stance unless explicitly stated.

Defensive Inputs

LB (Hold) – Block

LB + Limb Button – Limb Parry Attempt

## 3. Movement

Walk Forward / Back

Duck (Crouch)

Jump (Neutral / Forward / Back)

Forward walking speed is slightly faster than backward walking speed to prevent neutral stagnation.

Jumping uses fixed arcs with no mid-air steering. Once airborne, trajectory is locked.

Jumping is a committal evasive action, primarily used to avoid low attacks.

While airborne:

No blocking

No parrying

No ducking

Limited or no air attacks (by default)

Landing carries recovery frames and cannot be immediately defended.

No air dashing. Limited jump height and hangtime to preserve grounded play.

## 4. Close Contact Doctrine (Training Extract)

ARCHIVAL NOTE — SENTINEL NETWORK / HUMAN DISTRIBUTED RECORDS
Designation: CLOSE CONTACT
When ranged deterrence fails, when ammunition is scarce, when retreat is no longer possible, conflict collapses into proximity.

Close Contact is not a style of combat. It is a condition.
Every action commits flesh, balance, and intent. There are no safe states. Only choices.

Core Combat Loop (Moment-to-Moment)

Neutral → Commitment → Read → Punish → Reset

This loop defines all moment-to-moment decision-making. Every system must reinforce returning to neutral.

Neutral

Standing, spacing, micro-walks

Players probe with safer limbs (jabs, light kicks)

No constant blocking: chip damage + pushback discourages turtling

Commitment

Attacking commits a specific limb

High attacks are slightly faster and safer

Lows are slower but check movement

Large swings have obvious animation and meaningful recovery

Read

Defender chooses one option:

Hold Block (LB)

Duck

Limb Parry (LB + limb)

Ducking is a hard call, not a default state.

Punish

Correct read grants advantage, not instant victory

Wrong read results in real damage

Interaction resolves quickly back to neutral

Infinite depth through repetition, not escalation.

## 4. Attacks

Normal Attacks

Each limb supports a small, fixed set of contexts:

Neutral

Forward

Back

Crouching

This yields a maximum of 16 grounded normals per character.

Design rules:

Punches are faster, shorter range

Kicks are slower, longer range

Left/right limbs may differ slightly in frame data, but not wildly

## 5. Blocking

Holding LB blocks high and low

Blocking causes chip damage

Blocking builds small defender meter (optional tuning lever)

Blocking is safe but losing. It is a stopgap, not a solution.

## 6. Limb Parry & Defensive Priority System

Defensive Priority Rules (Locked)

Defensive systems resolve in the following strict order:

Parry overrides Block

Failed Parry results in no Block (full consequence)

Ducking cancels standing Block benefits

No fuzzy or overlapping defensive states exist

These rules ensure that defensive failure feels like a decision error, not an input error.

Parry Rules (Recap)

Parries are matched by attack type, not limb side:

Punches are parried with hands (X or Y)

Kicks are parried with legs (A or B)

Timing must occur just before impact

There is no parry buffering

Parries are high-risk, high-reward and are never safe by default.

## 7. Attack Height System

All attacks are categorized into exactly three heights. These definitions are rigid and system-critical.

High Attacks

Hit standing opponents

Whiff over ducking opponents

Can be blocked

Faster recovery on block than on whiff

Highs are used to probe, apply pressure, and gather information.

Mid Attacks

Hit standing and ducking opponents

Can be blocked

Cannot be avoided by ducking

Worse recovery on whiff than highs

Poor frame advantage on block

Mids exist to punish ducking and incorrect defensive reads, not to safely control neutral.

Low Attacks

Hit standing opponents

Miss airborne opponents

Can be blocked

Slower startup with clear animation

Lows are movement checks, not mixup engines.

Height Interaction Summary

Duck beats Highs

Mids beat Duck

Highs pressure standing pokes

Lows check movement

No overheads, unblockables, or ambiguous cross-ups exist in the system.

## 8. Combos & Damage Philosophy

Combos are short (2–4 hits)

Emphasis on confirms, not juggles

Pushback increases rapidly during strings

Primary goals:

Frequent resets to neutral

Strong positioning play

No infinite pressure loops

Launchers and air combos are either minimal or absent.

## 8. Hitboxes & Collision

Limb-based hitboxes, not full-body abstractions

Hurtboxes extend with limbs during attacks

No invisible range extensions

Visual clarity is mandatory. If it looks like it hit, it must hit.

Debug view (early):

Toggleable hitbox display

## 9. Character Scope

Initial target:

2 playable characters

Shared system mechanics

Distinct limb ranges and frame data

Avoid gimmick characters early. System clarity comes first.

## 10. Camera & Presentation

Fixed 2D side-on camera

Slight screen shake on heavy hits

Hitstop emphasized over VFX spam

Aesthetic goal: grounded, weighty, readable.

## 11. Ducking System (High-Risk, High-Reward)

Ducking Rules

Ducking does not block mids

Ducking slightly slows movement

Ducking locks out jumping and instant retaliation

These constraints prevent crouch-spam.

Ducking a High (Baseline Reward)

When a high attack whiffs over a ducking opponent:

Short whiff-stun window (similar to 3D fighter whiff states)

Guaranteed fast limb punish

Bonus frame advantage (+X frames)

This is strong, but not an automatic combo.

Duck Counter System

If the defender:

Ducks a high within a tight timing window

Presses a limb during that window

→ Duck Counter Hit

Effects:

Extra hitstop

Slight damage bonus

Allows 1–2 additional follow-ups

Unique audio + subtle screen shake

Duck Counters should feel earned, not accidental.

Anti-Cheese Safeguards

Ducking too early allows delayed highs or mids

Ducking too long exposes the defender to mids and lows

High attacks recover faster on block than on whiff, enabling baiting

This creates a stable interaction loop:

Highs beat standing pokes

Duck beats highs

Mids beat duck

Lows check movement

## 12. Prototype Success Criteria

The prototype is successful if:

A new player understands the controls in under 60 seconds

Neutral feels tense, not chaotic

Blocking feels bad but necessary

Parries feel earned, not random

If these are true, the game is worth expanding.

## 13. Non-Goals

Competitive balance at launch

Large rosters

Cinematic story content

Online infrastructure

The goal is a working, legible, fun fight.

Draft status: exploratory. All values subject to ruthless simplification.
