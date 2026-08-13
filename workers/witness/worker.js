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
   POST /certify {seed,roster,record}
                               — a PLAYED match: the input-log protocol
                                 (Circuit roadmap step 5), designed in the
                                 rules core (S.record / replayMatch) and
                                 inherited here. The record replays through
                                 the same verbs the player used; a replay
                                 that cannot reproduce its own input, or
                                 that ends unfinished, certifies nothing.

   The roster is the second certified input (`architecture/
   roster_in_the_match.md`): the law is now `seed + roster + record = the
   match`. It is validated at this boundary with the rules core's own
   check, replayed from rather than trusted, reported in the certificate
   as its own field, and folded into the content address — so the same
   record fought by a different squad is a DIFFERENT match, never an
   overwrite. It is deliberately NOT folded into the rules stamp: a wound
   is not a rules deployment, and conflating the two would mark ordinary
   season progression as drift on every card.
   ============================================================ */

import { S, bindIO, restart, endPlayerTurn, replayMatch, formatEvent, RATING, rosterValid, rosterKey } from "../../prototypes/tactical-core/rules.js";
import { SHOWRUNNER_GOLDEN } from "../../prototypes/tactical-core/showrunner-golden.js";
import { ROSTER_GOLDEN } from "../../prototypes/tactical-core/roster-golden.js";

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

// The rules version, as behavior: the fingerprint of the golden playouts
// under the rules actually running here. Doc changes don't bump it; any
// change to a draw, a guard, or a transcript line does. Certificates
// carry it, and a record claiming a different stamp is refused before
// replay — its faithfulness under these rules would be meaningless.
//
// THREE playouts, one stamp: the deadbeef golden exercises the base game,
// the showrunner golden exercises the twist grammar and card math a
// no-input playout can never reach, and the roster golden exercises the
// second certified input — without each of them, a change in that area
// would move nothing and old records would silently certify under new
// terms. Each golden contributes its transcript fingerprint AND its
// outcome (result, rating, purse): rating is deliberately never a
// transcript line, so payout behavior could otherwise change under an
// unchanged stamp (caught in review). Extending the stamp's INPUTS is
// the one legitimate way the stamp changes without behavior changing;
// it happened when twists landed, it happens again here, and both times
// deliberately. Note what this does NOT do: the stamp covers how a
// roster is APPLIED, never which roster a given card fielded — that is
// the certificate's own field, because a wound is not a deployment.
// Computed once per isolate; callers must hold the mutex (it runs the
// shared S machine).
let rulesStamp = null;
async function rulesFingerprint() {
  if (rulesStamp === null) {
    const base = await replay(0xdeadbeef);
    const twistLines = captureLines();
    await replayMatch(SHOWRUNNER_GOLDEN.seed, SHOWRUNNER_GOLDEN.record);
    const twist = [fnv(twistLines.join("\n")), S.gameOver, S.rating, S.rating * RATING.pursePerPoint];
    const rosterLines = captureLines();
    restart(ROSTER_GOLDEN.seed, ROSTER_GOLDEN.roster);
    for (let i = 0; i < 14 && !S.gameOver; i++) await endPlayerTurn();
    const roster = [
      fnv(rosterLines.join("\n")), S.gameOver, S.rating,
      S.rating * RATING.pursePerPoint, rosterKey(S.roster),
    ];
    rulesStamp = fnv([
      base.fingerprint, base.result, base.rating, base.purse,
      ...twist, ...roster,
    ].join(":"));
  }
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
    // The squad the REPLAY fielded, not the one the request claimed — a
    // certificate that echoed its input would be attesting to a promise
    // rather than to a playout. `rosterHash` is its own field on purpose;
    // see the header on why it is not in the rules stamp.
    roster: S.roster,
    rosterHash: fnv(rosterKey(S.roster)),
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
// player identity, which does not exist anywhere yet.
async function certify(seed, record, roster, claimedRules, claimedFp) {
  const rules = await rulesFingerprint();
  if (claimedRules !== undefined && claimedRules !== rules) {
    return { status: 422, body: {
      certified: false, error: "record claims a different rules version",
      rules, claimed: claimedRules,
    } };
  }
  const lines = captureLines();
  const fidelity = await replayMatch(seed, record, roster);
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
  const cert = certificate(seed, lines, { commands: record.length });
  // the fingerprint claim: "this is the match I watched." A page that
  // outlived a deploy can hold a record whose commands still replay under
  // newer rules — to a different match. Refusing the mismatch keeps the
  // archive from ever storing a transcript the player never saw.
  if (claimedFp !== undefined && claimedFp !== cert.fingerprint) {
    return { status: 422, body: {
      certified: false, error: "record replays to a different match than claimed",
      rules, fingerprint: cert.fingerprint, claimed: claimedFp,
    } };
  }
  // the ledger the post-match card shows, derived from the replayed state:
  // yielded stays true on the dead, which is how the record knows mercy
  // from execution
  const ledger = {
    walked:   S.units.filter(u => u.side === "ho" && u.alive && u.yielded).length,
    finished: S.units.filter(u => u.side === "ho" && !u.alive && u.yielded).length,
    lost:     S.units.filter(u => u.side === "op" && !u.alive).length,
  };
  return { status: 200, body: { certified: true, rules, ledger, ...cert } };
}

// CORS is open by design: the tactical prototype files records straight
// from the browser, and everything here is either public (replay, list)
// or self-verifying (file certifies before it stores).
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json", ...CORS },
  });
}

const SEED_RE = /^[0-9a-fA-F]{1,8}$/;

// Wire-level grammar: exact arity per verb, integer args in a sane
// domain. This keeps 400 for "you cannot even say that" and reserves 422
// for records that speak the grammar and still fail to replay. The real
// gatekeeper stays the dispatcher in the rules core — if the grammar
// grows a verb this table lags on, witness_check's played-match round
// trip fails loudly at deploy time, not silently in production.
const ARITY = { move: 4, shoot: 3, finish: 3, ow: 2, spare: 1, end: 1, twist: 2 };
function validRecord(record) {
  return Array.isArray(record) && record.length <= 1024 &&
    record.every(c => Array.isArray(c) && c.length === ARITY[c[0]] &&
      c.slice(1).every(v => Number.isInteger(v) && v >= 0 && v <= 255));
}

async function sha256hex(s) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("");
}

// Filing: certify, then archive. Identity is content-addressed — a
// SHA-256 digest of everything that makes the match the match: the rules
// stamp, the seed, the ROSTER, and the record. Rules included on purpose:
// the same record under different rules is a DIFFERENT match, never an
// overwrite. The roster is there for the same reason and answers the
// fourth item on run-core's price list — what a filed record means when
// two players play the same seed with different squads. It means what it
// says: a record individuates by what actually fought.
// (The transcript fingerprint stays FNV for continuity with the goldens;
// it is a checksum, not an identity — caught in review.) Filing is
// state-idempotent: an already-filed match returns the original entry,
// original timestamp — resubmission can neither inflate a career nor
// bump an old record to the top of the archive.
//
// The roster enters as its canonical KEY rather than the array: the
// address must not move because a caller spelled the same squad with
// different whitespace or key order.
async function fileMatch(env, seed, record, roster, claimedRules, claimedFp) {
  // KV work stays outside the mutex; the replay machine inside it
  const out = await serialized(() => certify(seed, record, roster, claimedRules, claimedFp));
  if (out.status !== 200) return { status: out.status, body: { filed: false, ...out.body } };
  const cert = out.body;
  const id = (await sha256hex(JSON.stringify({
    rules: cert.rules, seed: cert.seed, roster: rosterKey(cert.roster), record,
  }))).slice(0, 32);
  const key = `match:${id}`;
  const prior = await env.RECORDS.get(key, "json");
  if (prior) {
    return { status: 200, body: { filed: true, existing: true, id, filed_at: prior.filed_at, ...cert } };
  }
  // Best-effort cap, checked only for NEW entries so refiling always
  // works, even at capacity. Concurrent first-time filers near the limit
  // can overshoot by a few — this is a soft cap on a dev ledger, not an
  // invariant (a hard one wants a Durable Object, and this archive does
  // not want a Durable Object yet).
  const existing = await env.RECORDS.list({ prefix: "match:", limit: 1000 });
  if (existing.keys.length >= 1000) {
    return { status: 507, body: { filed: false, error: "the archive is full — this is a prototype ledger, not a product one" } };
  }
  const at = new Date().toISOString();
  const meta = {
    at, seed: cert.seed, result: cert.result, rating: cert.rating,
    purse: cert.purse, fingerprint: cert.fingerprint, rules: cert.rules,
    rosterHash: cert.rosterHash,
    commands: cert.commands, ledger: cert.ledger,
  };
  await env.RECORDS.put(key, JSON.stringify({ filed_at: at, record, certificate: cert }), { metadata: meta });
  return { status: 200, body: { filed: true, existing: false, id, filed_at: at, ...cert } };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
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
    if (url.pathname === "/certify" || url.pathname === "/file") {
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
      if (body.fingerprint !== undefined && !/^[0-9a-f]{1,8}$/.test(body.fingerprint ?? "")) {
        return json({ error: "fingerprint, if claimed, is the transcript hash the post-match card shows" }, 400);
      }
      // The roster is optional on the wire and canonical when absent, so
      // every record filed before this input existed still certifies to
      // the squad it was actually fought by. Present, it is checked with
      // the rules core's OWN boundary check — one definition of what a
      // roster is, not a second one drifting out here. 400, not 422: a
      // malformed roster is not a record that failed to replay, it is a
      // request that cannot be understood.
      if (body.roster !== undefined && !rosterValid(body.roster)) {
        return json({ error: "roster, if claimed, is three fielded operatives — [{name, hp}, ...] with unique names and hp 1..10" }, 400);
      }
      const roster = body.roster ?? null;
      try {
        const { status, body: out } = await (url.pathname === "/file"
          ? fileMatch(env, parseInt(raw, 16), body.record, roster, body.rules, body.fingerprint)
          : serialized(() => certify(parseInt(raw, 16), body.record, roster, body.rules, body.fingerprint)));
        return json(out, status);
      } catch (err) {
        console.log(JSON.stringify({ level: "error", event: "witness_certify_failed", path: url.pathname, seed: raw, message: String(err) }));
        return json({ error: "certify failed" }, 500);
      }
    }
    if (url.pathname === "/matches" && request.method === "GET") {
      // walk every page — the cap bounds this at a handful of list calls,
      // and a partial page sorted "newest first" is a lie (caught in review)
      const matches = [];
      let cursor;
      do {
        const page = await env.RECORDS.list({ prefix: "match:", limit: 1000, cursor });
        for (const k of page.keys) matches.push({ id: k.name.slice("match:".length), ...k.metadata });
        cursor = page.list_complete ? null : page.cursor;
      } while (cursor);
      matches.sort((a, b) => (b.at ?? "").localeCompare(a.at ?? ""));
      return json({ count: matches.length, matches });
    }
    if (url.pathname.startsWith("/matches/") && request.method === "GET") {
      const id = decodeURIComponent(url.pathname.slice("/matches/".length));
      const stored = await env.RECORDS.get(`match:${id}`, "json");
      if (!stored) return json({ error: "no such match on file" }, 404);
      return json({ id, ...stored });
    }
    return json({
      service: "sentinel-witness",
      what: "replays Kestrel Yard matches through the same rules module the renderers run, and certifies the transcript",
      usage: {
        replay: "GET /replay?seed=deadbeef — no-input playout, a pure function of the seed",
        certify: 'POST /certify {"seed":"<hex>","record":[...],"roster":[{"name":"VESPER","hp":10},...],"rules":"<optional fingerprint>"} — a played match; certified only if the record replays faithfully to a finished match under these rules and this roster',
        file: "POST /file — same body as /certify; certifies AND archives. Idempotent: the key is content-derived, so a match files once no matter how often it is submitted — and a different roster is a different key, because it is a different match",
        matches: "GET /matches — the archive, newest first (metadata only). GET /matches/{id} — one filed match in full: record + certificate",
      },
      note: "the record grammar lives in prototypes/tactical-core/rules.js (S.record / replayMatch) — seed + roster + record IS the match (architecture/roster_in_the_match.md; the roster is optional on the wire and canonical when absent). A certificate attests validity under the stamped rules version, not who played it; identity/signatures do not exist yet, so the archive is self-attested but replay-verified.",
    });
  },
};
