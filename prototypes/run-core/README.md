# run-core

What survives the door. The run layer for the walkable world's north
door: it banks what a returned card **cost** — and, since season-lite,
holds the slate: what the next card *means*, and whether the deal may
happen at all. Since pairwise-ledger step 4 it also banks what one certified
act now means between two owned people, and which room-layer pass that fact
makes legal.

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

Still true, and now true for a different reason. It used to be structural:
under `seed + record IS the match`, a run that handed a *wounded roster*
into the yard turned a certified card into a claim the edge could not
check, and the room's own verdict — `EDGE DISPUTES THE FEED — STRUCK` —
would have started firing on honest play. The price of changing that was
written here as a checklist:

- `restart(seed, roster)` and `replayMatch(seed, commands, roster)`
- a roster in the `/certify` and `/file` bodies
- the roster folded into the rules stamp and the content address
- a decision about what a filed record *means* when two players can play
  the same seed with different squads

**That bill has been paid** (`architecture/roster_in_the_match.md`,
2026-08-13). The law is now `seed + roster + record = the match`: the
roster is a certified input, replayed from rather than trusted, carried
in the certificate as its own field and in the content address — the last
item's answer being that a record individuates by what actually fought.
The third bullet landed with one deliberate correction: the roster is
**not** in the rules stamp, because a wound is not a rules deployment;
the stamp instead gained a golden that exercises roster handling.

So the line above is now a *choice* rather than a constraint. This module
still persists purse, the mercy ledger and who went down. Since the
faction-door slice (2026-08-16), it also owns four stable people and the
three-person lineup selected from them. The room still deals every selected
fighter at full strength — whether a wound changes starting hp remains a
separate design decision rather than something lineup choice smuggles in.

## The faction door

The run owns `roster.people` and `roster.lineup`. Each person carries a stable
lowercase id, a tactical name, an authored body id, and an origin with a stable
source, optional faction, and the reason they entered. The lineup is exactly
three unique person ids from that owned four-person crew.

Stable identity stops at the door. `fieldedRoster(run)` reduces the lineup to
exactly `{name, hp}` × 3, with no ids, origins, bodies, gear, or relationship
state riding along. `setLineup` is therefore run state with a certified output,
not a change to the yard's roster grammar. Court 01's authored entrance lives
in `world/recruitment/court-01.json`; NIX enters through the Ember Colonies and
borrows SYN's tracked canvas explicitly until original art exists.

Inside the run, durable wounds and recovery clocks key on the stable person id.
`recent[].down` deliberately keeps the tactical names the card carried across
the yard wire: it is a receipt, not another durable identity ledger.

## The durable moment

Run schema v5 adds `eventLedger`, keyed by the actor's stable person id. The
run never derives an event. On a filed certificate it accepts the Worker's
replay-authored tactical event, translates `actor` and `beneficiary` through
the lineup that was fielded for that card, and banks the stable ids once.
`recent[].derivedEvents` remains the certified receipt in tactical names.

The one event in this slice is `extraction`. A certified entry carries
`grade: {kind:"certified", matchId, commandIndex}`; the 32-hex match id points
to a filed Witness record and the command index points inside it. The ledger
is certified-grade-only in this slice. An unwitnessed or unarchived card still
counts as a card, and the yard may show its derived account for the current
session, but the run retains no derived event from it. Claim grade is deferred
until the append-only local event log exists: the rolling twelve-card receipt
is not a durable target, and no pointer is minted before its target survives.
Season entries carry the same authored slate stamp as other banked facts.

`sane()` validates the ledger all the way in: every key and beneficiary is an
owned stable person id, nobody names themselves, grades have exact shapes,
every grade is certified with a plausible filed id and command index,
certified counts agree with the retained receipts, non-certified receipts
carry no derived events, and slate stamps resolve to authored entries already
passed. `eventLedger` remains the event ledger: it grants no permissions and
computes no bond state. The relationship policy consuming it is the next,
separate run-owned layer.

## The pairwise mercy ledger

Run schema v6 adds `relationships`, an append-only array of named directional
facts:

```js
{
  kind: "owes-a-life",
  from: "koa",                  // debtor: the extracted beneficiary
  to: "sable",                 // creditor: the extraction actor
  origin: { matchId, commandIndex },
  status: "active",            // or "fulfilled"
  at,
  slate,                        // absent only on a plain run
  // fulfilled entries additionally carry:
  fulfilledAt,
  fulfilledSlate,
}
```

The origin is the certified event's filed `{matchId, commandIndex}`, not a
copy of prose or a rolling receipt. `sane()` requires that pointer, direction,
time, and mint stamp to resolve to the stable-id extraction in `eventLedger`.
It also requires owned distinct people, the exact lifecycle shape, a unique
origin, at most one active `owes-a-life` per directed pair, and — after
repayment — a matching dedicated pass at the exact fulfillment stamp. On a
season, each directed pair's entries are ordered by mint slate index (with the
origin command index as the within-card tie-break), and every successor must
be minted strictly after its predecessor's fulfillment slate index. The bound
is strict because `applyPass` fulfills at the current index and then advances
the position; only a card at the following or a later index can mint again.
On a plain run, `at` is an opaque caller-authored string rather than a clock and
there is no legal pass, so the module can honestly enforce only the reducer's
append order: one active relationship per pair, rooted at the first uncovered
event and covering later same-pair events.

### Recorded relationship decisions — 2026-08-17, pairwise-ledger step 4

These are implementation decisions recorded for designer veto at review:

1. **THE FIRST NAMED RELATIONSHIP IS OWES A LIFE.** `applyCard` consumes a
   certified extraction already derived by replay and applies run banking
   policy: beneficiary owes actor a life. The rules core derives the event;
   the run computes the relationship from that banked event. Those are
   deliberately different ownership claims. A second rescue while the same
   directed debt is active mints nothing, so the first source stands; a used
   origin never mints twice.
2. **THE FIRST OBLIGATION IS REPAY THE LIFE.** `applyPass(run, at,
   {kind:"repay-the-life", from, to})` is legal only for a real owned pair
   carrying an active debt whose named creditor has a running recovery clock.
   The dedicated pass advances that creditor by `DEDICATED_RECOVERY` (2)
   instead of 1, advances every other running clock by the ordinary 1, and
   fulfills the debt on the current slate stamp. The plain pass remains
   legal. This is recovery economics: no purse, match input, certified
   snapshot, or combat number changes.

`summary()` exposes both the relationship history and only the dedicated
passes legal now. The room renders that read model rather than independently
rebuilding the debt-and-clock gate.

## The slate (season-lite)

A run opened on a **slate** is a season (`architecture/
circuit_season_loop.md`, Tier 1). The slate is an authored tour — an
ordered list of entries, each carrying the faction framing that says what
that card *means*: who owns the venue, who sanctions the rules. The run
holds the slate, points at the current entry, and banks what happened to
each one: fought (a card, stamped with the entry's framing), or passed (a
declined entry, on the record with its framing and when).

**Nothing about the SEASON crosses the door.** The framing banked with a
fought card comes from the run's *own* slate, never from the payload —
the seam does not grow an input to tamper with just because the season
wants context. (The seam did grow one input since, and deliberately: the
roster, which is certified end to end. The season's slate, clocks and
passes are still not in it and never were.)

**Wounds are clocks, counted in slate positions — and passing is always
legal.** A fighter who went down recovers for `WOUND_CLOCK` positions;
while a *fielded* fighter's clock runs, the lineup is unfit and the deal is gated. A card
arriving anyway is refused `accepted:false`: the room gates the door, so
a card dealt to an unfit roster is a caller bug — the same contract as a
malformed payload, and the same seam-harness claim covers it. What
advances a clock is the *slate*: passing or banking a card advances the
position and every existing clock by one. A recovering person may be benched
while a fit lineup fights; passing stays legal because a run without a fit
replacement still needs a way to heal rather than deadlock (caught by both
review bots on the season doc's first draft).
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

## The purse spends (season-lite)

Purse stopped being a scoreboard the moment there was somewhere to spend
it. A run carries what it has **bought**, and the only thing it can buy
is flair.

**That is the tier boundary, and this is where it stops being a
promise.** `sentinel_circuit_design.md` sorts gear slots by whether they
carry *verbs*: head (sensing), torso (defense, where sponsor rigs
mount), legs (movement), primary (ammo) and sidearm all do — drape and
patch are "mechanically inert by law", because "the two most socially
loud slots being mechanically silent makes cosmetic power creep
impossible by architecture instead of by discipline". A verb is roster
state the yard would have to be told about, and roster state crossing
the door is the doctrine change season-lite is defined by *not* making.

So `FLAIR_SLOTS` is the whole shop, and an item declaring any other slot
is refused at this boundary — the same refusal a malformed card gets,
for a much larger reason. A stored purchase of a torso rig orphans the
run rather than restoring a verb nobody could have bought.

**Purse stays total earned.** Spending is tracked beside it and the
balance is derived, because a run that decremented purse could no longer
say what it *won* — the season's headline number would quietly become
"what you have left", and every card that paid for a hood would read as
a card that paid for nothing.

**A purchase is permanent, and a slot is bought once per fighter.**
There is no resale: the point of the register is history — *the squad you
dress is the squad you protect* — and gear you can liquidate back into
the purse is inventory, not history. An empty hook is information too. It
says you never bought one.

**A purchase moves no slate.** Only cards and passes move the position,
so a purchase needs no settling gate: closing and passing both refuse
while a card is in flight because both would move something the
settlement is about to move, and a purchase spends money that is already
banked. It is stamped with where on the tour it happened, the same way a
card is — trophies have provenance, and the same hood bought after the
Cold Court is a different object from one bought in week one. The one
exception is a tour that is already **over**: there is no entry left to
stamp with, so the purchase carries none, and that absence is terminal —
nothing stamped may follow it, and restore checks that the slate really
is complete.

**The books balance here too.** `spent` *is* the sum of the rack, and
never more than the purse; two drapes on one fighter, a free hood, a
purchase stamped off the authored slate, or one stamped at a position
the season has not reached all orphan on restore. A stored purchase
must also carry *exactly* the fields this module writes — one that
arrived with a `verb` on it would be Tier 2 roster state sitting inside
a Tier 1 run.

**And the purse itself is checked, now that it buys things.** `recent`
is the run's own receipt, and every card pushes exactly one entry, so
`cards + struck === recent.length` is precisely *nothing has scrolled
off* — while that holds, every total that is a sum or a count must *be*
that sum or count: cards, wins, struck, unwitnessed, purse, and the mercy
ledger. A hand-edited fresh run with `purse: 10000` used to restore and
buy a hood with it.

Not "the buffer is not full", which was the first cut and is a different
claim: a run of exactly 12 cards has evicted nothing either, and testing
fullness dropped it into the loose branch one card above where the hole
was closed. Once entries really have scrolled off, what is left is a
**floor** — the visible receipts, plus at most `MAX_PURSE` for each card
that vanished. A run claiming a hundred cards can claim a hundred cards'
purse; that is the honest limit of what a twelve-entry receipt proves.

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
kept. "Banked" in this table means the card's run consequences; only a
certified card may also bank replay-derived events. Infrastructure failures
never mint claim-grade events in this slice.

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
aside. Setting aside is not best-effort either: the orphan write is
**read back** before the live slot is cleared, because the write can
throw under quota and a store that silently drops writes — the inert
default is one — does not throw at all. When the read-back fails,
`loadRun` returns `how: "unpreserved"`: the unreadable run keeps the
live slot, the fresh run plays in memory, and the caller must not write
— the slot holds the only copy, and it is not the page's to spend. A run that is structurally wrong — hand-edited in devtools,
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
RUN_V, RUN_KEY, CLOSED_KEY, ORPHAN_KEY, WOUND_CLOCK, DEDICATED_RECOVERY, FLAIR_SLOTS,
LINEUP_SLOTS, FULL_STRENGTH

bindStore({read, write, remove})   host supplies storage; inert default
openRun(at, roster?)               a fresh run — `at` is injected, never read
openSeason(at, slate, roster?)     a run opened on a slate — a season; null
                                     rather than half a season if the slate
                                     or authored roster is invalid
slateValid(slate)                  the boundary check for authored slates
rosterValid(roster)                four stable people, origins, three owned ids
personOf(run, id)                  the owned person behind a stable id
fieldedRoster(run)                 exactly `{name, hp}` ×3 for the certified seam
setLineup(run, ids)                → {run, accepted, why}; pure lineup choice
applyCard(run, card)               → {run, accepted, counted, why}; pure
applyPass(run, at, dedication?)    → {run, accepted, why}; decline the current
                                     entry — optional `{kind:"repay-the-life",
                                     from,to}` dedicates its recovery
applyBuy(run, item, who, at)       → {run, accepted, why}; spend the balance on
                                     flair, permanently, one slot per fighter
itemValid(item) / stockValid(…)    the boundary checks for authored stock —
                                     where FLAIR_SLOTS stops being a promise
kitOf(run, who)                    what one fighter wears, derived from the
                                     purchase ledger rather than stored twice
cardValid(card)                    the boundary check, exported for callers
fitness(run)                       → {fit, clocks, fieldedClocks}; may the deal happen — the
                                     door and the surface get the same answer
loadRun(at, roster?)               → {run, how: fresh|restored|orphaned|
                                     unpreserved|invalid-roster}
saveRun(run)                       → false if storage refused, never throws
closeRun(run, at)                  → {run, archived, closed, saved}; refuses
                                     to close what it could not archive
readClosed()                       the archived run, or null
summary(run)                       every number the surface renders
```

`applyPass` returns no `counted` — there is no edge verdict to count. A
pass is the run's own act; nothing about it can be disputed, so the
two-negatives distinction has nothing to distinguish.

`applyBuy` returns no `counted` either, for the same reason: a purchase
is the run's own act and the edge never sees it. Both of its refusals are
`accepted:false` because the **surface** is the gate — the shop prices
the stock, knows the balance, and knows what each fighter already wears,
so an unaffordable purchase arriving here means the room offered
something it should have refused.

`RUN_V` is 6: the season joined the schema at 2, the purse at 3, the
owned roster plus lineup at 4, replay-derived pairwise events at 5, and named
relationship lifecycle at 6. A stored run of any older version takes the
orphan path below — moved aside and said so, which is the exact situation
that path was built and tested for. Hydrating a v5 run with a made-up empty
relationship ledger would be a silent migration wearing a default, so the
older payload is set aside instead.

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
