# CLAUDE.md

Context for AI assistants working on SENTINEL: Close Contact (the 1v1
fighting layer).

## Sources of truth (priority)

1. `architecture/close_contact_design.md` — combat mechanics and system
   rules (the SCC spec)
2. Repo `lore/` and `wiki/` — setting, factions, narrative constraints
3. `assets/ART_STYLE.md` + `architecture/art_style_audit.md` — visual
   direction (the audit is the current thesis; a conformance pass on
   this prototype is future work)

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
(idle → startup → active → recovery), per-attack frame data, hitbox /
hurtbox spawning, and duck state with its counter window
(`DUCK_COUNTER_WINDOW = 6` frames).

```gdscript
var ATTACK_DATA = {
    "lp": {height = "HIGH", startup = 4, active = 2, recovery = 8,  damage = 5,  range = 50},
    "rp": {height = "HIGH", startup = 5, active = 3, recovery = 10, damage = 7,  range = 55},
    "lk": {height = "LOW",  startup = 7, active = 3, recovery = 12, damage = 8,  range = 70},
    "rk": {height = "MID",  startup = 8, active = 4, recovery = 14, damage = 10, range = 75},
}
```

Frame data conventions: `startup` (frames before hitbox) + `active`
(hitbox live) + `recovery` (before actionable) = total duration;
`range` is hitbox x-offset from center; `height` is HIGH/MID/LOW.

Keep the loop readable and data-driven; prefer small, testable steps.
New attacks are `ATTACK_DATA` entries, not new systems. New characters
are frame-data variations within the 16-normal cap, never new height
rules.

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
