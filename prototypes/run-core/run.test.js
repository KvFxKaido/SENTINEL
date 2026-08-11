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
  RUN_V, RUN_KEY, CLOSED_KEY, ORPHAN_KEY, WOUND_CLOCK,
  bindStore, openRun, openSeason, slateValid, applyCard, applyPass,
  cardValid, fitness, loadRun, saveRun, closeRun, readClosed, summary,
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

// An authored slate: four entries, each saying what its card means.
// host and sanction are present-but-null on purpose — the author said
// nobody, rather than saying nothing.
function slate(over = {}) {
  return {
    id: "opening-tour",
    entries: [
      { venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
      { venue: "THE COLD COURT", host: null, sanction: "covenant" },
      { venue: "LATTICE FLOOR 9", host: "lattice", sanction: null },
      { venue: "THE DRAIN", host: "ghost-networks", sanction: null },
    ],
    ...over,
  };
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
  assert.equal(r.season, null, "a plain run has no slate — a season is opened, not implied");
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

test("a struck card does not get to define the run's provenance", () => {
  // A disputed card banks nothing. Letting it set the stamp meant a first
  // struck card under A set rules=A, and the first card that actually
  // counted — under B — then reported drift A→B, even though every banked
  // number in the run was earned under B (caught in review).
  const struck = applyCard(openRun(AT), card({ cert: "struck", rules: "stampA" })).run;
  assert.equal(struck.rules, null, "a card that banked nothing named the run's rules");
  assert.equal(struck.drift, null);

  const then = applyCard(struck, card({ rules: "stampB" })).run;
  assert.equal(then.rules, "stampB");
  assert.equal(then.drift, null, "invented a drift out of a card nobody banked");
});

test("a struck card cannot fire drift on an established run either", () => {
  const banked = applyCard(openRun(AT), card({ rules: "stampA" })).run;
  const after = applyCard(banked, card({ cert: "struck", rules: "stampZ", at: "z" })).run;
  assert.equal(after.drift, null);
  assert.equal(after.rules, "stampA");
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
    // a negative here restored fine and rendered a -100% mercy rate
    { ...openRun(AT), mercy: { walked: -1, finished: 2 } },
    { ...openRun(AT), mercy: { walked: 1, finished: -2 } },
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

test("the live key is not versioned, so a schema bump can actually orphan", () => {
  // The bug this pins: with RUN_KEY = `sentinel.run.v${RUN_V}`, bumping the
  // version pointed loadRun at an empty key and left the real run under a
  // key nothing reads — orphaned by nobody, surfaced to nobody.
  assert.equal(RUN_KEY.includes(String(RUN_V)), false, RUN_KEY);
  const box = memoryStore({
    [RUN_KEY]: JSON.stringify({ ...openRun(AT), v: RUN_V - 1, purse: 4321 }),
  });
  const { how } = loadRun(AT);
  assert.equal(how, "orphaned", "a previous-schema run was not seen at all");
  assert.match(box[ORPHAN_KEY], /4321/);
});

test("closing a run archives it and opens a fresh one in its place", () => {
  const box = memoryStore();
  const banked = applyCard(openRun(AT), card()).run;
  saveRun(banked);
  const out = closeRun(banked, "2026-08-09T00:00:00.000Z");
  assert.equal(out.closed, true);
  assert.equal(out.archived, true);
  assert.equal(out.run.cards, 0);
  assert.equal(out.run.opened, "2026-08-09T00:00:00.000Z");
  assert.equal(JSON.parse(box[RUN_KEY]).cards, 0, "the live slot holds the new run");
  const closed = readClosed();
  assert.equal(closed.purse, 620, "the closed run is still readable");
  assert.equal(closed.closed, "2026-08-09T00:00:00.000Z");
});

test("a close that cannot archive does not destroy the run", () => {
  // Storage with room for the one-byte startup probe but not a second full
  // run used to lose the run from BOTH slots while the panel said ARCHIVED
  // (caught in review). The destructive half only happens if the
  // preserving half worked.
  const banked = applyCard(openRun(AT), card()).run;
  const live = { [RUN_KEY]: JSON.stringify(banked) };
  bindStore({
    read: k => (k in live ? live[k] : null),
    write: (k, v) => { if (k === CLOSED_KEY) throw new Error("quota"); live[k] = v; },
    remove: k => { delete live[k]; },
  });
  const out = closeRun(banked, "2026-08-09T00:00:00.000Z");
  assert.equal(out.closed, false);
  assert.equal(out.archived, false);
  assert.equal(out.run, banked, "the run must still be the run");
  assert.equal(JSON.parse(live[RUN_KEY]).purse, 620, "the live slot was overwritten anyway");
});

test("an archive that silently drops the write is not an archive", () => {
  // A store that accepts everything and keeps nothing would otherwise
  // report a successful archive of nothing. The write is read back.
  const banked = applyCard(openRun(AT), card()).run;
  bindStore({ read: () => null, write: () => {}, remove: () => {} });
  const out = closeRun(banked, AT);
  assert.equal(out.archived, false);
  assert.equal(out.closed, false);
  assert.equal(out.run, banked);
});

test("the inert default store cannot fake an archive", () => {
  bindStore({ read: () => null, write: () => {}, remove: () => {} });
  assert.equal(closeRun(openRun(AT), AT).archived, false);
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

// ---- the slate (season-lite) ---------------------------------------

test("a season is a run opened on a slate", () => {
  const r = openSeason(AT, slate());
  assert.equal(r.v, RUN_V);
  assert.equal(r.cards, 0);
  assert.equal(r.season.pos, 0);
  assert.deepEqual(r.season.clocks, {});
  assert.deepEqual(r.season.passed, []);
  assert.equal(r.season.slate.id, "opening-tour");
  assert.equal(r.season.slate.entries.length, 4);
});

test("a slate that is not a slate opens nothing, not half a season", () => {
  for (const bad of [
    null, 42, {},
    slate({ id: "" }),
    slate({ id: "X".repeat(17) }),
    slate({ entries: [] }),
    slate({ entries: new Array(33).fill({ venue: "V", host: null, sanction: null }) }),
    slate({ entries: [{ venue: "", host: null, sanction: null }] }),
    slate({ entries: [{ venue: "V".repeat(25), host: null, sanction: null }] }),
    slate({ entries: [{ venue: "V", host: null }] }),       // sanction never said
    slate({ entries: [{ venue: "V", sanction: null }] }),   // host never said
    slate({ entries: [{ venue: "V", host: 7, sanction: null }] }),
  ]) {
    assert.equal(slateValid(bad), false, `a non-slate validated: ${JSON.stringify(bad)?.slice(0, 80)}`);
    assert.equal(openSeason(AT, bad), null, "and it must not open half a season");
  }
});

test("openSeason keeps its own copy of the slate, three facts per entry", () => {
  const authored = slate();
  authored.entries[0].extra = "rides along?";
  const r = openSeason(AT, authored);
  assert.equal(r.season.slate.entries[0].extra, undefined, "an entry is three facts, not whatever rode in");
  authored.entries[0].venue = "EDITED AFTER";
  assert.equal(r.season.slate.entries[0].venue, "KESTREL YARD", "the season holds its own slate");
});

test("a banked card is stamped from the run's own slate and advances it", () => {
  const { run, counted } = applyCard(openSeason(AT, slate()), card());
  assert.equal(counted, true);
  assert.equal(run.season.pos, 1);
  assert.deepEqual(
    run.recent[0].slate,
    { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
    "the framing is the slate's own word — the payload never carried one",
  );
});

test("a plain run's cards carry no slate stamp", () => {
  const { run } = applyCard(openRun(AT), card());
  assert.equal(run.recent[0].slate, undefined);
});

test("a pass banks the entry it declined and advances the slate", () => {
  const { run, accepted } = applyPass(openSeason(AT, slate()), AT);
  assert.equal(accepted, true);
  assert.equal(run.season.pos, 1);
  assert.equal(run.cards, 0, "a pass is not a card");
  assert.deepEqual(run.season.passed, [
    { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null, at: AT },
  ], "the card you declined is a fact of the season, framing and all");
});

test("wounds are clocks: a down fighter gates the deal", () => {
  const hurt = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 2, finished: 0, lost: 1 }, down: ["VESPER"] })).run;
  assert.deepEqual(hurt.season.clocks, { VESPER: WOUND_CLOCK });
  assert.equal(fitness(hurt).fit, false);
  const snapshot = JSON.stringify(hurt);
  const { run, accepted, counted, why } = applyCard(hurt, card());
  assert.equal(accepted, false, "a card dealt to an unfit roster is a caller bug, not an outcome");
  assert.equal(counted, false);
  assert.match(why, /unfit/);
  assert.equal(JSON.stringify(run), snapshot, "and the run is untouched");
});

test("passing is always legal, and passing is what heals — the deadlock law", () => {
  // Clocks counted in cards dealt would gate the only mechanism that
  // heals them (caught by both bots on the season doc's first draft).
  // Clocks count SLATE POSITIONS, and a pass advances both.
  let run = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 2, finished: 0, lost: 1 }, down: ["VESPER"] })).run;
  for (let i = 0; i < WOUND_CLOCK; i++) {
    assert.equal(fitness(run).fit, false);
    const out = applyPass(run, AT);
    assert.equal(out.accepted, true, "passing must stay legal while unfit — that is the point");
    run = out.run;
  }
  assert.equal(fitness(run).fit, true);
  assert.deepEqual(run.season.clocks, {}, "a cleared clock is dropped, not stored at zero");
  assert.equal(applyCard(run, card()).counted, true, "and the deal is legal again");
});

test("a struck card does not advance the slate", () => {
  const { run: after, counted } = applyCard(openSeason(AT, slate()),
    card({ cert: "struck", ledger: { walked: 0, finished: 0, lost: 1 }, down: ["KOA"] }));
  assert.equal(counted, false);
  assert.equal(after.season.pos, 0, "the entry the edge disputed is still the current entry");
  assert.deepEqual(after.season.clocks, {}, "and it wounds nobody");
  assert.equal(after.recent[0].slate.idx, 0, "but the attempt is on the record, with its framing");
  const again = applyCard(after, card()).run;
  assert.equal(again.season.pos, 1, "the entry can be fought again");
  assert.equal(again.recent[0].slate.idx, 0, "at the same position");
});

test("a completed slate refuses both verbs — closing is the player's verb", () => {
  const one = openSeason(AT, slate({ entries: [{ venue: "ONLY CARD", host: null, sanction: null }] }));
  const run = applyCard(one, card()).run;
  assert.equal(summary(run).season.complete, true);
  const fought = applyCard(run, card());
  assert.equal(fought.accepted, false);
  assert.match(fought.why, /complete/);
  const passed = applyPass(run, AT);
  assert.equal(passed.accepted, false);
  assert.match(passed.why, /complete/);
});

test("cards plus passes is the position — the books always balance", () => {
  let run = openSeason(AT, slate());
  run = applyCard(run, card()).run;                          // fought: pos 1
  run = applyPass(run, AT).run;                              // passed: pos 2
  run = applyCard(run, card({ cert: "struck" })).run;        // struck: pos 2 still
  run = applyCard(run, card({ cert: "unwitnessed" })).run;   // counted: pos 3
  assert.equal(run.season.pos, 3);
  assert.equal(run.cards + run.season.passed.length, run.season.pos);
});

test("a pass on a plain run is refused — there is nothing to decline", () => {
  const { accepted, why } = applyPass(openRun(AT), AT);
  assert.equal(accepted, false);
  assert.match(why, /without a slate/);
});

test("a pass with no timestamp is refused", () => {
  const r = openSeason(AT, slate());
  assert.equal(applyPass(r, "").accepted, false);
  assert.equal(applyPass(r, undefined).accepted, false);
});

test("applyPass never mutates the run it was given", () => {
  const hurt = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["KOA"] })).run;
  const snapshot = JSON.stringify(hurt);
  applyPass(hurt, AT);
  assert.equal(JSON.stringify(hurt), snapshot);
});

test("a season run survives the round trip through storage", () => {
  let run = openSeason(AT, slate());
  run = applyCard(run, card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["KOA"] })).run;
  run = applyPass(run, AT).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  const { run: back, how } = loadRun("2026-09-01T00:00:00.000Z");
  assert.equal(how, "restored");
  assert.deepEqual(back, run);
});

test("a hand-edited season that is structurally wrong is orphaned", () => {
  const good = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["KOA"] })).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored", "the real one must still restore");
  const s = good.season;
  const noSeasonKey = { ...good };
  delete noSeasonKey.season;
  for (const bad of [
    { ...good, season: 42 },
    { ...good, season: { ...s, slate: null } },
    { ...good, season: { ...s, pos: -1 } },
    { ...good, season: { ...s, pos: 99 } },
    // pos 3 with one card and no passes: the books do not balance
    { ...good, season: { ...s, pos: 3 } },
    // a stored zero clock was written by somebody else — advance() drops them
    { ...good, season: { ...s, clocks: { KOA: 0 } } },
    { ...good, season: { ...s, clocks: { KOA: -2 } } },
    { ...good, season: { ...s, clocks: { KOA: "soon" } } },
    { ...good, season: { ...s, passed: [{ idx: 0, venue: "V", host: null, sanction: null }] } },
    noSeasonKey,
    { ...good, recent: [{ ...good.recent[0], slate: { idx: -1, venue: "V", host: null, sanction: null } }] },
  ]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", `restored junk: ${JSON.stringify(bad).slice(0, 100)}`);
  }
});

test("closing a season archives the whole season with it", () => {
  memoryStore();
  let run = openSeason(AT, slate());
  run = applyCard(run, card()).run;
  saveRun(run);
  const out = closeRun(run, "2026-09-01T00:00:00.000Z");
  assert.equal(out.closed, true);
  assert.equal(readClosed().season.pos, 1, "the season's shape survives in the archive");
  assert.equal(out.run.season, null, "the fresh run is a plain one — a new season is opened, not inherited");
});

test("summary carries the season's numbers, and null for a plain run", () => {
  assert.equal(summary(openRun(AT)).season, null);
  const run = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["VESPER"] })).run;
  const s = summary(run).season;
  assert.equal(s.slate, "opening-tour");
  assert.equal(s.pos, 1);
  assert.equal(s.length, 4);
  assert.equal(s.complete, false);
  assert.equal(s.passes, 0);
  assert.equal(s.fit, false);
  assert.deepEqual(s.clocks, [["VESPER", WOUND_CLOCK]]);
  assert.deepEqual(s.next, { venue: "THE COLD COURT", host: null, sanction: "covenant" });
});
