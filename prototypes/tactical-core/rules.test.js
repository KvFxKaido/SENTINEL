/* Headless determinism tests for the tactical rules layer.
 *
 *   node --test prototypes/tactical-core/
 *
 * The golden hashes were captured from the browser build before the rules
 * were extracted, by pinning ?seed= and driving end-turn to a conclusion.
 * They are therefore a real regression guard, not a snapshot of whatever
 * this file happened to do on the day it was written: if a refactor
 * changes the order of a single random draw, these fail.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  S, bindIO, restart, endPlayerTurn, formatEvent,
  los, coverBonus, solution, reachable, living, unitAt, W, H,
  mulberry32, MORALE, RATING, tryShoot, tryFinish, spare, setOverwatch, tryMove,
  replayMatch, TWISTS, playTwist, twistWindow,
  rosterValid, rosterKey, CANON_ROSTER, ROSTER_SLOTS, OP_MAX_HP,
} from "./rules.js";
import { SHOWRUNNER_GOLDEN } from "./showrunner-golden.js";
import { ROSTER_GOLDEN } from "./roster-golden.js";
import { directorTick } from "./director.js";

// FNV-1a, matching the fingerprint taken in the browser
function fnv(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h.toString(16);
}

// Play an encounter with no player input: every hostile turn resolves and
// the operatives never act, so the entire transcript is a pure function of
// the seed. Sleeps are collapsed to nothing — timing must not affect rolls.
async function playOut(seed, maxTurns = 14, roster = null) {
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: ev => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  restart(seed, roster);
  for (let i = 0; i < maxTurns && !S.gameOver; i++) await endPlayerTurn();
  return lines;
}

test("seed deadbeef replays the captured browser transcript", async () => {
  const lines = await playOut(0xdeadbeef);
  assert.equal(lines.length, 42, "line count drifted:\n" + lines.join("\n"));
  assert.equal(fnv(lines.join("\n")), "39e8be71", "transcript drifted:\n" + lines.join("\n"));
  assert.equal(S.gameOver, "loss");
});

test("seed 1 replays the captured browser transcript", async () => {
  const lines = await playOut(1);
  assert.equal(lines.length, 39, "line count drifted:\n" + lines.join("\n"));
  assert.equal(fnv(lines.join("\n")), "bac5ad90", "transcript drifted:\n" + lines.join("\n"));
  assert.equal(S.gameOver, "loss");
});

test("same seed replays identically, twice in a row", async () => {
  const a = await playOut(0x5eed1e);
  const b = await playOut(0x5eed1e);
  assert.deepEqual(a, b);
});

test("different seeds diverge", async () => {
  const a = await playOut(7);
  const b = await playOut(8);
  assert.notDeepEqual(a, b);
});

test("sleep duration cannot influence the outcome", async () => {
  // If any roll ever depended on wall-clock time, this would drift.
  const fast = await playOut(0xc0ffee);
  const lines = [];
  bindIO({
    sleep: ms => new Promise(r => setTimeout(r, Math.min(ms, 3))),
    emit: ev => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  restart(0xc0ffee);
  for (let i = 0; i < 14 && !S.gameOver; i++) await endPlayerTurn();
  assert.deepEqual(lines, fast);
});

test("full cover blocks line of sight, half cover does not", () => {
  restart(1);
  // (6,1) and (6,2) are walls; (5,1) and (7,1) sit either side of one
  assert.equal(los(5, 1, 7, 1), false, "a wall between two tiles must block");
  assert.equal(los(0, 0, 9, 0), true, "an empty row must be clear");
});

test("cover is directional, not ambient", () => {
  restart(1);
  const def = { x: 3, y: 1 };           // crate sits at (2,1)
  const fromCoveredSide = coverBonus(def, { x: 0, y: 1 });
  const fromOpenSide    = coverBonus(def, { x: 6, y: 1 });
  assert.ok(fromCoveredSide > 0, "cover must apply against fire from the crate's side");
  assert.equal(fromOpenSide, 0, "the same crate must not protect against fire from behind");
});

test("firing solution stays inside its clamp and reports its own maths", () => {
  restart(1);
  const att = living("op")[0], def = living("ho")[0];
  for (const u of [att, def]) assert.ok(u);
  const sol = solution({ ...att, x: 4, y: 4 }, { ...def, x: 5, y: 4 });
  assert.ok(sol, "adjacent units in the open must have a solution");
  assert.ok(sol.pct >= 5 && sol.pct <= 95, "hit chance must stay clamped");
  assert.equal(sol.pct, Math.max(5, Math.min(95, sol.base + sol.range - sol.cover)));
});

test("movement never routes through cover or other units", () => {
  restart(1);
  const u = living("op")[0];
  const { cost } = reachable(u, u.mobility * u.ap);
  for (const k of cost.keys()) {
    const [x, y] = k.split(",").map(Number);
    assert.equal(S.map[y][x], 0, `reachable tile ${k} is not floor`);
    const occupant = unitAt(x, y);
    assert.ok(!occupant || occupant.id === u.id, `reachable tile ${k} is occupied`);
  }
});

test("the map is the size the renderer assumes", () => {
  restart(1);
  assert.equal(S.map.length, H);
  for (const row of S.map) assert.equal(row.length, W);
});

/* ---- yield states ----------------------------------------------
 * The golden transcripts above predate the morale mechanic and still pass
 * untouched: in a no-input playout the hostiles never take damage, morale
 * never moves, and nothing here draws from the RNG stream. The tests below
 * rig positions and morale directly, then land real shots — the one place
 * a seed matters is making the rigged shot connect, so seeds are chosen by
 * inspecting the first roll rather than by trial and error.
 */

// hit roll of a seed's first shot, computed without touching live state
const firstRoll = s => Math.floor(mulberry32(s)() * 100) + 1;
function seedHitting(pct) {
  for (let s = 1; s < 10000; s++) if (firstRoll(s) <= pct) return s;
  throw new Error("no seed found");
}

function captureEvents() {
  const events = [], lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: ev => { events.push(ev); const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  return { events, lines };
}

// Rig the board so one point-blank shot kills SYN-1 and morale-cascades the
// rest of the crew into yielding: VESPER at (1,0) has 83% on a 1 hp SYN-1
// at (2,0), and the squadmates are pre-drained to exactly the tipping point.
async function driveToDecision(cap) {
  restart(seedHitting(83));
  const v = living("op")[0];
  const [s1, s2, s3] = living("ho");
  v.x = 1; v.y = 0;
  s1.hp = 1;
  s2.morale = MORALE.mateDown;                     // the kill tips them
  s3.morale = MORALE.mateDown + MORALE.mateYield;  // ...and the cascade tips them
  await tryShoot(v, s1);
  return { v, s1, s2, s3 };
}

test("a kill drains the survivors; a survivable hit drains the defender", async () => {
  const { events } = captureEvents();
  restart(seedHitting(83));
  const v = living("op")[0];
  const [s1, s2, s3] = living("ho");
  v.x = 1; v.y = 0;
  s1.hp = 1;
  await tryShoot(v, s1);
  assert.equal(s1.alive, false);
  assert.equal(s2.morale, MORALE.start - MORALE.mateDown);
  assert.equal(s3.morale, MORALE.start - MORALE.mateDown);

  // survivable hit: same rig, enough hp to outlive even a crit
  restart(seedHitting(83));
  const v2 = living("op")[0];
  const t = living("ho")[0];
  v2.x = 1; v2.y = 0;
  t.hp = 20;
  const before = events.length;
  await tryShoot(v2, t);
  const shot = events.slice(before).find(e => e.type === "shot");
  assert.equal(shot.hit, true);
  assert.equal(t.morale, MORALE.start - (shot.crit ? MORALE.crit : MORALE.hit));
});

test("morale at zero is a yield, and yields cascade into the decision", async () => {
  const cap = captureEvents();
  const { s2, s3 } = await driveToDecision(cap);
  assert.equal(s2.yielded, true);
  assert.equal(s3.yielded, true);
  assert.equal(s2.ap, 0);
  assert.equal(s2.overwatch, false);
  assert.equal(S.decision, true);
  assert.equal(S.turn, "op");
  assert.equal(S.gameOver, null, "a yield is not an ending — the choice is");
  const seq = cap.events.map(e => e.type).filter(t => ["down", "yield", "yield-decision"].includes(t));
  assert.deepEqual(seq, ["down", "yield", "yield", "yield-decision"]);
});

test("spare ends the match as a win, on the record", async () => {
  const cap = captureEvents();
  const { s2, s3 } = await driveToDecision(cap);
  spare();
  assert.equal(S.gameOver, "win");
  const ev = cap.events.find(e => e.type === "spared");
  assert.deepEqual(ev.units, [s2, s3]);
  assert.ok(cap.lines.some(l => l.includes("spared — they walk.")));
});

test("a finish is a choice, not a roll — and the decision holds until resolved", async () => {
  const cap = captureEvents();
  const { v, s2, s3 } = await driveToDecision(cap);
  await tryFinish(v, s2);
  assert.equal(s2.alive, false);
  assert.equal(S.decision, true, "one fighter finished, one still kneeling — still your call");
  assert.equal(S.gameOver, null);
  await tryFinish(v, s3);
  assert.equal(S.gameOver, "win");
  assert.equal(cap.events.filter(e => e.type === "shot").length, 1, "executions never roll");
  assert.equal(cap.events.filter(e => e.type === "finish").length, 2);
});

test("a mid-fight finish is an activation: it needs the action and the sightline", async () => {
  captureEvents();
  restart(seedHitting(83));
  const [v, k] = living("op");
  const [s1, s2, s3] = living("ho");
  v.x = 1; v.y = 0;
  s1.hp = 20;
  s1.morale = MORALE.hit;   // any landed hit tips them
  await tryShoot(v, s1);
  assert.equal(s1.yielded, true);
  assert.equal(S.decision, false, "two fighters still standing");

  // wall at (6,1): KOA at (5,1) has no line to the kneeling SYN-1 at (7,1)
  s1.x = 7; s1.y = 1;
  k.x = 5; k.y = 1;
  await tryFinish(k, s1);
  assert.equal(s1.alive, true, "no sightline, no finish");
  k.x = 7; k.y = 2;
  k.ap = 0;
  await tryFinish(k, s1);
  assert.equal(s1.alive, true, "no action left, no finish");
  k.ap = 2;
  const m2 = s2.morale, m3 = s3.morale;
  await tryShoot(k, s1);   // shooting a yielded fighter reroutes to the finish
  assert.equal(s1.alive, false);
  assert.equal(k.ap, 0, "a mid-fight execution ends the activation");
  assert.equal(s2.morale, m2 - MORALE.mateDown, "the crew watched it happen");
  assert.equal(s3.morale, m3 - MORALE.mateDown);
});

test("yielded fighters sit out the hostile turn", async () => {
  captureEvents();
  restart(seedHitting(83));
  const v = living("op")[0];
  const s1 = living("ho")[0];
  v.x = 1; v.y = 0;
  s1.hp = 20;
  s1.morale = MORALE.hit;
  await tryShoot(v, s1);
  assert.equal(s1.yielded, true);
  const { x, y } = s1;
  const { events } = captureEvents();
  await endPlayerTurn();
  assert.equal(s1.x, x);
  assert.equal(s1.y, y);
  assert.equal(s1.ap, 0);
  assert.equal(s1.overwatch, false);
  assert.ok(!events.some(e => (e.att === s1) || (e.type === "overwatch-set" && e.unit === s1)),
    "a fighter with their hands up takes no actions");
});

test("during the decision, everything but the choice is inert", async () => {
  const cap = captureEvents();
  const { v } = await driveToDecision(cap);
  v.ap = 2;
  const before = cap.events.length;
  await endPlayerTurn();
  await tryMove(v, v.x + 1, v.y);
  setOverwatch(v);
  assert.equal(S.decision, true);
  assert.equal(S.turn, "op");
  assert.equal(v.x, 1, "no moving during the decision");
  assert.equal(v.overwatch, false);
  assert.ok(!cap.events.slice(before).some(e => e.type === "turn"), "the turn cycle is suspended");
});

test("finishing respects turn authority and the busy lock", async () => {
  captureEvents();
  restart(seedHitting(83));
  const v = living("op")[0];
  const s1 = living("ho")[0];
  v.x = 1; v.y = 0;
  s1.hp = 20;
  s1.morale = MORALE.hit;
  await tryShoot(v, s1);
  assert.equal(s1.yielded, true);
  v.ap = 2;   // a valid attacker in every respect — only the turn is wrong
  S.turn = "ho";
  await tryFinish(v, s1);
  assert.equal(s1.alive, true, "not the player's turn, not the player's verb");
  S.turn = "op";
  S.busy = true;
  await tryFinish(v, s1);
  assert.equal(s1.alive, true, "another action is mid-flight — the verb must refuse");
  S.busy = false;
  await tryFinish(v, s1);
  assert.equal(s1.alive, false);
});

test("a restart mid-finish releases cleanly and cannot touch the new encounter", async () => {
  const cap = captureEvents();
  const { v, s2 } = await driveToDecision(cap);
  // hold the finish animation open, restart underneath it, then let it resolve
  let release;
  bindIO({
    sleep: () => new Promise(r => { release = r; }),
    emit: () => {},
    changed: () => {},
  });
  const pending = tryFinish(v, s2);
  assert.equal(S.busy, true);
  restart(41);
  release();
  await pending;
  assert.equal(S.busy, false, "the restarted encounter must not inherit a stale lock");
  assert.equal(S.gameOver, null);
  assert.equal(S.decision, false);
  const fresh = living("ho");
  assert.equal(fresh.length, 3, "the stale finish must not kill into the new encounter");
  assert.ok(fresh.every(u => u.alive && !u.yielded));
});

test("a match with yields, a finish, and a spare replays identically", async () => {
  async function scriptedMatch() {
    const cap = captureEvents();
    const { v, s2 } = await driveToDecision(cap);
    await tryFinish(v, s2);
    spare();
    return { lines: cap.lines, rating: S.rating };
  }
  const a = await scriptedMatch();
  const b = await scriptedMatch();
  assert.deepEqual(a.lines, b.lines, "the input log plus the seed IS the match — it must replay");
  assert.equal(a.rating, b.rating, "the crowd is part of the record too");
  assert.equal(S.gameOver, "win");
  assert.ok(a.lines.some(l => l.includes("finishes")));
  assert.ok(a.lines.some(l => l.includes("spared")));
});

/* ---- rating ----------------------------------------------------
 * Same discipline as morale, one step further: rating is arithmetic on
 * events that already happen, draws nothing from the RNG, and never
 * writes a log line — which is why the golden transcripts above pass
 * untouched while the meter moves underneath them.
 */

test("rating never becomes a log line", () => {
  assert.equal(formatEvent({ type: "rating", delta: 5, total: 55 }), null);
});

test("landed player fire is scored, itemized for flash", async () => {
  const { events } = captureEvents();
  restart(seedHitting(83));
  const v = living("op")[0];
  const s1 = living("ho")[0];
  v.x = 1; v.y = 0;
  s1.hp = 20;
  const before = S.rating;
  await tryShoot(v, s1);
  const shot = events.find(e => e.type === "shot");
  assert.equal(shot.hit, true);
  // adjacent shot: no long-shot bonus; target flanked (+), shooter in the
  // open (+), crit if the dice said so
  assert.equal(S.rating,
    before + RATING.hit + RATING.flank + RATING.open + (shot.crit ? RATING.crit : 0));
});

test("a down pays the crowd, whoever fell", async () => {
  const { events } = captureEvents();
  restart(seedHitting(83));
  const v = living("op")[0];
  const s1 = living("ho")[0];
  v.x = 1; v.y = 0;
  s1.hp = 1;
  await tryShoot(v, s1);
  assert.equal(s1.alive, false);
  const deltas = events.filter(e => e.type === "rating").map(e => e.delta);
  assert.ok(deltas.includes(RATING.down), "blood is content");
});

test("the turtle bleeds: player overwatch and stalled AP", async () => {
  const { events } = captureEvents();
  restart(1);
  const v = living("op")[0];
  const before = S.rating;
  setOverwatch(v);
  assert.equal(S.rating, before + RATING.overwatch);
  await endPlayerTurn();   // the two untouched operatives stall 4 AP
  const deltas = events.filter(e => e.type === "rating").map(e => e.delta);
  assert.ok(deltas.includes(RATING.stalledAp * 4), "dead air must bleed the meter");
});

test("in an untouched playout the only crowd-pleaser is blood", async () => {
  const { events } = captureEvents();
  restart(1);
  for (let i = 0; i < 14 && !S.gameOver; i++) await endPlayerTurn();
  const ups = events.filter(e => e.type === "rating" && e.delta > 0);
  assert.ok(ups.length > 0, "operatives went down — those pay");
  assert.ok(ups.every(e => e.delta === RATING.down),
    "nothing the AI does builds the player's meter");
  assert.ok(S.rating < RATING.start, "a squad that never fights bleeds out on air");
});

test("yield economy pays out at the end, clamped at the ceiling", async () => {
  const cap = captureEvents();
  const { v, s2 } = await driveToDecision(cap);
  const yieldUps = cap.events.filter(e => e.type === "rating" && e.delta === RATING.yield);
  assert.equal(yieldUps.length, 2, "each fighter breaking on camera pays");
  S.rating = 98;             // stage the ceiling
  await tryFinish(v, s2);
  assert.equal(S.rating, 100, "the meter is clamped, not unbounded");
  spare();
  assert.equal(S.rating, 100 + RATING.spare, "mercy costs purse, applied before payout");
  const end = cap.events.find(e => e.type === "end");
  assert.equal(end.rating, S.rating);
  assert.equal(end.purse, S.rating * RATING.pursePerPoint);
});

test("rating events report the applied delta, never the requested one", async () => {
  const cap = captureEvents();
  const { v, s2 } = await driveToDecision(cap);
  S.rating = 98;
  const before = cap.events.length;
  await tryFinish(v, s2);
  const ev = cap.events.slice(before).find(e => e.type === "rating");
  assert.equal(ev.delta, 2, "the ceiling ate half the finish — the event must say so");
  assert.equal(ev.total, 100);

  const cap2 = captureEvents();
  restart(1);
  S.rating = 0;
  setOverwatch(living("op")[0]);
  assert.ok(!cap2.events.some(e => e.type === "rating"),
    "a change the clamp fully ate is not an event");
  assert.equal(S.rating, 0);
});

test("the floor is zero, and restart resets the meter", async () => {
  captureEvents();
  restart(1);
  S.rating = 1;
  setOverwatch(living("op")[0]);
  assert.equal(S.rating, 0, "the meter is clamped at the floor");
  restart(2);
  assert.equal(S.rating, RATING.start);
});

/* ---- the witness record ----------------------------------------
 * Circuit roadmap step 5: seed + record IS the match. These tests play
 * organic matches from spawn through the public verbs only — no state
 * rigging — because a record can only replay what the seed can rebuild.
 * The auto-player is deterministic: it reads game state, draws nothing.
 */

// shoot when confident, overwatch on a spare action, otherwise close
// distance; at the decision, resolve by choice. Public verbs only.
async function autoPlay(seed, resolve = "spare", maxTurns = 20, director = false) {
  const cap = captureEvents();
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
    if (director) directorTick();   // the house speaks at the bell, if it speaks
    for (const u of living("op")) {
      while (u.ap > 0 && u.alive && !S.gameOver && !S.decision) {
        const shot = bestTarget(u);
        if (shot && shot.sol.pct >= 50) { await tryShoot(u, shot.t); break; }
        if (u.ap === 1) { setOverwatch(u); break; }
        const mv = stepToward(u);
        if (!mv) break;
        const ap = u.ap;
        await tryMove(u, mv.x, mv.y);
        if (u.ap === ap) break;   // move refused — don't spin
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
  return { lines: cap.lines, rating: S.rating, over: S.gameOver };
}

test("a played match records itself, and seed + record replays it byte-identically", async () => {
  const live = await autoPlay(6, "spare");
  assert.equal(live.over, "win");
  // the record survives the wire: what replays is parsed JSON, not live refs
  const record = JSON.parse(JSON.stringify(S.record));
  const verbs = new Set(record.map(c => c[0]));
  for (const v of ["move", "shoot", "ow", "end", "spare"]) {
    assert.ok(verbs.has(v), `an organic match should exercise "${v}"`);
  }
  const cap = captureEvents();
  const cert = await replayMatch(6, record);
  assert.equal(cert.faithful, true, "a faithful replay reproduces its own input");
  assert.equal(cert.applied, record.length);
  assert.deepEqual(cap.lines, live.lines, "the transcript is the record's shadow");
  assert.equal(S.rating, live.rating, "the crowd replays too");
  assert.equal(S.gameOver, "win");
});

test("a finish resolves on the record and replays like any other verb", async () => {
  const live = await autoPlay(7, "finish");
  assert.equal(live.over, "win");
  const record = JSON.parse(JSON.stringify(S.record));
  assert.equal(record.at(-1)[0], "finish", "the last committed command is the execution");
  const cap = captureEvents();
  const cert = await replayMatch(7, record);
  assert.equal(cert.faithful, true);
  assert.deepEqual(cap.lines, live.lines);
  assert.ok(cap.lines.some(l => l.includes("finishes")));
});

test("the golden playout is a record of pure end-turns", async () => {
  await playOut(0xdeadbeef);
  const record = JSON.parse(JSON.stringify(S.record));
  assert.ok(record.length > 0);
  assert.ok(record.every(c => c.length === 1 && c[0] === "end"),
    "no player input means no command but the clock");
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: ev => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  const cert = await replayMatch(0xdeadbeef, record);
  assert.equal(cert.faithful, true);
  assert.equal(lines.length, 42);
  assert.equal(fnv(lines.join("\n")), "39e8be71",
    "the seed-only replay the Worker serves today is just this record");
});

test("rejected inputs never enter the record", async () => {
  captureEvents();
  restart(1);
  const v = living("op")[0];
  await tryMove(v, v.x, v.y);          // zero-cost non-move
  await tryMove(v, 9, 0);              // far beyond one turn's mobility
  v.ap = 0;
  setOverwatch(v);                     // no action left
  const s1 = living("ho")[0];
  await tryShoot(v, s1);               // no AP either
  assert.deepEqual(S.record, [], "only committed commands are play");
});

test("shooting a kneeling fighter records the finish, not the click", async () => {
  captureEvents();
  restart(seedHitting(83));
  const v = living("op")[0];
  const s1 = living("ho")[0];
  v.x = 1; v.y = 0;
  s1.hp = 20;
  s1.morale = MORALE.hit;
  await tryShoot(v, s1);
  assert.equal(s1.yielded, true);
  v.ap = 2;
  await tryShoot(v, s1);   // the renderer's shoot gesture, rerouted
  assert.equal(S.record.at(-1)[0], "finish",
    "the record captures what happened, not what was clicked");
});

test("a tampered record does not certify", async () => {
  await autoPlay(6, "spare");
  const record = JSON.parse(JSON.stringify(S.record));
  // (a) rewrite a move onto a wall — no path ever reaches FULL cover
  const bent = JSON.parse(JSON.stringify(record));
  const mi = bent.findIndex(c => c[0] === "move");
  bent[mi][2] = 6; bent[mi][3] = 1;
  const a = await replayMatch(6, bent);
  assert.equal(a.faithful, false, "a command the rules refuse cannot reproduce itself");
  // (b) commands past the ending are not play
  const padded = [...record, ["end"]];
  const b = await replayMatch(6, padded);
  assert.equal(b.faithful, false);
  // (c) grammar the renderers cannot produce is refused, not crashed on:
  // moving a hostile, friendly fire, garbage verbs, non-commands
  const c = await replayMatch(6, [["move", 3, 1, 1], ["shoot", 0, 1], ["warp", 0], null]);
  assert.equal(c.faithful, false);
  assert.equal(c.applied, 0);
});

test("a truncated record replays faithfully but is not a finished match", async () => {
  await autoPlay(6, "spare");
  const record = JSON.parse(JSON.stringify(S.record)).slice(0, -1);   // drop the spare
  const cert = await replayMatch(6, record);
  assert.equal(cert.faithful, true, "a partial record is honest play, just not all of it");
  assert.equal(S.gameOver, null, "fidelity is not completeness — certification needs both");
});

test("restart clears the record", async () => {
  captureEvents();
  restart(1);
  await endPlayerTurn();
  assert.ok(S.record.length > 0);
  restart(2);
  assert.deepEqual(S.record, []);
});

/* ---- showrunner twists (Circuit step 4) --------------------------
 * The house is a second actor with one verb: ["twist", cardId] is a
 * recorded input, validated and resolved by the core, chosen outside
 * it. The goldens at the top of this file prove the no-twist path is
 * untouched; these prove the card is announced before it lands, fails
 * closed outside its window, and certifies like any other play.
 */

test("a twist announces on the feed and goes live at the top of the next round", async () => {
  const cap = captureEvents();
  restart(1);
  assert.equal(twistWindow(), true, "match start is a between-rounds window");
  playTwist(1);
  assert.deepEqual(S.record, [["twist", 1]]);
  assert.equal(S.pendingTwist, 1);
  assert.equal(S.activeTwist, null, "announced is not live");
  assert.ok(cap.lines.some(l => l.includes("THE HOUSE PLAYS: MERCY ODDS")));
  assert.ok(!cap.lines.some(l => l.includes("IS LIVE")));
  await endPlayerTurn();
  assert.equal(S.activeTwist, 1, "live at the top of the next round");
  assert.equal(S.pendingTwist, null);
  const turnIdx = cap.lines.lastIndexOf("— OPERATIVE TURN —");
  assert.equal(cap.lines[turnIdx + 1], "— MERCY ODDS IS LIVE — A SPARE PAYS +6 —",
    "the resolution line lands right as the round opens");
});

test("MERCY ODDS replaces the spare payout — the number on the feed is the number paid", async () => {
  assert.ok(TWISTS[1].terms.includes(`+${TWISTS[1].spareRating}`),
    "the terms line must print the real number — legible corruption or none");
  const cap = captureEvents();
  restart(seedHitting(83));
  playTwist(1);   // played before the fight settles; resolves at the decision
  const v = living("op")[0];
  const [s1, s2, s3] = living("ho");
  v.x = 1; v.y = 0;
  s1.hp = 1;
  s2.morale = MORALE.mateDown;
  s3.morale = MORALE.mateDown + MORALE.mateYield;
  await tryShoot(v, s1);
  assert.equal(S.decision, true);
  assert.equal(S.activeTwist, 1, "the fight settled first — the card goes live as the choice opens");
  const di = cap.lines.findIndex(l => l.includes("THE FIGHT IS OVER"));
  assert.ok(cap.lines[di + 1].includes("MERCY ODDS IS LIVE"),
    "the house speaks right before the player chooses");
  S.rating = 50;   // stage clear of both clamps
  spare();
  assert.equal(S.rating, 50 + TWISTS[1].spareRating, "the card replaces RATING.spare, not adds to it");
});

test("the twist window fails closed: mid-round, wrong turn, unknown cards, the budget, the decision", async () => {
  captureEvents();
  restart(1);
  const v = living("op")[0];
  await tryMove(v, v.x, v.y - 1);   // any spent AP closes the window
  assert.equal(twistWindow(), false);
  playTwist(1);
  assert.ok(!S.record.some(c => c[0] === "twist"), "the house cannot speak mid-round");

  restart(1);
  S.turn = "ho";
  playTwist(1);
  assert.deepEqual(S.record, [], "not the player's turn, not a between-rounds window");
  S.turn = "op";

  playTwist(99);
  assert.deepEqual(S.record, [], "a card that does not exist cannot be played");

  // the budget: one card per match, enforced by the rules, not etiquette
  playTwist(1);
  assert.equal(S.record.length, 1);
  await endPlayerTurn();
  assert.equal(twistWindow(), true, "a fresh round reopens the window");
  playTwist(1);
  assert.equal(S.record.filter(c => c[0] === "twist").length, 1, "the house has played its card");

  // the decision: the card must precede the choice, never interrupt it
  const cap = captureEvents();
  await driveToDecision(cap);
  playTwist(1);
  assert.ok(!S.record.some(c => c[0] === "twist"),
    "no cards into the decision — pricing it required announcing a round earlier");
});

test("a mover who dies to overwatch cannot reopen the twist window (caught in review)", async () => {
  // The corner: the first operative to act dies to a reaction shot, and
  // their spent AP leaves living("op") with them — every survivor still
  // reads 2 AP. A window inferred from the roster's AP would reopen
  // mid-round; the explicit S.roundActed flag must not.
  captureEvents();
  restart(seedHitting(34));   // 65 aim +4 range −20 cover −15 reaction = 34
  const v = living("op")[0];
  const s1 = living("ho")[0];
  s1.x = 1; s1.y = 6;         // clear line down column 1 — the crate at (1,7) is half cover, not a wall
  s1.overwatch = true;
  v.hp = 1;                   // any landed reaction shot kills
  await tryMove(v, 1, 8);     // one step into the watched lane
  assert.equal(v.alive, false, "the rig must actually kill the mover");
  assert.ok(living("op").every(u => u.ap === 2),
    "the survivors' AP is exactly the inference that would have lied here");
  assert.equal(twistWindow(), false, "an action happened this round — the window stays shut");
  playTwist(1);
  assert.ok(!S.record.some(c => c[0] === "twist"),
    "the house cannot slip a card in behind a dead mover");
  await endPlayerTurn();
  if (!S.gameOver && !S.decision) {
    assert.equal(twistWindow(), true, "the next round reopens the window honestly");
  }
});

test("a record with an illegally-timed twist does not certify", async () => {
  await autoPlay(6, "spare");
  const organic = JSON.parse(JSON.stringify(S.record));
  // (a) mid-round: right after the first move, the mover has spent AP
  const mi = organic.findIndex(c => c[0] === "move");
  const bent = [...organic.slice(0, mi + 1), ["twist", 1], ...organic.slice(mi + 1)];
  const a = await replayMatch(6, bent);
  assert.equal(a.faithful, false, "a card played mid-round cannot reproduce itself");
  // (b) over budget
  const b = await replayMatch(6, [["twist", 1], ["twist", 1], ...organic]);
  assert.equal(b.faithful, false);
  // (c) a card that does not exist
  const c = await replayMatch(6, [["twist", 7], ...organic]);
  assert.equal(c.faithful, false);
});

test("the director is deterministic, plays at the bell, and its choice certifies", async () => {
  // quiet house: full morale at match start, no card
  captureEvents();
  restart(1);
  assert.equal(directorTick(), null, "nobody is near breaking — the house holds its card");
  assert.deepEqual(S.record, []);

  // a directed match: the director reads the board at each round top and
  // plays MERCY ODDS when a fighter is one bad beat from kneeling
  const a = await autoPlay(6, "spare", 20, true);
  const recA = JSON.parse(JSON.stringify(S.record));
  const ti = recA.findIndex(c => c[0] === "twist");
  assert.ok(ti > 0, "the card is a reaction to the fight, not weather at the deal");
  assert.equal(recA[ti - 1][0], "end", "the house speaks only at a round boundary");
  assert.deepEqual(recA[ti], ["twist", 1]);

  // deterministic: same seed, same fight, same call at the same moment
  const b = await autoPlay(6, "spare", 20, true);
  assert.deepEqual(JSON.parse(JSON.stringify(S.record)), recA);
  assert.deepEqual(b.lines, a.lines);

  // and the witness protocol certifies the director's choice without
  // knowing the director exists — it is just another hand on the record
  const cap = captureEvents();
  const cert = await replayMatch(6, recA);
  assert.equal(cert.faithful, true);
  assert.deepEqual(cap.lines, a.lines);
});

test("the showrunner golden replays to its captured fingerprint", async () => {
  const { seed, record, result, rating, purse, lines: lineCount, fingerprint } = SHOWRUNNER_GOLDEN;
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: ev => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  const cert = await replayMatch(seed, record);
  assert.equal(cert.faithful, true, "the twist splices into the organic record without disturbing it");
  assert.equal(S.gameOver, result);
  assert.equal(S.rating, rating, "the spare paid the card's number, not RATING.spare");
  assert.equal(S.rating * RATING.pursePerPoint, purse,
    "the pinned purse is a stamp input — it must be what the replay actually pays");
  assert.equal(lines.length, lineCount);
  assert.equal(fnv(lines.join("\n")), fingerprint,
    "the stamp's second golden: any change to twist behavior must move this");
  // and the same match without the card: identical fight, RATING.spare payout
  const bare = record.filter(c => c[0] !== "twist");
  await replayMatch(seed, bare);
  assert.equal(S.rating, rating - TWISTS[1].spareRating + RATING.spare,
    "card off, same fight — only the spare payout moves");
});

/* ---- the roster: the match's second certified input ---------------
 * `architecture/roster_in_the_match.md`. The old law was
 * `seed + record = the match`; the new one is
 * `seed + roster + record = the match`, and everything below is that
 * sentence made executable. The two goldens at the top of this file are
 * the other half of the proof: they field no roster at all and did not
 * move, so the input is genuinely additive.
 */

test("no roster fields the canonical three, exactly as before", async () => {
  await playOut(0xdeadbeef, 1);
  assert.deepEqual(
    S.units.filter(u => u.side === "op").map(u => ({ name: u.name, hp: u.hp })),
    CANON_ROSTER.map(f => ({ name: f.name, hp: f.hp })));
  assert.deepEqual(S.roster, CANON_ROSTER.map(f => ({ name: f.name, hp: f.hp })),
    "the state reports what was fielded, so a certificate need not take the caller's word");
});

test("passing the canonical roster is the same match as passing none", async () => {
  const bare = await playOut(0xdeadbeef);
  const named = await playOut(0xdeadbeef, 14, CANON_ROSTER.map(f => ({ ...f })));
  assert.deepEqual(named, bare, "saying the default out loud cannot change the match");
});

test("the roster golden: same seed, same input, different squad, different match", async () => {
  // The doctrine in one assertion. Nothing about the seed or the record
  // changed; the squad did, and the match is not the same match.
  const { seed, roster, result, rating, purse, lines: lineCount, fingerprint } = ROSTER_GOLDEN;
  const lines = await playOut(seed, 14, roster);
  assert.equal(lines.length, lineCount, "line count drifted:\n" + lines.join("\n"));
  assert.equal(fnv(lines.join("\n")), fingerprint,
    "the stamp's third golden: any change to roster behavior must move this");
  assert.equal(S.gameOver, result);
  assert.equal(S.rating, rating);
  assert.equal(S.rating * RATING.pursePerPoint, purse);
  assert.equal(rosterKey(roster), ROSTER_GOLDEN.key);

  const canonical = await playOut(seed);
  assert.notEqual(fnv(canonical.join("\n")), fingerprint,
    "if these ever agree, the roster is not an input and the doctrine is a lie");
  assert.equal(fnv(canonical.join("\n")), "39e8be71", "...and its twin is the untouched golden");
});

test("a substituted name rides the record", async () => {
  // Lineup is rules-level — this is precisely why season-lite could not
  // bench anyone without breaking the certificate.
  const lines = await playOut(0xdeadbeef, 14,
    [{ name: "NIX", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }]);
  assert.ok(lines.some(l => /NIX/.test(l)), "the fielded name reaches the transcript");
  assert.ok(!lines.some(l => /VESPER/.test(l)), "and the benched one does not");
});

test("a carried wound is hp, not a smaller fighter", async () => {
  await playOut(0xdeadbeef, 1, [{ name: "VESPER", hp: 4 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }]);
  const vesper = S.units.find(u => u.name === "VESPER");
  assert.equal(vesper.hp, 4);
  assert.equal(vesper.maxHp, OP_MAX_HP, "four OF ten — the distinction a wound heals across");
});

test("a roster that is not a roster is refused, never defaulted", async () => {
  // Falling back to the canonical three would field a squad the caller
  // never asked for and then certify the result.
  const bad = [
    [],
    [{ name: "VESPER", hp: 10 }],
    [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }, { name: "NIX", hp: 10 }],
    [{ name: "VESPER", hp: 0 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ name: "VESPER", hp: 11 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ name: "VESPER", hp: 1.5 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ name: "vesper", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ name: "", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ name: "KOA", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ name: "SYN-1", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    [{ hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
    "VESPER:10|KOA:10|SABLE:10",
    {},
  ];
  for (const roster of bad) {
    assert.equal(rosterValid(roster), false, JSON.stringify(roster));
    assert.throws(() => restart(1, roster), /not a roster/, JSON.stringify(roster));
  }
  assert.equal(rosterValid(CANON_ROSTER), true);
  assert.equal(ROSTER_SLOTS, 3);
});

test("a duplicated or hostile name is refused because the record must name one fighter", async () => {
  // The transcript is what gets certified. Two fighters answering to one
  // name makes a line that cannot say who did what.
  assert.equal(rosterValid([{ name: "SYN-2", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }]), false);
  assert.equal(rosterValid([{ name: "NIX", hp: 10 }, { name: "NIX", hp: 9 }, { name: "SABLE", hp: 10 }]), false);
});

test("rosterKey is one canonical form, and hp is part of it", () => {
  assert.equal(rosterKey(null), "VESPER:10|KOA:10|SABLE:10", "no roster keys as the canonical three");
  assert.equal(rosterKey(CANON_ROSTER), rosterKey(null));
  assert.notEqual(
    rosterKey([{ name: "VESPER", hp: 9 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }]),
    rosterKey(null),
    "a wound changes the key — otherwise the address could not individuate by it");
  assert.notEqual(
    rosterKey([{ name: "KOA", hp: 10 }, { name: "VESPER", hp: 10 }, { name: "SABLE", hp: 10 }]),
    rosterKey(null),
    "and so does the slot they stand in");
});

test("replayMatch takes the roster it was fought under", async () => {
  // The Worker's whole job: the record replays under the roster it was
  // played with, and under any other roster it is a different match.
  const roster = ROSTER_GOLDEN.roster.map(f => ({ ...f }));
  const record = [["move", 0, 2, 6], ["shoot", 0, 4], ["end"]];
  const played = await replayMatch(ROSTER_GOLDEN.seed, record, roster);
  assert.equal(played.faithful, true);
  assert.deepEqual(S.roster, roster);
  const names = S.units.filter(u => u.side === "op").map(u => u.name);
  assert.deepEqual(names, ["VESPER", "NIX", "SABLE"]);
});
