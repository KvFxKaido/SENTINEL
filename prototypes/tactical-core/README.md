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
playTwist, twistWindow, TWISTS
                      the house's verb, its legality window, and the deck
los, coverBonus, coveringTiles, solution, reachable, pathTo
MORALE                start value and drain amounts, exported for tuning
RATING                crowd-meter deltas and payout rate, exported for tuning
formatEvent(ev, wrap) one formatter, two skins
S.record              the witness record — committed commands, in order
replayMatch(seed, commands)
                      drive a record back through the verbs (see below)
```

The rules never call the renderer. They emit events — `fire`, `shot`, `down`,
`overwatch-set`, `overwatch-trigger`, `turn`, `select`, `reset`, `end`,
`yield`, `yield-decision`, `finish`, `spared`, `twist-announce`,
`twist-resolve` — and the host decides what a shot looks and sounds like. `formatEvent` takes a `wrap(text, class)` so the
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
**seed + roster + record IS the match** (`architecture/roster_in_the_match.md`
— the law was `seed + record` until the roster became a certified input).
Every player verb that changes the match
appends its canonical form to `S.record` at the moment its guards pass —
`["move", id, x, y]`, `["shoot", att, def]`, `["finish", att, def]`,
`["ow", id]`, `["spare"]`, `["end"]`. Rejected inputs never enter the
record, and selection is deliberately absent: it rolls nothing, logs
nothing, and every verb names its units explicitly, so it is
presentation, not play. Shooting a kneeling fighter records the finish it
reroutes to — the record captures what happened, not what was clicked.

`replayMatch(seed, commands, roster)` drives a record back through the same
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

## Showrunner twists

The house's verb (`sentinel_circuit_design.md` roadmap step 4). A twist is
a **recorded input**, never weather: `["twist", cardId]` enters the record
like any player command, the core validates and resolves it, and *who*
chose it — a scripted card, a reactive director, someday a live hand —
lives outside the rules and outside the record's concern. `playTwist` is
legal only in the between-rounds window (`twistWindow()`: the player has
control and nobody has acted yet), refuses unknown cards, and enforces the
budget of **one card per match** in the rules rather than as director
etiquette — a synthesized five-twist record can never certify.

A played card resolves at the next moment control returns to the player —
the top of the next round, or the decision entry if the fight settles
first — so the announcement always lands before the effect. Both moments
are transcript lines: the warning is on the feed, byte-for-byte.

The deck holds one card. **MERCY ODDS** replaces the spare payout
(`RATING.spare`, normally a cost) with a bounty — settled law: *the house
can monetize your decision; it cannot decide what the decision means.*
Cards price choices; they do not touch morale, yield thresholds, or what
a spare socially costs. The terms print on the feed with the number in
them, and a test asserts the number in the text is the number in the code.

On a record with no twist verbs, none of this draws RNG or emits a line —
the fifth rules change in a row to land with the goldens untouched. But a
no-input playout can never play a card, so the deadbeef golden alone can
no longer stamp the rules: `showrunner-golden.js` pins a **second golden**
(seed 6's organic spare match with the twist spliced at the first window,
captured fingerprint `6495eab3`), and the witness Worker's rules stamp
hashes every pinned playout — transcript *and* outcome (result, rating,
purse), because rating is never a transcript line and card economics must
not be able to change under an unchanged stamp. Changing card math moves
the stamp — that is the point.

`roster-golden.js` pins a **third** for the same reason: the other two
field the canonical three, so neither can stamp what a fielded ROSTER
does. It is the deadbeef golden's twin — same seed, same no-input
horizon, a substituted name and two carried wounds — and held against its
twin it is also the doctrine in one line:

| seed deadbeef, no input | transcript | lines | rating |
|---|---|---|---|
| canonical three | `39e8be71` | 42 | 29 |
| the roster golden's squad | `d44833c0` | 37 | 35 |

Same seed. Same (empty) record. Different match.

`director.js` is the reference chooser: deterministic, reactive, no RNG.
It reads the same visible state the player reads at each between-rounds
window and plays MERCY ODDS when a fighter is one bad beat from kneeling.
It is a *client* of the rules — same doorway as the player-input adapter,
refusable like any hand on the controls — not part of them. Renderers may
use it; tests script their own records.

## The fielded roster

The match's second certified input, and the one thing beside the seed a
caller may set: three operatives, in slot order, each a `{name, hp}`.
Names ride the transcript (a substitution is a different record) and `hp`
is where they start — `maxHp` stays `OP_MAX_HP` whatever the roster says,
because a fighter carried in at 7 is at seven *of* ten, not a smaller
fighter.

`rosterValid()` is the boundary check and `rosterKey()` the one canonical
form; both are exported because the room, the yard and the Worker all
have to agree about what a squad is, and a key computed three ways is
three keys. `restart()` **throws** on a malformed roster rather than
falling back to the canonical three — a fallback would field a squad
nobody asked for and then let the edge certify it. Absent, the canonical
three at full strength are fielded, which is exactly what every match was
fought by before this input existed: the goldens above did not move, and
that is the proof.

Slots, positions, hostiles, stats and gear are the encounter's, not the
caller's. See `architecture/roster_in_the_match.md`.

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
