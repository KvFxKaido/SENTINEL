# sentinel-witness

The Witness record as deployed infrastructure — the hello-world of the
Cloudflare platform direction, and the proof of its load-bearing claim:
**one rules module, three runtimes.** The browser plays
`prototypes/tactical-core/rules.js`, `node --test` guards it, and this
Worker certifies it at the edge — same bytes in all three.

Live at: `https://sentinel-witness.ishawnd.workers.dev`

```
GET  /replay?seed=deadbeef
POST /certify      {"seed":"6","record":[["move",0,1,7],...,["spare"]],
                    "roster":[{"name":"VESPER","hp":10},...]}
POST /file         same body — certifies AND archives
GET  /matches      the archive, newest first (metadata only)
GET  /matches/{id} one filed match in full: record + certificate
```

`/replay` replays the no-input encounter for a seed. `/certify` takes a
**played match** — the input-log protocol, Circuit roadmap step 5: `seed +
roster + record` is the match (`architecture/roster_in_the_match.md`;
the law was `seed + record` until the roster became a certified input),
where the record is the command list the rules core accumulated in
`S.record` while the match was played. Both replay through
the shared rules module and return the certified transcript: result,
rating, purse, line count, the FNV-1a fingerprint, and the transcript
itself. A certificate also carries `derivedEvents`, authored from the
Worker's own completed replay; request bodies never supply this field for the
edge to trust or cross-check. The grammar spans eight verbs — the player's seven and the house's
`["twist", cardId]` (Circuit step 4), which certifies like any other hand
on the record: legal only between rounds, budgeted by the rules, an
illegally-timed card fails closed as an unfaithful replay. Extraction's
`["drag", actorId, bodyId, x, y]` is likewise explicit on the record: who
acted, for whom, and where all cross the wire together.

## Certification policy

Replaying a record re-records it, and commands the rules refuse don't
re-record — so a faithful replay **reproduces its own input**, and that
closure is the integrity check. `/certify` refuses, with the reason on the
surface:

- `422 "record claims a different rules version"` — the optional `rules`
  field names the stamp the record was made under; a mismatch is refused
  *before* replay, because faithfulness under different rules is
  meaningless
- `422 "record does not replay"` — tampered or reordered; fails closed at
  the first refused command
- `422 "record replays but the match is unfinished"` — fidelity is not
  completeness; a certificate is for a match, not a fragment
- `400` — wire-level grammar violations (unknown verbs, wrong arity,
  non-integer args, oversized records) — reserved for "you cannot even
  say that," so 422 always means authentic replay divergence

## The rules stamp

Every response carries `rules`: the version, expressed as behavior —
derived from golden playouts under the rules actually running. Doc
changes don't bump it; any change to a draw, a guard, a transcript line,
or a card's terms does. Anything persisting records should store the
stamp alongside them and send it back as `rules` when certifying, so a
record can never be silently reinterpreted by newer rules as if history
had always been that way.

The stamp hashes **four** playouts, each pinning an area the others
cannot reach:

| golden | pins | fingerprint |
|---|---|---|
| deadbeef, no input | the base game | `39e8be71` |
| showrunner (`showrunner-golden.js`) | the twist grammar and card math | `6495eab3` |
| roster (`roster-golden.js`) | how a fielded squad is carried in | `d44833c0` |
| extraction (`drag-golden.js`) | the drag grammar, movement, reaction fire, and rating | `e9e0a018` |

The second landed with twists (2026-07-29) because a no-input playout can
never play a card: without it, a balance patch to a card's terms would
move nothing and old records would silently certify under new card math.
The third landed with the roster doctrine (2026-08-13) for exactly the
same reason — the other two both field the canonical three, so neither
can stamp what a roster does. The fourth landed with extraction: none of
the earlier records can exercise a two-person drag or its consequences.

Each golden contributes its transcript fingerprint **and its outcome** —
result, rating, purse — because rating is deliberately never a transcript
line, so payout behavior could otherwise change under an unchanged stamp
(caught in review); the roster golden adds its canonical key and its
`faithful` flag. Since durable-moment step 3, each also contributes its
derived-event array: the first three contribute `[]`, while the drag golden
contributes its pinned extraction predicate. Today's stamp is `b9a69b0c` =
`fnv("39e8be71:loss:29:290:[]:6495eab3:win:92:920:[]:d44833c0:loss:35:350:VESPER:6|NIX:10|SABLE:3:true:[]:e9e0a018:loss:41:410:[{\"kind\":\"extraction\",\"actor\":\"SABLE\",\"beneficiary\":\"KOA\",\"commandIndex\":6,\"underFire\":true,\"reached\":true}]")`.
The four transcript fingerprints stayed fixed; the stamp moved from
`78c24d5a` because the derivation predicate is now stamped rules behavior.

The roster golden runs through **`replayMatch(seed, record, roster)`**,
not `restart` — the path certification actually takes. Stamping the
neighbouring path left the roster's *forwarding* unstamped: a
`replayMatch` that dropped its third argument moved nothing while quietly
fielding the canonical three (caught in review, executed as a mutation).

Extending the stamp's *inputs* is the one legitimate way the stamp
changes without behavior changing — it has happened four times now, each
time deliberately. Records stamped under an older input set are correctly
refused as claiming a different rules version, because they are.

What the stamp does **not** cover: which roster a given card fielded. That
is the certificate's own `rosterHash` field. A wound is not a rules
deployment, and folding the two would report ordinary season progression
as rules drift on every card.

## The archive (campaign wiring, the persistence half)

`POST /file` certifies and then stores the match in KV. Identity is
**content-addressed**: the id is a SHA-256 digest (truncated to 128 bits)
of `{rules, seed, roster, record}` — everything that makes the match the
match. Rules are in the digest on purpose: the same record under different
rules is a *different* match, never an overwrite. The roster is there for
the same reason, and it answers the question run-core's price list left
open: what a filed record *means* when two players play the same seed with
different squads. It means what it says — a record individuates by what
actually fought, so the same commands under a substituted fighter file as
their own match and neither can clobber the other. (The transcript fingerprint
stays FNV-32 for continuity with the goldens — it is a checksum, not an
identity.) Filing is **state-idempotent**: an already-filed match returns
the original entry with its original timestamp, so resubmission can
neither inflate the ledger nor bump an old record to the top.

**Recorded design decision — 2026-08-16, durable-moment step 3:** the
walkable room's certified seam path will call `/file`, not bare `/certify` —
that consumer half ships separately and lands once this edge is deployed.
Therefore every card that surface labels certified receives a durable match
id in the same replay transaction. This is recorded for designer review and
can be vetoed there. It does not pre-decide feed cutting: a future deliberate
darkness path submits to neither endpoint. The tactical yard's explicit
**FILE THE RECORD** button also continues to call `/file` directly.

`POST /file` and `/certify` also accept an optional **fingerprint claim**
— "this is the match I watched." A browser page that outlived a rules
deploy can hold a record whose commands still replay under newer rules,
to a different match; the claim makes the worker refuse rather than
archive a transcript the player never saw. The prototype always sends it.

Certificates carry the **ledger** — walked / finished / lost — and
`derivedEvents`, all derived from the replayed state, plus the **roster** the
replay actually fielded with its own `rosterHash`, and the rules stamp,
so a future rules version can refuse to silently reinterpret the archive.
The full stored certificate retains the derived array; the metadata-only
archive listing does not need to duplicate it.

The roster is validated at this boundary with the rules core's own
`rosterValid` — one definition of what a squad is, not a second one
drifting out here — and a malformed one is a **400**, not a 422: it is a
request that cannot be understood, not a record that failed to replay.
Absent, the canonical three at full strength are fielded, so every record
filed before this input existed still certifies to the squad it was
actually fought by. `rosterHash` is deliberately its **own** field rather
than being folded into the rules stamp: a wound is not a rules
deployment, and conflating them would report ordinary season progression
as rules drift on every card.
`GET /matches` walks every KV page before sorting: the listing is
globally newest-first and complete, bounded by the cap.

The tactical prototype consumes this directly: the post-match card's FILE
THE RECORD button posts the exact `/file` wire shape and, after success,
shows each replay-derived event with its `(match id, command index)` pointer.
THE ARCHIVE line is `GET /matches` summarized — cards on file, W–L, purse paid out.
It is labeled *archive*, not *career*, because the ledger is one shared
public namespace and nothing scopes records to a player yet; when
identity exists, careers become a view over it.

Prototype-grade honesty: the archive is **self-attested but
replay-verified** — nothing proves *who* played a record (identity and
signatures don't exist anywhere yet), but nothing enters the archive
without replaying faithfully to a finished match under the current rules.
Writes are public with a **soft cap** (1,000 entries, checked
best-effort; concurrent filers near the limit can overshoot by a few —
a hard cap wants a Durable Object, and this dev ledger doesn't). The
campaign-consequence half of roadmap step 5 (matches as jobs, wiki
events, disposition, dormant threads) belongs to the campaign brain and
is deliberately not improvised here.

## What a certificate attests — and what it doesn't

A certificate attests that the record is a **valid match under the
stamped rules** and that this transcript is its one true replay. It does
not attest *who* played it, or that it was played live rather than
synthesized — a legal command sequence certifies no matter whose hand
wrote it. That is validation, not provenance. Provenance (commitments or
signatures binding a record to a player and a moment) is the campaign
wiring layer's problem, and it starts mattering exactly when purses do.

## The acceptance test is the goldens — and a locally-played match

Seed `deadbeef` must answer fingerprint `39e8be71` (42 lines) and seed `1`
must answer `bac5ad90` (39 lines) — the exact hashes captured from the
browser build *before the rules were extracted*, asserted in
`rules.test.js`, and now served from the edge. The showrunner golden must
certify to `6495eab3` with MERCY ODDS paid and an empty derived array, and the
extraction golden must certify its drag-containing record to `e9e0a018` with
the pinned extraction event. If the edge disagrees
with the goldens, the deploy is wrong, not the goldens.

`witness_check.mjs` goes one further: it imports the rules core, *plays* a
match locally (deterministic auto-player, public verbs only), and demands
the edge certify it to the identical fingerprint, rating, and purse —
local play and edge certification, same bytes.

## Run / deploy

```sh
cd workers/witness
pnpm dlx wrangler dev --port 8787     # local
pnpm dlx wrangler deploy              # to Cloudflare
node witness_check.mjs [base-url]     # goldens + played-match certification
                                      # + refusals + roster + archive + burst
```

The whole bundle — game rules included — is ~10.6 KiB gzipped.

**CI deploys this on every master push that touches the Worker or the
rules core it bundles**, gated on the suites that can falsify it and
verified against the live URL afterwards — deploy-then-assert, never
deploy-and-hope. That job exists because CI already *tests against
production*: the yard harness walks the seam against the live edge, so an
edge lagging behind master makes CI dishonest in both directions rather
than merely out of date.

It is inert without `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`
repo secrets — it says so and passes, rather than painting master red for
a setup step nobody has done. The token wants exactly two scopes: Workers
Scripts:Edit and Workers KV Storage:Edit.

Running `witness_check.mjs` against the live edge **files matches into the
real archive**, and that is fine on purpose: filing is content-addressed
off a deterministic auto-played match, so re-running it refiles the same
two ids instead of growing the ledger. It also skips its own
bulk-pagination section against any non-localhost URL, which is the one
part that would flood a real archive.

One live-only caveat, learned deploying: KV's `list` is **eventually
consistent** where a direct key read is not, so a freshly filed match can
fetch back in full while not yet appearing in `GET /matches` (~4s
observed). The archive-listing check polls for that rather than asserting
it within one round trip.

## Scope

The input-log protocol was designed in the rules core (`S.record` /
`replayMatch` in `prototypes/tactical-core/rules.js`, with its own test
suite) and this Worker inherits it — exactly the order the first version
of this README promised. What remains of roadmap step 5 is the campaign
wiring: persisting records, feeding results into wiki events, disposition,
and dormant threads. That lands when matches become a job type, not here.

One implementation note: `rules.js` keeps a single module-level encounter
by design (its README documents the deliberate deferral of forkable
state). Concurrent requests in one isolate would interleave at awaits, so
replays serialize through a promise-chain mutex — verified with an
8-request interleaved burst in `witness_check`. When a real caller needs
parallel encounters, the refactor happens in the core
(`createEncounter(seed)`), and this Worker inherits it.
