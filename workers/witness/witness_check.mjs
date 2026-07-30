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

// ---- the archive: file, refile, list, fetch back -----------------
// filing is certify + store under a content-addressed id (sha-256 of
// {rules, seed, record}), so a match files exactly once, keeps its
// original timestamp forever, and can never overwrite a different match
const postTo = async (path, payload) => {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { status: res.status, body: await res.json() };
};
const getJson = async (path) => {
  const res = await fetch(`${BASE}${path}`);
  return { status: res.status, body: await res.json() };
};

check(cert.body.ledger && cert.body.ledger.walked >= 1 && cert.body.ledger.finished === 0,
  `certificate carries the ledger: ${JSON.stringify(cert.body.ledger)}`);

// the fingerprint claim: "this is the match I watched"
const claimedOk = await postTo("/certify", { seed: "6", record: local.record, fingerprint: local.fingerprint });
check(claimedOk.status === 200, `record claiming its own fingerprint certifies: ${claimedOk.status}`);
const claimedBad = await postTo("/certify", { seed: "6", record: local.record, fingerprint: "abcdef1" });
check(claimedBad.status === 422 && claimedBad.body.error === "record replays to a different match than claimed",
  `record claiming a different fingerprint refused: ${claimedBad.status} "${claimedBad.body.error}"`);

const filed = await postTo("/file", { seed: "6", record: local.record, fingerprint: local.fingerprint });
check(filed.status === 200 && filed.body.filed === true &&
      filed.body.fingerprint === local.fingerprint &&
      /^[0-9a-f]{32}$/.test(filed.body.id ?? ""),
  `match filed under content-addressed id: ${filed.body.id}`);

const countAfterFirst = (await getJson("/matches")).body.count;
const refiled = await postTo("/file", { seed: "6", record: local.record });
const countAfterSecond = (await getJson("/matches")).body.count;
check(refiled.body.id === filed.body.id && refiled.body.existing === true &&
      refiled.body.filed_at === filed.body.filed_at &&
      countAfterSecond === countAfterFirst,
  `refiling is state-idempotent: same id, original filed_at kept, count stays ${countAfterSecond}`);

const listing = (await getJson("/matches")).body;
const mine = listing.matches.find(m => m.id === filed.body.id);
check(!!mine && mine.rating === local.rating && mine.result === local.result,
  `archive lists the match with its metadata: rating=${mine?.rating} result=${mine?.result}`);

const fetched = (await getJson(`/matches/${filed.body.id}`)).body;
check(JSON.stringify(fetched.record) === JSON.stringify(local.record) &&
      fetched.certificate?.fingerprint === local.fingerprint,
  `filed match fetches back in full: ${fetched.record?.length} commands + certificate`);

const tamperedFile = await postTo("/file", { seed: "6", record: bent });
check(tamperedFile.status === 422 && tamperedFile.body.filed === false,
  `tampered record cannot be filed: ${tamperedFile.status}`);

const missing = await getJson("/matches/00000000000000000000000000000000");
check(missing.status === 404 && missing.body.error === "no such match on file",
  `missing match 404s: ${missing.status} "${missing.body.error}"`);

// ---- pagination past the first KV page (local worker only) -------
// bulk-files >100 pure-end matches so /matches must walk cursors to
// stay complete. Skipped against the live archive: it would flood the
// real ledger with synthetic losses. CI runs this against localhost.
if (BASE.startsWith("http://localhost") || BASE.startsWith("http://127.")) {
  // each seed's pure-end record is generated through the core — a fixed
  // 14-end record would be UNFAITHFUL for any seed that finishes early
  // (commands past the ending are not play)
  bindIO({ sleep: () => Promise.resolve(), emit: () => {}, changed: () => {} });
  const pureEnd = async (seedHex) => {
    restart(parseInt(seedHex, 16));
    for (let i = 0; i < 14 && !S.gameOver; i++) await endPlayerTurn();
    return S.gameOver ? JSON.parse(JSON.stringify(S.record)) : null;   // unfinished seeds don't file
  };
  const bulkIds = [];
  let seedN = 0x100;
  while (bulkIds.length < 110 && seedN < 0x100 + 400) {
    const batch = [];
    while (batch.length < 10 && bulkIds.length + batch.length < 110 && seedN < 0x100 + 400) {
      const s = (seedN++).toString(16);
      const rec = await pureEnd(s);
      if (rec) batch.push({ seed: s, record: rec });
    }
    const results = await Promise.all(batch.map(b => postTo("/file", b)));
    for (const r of results) if (r.status === 200) bulkIds.push(r.body.id);
  }
  const bulk = (await getJson("/matches")).body;
  const present = bulkIds.filter(id => bulk.matches.some(m => m.id === id)).length;
  const sorted = bulk.matches.every((m, i) => i === 0 || (bulk.matches[i - 1].at ?? "") >= (m.at ?? ""));
  check(bulkIds.length >= 110, `bulk-filed ${bulkIds.length} matches for the pagination test`);
  check(bulk.count === bulk.matches.length && present === bulkIds.length,
    `archive lists past the first KV page: ${bulk.count} entries, all ${bulkIds.length} bulk ids present`);
  check(sorted, "archive is globally newest-first, not per-page");
} else {
  console.log("SKIP pagination bulk test — live archive; CI covers it against a local worker");
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
