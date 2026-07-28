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
  mulberry32, MORALE, tryShoot, tryFinish, spare, setOverwatch, tryMove,
} from "./rules.js";

// FNV-1a, matching the fingerprint taken in the browser
function fnv(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h.toString(16);
}

// Play an encounter with no player input: every hostile turn resolves and
// the operatives never act, so the entire transcript is a pure function of
// the seed. Sleeps are collapsed to nothing — timing must not affect rolls.
async function playOut(seed, maxTurns = 14) {
  const lines = [];
  bindIO({
    sleep: () => Promise.resolve(),
    emit: ev => { const l = formatEvent(ev); if (l !== null) lines.push(l); },
    changed: () => {},
  });
  restart(seed);
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
    return cap.lines;
  }
  const a = await scriptedMatch();
  const b = await scriptedMatch();
  assert.deepEqual(a, b, "the input log plus the seed IS the match — it must replay");
  assert.equal(S.gameOver, "win");
  assert.ok(a.some(l => l.includes("finishes")));
  assert.ok(a.some(l => l.includes("spared")));
});
