# tactical-core

The rules layer for the tactical encounter prototype. No DOM, no canvas, no
audio, no timers of its own — it runs in Node, which is the entire point.

Two renderers consume it:

- [`../tactical/`](../tactical/) — 2D canvas, immediate-mode
- [`../tactical3d/`](../tactical3d/) — three.js, retained-mode

## Run the tests

```sh
cd prototypes/tactical-core
node --test
```

No dependencies. Runs in CI as the `tactical-rules` job.

## Why this exists

`architecture/Sentinel 2D.md` names determinism and turn authority as the
invariants that win over implementation convenience. Before this split, the
only way to check determinism was by hand: open the page, play a turn, hit
`shift+R`, and eyeball whether the comms log matched. An invariant that
load-bearing should not depend on somebody remembering to look.

Extracting the rules made them runnable headlessly, which made the check a
test. The golden hashes in `rules.test.js` were captured from the *browser
build before the extraction* — so they are a real regression guard, not a
snapshot of whatever the extracted code happened to do on day one.

Three independent paths were confirmed to produce the identical 42-line
transcript for seed `deadbeef`: the pre-extraction browser build, the
headless Node suite, and both post-extraction renderers.

## Shape of the interface

```
S                     shared mutable encounter state (map, units, turn, …)
bindIO({...})         host supplies sleep / emit / changed
restart(seed)         deal an encounter
                      → emits reset, mission, turn

tryMove, tryShoot, setOverwatch, selectUnit, cycleSelect, endPlayerTurn
tryFinish, spare      the two halves of the yield decision (see below)
los, coverBonus, coveringTiles, solution, reachable, pathTo
MORALE                start value and drain amounts, exported for tuning
RATING                crowd-meter deltas and payout rate, exported for tuning
formatEvent(ev, wrap) one formatter, two skins
S.record              the witness record — committed player commands, in order
replayMatch(seed, commands)
                      drive a record back through the verbs (see below)
```

The rules never call the renderer. They emit events — `fire`, `shot`, `down`,
`overwatch-set`, `overwatch-trigger`, `turn`, `select`, `reset`, `end`,
`yield`, `yield-decision`, `finish`, `spared` — and the host decides what a
shot looks and sounds like. `formatEvent` takes a `wrap(text, class)` so the
browser gets coloured HTML and the test gets plain text from the same code
path. That is why the test can assert against exactly the words a player
reads in the comms log.

## Yield states

Hostiles carry morale (`sentinel_circuit_design.md` §5, roadmap step 1). It
only moves down, and only for things a fighter can perceive: a landed hit, a
squadmate dropping, a squadmate quitting. Perception is squad-wide by design
— the yard is small and gunfire carries, so drains are not gated on
sightlines. Morale is legible squad state, not a per-witness simulation the
player has to audit unit by unit; per-witness morale is a real future fork
(an execution as a performance wants an audience), but it belongs to the
rating/witness layer. At zero the fighter yields — deterministically, no
roll, because a collapse the player can see coming is one they can play
around, or play for. Operatives have no morale; the player's people don't
quit under the player.

When every hostile still standing has yielded, the fight is settled but the
match holds (`S.decision`): the only verbs left are `spare()` — accept every
yield, end the match — and `tryFinish(att, def)` — an execution, no roll, no
miss. Mid-fight, finishing a lone yielder is also legal; it costs the
activation, needs line of sight, and drains the morale of everyone who
watched. Which ending you chose stays visible on the corpse: `yielded`
remains true on a finished fighter, and both renderers read it back for the
end screen.

Notably, adding this mechanic did **not** re-capture the golden transcripts:
morale reacts to damage and never draws from the RNG, and in a no-input
playout the hostiles are never damaged. The goldens passing untouched is the
draw-order rule below doing its job in the other direction.

## Rating

The crowd meter (`sentinel_circuit_design.md` §5, roadmap step 2): 0–100,
squad-level, visible on the panel, paid out as purse at match end whether
you won or not. Landed player fire builds it — itemized for flash (crit,
long shot, flanked target, shooting from the open). The player's overwatch
and unspent AP bleed it; the AI's choices never move it. Anyone going down
pays +3, including your own people: "playing to the crowd versus keeping
your people safe" is the design's named loop, and that line is it. Yields
pay, finishes pay more, sparing costs — mercy is priced in purse, and what
it buys lives in systems this module doesn't know about.

Rating survives the golden transcripts by the same discipline as morale,
plus one more trick: rating changes are events but **never log lines**, so
the meter moves underneath the pre-meter transcripts without disturbing a
byte. Deltas live in the exported `RATING` table; tuning them is free until
they interlock with ammo (Circuit doc §6, gated on this prototype).

## The witness record

The input-log protocol (`sentinel_circuit_design.md` §9, roadmap step 5):
**seed + record IS the match.** Every player verb that changes the match
appends its canonical form to `S.record` at the moment its guards pass —
`["move", id, x, y]`, `["shoot", att, def]`, `["finish", att, def]`,
`["ow", id]`, `["spare"]`, `["end"]`. Rejected inputs never enter the
record, and selection is deliberately absent: it rolls nothing, logs
nothing, and every verb names its units explicitly, so it is
presentation, not play. Shooting a kneeling fighter records the finish it
reroutes to — the record captures what happened, not what was clicked.

`replayMatch(seed, commands)` drives a record back through the same
verbs. Because replaying re-records, and commands the rules refuse don't
re-record, **a faithful replay reproduces its own input** — that closure
is the integrity check. A record that cannot reproduce itself (tampered,
reordered, from a different rules version) is not a match record, and
nothing downstream certifies it. The dispatcher also refuses grammar the
renderers can never produce (moving hostiles, friendly fire), so a
renderer bug that recorded one fails closed at replay.

`workers/witness/` inherits all of this as `POST /certify`: play a match
anywhere, and the edge will attest that the record is a valid match under
the running rules and what its one replay says happened. (That is
validation, not provenance — *who* played it is a claim certification
cannot check yet, and belongs to campaign wiring.)

Recording draws nothing from the RNG and emits nothing — the fourth rules
change in a row to land with the golden transcripts untouched.

## Rules for changing this file

1. **Never consult the clock, the platform, or `Math.random`.** Every draw
   comes from `S.rng`, in a fixed order. One stray draw desyncs the encounter
   and `shift+R` stops meaning anything.
2. **Adding or reordering a draw is a breaking change.** The golden hashes
   will fail. That is the test working. Re-capture them deliberately, in a
   commit that says why — never by pasting in whatever the new hash is.
3. **No DOM, no `window`, no `performance`.** If it cannot run under
   `node --test`, it belongs in a renderer.

## Known limitation

`S` is a single module-level encounter. That is deliberate — forkable state
is a real future want (a "preview this action's consequences" mode would
need it, and `/simulate preview` already exists elsewhere in SENTINEL), but
nothing asks for it yet, and design philosophy #4 is explicit that complexity
gets justified before it gets built.

When something does ask, the change is `createEncounter(seed) → state` plus
threading `st` through as a first argument. The tests make that refactor
checkable rather than nerve-wracking, which is most of why they exist.
