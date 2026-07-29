// Execute the claim: the edge must answer with the golden fingerprints,
// certify a locally-played match byte-for-byte, refuse tampered and
// unfinished records, and hold all of it under concurrent load (the
// serialization mutex is a claim too).
//
//   node witness_check.mjs [base-url]     (default http://localhost:8787)
import {
  S, bindIO, restart, endPlayerTurn, tryShoot, tryFinish, spare, tryMove,
  setOverwatch, solution, reachable, living, formatEvent,
} from "../../prototypes/tactical-core/rules.js";

const BASE = process.argv[2] ?? "http://localhost:8787";
const GOLDENS = [
  { seed: "deadbeef", lines: 42, fingerprint: "39e8be71", result: "loss" },
  { seed: "1", lines: 39, fingerprint: "bac5ad90", result: "loss" },
];

function fnv(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h.toString(16);
}

let failed = 0;
const check = (ok, label) => { console.log(`${ok ? "PASS" : "FAIL"} ${label}`); if (!ok) failed++; };
const get = async (seed) => (await fetch(`${BASE}/replay?seed=${seed}`)).json();
const post = async (payload) => {
  const res = await fetch(`${BASE}/certify`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { status: res.status, body: await res.json() };
};

// ---- goldens over GET /replay ----------------------------------
for (const g of GOLDENS) {
  const r = await get(g.seed);
  check(r.fingerprint === g.fingerprint && r.lines === g.lines && r.result === g.result,
    `replay seed=${g.seed} fp=${r.fingerprint} lines=${r.lines} result=${r.result} rating=${r.rating} purse=${r.purse}`);
}

// ---- play a match HERE, have the edge certify it ---------------
// The same deterministic auto-player the core tests use: any record a
// player produces locally, the edge must replay to the same bytes.
async function autoPlay(seed, resolve = "spare", maxTurns = 20) {
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: ev => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  restart(seed);
  const bestTarget = u => {
    let best = null;
    for (const t of living("ho").filter(t => !t.yielded)) {
      const sol = solution(u, t);
      if (sol && (!best || sol.pct > best.sol.pct)) best = { t, sol };
    }
    return best;
  };
  const stepToward = u => {
    const { cost } = reachable(u, u.mobility);
    const hos = living("ho").filter(t => !t.yielded);
    if (!hos.length) return null;
    let best = null;
    for (const k of cost.keys()) {
      const [x, y] = k.split(",").map(Number);
      if (x === u.x && y === u.y) continue;
      const d = Math.min(...hos.map(t => Math.hypot(t.x - x, t.y - y)));
      if (!best || d < best.d) best = { x, y, d };
    }
    return best;
  };
  for (let turn = 0; turn < maxTurns && !S.gameOver && !S.decision; turn++) {
    for (const u of living("op")) {
      while (u.ap > 0 && u.alive && !S.gameOver && !S.decision) {
        const shot = bestTarget(u);
        if (shot && shot.sol.pct >= 50) { await tryShoot(u, shot.t); break; }
        if (u.ap === 1) { setOverwatch(u); break; }
        const mv = stepToward(u);
        if (!mv) break;
        const ap = u.ap;
        await tryMove(u, mv.x, mv.y);
        if (u.ap === ap) break;
      }
      if (S.gameOver || S.decision) break;
    }
    if (S.gameOver || S.decision) break;
    await endPlayerTurn();
  }
  if (S.decision) {
    if (resolve === "finish") {
      const v = living("op")[0];
      for (const t of living("ho").filter(t => t.yielded)) {
        if (S.gameOver) break;
        await tryFinish(v, t);
      }
    }
    if (!S.gameOver) spare();
  }
  return {
    record: JSON.parse(JSON.stringify(S.record)),
    fingerprint: fnv(lines.join("\n")),
    lines: lines.length,
    rating: S.rating,
    result: S.gameOver,
  };
}

const local = await autoPlay(6, "spare");
check(local.result === "win", `local match played: seed=6 result=${local.result} cmds=${local.record.length} rating=${local.rating}`);

const cert = await post({ seed: "6", record: local.record });
check(cert.status === 200 && cert.body.certified === true &&
      cert.body.fingerprint === local.fingerprint &&
      cert.body.lines === local.lines &&
      cert.body.rating === local.rating &&
      cert.body.result === local.result,
  `certify: edge fp=${cert.body.fingerprint} vs local ${local.fingerprint}, rating ${cert.body.rating} vs ${local.rating}, purse=${cert.body.purse}`);

// ---- the rules stamp --------------------------------------------
// The version-as-behavior stamp is the golden fingerprint itself: the
// edge must be running rules that produce 39e8be71 for deadbeef, and a
// record claiming other rules must be refused before replay.
check(cert.body.rules === GOLDENS[0].fingerprint,
  `certificate carries the rules stamp: ${cert.body.rules}`);
const claimed = await post({ seed: "6", record: local.record, rules: GOLDENS[0].fingerprint });
check(claimed.status === 200 && claimed.body.certified === true,
  `record claiming the current rules certifies: ${claimed.status}`);
const misclaimed = await post({ seed: "6", record: local.record, rules: "00000000" });
check(misclaimed.status === 422 && misclaimed.body.error === "record claims a different rules version",
  `record claiming other rules refused: ${misclaimed.status} "${misclaimed.body.error}"`);

// ---- refusals ---------------------------------------------------
const bent = JSON.parse(JSON.stringify(local.record));
const mi = bent.findIndex(c => c[0] === "move");
bent[mi][2] = 6; bent[mi][3] = 1;   // a wall — no path ever reaches FULL cover
const tampered = await post({ seed: "6", record: bent });
check(tampered.status === 422 && tampered.body.certified === false &&
      tampered.body.error === "record does not replay",
  `tampered record refused: ${tampered.status} "${tampered.body.error}" applied=${tampered.body.applied}/${tampered.body.submitted}`);

const cut = await post({ seed: "6", record: local.record.slice(0, -1) });
check(cut.status === 422 && cut.body.error === "record replays but the match is unfinished",
  `truncated record refused: ${cut.status} "${cut.body.error}"`);

// 400 is for "you cannot even say that"; 422 stays reserved for records
// that speak the grammar and still fail to replay
for (const [label, record] of [
  ["unknown verb", [["warp", 0, 1]]],
  ["wrong arity", [["move", 0, 1]]],
  ["fractional coordinate", [["move", 0, 1.5, 2]]],
  ["non-array command", ["move"]],
]) {
  const r = await post({ seed: "6", record });
  check(r.status === 400, `malformed record (${label}) rejected at the wire: ${r.status}`);
}

// ---- concurrency: interleave replays and certifies --------------
// every response must still match its own expectation, or the mutex is fiction
const burst = await Promise.all(
  Array.from({ length: 8 }, (_, i) =>
    i % 2 === 0 ? get(GOLDENS[(i / 2) % 2].seed) : post({ seed: "6", record: local.record })),
);
burst.forEach((r, i) => {
  if (i % 2 === 0) {
    const g = GOLDENS[(i / 2) % 2];
    check(r.fingerprint === g.fingerprint && r.lines === g.lines, `burst[${i}] replay seed=${g.seed} fp=${r.fingerprint}`);
  } else {
    check(r.status === 200 && r.body.fingerprint === local.fingerprint, `burst[${i}] certify fp=${r.body.fingerprint}`);
  }
});

console.log(failed === 0 ? "ALL PASS" : `${failed} FAILURES`);
process.exit(failed === 0 ? 0 : 1);
