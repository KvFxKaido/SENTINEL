/* ============================================================
   sentinel-witness — the Witness record as an endpoint.

   Replays a Kestrel Yard encounter from its seed through the SAME rules
   module both renderers run (../../prototypes/tactical-core/rules.js,
   bundled in by wrangler) and returns the certified transcript: the
   fingerprint here is the byte-for-byte FNV-1a hash the golden tests
   assert, so seed deadbeef answers 39e8be71 from the edge or it is a
   deploy failure.

   Two endpoints, one discipline:

   GET  /replay?seed=<hex>     — no-input playout, a pure function of the
                                 seed. The goldens live here.
   POST /certify {seed,record} — a PLAYED match: the input-log protocol
                                 (Circuit roadmap step 5), designed in the
                                 rules core (S.record / replayMatch) and
                                 inherited here. The record replays through
                                 the same verbs the player used; a replay
                                 that cannot reproduce its own input, or
                                 that ends unfinished, certifies nothing.
   ============================================================ */

import { S, bindIO, restart, endPlayerTurn, replayMatch, formatEvent, RATING } from "../../prototypes/tactical-core/rules.js";

// FNV-1a, mirroring rules.test.js — the certificate must be the same hash
// the goldens assert or it certifies nothing.
function fnv(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h.toString(16);
}

// rules.js keeps one module-level encounter by design (its README:
// forkable state waits for a real caller — this Worker may become that
// caller someday, but does not get to force the refactor from outside).
// Within an isolate, concurrent requests would interleave at the awaits
// inside a playout, so replays serialize through a promise chain. This is
// a mutex, not request state; a failed replay must not wedge the chain.
let chain = Promise.resolve();
function serialized(fn) {
  const run = chain.then(fn);
  chain = run.then(() => {}, () => {});
  return run;
}

// The rules version, as behavior: the fingerprint of the golden playout
// under the rules actually running here. Doc changes don't bump it; any
// change to a draw, a guard, or a transcript line does. Certificates
// carry it, and a record claiming a different stamp is refused before
// replay — its faithfulness under these rules would be meaningless.
// Computed once per isolate; callers must hold the mutex (it runs the
// shared S machine).
let rulesStamp = null;
async function rulesFingerprint() {
  if (rulesStamp === null) rulesStamp = (await replay(0xdeadbeef)).fingerprint;
  return rulesStamp;
}

function captureLines() {
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: (ev) => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  return lines;
}

function certificate(seed, lines, extra = {}) {
  return {
    seed: (seed >>> 0).toString(16),
    result: S.gameOver,
    rating: S.rating,
    purse: S.rating * RATING.pursePerPoint,
    ...extra,
    lines: lines.length,
    fingerprint: fnv(lines.join("\n")),
    transcript: lines,
  };
}

async function replay(seed) {
  const lines = captureLines();
  restart(seed);
  // the goldens' horizon: hostile turns need no player input, so the
  // transcript is a pure function of the seed
  for (let i = 0; i < 14 && !S.gameOver; i++) await endPlayerTurn();
  return certificate(seed, lines);
}

// The certification policy, in full: a record must claim these rules (or
// stay silent), must reproduce itself (rules-refused commands don't
// re-record, so tampering fails closed), and must end the match (fidelity
// is not completeness). Everything else is a refusal with the reason on
// the surface. What a certificate attests: this record is a valid match
// under the stamped rules and this transcript is its one true replay —
// validation, not provenance. WHO played it is a claim this Worker
// cannot check yet; that layer (commitments/signatures) arrives with
// campaign wiring, where purses start to matter.
async function certify(seed, record, claimedRules) {
  const rules = await rulesFingerprint();
  if (claimedRules !== undefined && claimedRules !== rules) {
    return { status: 422, body: {
      certified: false, error: "record claims a different rules version",
      rules, claimed: claimedRules,
    } };
  }
  const lines = captureLines();
  const fidelity = await replayMatch(seed, record);
  if (!fidelity.faithful) {
    return { status: 422, body: {
      certified: false, error: "record does not replay", rules,
      applied: fidelity.applied, submitted: fidelity.submitted,
    } };
  }
  if (!S.gameOver) {
    return { status: 422, body: {
      certified: false, error: "record replays but the match is unfinished",
      rules, commands: record.length,
    } };
  }
  return { status: 200, body: { certified: true, rules, ...certificate(seed, lines, { commands: record.length }) } };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const SEED_RE = /^[0-9a-fA-F]{1,8}$/;

// Wire-level grammar: exact arity per verb, integer args in a sane
// domain. This keeps 400 for "you cannot even say that" and reserves 422
// for records that speak the grammar and still fail to replay. The real
// gatekeeper stays the dispatcher in the rules core — if the grammar
// grows a verb this table lags on, witness_check's played-match round
// trip fails loudly at deploy time, not silently in production.
const ARITY = { move: 4, shoot: 3, finish: 3, ow: 2, spare: 1, end: 1 };
function validRecord(record) {
  return Array.isArray(record) && record.length <= 1024 &&
    record.every(c => Array.isArray(c) && c.length === ARITY[c[0]] &&
      c.slice(1).every(v => Number.isInteger(v) && v >= 0 && v <= 255));
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/replay") {
      const raw = url.searchParams.get("seed");
      if (!raw || !SEED_RE.test(raw)) {
        return json({ error: "seed required — GET /replay?seed=<hex, up to 8 digits>" }, 400);
      }
      try {
        return json(await serialized(async () => {
          const rules = await rulesFingerprint();
          return { rules, ...(await replay(parseInt(raw, 16))) };
        }));
      } catch (err) {
        console.log(JSON.stringify({ level: "error", event: "witness_replay_failed", seed: raw, message: String(err) }));
        return json({ error: "replay failed" }, 500);
      }
    }
    if (url.pathname === "/certify") {
      if (request.method !== "POST") {
        return json({ error: 'POST a witness record — {"seed":"<hex>","record":[["move",0,3,7],...]}' }, 405);
      }
      let body;
      try { body = await request.json(); } catch { return json({ error: "body must be JSON" }, 400); }
      const raw = typeof body?.seed === "string" ? body.seed : "";
      if (!SEED_RE.test(raw)) return json({ error: "seed required — hex, up to 8 digits" }, 400);
      if (!validRecord(body.record)) {
        return json({ error: "record must be an array of at most 1024 commands, each [verb, ...int args] with exact arity" }, 400);
      }
      if (body.rules !== undefined && typeof body.rules !== "string") {
        return json({ error: "rules, if claimed, is the fingerprint string a certificate carries" }, 400);
      }
      try {
        const { status, body: out } = await serialized(() => certify(parseInt(raw, 16), body.record, body.rules));
        return json(out, status);
      } catch (err) {
        console.log(JSON.stringify({ level: "error", event: "witness_certify_failed", seed: raw, message: String(err) }));
        return json({ error: "certify failed" }, 500);
      }
    }
    return json({
      service: "sentinel-witness",
      what: "replays Kestrel Yard matches through the same rules module the renderers run, and certifies the transcript",
      usage: {
        replay: "GET /replay?seed=deadbeef — no-input playout, a pure function of the seed",
        certify: 'POST /certify {"seed":"<hex>","record":[...],"rules":"<optional fingerprint>"} — a played match; certified only if the record replays faithfully to a finished match under these rules',
      },
      note: "the record grammar lives in prototypes/tactical-core/rules.js (S.record / replayMatch) — seed + record IS the match. A certificate attests validity under the stamped rules version, not who played it; provenance is the campaign-wiring layer.",
    });
  },
};
