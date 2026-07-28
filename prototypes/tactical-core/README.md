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
formatEvent(ev, wrap) one formatter, two skins
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
only moves down, and only for things a fighter can see: a landed hit, a
squadmate dropping, a squadmate quitting. At zero the fighter yields —
deterministically, no roll, because a collapse the player can see coming is
one they can play around, or play for. Operatives have no morale; the
player's people don't quit under the player.

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
