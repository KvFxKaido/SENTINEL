/* ============================================================
   sentinel-witness — the Witness record as an endpoint.

   Replays a Kestrel Yard encounter from its seed through the SAME rules
   module both renderers run (../../prototypes/tactical-core/rules.js,
   bundled in by wrangler) and returns the certified transcript: the
   fingerprint here is the byte-for-byte FNV-1a hash the golden tests
   assert, so seed deadbeef answers 39e8be71 from the edge or it is a
   deploy failure.

   Scope, deliberately: no-input playouts only — the entire transcript is
   a pure function of the seed. The full input-log protocol (a played
   match as seed + player commands) is Circuit roadmap step 5 and gets
   designed in the rules core first, not improvised in a Worker.
   ============================================================ */

import { S, bindIO, restart, endPlayerTurn, formatEvent, RATING } from "../../prototypes/tactical-core/rules.js";

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
function replaySerialized(seed) {
  const run = chain.then(() => replay(seed));
  chain = run.then(() => {}, () => {});
  return run;
}

async function replay(seed) {
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: (ev) => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  restart(seed);
  // the goldens' horizon: hostile turns need no player input, so the
  // transcript is a pure function of the seed
  for (let i = 0; i < 14 && !S.gameOver; i++) await endPlayerTurn();
  return {
    seed: (seed >>> 0).toString(16),
    result: S.gameOver,
    rating: S.rating,
    purse: S.rating * RATING.pursePerPoint,
    lines: lines.length,
    fingerprint: fnv(lines.join("\n")),
    transcript: lines,
  };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj, null, 2), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/replay") {
      const raw = url.searchParams.get("seed");
      if (!raw || !/^[0-9a-fA-F]{1,8}$/.test(raw)) {
        return json({ error: "seed required — GET /replay?seed=<hex, up to 8 digits>" }, 400);
      }
      try {
        return json(await replaySerialized(parseInt(raw, 16)));
      } catch (err) {
        console.log(JSON.stringify({ level: "error", event: "witness_replay_failed", seed: raw, message: String(err) }));
        return json({ error: "replay failed" }, 500);
      }
    }
    return json({
      service: "sentinel-witness",
      what: "replays a Kestrel Yard encounter from its seed through the same rules module the renderers run, and certifies the transcript",
      usage: "GET /replay?seed=deadbeef",
      note: "no-input playouts only — the full input-log protocol is Circuit roadmap step 5 and lands in the rules core first",
    });
  },
};
