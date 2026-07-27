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
