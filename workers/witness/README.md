# sentinel-witness

The Witness record as deployed infrastructure — the hello-world of the
Cloudflare platform direction, and the proof of its load-bearing claim:
**one rules module, three runtimes.** The browser plays
`prototypes/tactical-core/rules.js`, `node --test` guards it, and this
Worker certifies it at the edge — same bytes in all three.

Live at: `https://sentinel-witness.ishawnd.workers.dev`

```
GET /replay?seed=deadbeef
```

Replays the encounter for that seed through the shared rules module and
returns the certified transcript: result, rating, purse, line count, the
FNV-1a fingerprint, and the transcript itself.

## The acceptance test is the goldens

Seed `deadbeef` must answer fingerprint `39e8be71` (42 lines) and seed `1`
must answer `bac5ad90` (39 lines) — the exact hashes captured from the
browser build *before the rules were extracted*, asserted in
`rules.test.js`, and now served from the edge. If the edge disagrees with
the goldens, the deploy is wrong, not the goldens.

## Run / deploy

```sh
cd workers/witness
pnpm dlx wrangler dev --port 8787     # local
pnpm dlx wrangler deploy              # to Cloudflare
node <repo>/... witness_check.mjs     # goldens + concurrency burst, local or live
```

The whole bundle — game rules included — is ~5.6 KiB gzipped.

## Scope, deliberately

No-input playouts only: hostile turns need no player input, so the entire
transcript is a pure function of the seed. The full input-log protocol (a
*played* match as seed + player commands — the real Witness record) is
Circuit roadmap step 5 and gets designed in the rules core first, not
improvised in a Worker.

One implementation note: `rules.js` keeps a single module-level encounter
by design (its README documents the deliberate deferral of forkable
state). Concurrent requests in one isolate would interleave at awaits, so
replays serialize through a promise-chain mutex — verified with an
8-request interleaved burst in `witness_check`. When a real caller needs
parallel encounters, the refactor happens in the core
(`createEncounter(seed)`), and this Worker inherits it.
