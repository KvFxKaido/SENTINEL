# The Roster Is In The Match

> **Version:** 1.0
> **Date:** August 13, 2026
> **Status:** Current (2026-08-13) — binding; changing it takes a PR that says so
> **Supersedes:** the determinism law stated in `prototypes/tactical-core/README.md`,
> `prototypes/run-core/README.md` and `workers/witness/README.md` as
> *seed + record IS the match*. Those docs are amended, not archived.
> **Provenance:** step 2 of `circuit_season_loop.md` §7's build order, argued
> on its own as that doc requires. Season-lite (beats 1–3, PRs #120–#122)
> was the migration path; this is the doctrine it was migrating toward.

---

## 1. The Change, In One Line

```
old law:   seed + record            = the match
new law:   seed + roster + record   = the match
```

That is the whole thing. Everything below is what it costs, what it buys,
and what had to be true before it could be said.

## 2. Why This Is A Doctrine Change And Not A Feature

The old law is not a convention. It is written into the rules core, the
witness Worker's own docs, the content-addressed key every filed record
lives under, and — most importantly — into what a **certificate means**.
The Worker replays a match from its seed and its record alone. If a run
had ever handed a wounded roster into the yard under the old law, a
certified card would have become a claim the edge could not check, and
the room's own honest verdict — `EDGE DISPUTES THE FEED — STRUCK` —
would have started firing on completely honest play.

So the fork was never "should wounds carry over". It was: **is the squad
part of what makes a match that match?** Answer it yes, and the roster
must be a *certified input* — snapshotted, transmitted, replayed from,
hashed, and addressed. Answer it no, and the roster may never touch the
yard, which is exactly the wall season-lite was built to respect while
the rest of the loop got built.

This doc answers yes, and pays for it.

## 3. What A Roster Is

Three fielded operatives, in slot order, each with a name and the shape
they are in:

```js
[{ name: "VESPER", hp: 10 }, { name: "NIX", hp: 10 }, { name: "SABLE", hp: 3 }]
```

Two axes, deliberately, and no more:

- **Who** — the name rides the transcript, so a substitution is a
  different record. This is precisely why season-lite could not bench
  anyone: lineup was already rules-level, and there was no lite version
  of benching-with-substitution that did not either lie to the renderer
  or break the certificate.
- **What shape they are in** — starting `hp`. `maxHp` stays 10 whatever
  the roster says: a fighter carried in at 7 is at seven **of** ten, not
  a smaller fighter. That distinction is the whole reason a wound can
  heal rather than becoming who someone is.

What a roster deliberately is **not**: positions, hostiles, stats, gear,
or verbs. Slots belong to the encounter. Everything in Circuit §6 that
grants a *verb* — head, torso, legs, primary, sidearm — is a further
step, and it is a much easier one now that this exists: it is just more
roster state in a snapshot that is already certified.

`rosterValid()` is the boundary check and lives in the rules core, so the
room, the yard and the Worker cannot each hold a different idea of what a
squad is. `rosterKey()` is its one canonical form — a hash computed three
ways is three hashes.

A roster entry carries **exactly** those two fields. Checking only that
the required ones were present let a caller send a fighter with `gear`
bolted on, get a 200 back, and file under the same content address as the
clean roster — the extra silently dropped on the way in. That bug's worst
property is that it looks exactly like the Tier 2 future already working.

**Malformed is a fault, never a default.** `restart()` throws rather than
falling back to the canonical three, because falling back would field a
squad nobody asked for and then certify the result. Each caller answers
for it in its own grammar: the Worker with a 400, the yard with a boot
fault.

And the yard asks a **second** question the rules core does not:
`rosterValid` says who may *fight*; the renderer says who it can *draw*.
A name that passes the first and fails the second used to validate,
field, and then throw inside `fighterSlug` on the first frame — after the
boot guard, so the yard died silently and the room sat waiting out its
hand-off timer (caught in review). A body with no sheets is now a fault
at the door, naming who it cannot draw and who it can.

The room, notably, does **not** validate. It cannot import the rules, and
a first cut that re-checked name shape and uniqueness at the room's own
boundary was worse than nothing: a second, *incomplete* roster grammar
(no slot count, no hp bounds, no hostile-name collision) sitting where
the single definition is supposed to be, free to drift. The room
publishes the wire form it deals; the harness holds that against
`rosterValid` and `CANON_ROSTER`, which is the same asymmetry that has
always guarded the operative names — the room may not import the rules,
the test may.

**Absent is canonical.** No roster means the canonical three at full
strength — what every match was fought by before this input existed. That
is not a fallback, it is the identity element: a standalone yard opened
from a bookmark still works, and every record filed before today still
certifies to the squad it was actually fought by.

## 4. One Owner Per Phase

| Phase | Owns | Does not |
|---|---|---|
| the **room** | which squad is fielded; deals it at the threshold | reinterpret what comes back — it compares, field by field |
| the **card** | an immutable snapshot, taken at the deal | change once dealt |
| the **yard** | fielding exactly what it was handed | edit the squad it was dealt |
| the **witness** | replaying *from* the snapshot | trust the room about it — the certificate reports what the replay fielded |
| the **archive** | an id that includes the roster | overwrite a different squad's match |

Nobody reinterprets it afterward. That sentence is the mechanism.

## 5. The Stamp And The Hash Are Different Things

This is the part that was got wrong in the season doc's first draft and
corrected in review, and it is worth restating because it looks like a
detail and is not:

- **`rosterHash` is its own certificate field.** It is NOT folded into
  the rules stamp. The stamp is the behavioral version of the *rules*;
  a wound is not a rules deployment. Folding them would mark ordinary
  season progression as rules drift on every single card, and the room
  would report `RULES CHANGED MID-RUN` for a fighter having a limp.
- **The roster golden IS a stamp input.** How a fielded squad is *applied*
  is rules behavior, and the two existing goldens both field the
  canonical three — so without a third golden, a change to roster
  handling would move nothing and old records would silently certify
  under new semantics. Same gap the showrunner golden closed for twists,
  closed the same way. It carries a **record** and runs through
  `replayMatch(seed, record, roster)` rather than `restart`, because that
  is the path certification takes: stamping the neighbouring path left
  the roster's *forwarding* unstamped, and a `replayMatch` that dropped
  its third argument moved nothing while fielding the canonical three
  (caught in review, executed as a mutation).

So the stamp moves once, on this deploy, because its inputs grew — the
second time that has happened, and deliberately both times. Runs open
across the deploy will report drift, which is correct: their banked
numbers *were* earned under different rules.

## 6. The Content Address

`/file` keys on a SHA-256 of `{rules, seed, roster, record}` — the roster
entering as its canonical key, so the address cannot move because a
caller spelled the same squad with different whitespace.

This answers the fourth item on run-core's price list, which has been
open since the run layer was built: *what does a filed record mean when
two players play the same seed with different squads?* It means what it
says. The roster is in the address, so a record individuates by what
actually fought. Two squads, two matches, two ids, and neither can
overwrite the other.

The cost, named: entries filed under the old formula keep their old ids,
and the same match resubmitted today files fresh. The stamp moved anyway
(§5), so those records would be refused as claiming different rules
regardless — the archive is a prototype ledger and this is a one-time
discontinuity, not an ongoing one.

## 7. The Price List, Checked Off

`prototypes/run-core/README.md` priced this change before it was built.
Every line is paid here:

- ✅ `restart(seed, roster)` and `replayMatch(seed, commands, roster)`
- ✅ a roster in the `/certify` and `/file` bodies
- ✅ the roster in the content address — and, deliberately **not** in the
  rules stamp (§5); the stamp instead gains a golden that exercises it
- ✅ a decision about what a filed record *means* when two players play
  the same seed with different squads (§6)

## 8. Deploying It

The Worker and the pages ship separately, so the two orders differ:

- **new Worker, old pages** — fine. The certificate grows a field nobody
  reads yet.
- **old Worker, new pages** — the certificate says nothing about the
  squad. The room treats that as a third case rather than a failure:
  the card is **counted and labelled** `SQUAD NOT ATTESTED — THIS EDGE
  PREDATES THE ROSTER`. Requiring the field would strike every honest
  card until the Worker is redeployed; assuming agreement would be the
  silent half of the same mistake. All three cases are executed in
  `test_seam_round_trip.mjs` against a stubbed edge.

The stamp moves on this deploy (§5), so runs open across it report drift.
That is correct: their banked numbers were earned under different rules.

## 9. What This Does Not Do

Named plainly, because a doctrine PR that quietly smuggled a balance
change would be exactly the thing this repo argues against:

- **Wounds still do not impair.** The room deals the canonical three at
  full strength. The plumbing carries `hp` end to end and the goldens
  exercise it, but whether a fighter who went down last card is carried
  in at 7 is a *design* decision — it interacts with the season doc's
  open questions 2 (recovery economics) and 4 (death vs downed), and it
  belongs to the designer, not to the PR that made it possible. It is now
  a one-line change in the room.
- **The run does not own roster state yet.** Season-lite's wound clocks
  live in `run-core` and gate the *deal*; the lineup lives in the room.
  The season doc's "the run owns mutable roster state" is the next step,
  and it is now unblocked rather than blocked.
- **No benching.** A roster is exactly three fielded operatives. Fielding
  two is a real want (Circuit §6) and needs slot handling the encounter
  does not have.
- **No gear, no verbs.** Circuit §6's registers stay asleep. They wake as
  more roster state, in a snapshot that is already certified.

## 10. What Wakes Up

Everything §6 of the Circuit doc designed and gated, and everything Tier 2
of the season doc promised: gear slots carrying verbs and geometry,
primary ammo and the sidearm floor, sponsor rigs mounted on a torso,
lineup choice against a known opponent as the tale of the tape, wounded
fighters fielded impaired or benched for real.

None of those need individual holes punched through determinism any more.
They are all just roster state, snapshotted and certified — which is the
sentence this whole change exists to make true.
