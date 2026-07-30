# CLAUDE.md

Context for AI assistants working on SENTINEL: Close Contact (the 1v1
fighting layer).

## Sources of truth (priority)

1. `architecture/close_contact_design.md` — combat mechanics and system
   rules (the SCC spec)
2. Repo `lore/` and `wiki/` — setting, factions, narrative constraints
3. `assets/ART_STYLE.md` + `architecture/art_style_audit.md` — visual
   direction (the audit is the current thesis; a conformance pass on
   this prototype is future work). **Fighter bodies obey the body law**
   (`architecture/art_direction_gba_tactics.md`, decided 2026-07-30):
   the 32×32 System A canvas at ~4× integer zoom — the fighter adds
   frame sets (stances, limb commitments, hitstun), never a larger
   format. The animation-detail cap is the body law's own tradeoff,
   not a spec mandate; the spec independently wants hitstop-over-VFX
   impact and readability-first animation, which is why the two are
   compatible.

If there's a conflict: **mechanics > lore > visuals**.

## Design pillars (non-negotiable)

| Pillar | Meaning |
|--------|---------|
| **Physical Intent** | Buttons map to limbs (LP/RP/LK/RK), not move categories |
| **Low Move Count** | 16 grounded normals max per character |
| **Active Defense** | Blocking is weak; parry/duck are high-risk alternatives |
| **Solo-Dev Realism** | Systems must be buildable without bespoke tooling |

Core loop: `Neutral → Commitment → Read → Punish → Reset`. Every system
reinforces returning to neutral.

## The rules that cannot bend

- Heights are only HIGH/MID/LOW. No overheads, unblockables, or
  ambiguous cross-ups — defensive failure must be a decision error,
  never an input error.
- Defensive priority is strict: Parry overrides Block; failed Parry
  means no Block (full consequence); Ducking cancels standing Block.
  No fuzzy or overlapping defensive states.
- Jumping is committal: fixed arcs, no air control, no air defense.
- Blocking is safe but losing — chip and pushback, never a solution.
- Combos are 2–4 hit confirms. No launchers, no juggles, no infinite
  pressure.
- "If it looks like it hit, it must hit" — hitboxes are limb-based and
  visually honest (this is design philosophy #1 wearing gloves).

## Implementation shape (Main.gd)

The `Fighter` class owns position/facing, the attack state machine
(NEUTRAL → startup → active → recovery), per-attack frame data, hitbox /
hurtbox rects, and duck state with its counter window
(`DUCK_COUNTER_WINDOW = 6` frames).

The real frame data — this table is copied from the `ATTACKS` const in
Main.gd and must be kept in step with it (an earlier version of this
file carried a stale fork of it; caught in review):

```gdscript
const ATTACKS := {
    "LP": {"height": "HIGH", "startup": 6, "active": 3, "recovery": 10, "range": 40.0, "hitstun": 12, "blockstun": 8, "push": 22.0},
    "RP": {"height": "MID",  "startup": 7, "active": 3, "recovery": 11, "range": 42.0, "hitstun": 13, "blockstun": 8, "push": 23.0},
    "LK": {"height": "LOW",  "startup": 8, "active": 3, "recovery": 12, "range": 55.0, "hitstun": 14, "blockstun": 9, "push": 26.0},
    "RK": {"height": "LOW",  "startup": 8, "active": 3, "recovery": 12, "range": 55.0, "hitstun": 14, "blockstun": 9, "push": 26.0}
}
```

Frame data conventions: `startup` (frames before hitbox) + `active`
(hitbox live) + `recovery` (before actionable) = total duration;
`range` is hitbox reach beyond the body edge; `hitstun`/`blockstun`
are the defender's frozen frames; `push` is pushback distance. There
is no `damage` field yet — the harness has no health (see status
below).

Keep the loop readable and data-driven; prefer small, testable steps.
New attacks are `ATTACKS` entries, not new systems. New characters are
frame-data variations within the 16-normal cap, never new height rules.

## Harness status — what is actually implemented

The spec is the design; the harness is a slice of it. Today:

**In:** walk (forward faster than back), crouch, block (stun only),
the three-height law, edge-triggered limb attacks (one press, one
commitment), duck-counter window + resolution, simultaneous-hit trades,
pushback and the pushbox, debug hitbox draw, per-fighter state labels.

**Not in yet:** **parry** (the LB+limb input is reserved and inert —
holding block suppresses normals so the spec's input can never misfire
as an attack; implementing parry per spec §6 is the next milestone),
**jump** (the up key is read and unused), **chip damage**, **health /
rounds / win state** (hitstun is the only currency), meter, and any
per-character variation.

Consequences for the success criteria: #1 and #2 are testable today;
#3 ("blocking feels bad but necessary") needs chip damage first; #4
("parries feel earned") needs parry to exist. Do not claim them until
their mechanics do.

`tests/logic_check.gd` executes the harness's load-bearing claims
headlessly (height law, duck-counter reachability, trades, parry-input
inertness):

```sh
godot --headless --path prototypes/close-contact --script res://tests/logic_check.gd
```

Run it after touching Main.gd. It is not in CI (no Godot runtime
there) — that makes it your job.

## Non-goals (out of scope until the core is fun)

Competitive balance, large rosters, cinematic story, online
infrastructure, gimmick characters, complex combo systems.

## The Circuit connection (future work, not license)

This game is what the Circuit institution hosts at 1v1 scale — cards,
purses, rating, witness records, and the showrunner all apply
conceptually, and the yield question ("blocking is losing" taken to its
end) is where the two designs will eventually meet. None of that is
wired yet, and none of it should be improvised into the prototype: the
prototype's only job is the spec's success criteria — a legible, tense,
fun fight in under 60 seconds of learning. If replay/witness support
ever lands here, it needs the same discipline as everywhere else:
deterministic fixed-tick sim + input log, adopted deliberately, not
retrofitted.

## Prototype success criteria

1. New player understands controls in <60 seconds
2. Neutral feels tense, not chaotic
3. Blocking feels bad but necessary
4. Parries feel earned, not random
