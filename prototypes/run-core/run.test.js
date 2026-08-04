/* Headless tests for the run layer.
 *
 *   node --test prototypes/run-core/
 *
 * The run layer has no golden transcripts to guard, because it is not in
 * the determinism chain — that is the whole point of it being a third
 * module. What it does have is a policy (what counts, what does not, and
 * what gets said about it) and a store it does not own. Both are tested
 * here, including the failure modes: storage that lies, storage that
 * refuses, and cards that arrive malformed.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  RUN_V, RUN_KEY, CLOSED_KEY, ORPHAN_KEY,
  bindStore, openRun, applyCard, cardValid, loadRun, saveRun, closeRun,
  readClosed, summary,
} from "./run.js";

const AT = "2026-08-04T12:00:00.000Z";

// A store that is a plain object, so a test can look at exactly what was
// written rather than at what the module says it wrote.
function memoryStore(seed = {}) {
  const box = { ...seed };
  bindStore({
    read: k => (k in box ? box[k] : null),
    write: (k, v) => { box[k] = v; },
    remove: k => { delete box[k]; },
  });
  return box;
}

// A certified win, three hostiles yielded and walked, nobody of ours lost.
function card(over = {}) {
  return {
    seed: "deadbeef",
    result: "win",
    rating: 62,
    purse: 620,
    cert: "certified",
    ledger: { walked: 3, finished: 0, lost: 0 },
    down: [],
    rules: "abc123",
    at: AT,
    ...over,
  };
}

// ---- shape ---------------------------------------------------------

test("a fresh run is empty, versioned, and stamped with when it opened", () => {
  const r = openRun(AT);
  assert.equal(r.v, RUN_V);
  assert.equal(r.opened, AT);
  assert.equal(r.cards, 0);
  assert.equal(r.purse, 0);
  assert.equal(r.rules, null);
  assert.deepEqual(r.wounds, {});
  assert.deepEqual(r.recent, []);
});

// ---- the reducer ---------------------------------------------------

test("applying a card never mutates the run it was given", () => {
  const before = openRun(AT);
  const snapshot = JSON.stringify(before);
  const { run: after } = applyCard(before, card({ down: ["VESPER"], ledger: { walked: 3, finished: 0, lost: 1 } }));
  assert.equal(JSON.stringify(before), snapshot, "the input run was modified in place");
  assert.notEqual(after, before);
  assert.equal(after.cards, 1);
});

test("a certified win banks the purse and opens a streak", () => {
  const { run, counted } = applyCard(openRun(AT), card());
  assert.equal(counted, true);
  assert.equal(run.cards, 1);
  assert.equal(run.wins, 1);
  assert.equal(run.purse, 620);
  assert.equal(run.best, 62);
  assert.equal(run.streak, 1);
  assert.equal(run.longest, 1);
  assert.equal(run.unwitnessed, 0);
  assert.equal(run.struck, 0);
});

test("a loss banks the purse too — a watchable loss still sells", () => {
  const { run } = applyCard(openRun(AT), card({ result: "loss", rating: 71, purse: 710 }));
  assert.equal(run.cards, 1);
  assert.equal(run.wins, 0);
  assert.equal(run.purse, 710, "rating pays out whether you won or not");
  assert.equal(run.best, 71);
  assert.equal(run.streak, 0);
});

test("a loss breaks the streak but not the longest", () => {
  let run = openRun(AT);
  for (let i = 0; i < 3; i++) run = applyCard(run, card()).run;
  assert.equal(run.streak, 3);
  run = applyCard(run, card({ result: "loss" })).run;
  assert.equal(run.streak, 0);
  assert.equal(run.longest, 3);
  run = applyCard(run, card()).run;
  assert.equal(run.streak, 1);
  assert.equal(run.longest, 3, "a new streak must not shrink the longest one");
});

test("a struck card banks nothing and is tallied anyway", () => {
  const start = applyCard(openRun(AT), card()).run;
  const { run, accepted, counted, why } = applyCard(start, card({ cert: "struck", purse: 990 }));
  assert.equal(accepted, true, "a struck card is still a card");
  assert.equal(counted, false);
  assert.match(why, /disputed/);
  assert.equal(run.struck, 1);
  assert.equal(run.cards, 1, "a disputed card is not a card");
  assert.equal(run.purse, 620, "a disputed card moves no money");
  assert.equal(run.recent.length, 2, "but it is on the run's own record");
  assert.equal(run.recent[0].cert, "struck");
});

test("a struck card moves no mercy and no wounds", () => {
  const { run } = applyCard(openRun(AT), card({
    cert: "struck", ledger: { walked: 2, finished: 1, lost: 1 }, down: ["KOA"],
  }));
  assert.deepEqual(run.mercy, { walked: 0, finished: 0 });
  assert.deepEqual(run.wounds, {});
});

test("an unwitnessed card counts and says that it counted unwitnessed", () => {
  const { run, counted } = applyCard(openRun(AT), card({ cert: "unwitnessed" }));
  assert.equal(counted, true);
  assert.equal(run.cards, 1);
  assert.equal(run.purse, 620);
  assert.equal(run.unwitnessed, 1);
});

test("the mercy ledger accumulates across cards", () => {
  let run = openRun(AT);
  run = applyCard(run, card({ ledger: { walked: 3, finished: 0, lost: 0 } })).run;
  run = applyCard(run, card({ ledger: { walked: 1, finished: 2, lost: 0 } })).run;
  assert.deepEqual(run.mercy, { walked: 4, finished: 2 });
});

test("wounds accumulate per operative, by name", () => {
  let run = openRun(AT);
  run = applyCard(run, card({ result: "loss", ledger: { walked: 0, finished: 0, lost: 2 }, down: ["VESPER", "KOA"] })).run;
  run = applyCard(run, card({ result: "loss", ledger: { walked: 0, finished: 0, lost: 1 }, down: ["VESPER"] })).run;
  assert.deepEqual(run.wounds, { VESPER: 2, KOA: 1 });
});

test("the recent list is newest first and bounded", () => {
  let run = openRun(AT);
  for (let i = 0; i < 20; i++) run = applyCard(run, card({ rating: 10 + i, purse: 100 + i })).run;
  assert.equal(run.recent.length, 12);
  assert.equal(run.recent[0].rating, 29, "newest first");
  assert.equal(run.cards, 20, "the totals are not bounded — only the detail is");
});

// ---- the rules stamp -----------------------------------------------

test("the run adopts the rules stamp from its first stamped card", () => {
  const { run } = applyCard(openRun(AT), card({ rules: "stampA" }));
  assert.equal(run.rules, "stampA");
  assert.equal(run.drift, null);
});

test("a rules change mid-run is recorded, not absorbed", () => {
  let run = applyCard(openRun(AT), card({ rules: "stampA" })).run;
  run = applyCard(run, card({ rules: "stampB", at: "2026-08-05T00:00:00.000Z" })).run;
  assert.deepEqual(run.drift, { from: "stampA", to: "stampB", at: "2026-08-05T00:00:00.000Z" });
  assert.equal(run.rules, "stampA", "the run's banked numbers were earned under the first stamp");
});

test("only the first drift is kept, so the run's history is not rewritten", () => {
  let run = applyCard(openRun(AT), card({ rules: "stampA" })).run;
  run = applyCard(run, card({ rules: "stampB", at: "b" })).run;
  run = applyCard(run, card({ rules: "stampC", at: "c" })).run;
  assert.equal(run.drift.from, "stampA");
  assert.equal(run.drift.to, "stampB");
  assert.equal(run.drift.at, "b");
});

// ---- refusals ------------------------------------------------------

test("a malformed card is refused and leaves the run exactly as it was", () => {
  const start = applyCard(openRun(AT), card()).run;
  const snapshot = JSON.stringify(start);
  for (const bad of [
    null, undefined, 42, "card", {},
    card({ seed: "not hex" }),
    card({ seed: "" }),
    card({ result: "draw" }),
    card({ rating: 101 }),
    card({ rating: -1 }),
    card({ rating: 1.5 }),
    card({ purse: 99999 }),
    card({ cert: "probably" }),
    card({ ledger: null }),
    card({ ledger: { walked: 3, finished: 0 } }),
    card({ down: "VESPER" }),
    card({ down: [""] }),
    card({ down: ["X".repeat(17)], ledger: { walked: 0, finished: 0, lost: 1 } }),
    card({ at: "" }),
    card({ rules: 7 }),
  ]) {
    const { run, accepted, counted, why } = applyCard(start, bad);
    assert.equal(accepted, false, `accepted a malformed card: ${JSON.stringify(bad)}`);
    assert.equal(counted, false);
    assert.equal(why, "card is not a shape a run can bank");
    assert.equal(JSON.stringify(run), snapshot);
  }
});

test("a struck card and a malformed one are told apart", () => {
  // A renderer bug must never be indistinguishable from an honest dispute.
  const start = openRun(AT);
  const struck = applyCard(start, card({ cert: "struck" }));
  const junk = applyCard(start, { seed: "zzz" });
  assert.deepEqual(
    [struck.accepted, struck.counted], [true, false],
    "a struck card is accepted as a card and not counted",
  );
  assert.deepEqual(
    [junk.accepted, junk.counted], [false, false],
    "junk is neither",
  );
  assert.equal(struck.run.struck, 1);
  assert.equal(junk.run.struck, 0, "junk must not inflate the dispute tally");
});

test("a card whose named dead disagree with its own count is refused", () => {
  // The count is what the edge certifies; the names are the yard's word.
  // A renderer that miscounts its own dead must fail closed rather than
  // write a run whose wounds cannot be reconciled with its card log.
  assert.equal(cardValid(card({ ledger: { walked: 0, finished: 0, lost: 2 }, down: ["VESPER"] })), false);
  assert.equal(cardValid(card({ ledger: { walked: 0, finished: 0, lost: 0 }, down: ["VESPER"] })), false);
  assert.equal(cardValid(card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["VESPER"] })), true);
});

test("a run from another schema version is refused rather than upgraded in place", () => {
  const alien = { ...openRun(AT), v: 99 };
  const { counted, why } = applyCard(alien, card());
  assert.equal(counted, false);
  assert.match(why, /schema version/);
});

// ---- storage -------------------------------------------------------

test("nothing stored opens a fresh run", () => {
  memoryStore();
  const { run, how } = loadRun(AT);
  assert.equal(how, "fresh");
  assert.equal(run.cards, 0);
});

test("a stored run of this version is restored intact", () => {
  const banked = applyCard(openRun(AT), card()).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(banked) });
  const { run, how } = loadRun("2026-09-09T00:00:00.000Z");
  assert.equal(how, "restored");
  assert.equal(run.purse, 620);
  assert.equal(run.opened, AT, "restoring must not restamp when the run opened");
});

test("a stored run this schema cannot read is MOVED aside, never dropped", () => {
  const box = memoryStore({ [RUN_KEY]: JSON.stringify({ v: 0, purse: 9999 }) });
  const { run, how } = loadRun(AT);
  assert.equal(how, "orphaned");
  assert.equal(run.cards, 0);
  assert.equal(box[RUN_KEY], undefined, "the unreadable run is out of the live slot");
  assert.match(box[ORPHAN_KEY], /9999/, "and it still exists");
});

test("unparseable storage is orphaned, not thrown", () => {
  const box = memoryStore({ [RUN_KEY]: "{not json" });
  const { how } = loadRun(AT);
  assert.equal(how, "orphaned");
  assert.equal(box[ORPHAN_KEY], "{not json");
});

test("a hand-edited run that is structurally wrong is orphaned", () => {
  // localStorage is shared with every page on the origin and editable in
  // a devtools panel. A run that arrives with the wrong types must not be
  // rendered as if it were real.
  for (const bad of [
    { v: 1, purse: "lots" },
    { ...openRun(AT), cards: -1 },
    { ...openRun(AT), wins: 5, cards: 2 },
    { ...openRun(AT), mercy: null },
    { ...openRun(AT), wounds: ["VESPER"] },
    { ...openRun(AT), wounds: { VESPER: "many" } },
    { ...openRun(AT), recent: null },
    { ...openRun(AT), opened: 12345 },
    { ...openRun(AT), rules: 7 },
    { ...openRun(AT), drift: { from: 1, to: 2 } },
  ]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", `rendered a bad run: ${JSON.stringify(bad)}`);
  }
});

test("the check goes inside the collections, not just around them", () => {
  // Everything in a restored run reaches a surface. A run whose ARRAY is
  // an array but whose entries are junk must be orphaned too, or the
  // structural check is only guarding the shape of the guard.
  const good = applyCard(openRun(AT), card({ ledger: { walked: 1, finished: 0, lost: 1 }, down: ["KOA"] })).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored", "a real run must still restore");

  for (const bad of [
    { ...good, recent: [{ seed: "1", result: "win", rating: 5, purse: 50, cert: "certified", down: "KOA" }] },
    { ...good, recent: [{ seed: "1", result: "draw", rating: 5, purse: 50, cert: "certified", down: [] }] },
    { ...good, recent: [{ seed: "1", result: "win", rating: "<img>", purse: 50, cert: "certified", down: [] }] },
    { ...good, recent: [{ seed: "1", result: "win", rating: 5, purse: 50, cert: "totally fine", down: [] }] },
    { ...good, recent: [null] },
    { ...good, recent: new Array(13).fill(good.recent[0]) },
    { ...good, wounds: { ["X".repeat(40)]: 1 } },
  ]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", `restored junk: ${JSON.stringify(bad).slice(0, 90)}`);
  }
});

test("a storage that refuses to write is survivable and says so", () => {
  bindStore({
    read: () => null,
    write: () => { throw new Error("quota"); },
    remove: () => {},
  });
  assert.equal(saveRun(openRun(AT)), false);
  // and a read that throws still yields a working run rather than a crash
  bindStore({ read: () => { throw new Error("blocked"); }, write: () => {}, remove: () => {} });
  assert.equal(loadRun(AT).how, "fresh");
});

test("closing a run archives it and opens a fresh one in its place", () => {
  const box = memoryStore();
  const banked = applyCard(openRun(AT), card()).run;
  saveRun(banked);
  const fresh = closeRun(banked, "2026-08-09T00:00:00.000Z");
  assert.equal(fresh.cards, 0);
  assert.equal(fresh.opened, "2026-08-09T00:00:00.000Z");
  assert.equal(JSON.parse(box[RUN_KEY]).cards, 0, "the live slot holds the new run");
  const closed = readClosed();
  assert.equal(closed.purse, 620, "the closed run is still readable");
  assert.equal(closed.closed, "2026-08-09T00:00:00.000Z");
  assert.equal(box[CLOSED_KEY] !== undefined, true);
});

// ---- the surface's numbers -----------------------------------------

test("summary derives the record, the mercy rate and the wounded list", () => {
  let run = openRun(AT);
  run = applyCard(run, card({ ledger: { walked: 3, finished: 0, lost: 0 } })).run;
  run = applyCard(run, card({
    result: "loss", rating: 40, purse: 400,
    ledger: { walked: 0, finished: 1, lost: 2 }, down: ["SABLE", "VESPER"],
  })).run;
  run = applyCard(run, card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"] })).run;
  const s = summary(run);
  assert.equal(s.cards, 3);
  assert.equal(s.record, "2–1");
  assert.equal(s.purse, 620 + 400 + 620);
  assert.equal(s.walked, 3);
  assert.equal(s.finished, 1);
  assert.equal(s.mercyRate, 3 / 4);
  assert.deepEqual(s.wounded, [["SABLE", 2], ["VESPER", 1]], "most wounded first");
});

test("the mercy rate is null before anyone has yielded, never a made-up zero", () => {
  const run = applyCard(openRun(AT), card({ ledger: { walked: 0, finished: 0, lost: 0 } })).run;
  assert.equal(summary(run).mercyRate, null);
});

test("summary reports drift so the surface can refuse to imply continuity", () => {
  let run = applyCard(openRun(AT), card({ rules: "stampA" })).run;
  assert.equal(summary(run).drift, null);
  run = applyCard(run, card({ rules: "stampB", at: "later" })).run;
  assert.deepEqual(summary(run).drift, { from: "stampA", to: "stampB", at: "later" });
});
