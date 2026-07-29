# sentinel-witness

The Witness record as deployed infrastructure — the hello-world of the
Cloudflare platform direction, and the proof of its load-bearing claim:
**one rules module, three runtimes.** The browser plays
`prototypes/tactical-core/rules.js`, `node --test` guards it, and this
Worker certifies it at the edge — same bytes in all three.

Live at: `https://sentinel-witness.ishawnd.workers.dev`

```
GET  /replay?seed=deadbeef
POST /certify   {"seed":"6","record":[["move",0,1,7],...,["spare"]]}
```

`/replay` replays the no-input encounter for a seed. `/certify` takes a
**played match** — the input-log protocol, Circuit roadmap step 5: `seed +
record` is the match, where the record is the command list the rules core
accumulated in `S.record` while the player played. Both replay through the
shared rules module and return the certified transcript: result, rating,
purse, line count, the FNV-1a fingerprint, and the transcript itself.

## Certification policy

Replaying a record re-records it, and commands the rules refuse don't
re-record — so a faithful replay **reproduces its own input**, and that
closure is the integrity check. `/certify` refuses, with the reason on the
surface:

- `422 "record does not replay"` — tampered, reordered, or from a
  different rules version; fails closed at the first refused command
- `422 "record replays but the match is unfinished"` — fidelity is not
  completeness; a certificate is for a match, not a fragment
- `400` — wire-level garbage (non-array commands, oversized records)

## The acceptance test is the goldens — and a locally-played match

Seed `deadbeef` must answer fingerprint `39e8be71` (42 lines) and seed `1`
must answer `bac5ad90` (39 lines) — the exact hashes captured from the
browser build *before the rules were extracted*, asserted in
`rules.test.js`, and now served from the edge. If the edge disagrees with
the goldens, the deploy is wrong, not the goldens.

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
                                      # + refusals + concurrency burst
```

The whole bundle — game rules included — is ~5.6 KiB gzipped.

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
