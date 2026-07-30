# close-contact

SENTINEL: Close Contact — the 1v1 fighting layer, as a Godot 4.5
prototype. Limb-mapped inputs (every button commits a body part), rigid
three-height system, active defense where blocking is deliberately the
losing option. Design spec:
[`architecture/close_contact_design.md`](../../architecture/close_contact_design.md).

This is the universe's fight at its closest zoom: the tabletop plays the
world at conversation scale, `tactical-core/` plays the fight at squad
scale, and this is the scale where you can watch someone decide to
commit a limb. The Circuit institution (cards, purses, witnesses, the
showrunner) wraps this game the same way it wraps the squad layer —
that wiring is future work, deliberately not improvised here.

Unlike its siblings this prototype is Godot, not web — the right tool
for proving fight-feel fast. The platform direction (web-first, TS)
applies to shipping, not to prototyping; if the fight proves fun, the
port inherits a settled design instead of a guess.

## Run

- Open `project.godot` in Godot 4.5+
- Main scene: `Main.tscn`
- Press Play (F5)

## Controls (current prototype)

- P1: Arrows + U/I/J/K (LP/RP/LK/RK) + Space (block)
- P2: WASD + T/Y/G/H (LP/RP/LK/RK) + Shift (block)

Gamepad target (per spec): A(LK) B(RK) X(LP) Y(RP), LB block/parry.

## Success criteria (from the spec)

1. A new player understands the controls in under 60 seconds
2. Neutral feels tense, not chaotic
3. Blocking feels bad but necessary
4. Parries feel earned, not random
