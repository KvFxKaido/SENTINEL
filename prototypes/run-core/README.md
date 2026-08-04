# run-core

What survives the door. The run layer for the walkable world's north
door: it banks what a returned card **cost**, and nothing else.

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

## Storage

Injected, like `io` in the rules core, and inert by default — the module
is fully usable and fully testable with no browser at all.

```js
bindStore({ read, write, remove });
```

Three keys, all under `sentinel.run.`:

| Key | Holds |
|-----|-------|
| `sentinel.run.v1` | the live run |
| `sentinel.run.v1.closed` | the last run the player closed |
| `sentinel.run.orphan` | a stored run this schema could not read |

**Nothing is ever silently migrated or dropped.** A run from another
schema version is *moved* to the orphan key and a fresh one opens, and
`loadRun` returns `how: "orphaned"` so the surface can say a run was set
aside. A run that is structurally wrong — hand-edited in devtools,
clobbered by another page on the origin — takes the same path: storage is
not a trusted input.

The room probes storage rather than assuming it. Private mode, a blocked
origin, and a sandboxed frame all make `localStorage` throw *on access*,
so the feature test has to touch it. A room that cannot persist still
plays; it says the run will not survive the page instead of quietly
forgetting at the end of it.

## Shape of the interface

```
RUN_V, RUN_KEY, CLOSED_KEY, ORPHAN_KEY

bindStore({read, write, remove})   host supplies storage; inert default
openRun(at)                        a fresh run — `at` is injected, never read
applyCard(run, card)               → {run, accepted, counted, why}; pure
cardValid(card)                    the boundary check, exported for callers
loadRun(at)                        → {run, how: fresh|restored|orphaned}
saveRun(run)                       → false if storage refused, never throws
closeRun(run, at)                  archive and open a fresh one
readClosed()                       the archived run, or null
summary(run)                       every number the surface renders
```

`summary()` exists so the room renders numbers and does not compute them.
Anything that could be got wrong in two places is got right in one.

## Why `at` is injected

Nothing here reads the clock, for the same reason the rules core does
not: a module that consults the clock cannot be *tested* for what it does
at a given moment, only observed doing it. Every timestamp arrives from
the caller.
