# run-core

What survives the door. The run layer for the walkable world's north
door: it banks what a returned card **cost** — and, since season-lite,
holds the slate: what the next card *means*, and whether the deal may
happen at all.

No DOM, no rules import, no clock of its own — it runs in Node, which is
why the policy below is a test instead of a habit.

## Run the tests

```sh
cd prototypes/run-core
node --test
```

No dependencies. Runs in CI as the `run-rules` job.

## Why this is a third module

`tactical-core` is trustworthy because it has no host. The walkable room
is honest because it has no rules import. Run state smuggled into either
would cost exactly the property that makes it believable, so it lives
here, and the room reaches it the same way it reaches three.js — as
something it renders, not something it decides with.

The room still cannot compute an outcome. That is the wall, and this
module does not cross it.

## The line this module will not cross

**A run accumulates the consequences of cards. It does not change what a
card is.**

That is load-bearing, not fastidious. `seed + record IS the match` is
written into the rules core, into the witness Worker's own docs, and into
the content-addressed key every filed record lives under. The Worker
replays a match from its seed alone. The moment a run hands a *wounded
roster* into the yard, a certified card becomes a claim the edge cannot
check — and the room's own verdict, `EDGE DISPUTES THE FEED — STRUCK`,
starts firing on honest play.

So v1 persists purse, the mercy ledger, and who went down, and the next
card is still fought by the canonical three at full strength. **Wounds
are a record, not a modifier.**

Making them a modifier is wanted, and it is a doctrine change rather than
a feature. It needs, at minimum:

- `restart(seed, roster)` and `replayMatch(seed, commands, roster)`
- a roster in the `/certify` and `/file` bodies
- the roster folded into the rules stamp and the content address
- a decision about what a filed record *means* when two players can play
  the same seed with different squads

That deserves its own PR and its own argument. It is not something this
module gets to smuggle in by being convenient.

## The slate (season-lite)

A run opened on a **slate** is a season (`architecture/
circuit_season_loop.md`, Tier 1). The slate is an authored tour — an
ordered list of entries, each carrying the faction framing that says what
that card *means*: who owns the venue, who sanctions the rules. The run
holds the slate, points at the current entry, and banks what happened to
each one: fought (a card, stamped with the entry's framing), or passed (a
declined entry, on the record with its framing and when).

**Nothing about this crosses the door.** The card payload from the yard
is unchanged and the witness certifies exactly what it certified
yesterday. The framing banked with a fought card comes from the run's
*own* slate, never from the payload — the seam does not grow a new input
to tamper with just because the season wants context.

**Wounds are clocks, counted in slate positions — and passing is always
legal.** A fighter who went down recovers for `WOUND_CLOCK` positions;
while any clock runs, the roster is unfit and the deal is gated. A card
arriving anyway is refused `accepted:false`: the room gates the door, so
a card dealt to an unfit roster is a caller bug — the same contract as a
malformed payload, and the same seam-harness claim covers it. What
advances a clock is the *slate*: passing advances the position and every
clock by one, at the entry's own cost — the purse not won, the framing
of the card you declined sitting on the record. Passing must stay legal
precisely because clocks gate the deal; a clock counted in cards dealt
would gate the only mechanism that heals it, and the season would
deadlock (caught by both review bots on the season doc's first draft).
`WOUND_CLOCK` is 2 today and lives in one place — the season doc's open
question 2 says that number wants this prototype, not the doc.

**Only banked cards advance the slate.** A struck card moves no money,
no mercy, no wounds — and no slate. The entry it was fought at stays
current, to be fought again or passed; the attempt stays on the run's
record, stamped with where it happened. Same reasoning as the rules
stamp sitting below the struck early-return: what the edge disputed does
not get to move the season.

**The books always balance.** Banked cards plus passes *is* the slate
position. `sane()` enforces the arithmetic on restore — a stored season
whose books do not check out was not kept by this module, and is
orphaned rather than rendered.

A completed slate refuses both verbs. It does not close the run —
closing stays the player's verb, and it archives the season whole; the
fresh run that opens is a plain one. A new season is opened, not
inherited.

## What counts

Inherited verbatim from the session ledger this replaced — the policy was
already right and only its lifetime was wrong.

| Verdict | Banked? | Surface says |
|---------|---------|--------------|
| `certified` | yes | CERTIFIED AT THE EDGE |
| `unwitnessed` | yes | counted, and labelled `COUNTED UNWITNESSED` |
| `struck` | **no** | tallied separately as `BANKED BY NOBODY` |

An unverified truth that says it is unverified beats a silent one. A card
the edge *disputes* is not a card, but a run that quietly discarded
disputes would look identical to one that never had any — so the count is
kept.

`applyCard` returns two different negatives on purpose:

```
accepted:false   this is not a card — a caller bug or a tampered payload
counted:false    this IS a card, and the edge struck it
```

Collapsing them would make a renderer bug indistinguishable from an
honest dispute, which is the failure the whole certification chain exists
to prevent. The seam harness asserts the room never hits the first one.

## The mercy ledger

The run's actual thesis. Across every card: how often a yield was honored
rather than collected on.

The Circuit prices this already — `RATING.spare` is negative and
`RATING.finish` is positive, so mercy costs purse *per card*. What the run
adds is the only thing a single card cannot show you: the shape of it over
time. `MERCY · 12 WALKED · 3 FINISHED · 80% HONORED` is a sentence about
who you have been, assembled entirely out of numbers the edge certified.

The rate renders only once somebody has yielded. Zero of zero is not 0%,
and this repo has already paid for one made-up number.

## The rules stamp

Every certificate carries the fingerprint of the rules that produced it.
A run adopts the first one it sees and, if it ever changes, records the
drift instead of absorbing it — the surface then says the totals were
earned across a rules boundary rather than presenting one clean number
that spans two different games.

Only the *first* drift is kept. `from` has to stay the stamp the banked
numbers were actually earned under; overwriting it on each later card
would quietly rewrite that history.

**Only banked cards define provenance.** The stamp logic sits *below* the
struck early-return: a disputed card banks nothing, so letting it set the
stamp meant a first struck card under A set `rules=A`, and the first card
that actually counted — under B — then reported drift A→B, even though
every number in the run was earned under B.

## Storage

Injected, like `io` in the rules core, and inert by default — the module
is fully usable and fully testable with no browser at all.

```js
bindStore({ read, write, remove });
```

Three keys, all under `sentinel.run`:

| Key | Holds |
|-----|-------|
| `sentinel.run` | the live run |
| `sentinel.run.closed` | the last run the player closed |
| `sentinel.run.orphan` | a stored run this schema could not read |

**The live key is not versioned, and that is the point.** It was
`sentinel.run.v${RUN_V}` at first, which made the orphan path below
unreachable in the one situation it exists for: bumping `RUN_V` to 2 would
point `loadRun` at an empty `sentinel.run.v2`, report a fresh run, and
leave the real v1 run under a key nothing reads — never moved, never
surfaced, with this README claiming otherwise. One stable slot with the
version carried *in the payload* is what makes the next line a behaviour
instead of a sentence.

**Nothing is ever silently migrated or dropped.** A run from another
schema version is *moved* to the orphan key and a fresh one opens, and
`loadRun` returns `how: "orphaned"` so the surface can say a run was set
aside. A run that is structurally wrong — hand-edited in devtools,
clobbered by another page on the origin — takes the same path: storage is
not a trusted input, and the structural check goes *inside* the
collections rather than stopping at "is it an array".

**Closing is not best-effort.** `closeRun` archives first and only then
replaces the live run, because storage with room for the one-byte startup
probe but not a second full run would otherwise lose the run from *both*
slots while the surface said `ARCHIVED`. Success is **read back** rather
than inferred from the write not throwing — a store that silently drops
writes (the inert default is one) would otherwise report a successful
archive of nothing. A close that cannot archive returns the run unchanged
and says so; the destructive half only happens if the preserving half
worked.

The room probes storage rather than assuming it. Private mode, a blocked
origin, and a sandboxed frame all make `localStorage` throw *on access*,
so the feature test has to touch it. A room that cannot persist still
plays; it says the run will not survive the page instead of quietly
forgetting at the end of it.

## Shape of the interface

```
RUN_V, RUN_KEY, CLOSED_KEY, ORPHAN_KEY, WOUND_CLOCK

bindStore({read, write, remove})   host supplies storage; inert default
openRun(at)                        a fresh run — `at` is injected, never read
openSeason(at, slate)              a run opened on a slate — a season; null
                                     rather than half a season if the slate
                                     is not a slate
slateValid(slate)                  the boundary check for authored slates
applyCard(run, card)               → {run, accepted, counted, why}; pure
applyPass(run, at)                 → {run, accepted, why}; decline the current
                                     entry — advance the slate and every clock
cardValid(card)                    the boundary check, exported for callers
fitness(run)                       → {fit, clocks}; may the deal happen — the
                                     door and the surface get the same answer
loadRun(at)                        → {run, how: fresh|restored|orphaned}
saveRun(run)                       → false if storage refused, never throws
closeRun(run, at)                  → {run, archived, closed, saved}; refuses
                                     to close what it could not archive
readClosed()                       the archived run, or null
summary(run)                       every number the surface renders
```

`applyPass` returns no `counted` — there is no edge verdict to count. A
pass is the run's own act; nothing about it can be disputed, so the
two-negatives distinction has nothing to distinguish.

`RUN_V` is 2: the season joined the schema. A stored v1 run takes the
orphan path below — moved aside and said so, which is the exact
situation that path was built and tested for. Hydrating a v1 run with an
empty season in place would have been a silent migration wearing a
default.

`saveRun`'s return value is not decoration — the room raises a standing
warning when a write fails after the probe passed, because a panel
describing a run the next reload cannot produce is the surface lying.

`summary()` exists so the room renders numbers and does not compute them.
Anything that could be got wrong in two places is got right in one.

## Why `at` is injected

Nothing here reads the clock, for the same reason the rules core does
not: a module that consults the clock cannot be *tested* for what it does
at a given moment, only observed doing it. Every timestamp arrives from
the caller.
