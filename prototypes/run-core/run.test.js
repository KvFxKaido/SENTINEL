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
import fs from "node:fs";
import {
  RUN_V, RUN_KEY, CLOSED_KEY, ORPHAN_KEY, WOUND_CLOCK, FLAIR_SLOTS,
  LINEUP_SLOTS, FULL_STRENGTH,
  bindStore, openRun, openSeason, slateValid, applyCard, applyPass,
  applyBuy, itemValid, stockValid, kitOf,
  cardValid, rosterValid, personOf, fieldedRoster, setLineup,
  fitness, loadRun, saveRun, closeRun, readClosed, summary,
} from "./run.js";
import {
  LOG_KEY, bindStore as bindLogStore, appendEntry, readEntry,
} from "./log.js";

const AT = "2026-08-04T12:00:00.000Z";
const MATCH_ID = "0123456789abcdef0123456789abcdef";
const MATCH_ID_2 = "fedcba9876543210fedcba9876543210";
const authoredCourt = JSON.parse(fs.readFileSync(
  new URL("../../world/recruitment/court-01.json", import.meta.url), "utf8"));
const COURT_ROSTER = { people: authoredCourt.people, lineup: authoredCourt.lineup };

// A store that is a plain object, so a test can look at exactly what was
// written rather than at what the module says it wrote.
function memoryStore(seed = {}) {
  const box = { ...seed };
  const binding = {
    read: k => (k in box ? box[k] : null),
    write: (k, v) => { box[k] = v; },
    remove: k => { delete box[k]; },
  };
  bindStore(binding);
  bindLogStore(binding);
  return box;
}

function logMatch(over = {}) {
  return {
    kind: "match",
    cert: "dark",
    seed: "deadbeef",
    roster: [
      { name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 },
    ],
    record: [
      ["cut", 2], ["end-turn"], ["end-turn"], ["end-turn"],
      ["end-turn"], ["end-turn"], ["drag", 2, 1, 3, 4], ["end"],
    ],
    derivedEvents: [extraction()],
    aftermath: { result: "win", rating: 62, purse: 620, feedCut: { commandIndex: 0 } },
    at: AT,
    ...over,
  };
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

// A thing a purse may buy: flair, in one of the two slots that carry no
// verbs. Colour rides along because a bought thing has to keep looking
// like itself after the shop restocks.
function item(over = {}) {
  return {
    id: "ashen-hood",
    name: "ASHEN HOOD",
    slot: "drape",
    cost: 300,
    color: "#7da888",
    ...over,
  };
}

// A run with money in it, so the shop tests are about the shop rather
// than about being broke.
function funded(run, purse = 1000) {
  return applyCard(run, card({ purse, rating: 62 })).run;
}

// A certified win, three hostiles yielded and walked, nobody of ours lost.
function card(over = {}) {
  const out = {
    seed: "deadbeef",
    result: "win",
    rating: 62,
    purse: 620,
    cert: "certified",
    ledger: { walked: 3, finished: 0, lost: 0 },
    down: [],
    derivedEvents: [],
    rules: "abc123",
    at: AT,
    ...over,
  };
  if (!("matchId" in over)) out.matchId = out.cert === "certified" ? MATCH_ID : null;
  return out;
}

function extraction(over = {}) {
  return {
    kind: "extraction", actor: "SABLE", beneficiary: "KOA",
    commandIndex: 6, underFire: true, reached: true,
    ...over,
  };
}

const lifeDedication = (over = {}) => ({
  kind: "repay-the-life", from: "koa", to: "sable", ...over,
});

// ---- shape ---------------------------------------------------------

test("a fresh run is empty, versioned, and stamped with when it opened", () => {
  const r = openRun(AT);
  assert.equal(r.v, RUN_V);
  assert.equal(r.opened, AT);
  assert.equal(r.cards, 0);
  assert.equal(r.purse, 0);
  assert.equal(r.rules, null);
  assert.deepEqual(r.wounds, {});
  assert.deepEqual(r.eventLedger, {});
  assert.deepEqual(r.relationships, []);
  assert.deepEqual(r.recent, []);
  assert.equal(r.dark, 0);
  assert.equal(r.season, null, "a plain run has no slate — a season is opened, not implied");
});

test("a fresh run owns four stable people, their origins, and a three-person lineup", () => {
  const r = openRun(AT);
  assert.deepEqual(r.roster, COURT_ROSTER,
    "run-core's default and the room's authored Court 01 file must not drift");
  assert.equal(r.roster.people.length, 4);
  assert.equal(r.roster.lineup.length, LINEUP_SLOTS);
  assert.deepEqual(r.roster.lineup, ["vesper", "koa", "sable"]);
  assert.equal(personOf(r, "nix").name, "NIX");
  assert.deepEqual(personOf(r, "nix").origin, {
    source: "ember-winter-entry",
    faction: "ember_colonies",
    reason: "The north valley entered a defender because winter was bad.",
  });
  assert.deepEqual(fieldedRoster(r), [
    { name: "VESPER", hp: FULL_STRENGTH },
    { name: "KOA", hp: FULL_STRENGTH },
    { name: "SABLE", hp: FULL_STRENGTH },
  ], "stable ids and origins stop at the door; the yard still gets exactly name and hp");
});

test("an authored roster is exact, unique, larger than the fielded three, and source-complete", () => {
  const good = openRun(AT).roster;
  assert.equal(rosterValid(good), true);
  const cases = [
    { ...good, people: good.people.slice(0, 3) },
    { ...good, lineup: ["vesper", "koa"] },
    { ...good, lineup: ["vesper", "vesper", "sable"] },
    { ...good, lineup: ["vesper", "koa", "nobody"] },
    { ...good, extra: true },
    { ...good, people: good.people.map((person, i) => i ? person : { ...person, id: "koa" }) },
    { ...good, people: good.people.map((person, i) => i ? person : { ...person, name: "KOA" }) },
    { ...good, people: good.people.map((person, i) => i ? person : {
      ...person, origin: { ...person.origin, reason: "" },
    }) },
    { ...good, people: good.people.map((person, i) => i ? person : {
      ...person, origin: { ...person.origin, account: "trust me" },
    }) },
  ];
  for (const bad of cases) assert.equal(rosterValid(bad), false);
  assert.equal(openRun(AT, cases[0]), null, "bad authored content opens no half-run");
  assert.equal(openSeason(AT, slate(), cases[0]), null,
    "bad authored content opens no half-season either");
});

test("an invalid authored roster does not consume or orphan a stored run", () => {
  const stored = JSON.stringify(openRun(AT));
  const box = memoryStore({ [RUN_KEY]: stored });
  const bad = { ...COURT_ROSTER, lineup: ["vesper", "koa", "stranger"] };
  const loaded = loadRun(AT, bad);
  assert.deepEqual(loaded, { run: null, how: "invalid-roster" });
  assert.equal(box[RUN_KEY], stored);
  assert.equal(box[ORPHAN_KEY], undefined);
});

test("lineup choice is immutable, id-based, and changes only the certified roster snapshot", () => {
  const before = openRun(AT);
  const out = setLineup(before, ["vesper", "nix", "sable"]);
  assert.equal(out.accepted, true);
  assert.deepEqual(before.roster.lineup, ["vesper", "koa", "sable"]);
  assert.deepEqual(out.run.roster.lineup, ["vesper", "nix", "sable"]);
  assert.deepEqual(fieldedRoster(out.run), [
    { name: "VESPER", hp: 10 },
    { name: "NIX", hp: 10 },
    { name: "SABLE", hp: 10 },
  ]);
  assert.equal(Object.keys(fieldedRoster(out.run)[1]).length, 2);
  assert.equal(setLineup(before, ["vesper", "vesper", "nix"]).accepted, false);
  assert.equal(setLineup(before, ["vesper", "nix", "stranger"]).accepted, false);
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

test("certified derived events bank under stable ids with a filed command source", () => {
  const event = extraction();
  const out = applyCard(openSeason(AT, slate()), card({ derivedEvents: [event] }));
  assert.equal(out.accepted, true);
  assert.deepEqual(out.run.recent[0].derivedEvents, [event],
    "the receipt keeps the tactical names that crossed the wire");
  assert.deepEqual(out.run.eventLedger, {
    sable: [{
      kind: "extraction",
      beneficiary: "koa",
      underFire: true,
      reached: true,
      grade: "certified",
      origin: { matchId: MATCH_ID, commandIndex: 6 },
      at: AT,
      slate: { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
    }],
  });
  assert.deepEqual(summary(out.run).derivedEvents[0], {
    actor: "sable",
    kind: "extraction",
    beneficiary: "koa",
    underFire: true,
    reached: true,
    grade: "certified",
    origin: { matchId: MATCH_ID, commandIndex: 6 },
    at: AT,
    slate: { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
  });
  assert.deepEqual(out.run.relationships, [{
    kind: "owes-a-life",
    from: "koa",
    to: "sable",
    grade: "certified",
    origin: { matchId: MATCH_ID, commandIndex: 6 },
    status: "active",
    at: AT,
    slate: { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
  }], "the run's banking policy says the beneficiary owes the actor a life");
  assert.deepEqual(summary(out.run).relationships, out.run.relationships);
  assert.deepEqual(summary(out.run).season.dedicatedPasses, [],
    "a debt alone is not an offer while its creditor is fit");
});

test("an active life debt keeps its first rescue origin — no repetition treadmill", () => {
  let run = applyCard(openRun(AT), card({ derivedEvents: [extraction()] })).run;
  run = applyCard(run, card({
    seed: "fadedcab",
    matchId: MATCH_ID_2,
    at: "2026-08-05T12:00:00.000Z",
    derivedEvents: [extraction({ commandIndex: 9, underFire: false })],
  })).run;
  assert.equal(run.eventLedger.sable.length, 2, "both certified events remain history");
  assert.equal(run.relationships.length, 1, "the second rescue is not relationship XP");
  assert.deepEqual(run.relationships[0].origin, { matchId: MATCH_ID, commandIndex: 6 },
    "the first active debt's origin stands");
});

test("an unwitnessed card with no surviving local origin banks no claim", () => {
  const event = {
    kind: "extraction", actor: "VESPER", beneficiary: "KOA",
    commandIndex: 0, underFire: false, reached: true,
  };
  const out = applyCard(openRun(AT), card({
    cert: "unwitnessed", derivedEvents: [event], rules: null,
  }));
  assert.equal(out.counted, true);
  assert.deepEqual(out.run.eventLedger, {},
    "a rolling receipt is not the append-only event target claim grade requires");
  assert.deepEqual(out.run.recent[0].derivedEvents, [],
    "the yard's in-session account does not become stored run history");
  assert.deepEqual(summary(out.run).derivedEvents, []);
  assert.equal(out.run.recent[0].matchId, null);
});

test("the chronicle append precedes claim banking, and a refused origin mints nothing", () => {
  memoryStore();
  const darkCard = card({
    cert: "dark", derivedEvents: [extraction()], rules: null,
  });

  const beforeTarget = applyCard(openRun(AT), darkCard);
  assert.equal(beforeTarget.counted, true, "the card still counts when no target survived");
  assert.equal(beforeTarget.run.dark, 1);
  assert.deepEqual(beforeTarget.run.eventLedger, {});
  assert.deepEqual(beforeTarget.run.relationships, []);
  assert.deepEqual(beforeTarget.run.recent[0].derivedEvents, []);

  const logId = appendEntry(logMatch());
  assert.notEqual(readEntry(logId), null, "the target survives before the pointer is minted");
  const banked = applyCard(openRun(AT), darkCard, logId);
  assert.equal(banked.counted, true);
  assert.deepEqual(banked.run.eventLedger.sable[0], {
    kind: "extraction", beneficiary: "koa", underFire: true, reached: true,
    grade: "claim", origin: { logId, commandIndex: 6 }, at: AT,
  });
  assert.deepEqual(banked.run.relationships[0], {
    kind: "owes-a-life", from: "koa", to: "sable", grade: "claim",
    origin: { logId, commandIndex: 6 }, status: "active", at: AT,
  });
  assert.deepEqual(banked.run.recent[0].derivedEvents, [extraction()]);
});

test("dark and accidental verdicts count separately and restore with exact receipts", () => {
  let run = applyCard(openRun(AT), card({ cert: "dark", rules: null })).run;
  run = applyCard(run, card({ cert: "unwitnessed", seed: "1", rules: null })).run;
  assert.equal(run.cards, 2);
  assert.equal(run.dark, 1);
  assert.equal(run.unwitnessed, 1);
  assert.deepEqual(run.recent.map(entry => entry.cert), ["unwitnessed", "dark"]);
  assert.deepEqual({ dark: summary(run).dark, unwitnessed: summary(run).unwitnessed },
    { dark: 1, unwitnessed: 1 });
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored");

  const forged = JSON.parse(JSON.stringify(run));
  forged.dark = 0;
  memoryStore({ [RUN_KEY]: JSON.stringify(forged) });
  assert.equal(loadRun(AT).how, "orphaned", "the split is banking-time state, not forensic display");
});

test("one active life debt per directed pair spans certified and claim grades", () => {
  const claim = card({
    cert: "dark", seed: "1", rules: null, at: "claim-at", derivedEvents: [extraction()],
  });
  let certifiedFirst = applyCard(openRun(AT), card({ derivedEvents: [extraction()] })).run;
  certifiedFirst = applyCard(certifiedFirst, claim, 7).run;
  assert.equal(certifiedFirst.eventLedger.sable.length, 2);
  assert.equal(certifiedFirst.relationships.length, 1);
  assert.equal(certifiedFirst.relationships[0].grade, "certified",
    "a later claim cannot open a parallel debt ledger");

  let claimFirst = applyCard(openRun(AT), claim, 8).run;
  claimFirst = applyCard(claimFirst, card({
    seed: "2", matchId: MATCH_ID_2, at: "certified-at", derivedEvents: [extraction({ commandIndex: 9 })],
  })).run;
  assert.equal(claimFirst.eventLedger.sable.length, 2);
  assert.equal(claimFirst.relationships.length, 1);
  assert.equal(claimFirst.relationships[0].grade, "claim",
    "a later certificate cannot replace the first still-active claimed debt");
  memoryStore({ [RUN_KEY]: JSON.stringify(claimFirst) });
  assert.equal(loadRun(AT).how, "restored");
});

test("claim shapes are exact; a missing-target forgery remains render-time truth", () => {
  const good = applyCard(openRun(AT), card({
    cert: "dark", rules: null, derivedEvents: [extraction()],
  }), 99).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored",
    "sane has no jurisdiction over the independent chronicle, so it cannot detect this forgery");
  assert.equal(readEntry(99), null,
    "a shape-valid pointer whose target is absent must fail when the source is opened");

  const changed = mutate => {
    const copy = JSON.parse(JSON.stringify(good));
    mutate(copy);
    return copy;
  };
  const forged = [
    changed(run => { run.eventLedger.sable[0].grade = "rumor"; }),
    changed(run => { run.eventLedger.sable[0].origin.logId = -1; }),
    changed(run => { run.eventLedger.sable[0].origin.commandIndex = -1; }),
    changed(run => { run.eventLedger.sable[0].origin.matchId = MATCH_ID; }),
    changed(run => { run.relationships[0].grade = "certified"; }),
    changed(run => { run.relationships[0].origin = { logId: 99, commandIndex: 5 }; }),
    changed(run => { delete run.relationships[0].grade; }),
  ];
  for (const run of forged) {
    memoryStore({ [RUN_KEY]: JSON.stringify(run) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(run.eventLedger));
  }
});

test("a derived event cannot name someone outside the fielded lineup", () => {
  const start = openRun(AT);
  const bad = card({ derivedEvents: [{
    kind: "extraction", actor: "NIX", beneficiary: "KOA",
    commandIndex: 0, underFire: false, reached: true,
  }] });
  const out = applyCard(start, bad);
  assert.equal(out.accepted, false);
  assert.match(out.why, /did not field/);
  assert.deepEqual(out.run, start);
});

test("certified grade requires a plausible filed match id", () => {
  assert.equal(cardValid(card({ matchId: null })), false);
  assert.equal(cardValid(card({ matchId: "short" })), false);
  assert.equal(cardValid(card()), true);
  assert.equal(cardValid(card({ cert: "unwitnessed", matchId: MATCH_ID })), false);
});

test("the mercy ledger accumulates across cards", () => {
  let run = openRun(AT);
  run = applyCard(run, card({ ledger: { walked: 3, finished: 0, lost: 0 } })).run;
  run = applyCard(run, card({ ledger: { walked: 1, finished: 2, lost: 0 } })).run;
  assert.deepEqual(run.mercy, { walked: 4, finished: 2 });
});

test("wounds accumulate per person, by stable id", () => {
  let run = openRun(AT);
  run = applyCard(run, card({ result: "loss", ledger: { walked: 0, finished: 0, lost: 2 }, down: ["VESPER", "KOA"] })).run;
  run = applyCard(run, card({ result: "loss", ledger: { walked: 0, finished: 0, lost: 1 }, down: ["VESPER"] })).run;
  assert.deepEqual(run.wounds, { vesper: 2, koa: 1 });
});

test("a yard name is only the wire alias for a wound banked under the person id", () => {
  const futureAlias = {
    people: COURT_ROSTER.people.map(person =>
      person.id === "vesper" ? { ...person, name: "WRAITH" } : person),
    lineup: COURT_ROSTER.lineup.slice(),
  };
  const out = applyCard(openSeason(AT, slate(), futureAlias), card({
    result: "loss",
    ledger: { walked: 0, finished: 0, lost: 1 },
    down: ["WRAITH"],
  }));
  assert.equal(out.accepted, true);
  assert.deepEqual(out.run.wounds, { vesper: 1 }, "the durable wound key is not the current alias");
  assert.deepEqual(out.run.season.clocks, { vesper: WOUND_CLOCK });
  assert.deepEqual(out.run.recent[0].down, ["WRAITH"], "the receipt preserves the name on the wire");
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
    { ...openRun(AT), wounds: { vesper: "many" } },
    { ...openRun(AT), recent: null },
    { ...openRun(AT), opened: 12345 },
    { ...openRun(AT), rules: 7 },
    { ...openRun(AT), drift: { from: 1, to: 2 } },
  ]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", `rendered a bad run: ${JSON.stringify(bad)}`);
  }
});

test("stored derived-event ledgers validate owned ids, grades, sources, and exact entries", () => {
  const event = {
    kind: "extraction", actor: "SABLE", beneficiary: "KOA",
    commandIndex: 6, underFire: true, reached: true,
  };
  const good = applyCard(openRun(AT), card({ derivedEvents: [event] })).run;
  const changed = mutate => {
    const copy = JSON.parse(JSON.stringify(good));
    mutate(copy);
    return copy;
  };
  const bad = [
    changed(run => { run.eventLedger = []; }),
    changed(run => { run.eventLedger.stranger = run.eventLedger.sable; delete run.eventLedger.sable; }),
    changed(run => { run.eventLedger.sable[0].beneficiary = "stranger"; }),
    changed(run => { run.eventLedger.sable[0].beneficiary = "sable"; }),
    changed(run => { run.eventLedger.sable[0].origin.matchId = "short"; }),
    changed(run => { run.eventLedger.sable[0].origin.commandIndex = -1; }),
    changed(run => { run.eventLedger.sable[0].grade = "claim"; }),
    changed(run => { run.eventLedger.sable[0].origin = { logId: -1, commandIndex: 6 }; }),
    changed(run => { run.eventLedger.sable[0].relationship = "not this slice"; }),
    changed(run => { run.eventLedger.sable[0].reached = false; }),
  ];
  for (const run of bad) {
    memoryStore({ [RUN_KEY]: JSON.stringify(run) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(run.eventLedger));
  }

  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored");
});

test("an active and then fulfilled relationship survives save and restore; v6 is orphaned", () => {
  let run = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
    ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"],
  })).run;
  run = applyPass(run, "2026-08-05T13:00:00.000Z", lifeDedication()).run;
  const box = memoryStore();
  assert.equal(saveRun(run), true);
  const restored = loadRun("2026-09-01T00:00:00.000Z");
  assert.equal(restored.how, "restored");
  assert.deepEqual(restored.run.relationships, run.relationships);
  assert.deepEqual(restored.run.season.passed, run.season.passed);

  const v6 = { ...run, v: 6 };
  box[RUN_KEY] = JSON.stringify(v6);
  const orphaned = loadRun(AT);
  assert.equal(orphaned.how, "orphaned");
  assert.equal(box[RUN_KEY], undefined);
  assert.match(box[ORPHAN_KEY], /"v":6/);
});

test("stored relationship forgeries are orphaned all the way through repayment", () => {
  let good = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
    ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"],
  })).run;
  good = applyPass(good, "2026-08-05T13:00:00.000Z", lifeDedication()).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored", "the reducer's repayment must restore");

  const changed = mutate => {
    const copy = JSON.parse(JSON.stringify(good));
    mutate(copy);
    return copy;
  };
  const missingLedger = changed(run => { delete run.relationships; });
  const forged = [
    missingLedger,
    changed(run => { run.relationships = {}; }),
    changed(run => { run.relationships[0].from = "stranger"; }),
    changed(run => { run.relationships[0].from = "sable"; }),
    changed(run => { run.relationships[0].origin.matchId = "short"; }),
    changed(run => { run.relationships[0].origin.commandIndex = -1; }),
    changed(run => { run.relationships[0].origin.matchId = MATCH_ID_2; }),
    changed(run => { run.relationships[0].status = "trusted"; }),
    changed(run => { run.relationships[0].trust = 1; }),
    changed(run => { delete run.relationships[0].fulfilledAt; }),
    changed(run => { run.relationships[0].fulfilledSlate.venue = "MADE UP STOP"; }),
    changed(run => { delete run.season.passed[0].dedication; }),
    changed(run => { run.season.passed[0].dedication.to = "vesper"; }),
  ];
  for (const run of forged) {
    memoryStore({ [RUN_KEY]: JSON.stringify(run) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(run.relationships));
  }

  let twoEvents = applyCard(openRun(AT), card({ derivedEvents: [extraction()] })).run;
  const secondAt = "2026-08-05T12:00:00.000Z";
  twoEvents = applyCard(twoEvents, card({
    seed: "fadedcab", matchId: MATCH_ID_2, at: secondAt,
    derivedEvents: [extraction({ commandIndex: 9 })],
  })).run;
  const duplicateActive = JSON.parse(JSON.stringify(twoEvents));
  duplicateActive.relationships.push({
    ...duplicateActive.relationships[0],
    origin: { matchId: MATCH_ID_2, commandIndex: 9 },
    at: secondAt,
  });
  memoryStore({ [RUN_KEY]: JSON.stringify(duplicateActive) });
  assert.equal(loadRun(AT).how, "orphaned",
    "two active owes-a-life entries for one directed pair cannot be hand-written in");

  const erased = applyCard(openRun(AT), card({ derivedEvents: [extraction()] })).run;
  erased.relationships = [];
  memoryStore({ [RUN_KEY]: JSON.stringify(erased) });
  assert.equal(loadRun(AT).how, "orphaned",
    "a certified extraction cannot restore with its deterministically banked debt erased");
});

test("a relationship minted inside its predecessor's active season interval is orphaned", () => {
  let run = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
  })).run;
  const secondAt = "2026-08-05T12:00:00.000Z";
  run = applyCard(run, card({
    seed: "fadedcab", matchId: MATCH_ID_2, at: secondAt,
    derivedEvents: [extraction({ commandIndex: 9 })],
    ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"],
  })).run;
  run = applyPass(run, "2026-08-05T13:00:00.000Z", lifeDedication()).run;
  assert.equal(run.relationships.length, 1,
    "the reducer suppresses the second rescue while the first debt is active");
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored",
    "the reducer-authored history beneath the forged mint must remain valid");

  const overlapped = JSON.parse(JSON.stringify(run));
  overlapped.relationships.push({
    kind: "owes-a-life",
    from: "koa",
    to: "sable",
    grade: "certified",
    origin: { matchId: MATCH_ID_2, commandIndex: 9 },
    status: "active",
    at: secondAt,
    slate: {
      idx: 1, venue: "THE COLD COURT", host: null, sanction: "covenant",
    },
  });
  memoryStore({ [RUN_KEY]: JSON.stringify(overlapped) });
  assert.equal(loadRun(AT).how, "orphaned",
    "a later fulfillment cannot retroactively make an in-interval mint possible");
});

test("a fulfilled season debt can be re-minted by a post-fulfillment extraction", () => {
  let run = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
    ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"],
  })).run;
  run = applyPass(run, "2026-08-05T13:00:00.000Z", lifeDedication()).run;
  run = applyCard(run, card({
    seed: "fadedcab", matchId: MATCH_ID_2, at: "2026-08-06T12:00:00.000Z",
    derivedEvents: [extraction({ commandIndex: 9 })],
  })).run;

  assert.deepEqual(run.relationships.map(relationship => ({
    status: relationship.status,
    minted: relationship.slate.idx,
    fulfilled: relationship.fulfilledSlate?.idx,
  })), [
    { status: "fulfilled", minted: 0, fulfilled: 1 },
    { status: "active", minted: 2, fulfilled: undefined },
  ]);
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored");
});

test("plain runs order repeated rescues by ledger append, not opaque at strings", () => {
  let run = applyCard(openRun(AT), card({
    at: "z-later-looking", derivedEvents: [extraction()],
  })).run;
  run = applyCard(run, card({
    seed: "fadedcab", matchId: MATCH_ID_2, at: "a-earlier-looking",
    derivedEvents: [extraction({ commandIndex: 9 })],
  })).run;

  assert.equal(run.relationships.length, 1,
    "without passes, the first active relationship covers the later appended rescue");
  assert.deepEqual(run.relationships[0].origin, { matchId: MATCH_ID, commandIndex: 6 });
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored",
    "plain-run timestamps are retained labels, not a chronology sane() can prove");
});

test("stored unwitnessed receipts cannot smuggle in a pointerless derived event", () => {
  const event = {
    kind: "extraction", actor: "VESPER", beneficiary: "KOA",
    commandIndex: 0, underFire: false, reached: true,
  };
  const good = applyCard(openRun(AT), card({
    cert: "unwitnessed", derivedEvents: [event], rules: null,
  })).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored");

  const minted = JSON.parse(JSON.stringify(good));
  minted.recent[0].derivedEvents = [event];
  memoryStore({ [RUN_KEY]: JSON.stringify(minted) });
  assert.equal(loadRun(AT).how, "orphaned");
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
    { ...good, wounds: { KOA: 1 } },
    { ...good, wounds: { stranger: 1 } },
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

test("the chronicle survives RUN_V orphaning and closeRun because it is not run state", () => {
  const box = memoryStore();
  const logId = appendEntry(logMatch());
  const logged = box[LOG_KEY];

  box[RUN_KEY] = JSON.stringify({ ...openRun(AT), v: RUN_V - 1 });
  assert.equal(loadRun(AT).how, "orphaned");
  assert.equal(box[LOG_KEY], logged);
  assert.equal(readEntry(logId).id, logId);

  const banked = applyCard(openRun(AT), card()).run;
  assert.equal(closeRun(banked, "2026-08-09T00:00:00.000Z").closed, true);
  assert.equal(box[LOG_KEY], logged);
  assert.equal(readEntry(logId).id, logId);
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
  assert.deepEqual(s.wounded, [["sable", 2], ["vesper", 1]], "most wounded first, keyed by id");
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

test("dedicated repayment refuses wrong people, no debt, and no clock distinctly", () => {
  const wrongPersonRun = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
    ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"],
  })).run;
  const wrongPerson = applyPass(wrongPersonRun, AT, lifeDedication({ to: "stranger" }));
  assert.equal(wrongPerson.accepted, false);
  assert.match(wrongPerson.why, /wrong person/);

  const noDebtRun = applyCard(openSeason(AT, slate()), card({
    ledger: { walked: 0, finished: 0, lost: 1 }, down: ["SABLE"],
  })).run;
  const noDebt = applyPass(noDebtRun, AT, lifeDedication());
  assert.equal(noDebt.accepted, false);
  assert.match(noDebt.why, /no active life debt/);

  const noClockRun = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
  })).run;
  const noClock = applyPass(noClockRun, AT, lifeDedication());
  assert.equal(noClock.accepted, false);
  assert.match(noClock.why, /no running recovery clock/);

  assert.equal(new Set([wrongPerson.why, noDebt.why, noClock.why]).size, 3,
    "the three illegal requests must not collapse into one mysterious refusal");
  assert.deepEqual(summary(noDebtRun).season.dedicatedPasses, []);
  assert.deepEqual(summary(noClockRun).season.dedicatedPasses, []);
});

test("REPAY THE LIFE advances the creditor by two, everyone else by one, and fulfills the debt", () => {
  const start = applyCard(openSeason(AT, slate()), card({
    derivedEvents: [extraction()],
    ledger: { walked: 0, finished: 0, lost: 2 }, down: ["VESPER", "SABLE"],
  })).run;
  assert.deepEqual(start.season.clocks, { vesper: WOUND_CLOCK, sable: WOUND_CLOCK });
  assert.deepEqual(summary(start).season.dedicatedPasses, [{
    kind: "repay-the-life", from: "koa", to: "sable", recovers: 2,
  }]);
  const snapshot = JSON.stringify(start);
  const repaidAt = "2026-08-05T13:00:00.000Z";
  const out = applyPass(start, repaidAt, lifeDedication());
  assert.equal(out.accepted, true);
  assert.equal(JSON.stringify(start), snapshot, "repayment must not mutate the run it was given");
  assert.deepEqual(out.run.season.clocks, { vesper: WOUND_CLOCK - 1 },
    "SABLE receives two stops; VESPER receives the ordinary one");
  assert.deepEqual(out.run.season.passed[0], {
    idx: 1, venue: "THE COLD COURT", host: null, sanction: "covenant", at: repaidAt,
    dedication: { kind: "repay-the-life", from: "koa", to: "sable" },
  });
  assert.deepEqual(out.run.relationships[0], {
    kind: "owes-a-life",
    from: "koa",
    to: "sable",
    grade: "certified",
    origin: { matchId: MATCH_ID, commandIndex: 6 },
    status: "fulfilled",
    at: AT,
    slate: { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
    fulfilledAt: repaidAt,
    fulfilledSlate: { idx: 1, venue: "THE COLD COURT", host: null, sanction: "covenant" },
  });
  assert.deepEqual(summary(out.run).season.dedicatedPasses, [],
    "a fulfilled debt is history, not a repeatable recovery button");
});

test("REPAY THE LIFE has identical force and stamps on a claim-grade debt", () => {
  const start = applyCard(openSeason(AT, slate()), card({
    cert: "dark", rules: null, derivedEvents: [extraction()],
    ledger: { walked: 0, finished: 0, lost: 2 }, down: ["VESPER", "SABLE"],
  }), 17).run;
  assert.deepEqual(summary(start).season.dedicatedPasses, [{
    kind: "repay-the-life", from: "koa", to: "sable", recovers: 2,
  }]);

  const repaidAt = "2026-08-05T13:00:00.000Z";
  const out = applyPass(start, repaidAt, lifeDedication());
  assert.equal(out.accepted, true);
  assert.deepEqual(out.run.season.clocks, { vesper: WOUND_CLOCK - 1 });
  assert.deepEqual(out.run.relationships[0], {
    kind: "owes-a-life", from: "koa", to: "sable", grade: "claim",
    origin: { logId: 17, commandIndex: 6 }, status: "fulfilled", at: AT,
    slate: { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
    fulfilledAt: repaidAt,
    fulfilledSlate: { idx: 1, venue: "THE COLD COURT", host: null, sanction: "covenant" },
  }, "claim fulfillment carries exactly the certified lifecycle fields");
  memoryStore({ [RUN_KEY]: JSON.stringify(out.run) });
  assert.equal(loadRun(AT).how, "restored");
});

test("wounds are clocks: a down fighter gates the deal", () => {
  const hurt = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 2, finished: 0, lost: 1 }, down: ["VESPER"] })).run;
  assert.deepEqual(hurt.season.clocks, { vesper: WOUND_CLOCK });
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

test("benching a recovering person makes a fit lineup, and fighting advances their clock", () => {
  let run = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 2, finished: 0, lost: 1 }, down: ["KOA"] })).run;
  assert.equal(fitness(run).fit, false);

  const changed = setLineup(run, ["vesper", "nix", "sable"]);
  assert.equal(changed.accepted, true);
  run = changed.run;
  assert.equal(fitness(run).fit, true, "the clock belongs to KOA, not to an abstract squad slot");
  assert.deepEqual(fitness(run).clocks, [["koa", WOUND_CLOCK]], "the benched wound still exists");
  assert.deepEqual(fitness(run).fieldedClocks, []);

  const fought = applyCard(run, card({ seed: "f00d" }));
  assert.equal(fought.accepted, true);
  assert.equal(fought.counted, true);
  assert.deepEqual(fought.run.season.clocks, { koa: WOUND_CLOCK - 1 },
    "the slate moved, so the benched recovery clock moved too");
});

test("a returned card cannot claim somebody outside the lineup went down", () => {
  const run = setLineup(openRun(AT), ["vesper", "nix", "sable"]).run;
  const out = applyCard(run,
    card({ ledger: { walked: 2, finished: 0, lost: 1 }, down: ["KOA"] }));
  assert.equal(out.accepted, false);
  assert.equal(out.counted, false);
  assert.match(out.why, /did not field/);
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
    { ...good, season: { ...s, clocks: { koa: 0 } } },
    { ...good, season: { ...s, clocks: { koa: -2 } } },
    { ...good, season: { ...s, clocks: { koa: "soon" } } },
    { ...good, season: { ...s, clocks: { KOA: WOUND_CLOCK } } },
    { ...good, season: { ...s, clocks: { stranger: WOUND_CLOCK } } },
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

// ---- review findings, executed --------------------------------------

test("an orphan that cannot be preserved does not claim it was", () => {
  // The write can throw under quota. Before the read-back, loadRun said
  // "orphaned" anyway — and the room saves a fresh run over the live
  // slot on that answer, destroying the only copy while the panel said
  // SET ASIDE (caught in review, on the schema bump that made this path
  // hot for every v1 run).
  const v1 = JSON.stringify({ v: 1, purse: 4321 });
  const live = { [RUN_KEY]: v1 };
  bindStore({
    read: k => (k in live ? live[k] : null),
    write: k => { if (k === ORPHAN_KEY) throw new Error("quota"); },
    remove: k => { delete live[k]; },
  });
  const out = loadRun(AT);
  assert.equal(out.how, "unpreserved");
  assert.equal(out.run.cards, 0, "a fresh run still opens, in memory");
  assert.equal(live[RUN_KEY], v1, "the unreadable run keeps the live slot");
});

test("a store that silently drops the orphan write cannot fake a set-aside", () => {
  // The inert default is exactly this store: the write succeeds and
  // keeps nothing. Same failure closeRun already guards against — read
  // it back, or it did not happen.
  const v1 = JSON.stringify({ v: 1, purse: 4321 });
  const live = { [RUN_KEY]: v1 };
  bindStore({
    read: k => (k in live ? live[k] : null),
    write: (k, v) => { if (k !== ORPHAN_KEY) live[k] = v; },
    remove: k => { delete live[k]; },
  });
  assert.equal(loadRun(AT).how, "unpreserved");
  assert.equal(live[RUN_KEY], v1);
});

test("__proto__ is not a fighter name — the deal gate cannot be walked around", () => {
  // Durable ledgers now use the stricter person id, but the yard wire still
  // arrives as tactical names. Refuse the hostile spelling at that boundary
  // before any caller can treat it as an object key.
  const down = { ledger: { walked: 0, finished: 0, lost: 1 }, down: ["__proto__"] };
  assert.equal(cardValid(card(down)), false);
  const { accepted } = applyCard(openSeason(AT, slate()), card(down));
  assert.equal(accepted, false, "the card is refused before it can wound nobody");
});

test("a stored run that smuggles __proto__ in is orphaned, not restored", () => {
  const good = applyCard(openSeason(AT, slate()),
    card({ ledger: { walked: 0, finished: 0, lost: 1 }, down: ["KOA"] })).run;
  const blob = JSON.stringify(good);
  for (const bad of [
    blob.replace(`"clocks":{"koa":${WOUND_CLOCK}}`, `"clocks":{"__proto__":${WOUND_CLOCK}}`),
    blob.replace('"wounds":{"koa":1}', '"wounds":{"__proto__":1}'),
  ]) {
    assert.notEqual(bad, blob, "the replacement must have found its target");
    memoryStore({ [RUN_KEY]: bad });
    assert.equal(loadRun(AT).how, "orphaned", bad.slice(0, 90));
  }
});

test("a stored season cannot forge framing the slate never said", () => {
  // Restore binds every record back to the authored slate: a pass or a
  // stamp whose framing is not the slate's own word at its index was not
  // written by this module (caught in review — it restored fine, and
  // summary() reported a venue the slate never said).
  let good = openSeason(AT, slate());
  good = applyCard(good, card()).run;
  good = applyPass(good, AT).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored", "the honest season must still restore");

  const forgedPass = JSON.parse(JSON.stringify(good));
  forgedPass.season.passed[0].venue = "FORGED HALL";

  const wanderedPass = JSON.parse(JSON.stringify(good));
  wanderedPass.season.passed[0].idx = 2;   // in range, but entry 2's framing is not this one

  const forgedStamp = JSON.parse(JSON.stringify(good));
  forgedStamp.recent[0].slate.venue = "FORGED HALL";

  const offSlateStamp = JSON.parse(JSON.stringify(good));
  offSlateStamp.recent[0].slate.idx = 31;  // shaped fine, but not on this slate

  const strippedStamp = JSON.parse(JSON.stringify(good));
  delete strippedStamp.recent[0].slate;    // a season card always carries one

  for (const bad of [forgedPass, wanderedPass, forgedStamp, offSlateStamp, strippedStamp]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(bad).slice(0, 110));
  }
});

test("a plain run's card cannot wear a stamp — no slate to answer to", () => {
  const plain = applyCard(openRun(AT), card()).run;
  const grafted = JSON.parse(JSON.stringify(plain));
  grafted.recent[0].slate = { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null };
  memoryStore({ [RUN_KEY]: JSON.stringify(grafted) });
  assert.equal(loadRun(AT).how, "orphaned");
});

test("pass indices climb — a duplicated pass cannot balance its way in", () => {
  // applyPass banks the current position and advances, so indices
  // strictly increase; a duplicate keeps the books balanced and is
  // still not something this module could have written.
  let good = openSeason(AT, slate());
  good = applyPass(good, AT).run;
  good = applyPass(good, AT).run;
  const dup = JSON.parse(JSON.stringify(good));
  dup.season.passed[1] = { ...dup.season.passed[0] };
  memoryStore({ [RUN_KEY]: JSON.stringify(dup) });
  assert.equal(loadRun(AT).how, "orphaned");
});

// ---- the purse spends ----------------------------------------------

test("a fresh run has spent nothing and wears nothing", () => {
  const r = openRun(AT);
  assert.equal(r.spent, 0);
  assert.deepEqual(r.bought, []);
  assert.deepEqual(kitOf(r, "VESPER"), {}, "every hook starts empty, and an empty hook is information");
});

test("buying spends the balance and leaves the purse alone", () => {
  // The distinction the whole field exists for: purse is what the season
  // WON, spent is what left. A run that decremented purse could no longer
  // say what it earned, and every card that paid for a hood would read as
  // a card that paid for nothing.
  const run = funded(openRun(AT), 1000);
  const { run: after, accepted, why } = applyBuy(run, item(), "VESPER", AT);
  assert.equal(accepted, true, why ?? "");
  assert.equal(after.purse, 1000, "the purse still says what the season won");
  assert.equal(after.spent, 300);
  assert.equal(summary(after).balance, 700);
  assert.equal(after.bought.length, 1);
  assert.equal(after.bought[0].who, "VESPER");
  assert.equal(after.bought[0].name, "ASHEN HOOD");
});

test("the purse will not cover it — and the refusal is a caller bug", () => {
  // accepted:false on purpose: the room prices the stock and knows the
  // balance, so a purchase that arrives here unaffordable means the shop
  // offered something it should have refused at the surface. Same
  // contract as a card dealt to an unfit roster.
  const run = funded(openRun(AT), 200);
  const { run: after, accepted, why } = applyBuy(run, item({ cost: 300 }), "VESPER", AT);
  assert.equal(accepted, false);
  assert.match(why, /purse will not cover/);
  assert.equal(after.spent, 0, "a refused purchase spends nothing");
  assert.deepEqual(after.bought, []);
});

test("the balance is what is left, not what was won — twice over", () => {
  let run = funded(openRun(AT), 500);
  run = applyBuy(run, item({ cost: 300 }), "VESPER", AT).run;
  const second = applyBuy(run, item({ id: "chain", name: "LENGTH OF CHAIN", slot: "patch", cost: 300 }), "VESPER", AT);
  assert.equal(second.accepted, false, "500 earned, 300 gone — the second 300 is not there");
  assert.equal(summary(run).balance, 200);
});

test("a slot is bought once per fighter — one hook each", () => {
  let run = funded(openRun(AT), 2000);
  run = applyBuy(run, item(), "VESPER", AT).run;
  const again = applyBuy(run, item({ id: "storm-cloak", name: "STORM CLOAK" }), "VESPER", AT);
  assert.equal(again.accepted, false);
  assert.match(again.why, /already wears a drape/);
  // ...but the other slot, and the other fighters, are untouched
  assert.equal(applyBuy(run, item({ id: "chain", name: "CHAIN", slot: "patch" }), "VESPER", AT).accepted, true);
  assert.equal(applyBuy(run, item(), "KOA", AT).accepted, true);
});

test("a verb-carrying slot is not for sale — the tier boundary, enforced", () => {
  // This is the line season-lite is DEFINED by not crossing. head, torso,
  // legs, primary and sidearm carry verbs; a verb is roster state, and
  // roster state reaching the yard is the doctrine change. So the refusal
  // lives at the boundary rather than in a comment about what the shop
  // ought to stock.
  assert.deepEqual([...FLAIR_SLOTS], ["drape", "patch"]);
  const run = funded(openRun(AT), 5000);
  for (const slot of ["head", "torso", "legs", "primary", "sidearm", "", null]) {
    assert.equal(itemValid(item({ slot })), false, `${slot} is not a flair slot`);
    const out = applyBuy(run, item({ slot }), "VESPER", AT);
    assert.equal(out.accepted, false, `${slot} was bought, and it must not be`);
    assert.equal(out.run.spent, 0);
  }
});

test("an item that is not an item is refused at the boundary", () => {
  assert.equal(itemValid(item()), true);
  for (const bad of [
    item({ id: "__proto__" }),
    item({ id: "" }),
    item({ name: "" }),
    item({ name: "A".repeat(25) }),
    item({ cost: -1 }),
    item({ cost: 1.5 }),
    item({ cost: 999999 }),
    item({ color: "7da888" }),      // a colour is a colour, not nearly one
    item({ color: "#7DA888" }),     // one spelling, so a stored kit cannot have two
    item({ color: "red" }),
    null,
    "ashen-hood",
  ]) {
    assert.equal(itemValid(bad), false, JSON.stringify(bad));
  }
});

test("a shop's stock is validated whole, ids and all", () => {
  const stock = [item(), item({ id: "chain", name: "CHAIN", slot: "patch", cost: 120 })];
  assert.equal(stockValid(stock), true);
  assert.equal(stockValid([]), false, "an empty case is not a shop");
  assert.equal(stockValid([item(), item({ name: "OTHER HOOD" })]), false,
    "two different items under one id makes a purchase record ambiguous");
  assert.equal(stockValid([item(), item({ id: "rig", slot: "torso" })]), false);
  assert.equal(stockValid({ 0: item() }), false);
});

test("a purchase needs a name and a when", () => {
  const run = funded(openRun(AT), 1000);
  assert.equal(applyBuy(run, item(), "", AT).accepted, false);
  assert.equal(applyBuy(run, item(), "__proto__", AT).accepted, false,
    "the one name that is an accessor, refused where every key here is minted");
  assert.equal(applyBuy(run, item(), "STRANGER", AT).accepted, false,
    "a valid tactical name with no owned person behind it has no hook");
  assert.equal(applyBuy(run, item(), "VESPER", "").accepted, false);
  assert.equal(applyBuy(run, item(), "VESPER", null).accepted, false);
});

test("buying moves no slate — the books still balance", () => {
  // A purchase touches neither the position nor the clocks, which is why
  // it needs no settling gate: there is nothing a card in flight could
  // invalidate. The arithmetic sane() enforces on restore says so.
  let run = openSeason(AT, slate());
  run = funded(run, 1000);
  const before = run.season.pos;
  run = applyBuy(run, item(), "VESPER", AT).run;
  assert.equal(run.season.pos, before, "the tour did not move because you bought a hood");
  assert.equal(run.cards + run.season.passed.length, run.season.pos);
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored");
});

test("a purchase is stamped with where on the tour it happened", () => {
  // Trophies have provenance (Circuit §6): the same hood bought after the
  // Cold Court is a different object from one bought in week one, and the
  // purchase record is the only place that can live.
  let run = funded(openSeason(AT, slate()), 2000);
  run = applyPass(run, AT).run;
  run = applyBuy(run, item(), "VESPER", AT).run;
  assert.deepEqual(run.bought[0].slate,
    { idx: 2, venue: "LATTICE FLOOR 9", host: "lattice", sanction: null });
});

test("a plain run's purchase carries no stamp — no slate to answer to", () => {
  const run = applyBuy(funded(openRun(AT), 1000), item(), "VESPER", AT).run;
  assert.equal(run.bought[0].slate, undefined);
  const grafted = JSON.parse(JSON.stringify(run));
  grafted.bought[0].slate = { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null };
  memoryStore({ [RUN_KEY]: JSON.stringify(grafted) });
  assert.equal(loadRun(AT).how, "orphaned");
});

test("applyBuy never mutates the run it was given", () => {
  const before = funded(openRun(AT), 1000);
  const snapshot = JSON.stringify(before);
  const { run: after } = applyBuy(before, item(), "VESPER", AT);
  assert.equal(JSON.stringify(before), snapshot, "the input run was modified in place");
  assert.equal(before.spent, 0);
  assert.equal(after.spent, 300);
});

test("the kit is derived from the ledger, never stored beside it", () => {
  let run = funded(openRun(AT), 2000);
  run = applyBuy(run, item(), "VESPER", AT).run;
  run = applyBuy(run, item({ id: "chain", name: "LENGTH OF CHAIN", slot: "patch", cost: 120 }), "VESPER", AT).run;
  run = applyBuy(run, item({ id: "storm-cloak", name: "STORM CLOAK", cost: 400 }), "KOA", AT).run;

  assert.deepEqual(Object.keys(kitOf(run, "VESPER")).sort(), ["drape", "patch"]);
  assert.equal(kitOf(run, "KOA").drape.name, "STORM CLOAK");
  assert.deepEqual(kitOf(run, "SABLE"), {});

  const s = summary(run);
  assert.equal(s.spent, 820);
  assert.equal(s.balance, 1180);
  assert.deepEqual(s.kit.map(([who]) => who), ["KOA", "VESPER"], "a stable order the surface does not invent");
  assert.equal(s.kit[1][1].drape.name, "ASHEN HOOD");
});

test("a run that wears what it never bought does not restore", () => {
  const good = applyBuy(funded(openRun(AT), 1000), item(), "VESPER", AT).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored", "the honest rack must still restore");

  const freeHood = JSON.parse(JSON.stringify(good));
  freeHood.spent = 0;                       // a hood on the rack that cost nothing

  const overspent = JSON.parse(JSON.stringify(good));
  overspent.spent = 5000;                   // more gone than was ever earned
  overspent.bought[0].cost = 5000;          // books balanced, purse impossible

  const twoHoods = JSON.parse(JSON.stringify(good));
  twoHoods.bought.push({ ...twoHoods.bought[0], id: "storm-cloak" });
  twoHoods.spent = 600;                     // balanced, and still two drapes on one body

  const soldAVerb = JSON.parse(JSON.stringify(good));
  soldAVerb.bought[0].slot = "torso";       // a verb nobody could have bought

  for (const bad of [freeHood, overspent, twoHoods, soldAVerb]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(bad.bought).slice(0, 110));
  }
});

test("a stored purchase cannot forge the tour it was bought on", () => {
  let good = funded(openSeason(AT, slate()), 2000);
  good = applyPass(good, AT).run;
  good = applyBuy(good, item(), "VESPER", AT).run;
  good = applyBuy(good, item({ id: "chain", name: "CHAIN", slot: "patch", cost: 120 }), "VESPER", AT).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored");

  const forged = JSON.parse(JSON.stringify(good));
  forged.bought[0].slate.venue = "FORGED HALL";

  const offSlate = JSON.parse(JSON.stringify(good));
  offSlate.bought[0].slate.idx = 31;

  const regressed = JSON.parse(JSON.stringify(good));
  regressed.bought[1].slate = { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null };

  for (const bad of [forged, offSlate, regressed]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(bad.bought[0].slate));
  }
});

test("a slate finished mid-run leaves later purchases unstamped, and that is terminal", () => {
  // Once the tour is complete there is no entry to stamp with, so a
  // purchase carries none — and nothing stamped may follow it, because
  // the position never goes back.
  let run = funded(openSeason(AT, slate()), 3000);
  for (let i = 0; i < 3; i++) run = applyPass(run, AT).run;
  assert.equal(summary(run).season.complete, true);
  run = applyBuy(run, item(), "VESPER", AT).run;
  assert.equal(run.bought[0].slate, undefined, "nothing left on the tour to stamp it with");
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored");

  const resurrected = JSON.parse(JSON.stringify(run));
  resurrected.bought.push({
    ...resurrected.bought[0], id: "chain", slot: "patch", cost: 0,
    slate: { idx: 0, venue: "KESTREL YARD", host: "steel-syndicate", sanction: null },
  });
  memoryStore({ [RUN_KEY]: JSON.stringify(resurrected) });
  assert.equal(loadRun(AT).how, "orphaned", "the tour cannot un-complete itself");
});

test("a purse nobody won does not restore — and now it would have bought things", () => {
  // The exact probe from beat 3's review: a hand-edited fresh season with
  // a fat purse restored, reported the balance, and applyBuy accepted a
  // hood out of it. `recent` is the run's own receipt, so while nothing
  // has been evicted every total that is a sum or a count must BE it.
  const honest = applyBuy(funded(openSeason(AT, slate()), 1000), item(), "VESPER", AT).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(honest) });
  assert.equal(loadRun(AT).how, "restored", "the honest run must still restore");

  const mintedFresh = openSeason(AT, slate());
  mintedFresh.purse = 10000;

  const forgeries = [mintedFresh];
  for (const [field, value] of [
    ["purse", 4321], ["cards", 2], ["wins", 0], ["struck", 3], ["unwitnessed", 1], ["dark", 1],
  ]) {
    const bad = JSON.parse(JSON.stringify(honest));
    bad[field] = value;
    forgeries.push(bad);
  }
  const forgedMercy = JSON.parse(JSON.stringify(honest));
  forgedMercy.mercy = { walked: 99, finished: 0 };
  forgeries.push(forgedMercy);

  for (const bad of forgeries) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned",
      `${bad.cards} cards / ${bad.purse}c / mercy ${bad.mercy.walked}`);
  }
});

test("a run whose history has scrolled off still restores — on the bound", () => {
  // The counterpart, and the more important half: `recent` caps at 12, so
  // past that the receipts are gone BY DESIGN and only the bound survives
  // (a card can pay at most MAX_PURSE). Orphaning a long honest run would
  // be a far worse bug than the forgery above.
  let run = openRun(AT);
  for (let i = 0; i < 15; i++) run = applyCard(run, card()).run;
  assert.equal(run.cards, 15);
  assert.equal(run.recent.length, 12, "the receipts have scrolled off");
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored");

  const overRich = JSON.parse(JSON.stringify(run));
  overRich.purse = 15 * 10000 + 1;   // past what 15 cards could ever have paid
  memoryStore({ [RUN_KEY]: JSON.stringify(overRich) });
  assert.equal(loadRun(AT).how, "orphaned");
});

test("a full receipt buffer is still a complete receipt", () => {
  // The boundary both review bots found: RECENT cards have evicted
  // nothing, so testing the buffer's FULLNESS instead of its
  // COMPLETENESS dropped an honest-length run into the loose branch and
  // reopened the forged-purse hole one card above where it was closed.
  let run = openRun(AT);
  for (let i = 0; i < 12; i++) run = applyCard(run, card({ purse: 0, rating: 0 })).run;
  assert.equal(run.recent.length, 12, "the buffer is exactly full");
  assert.equal(run.purse, 0);
  memoryStore({ [RUN_KEY]: JSON.stringify(run) });
  assert.equal(loadRun(AT).how, "restored", "an honest full buffer must restore");

  const rich = JSON.parse(JSON.stringify(run));
  rich.purse = 120000;
  memoryStore({ [RUN_KEY]: JSON.stringify(rich) });
  assert.equal(loadRun(AT).how, "orphaned", "full is not the same as truncated");

  // ...and claiming an extra card to escape into the loose branch buys
  // exactly one card's worth of headroom, not a free pass: what is still
  // on the receipt is a floor.
  const inflated = JSON.parse(JSON.stringify(rich));
  inflated.cards = 13;
  memoryStore({ [RUN_KEY]: JSON.stringify(inflated) });
  assert.equal(loadRun(AT).how, "orphaned");
});

test("a purchase cannot be stamped where the season has not been", () => {
  // Both caught in review, beat 3. applyBuy stamps the CURRENT position
  // and the position only climbs, so a stamp in the future is impossible —
  // and an unstamped purchase means the tour was over, which is terminal.
  let good = funded(openSeason(AT, slate()), 2000);
  good = applyBuy(good, item(), "VESPER", AT).run;
  memoryStore({ [RUN_KEY]: JSON.stringify(good) });
  assert.equal(loadRun(AT).how, "restored");

  const fromTheFuture = JSON.parse(JSON.stringify(good));
  fromTheFuture.bought[0].slate = {
    idx: 2, venue: "LATTICE FLOOR 9", host: "lattice", sanction: null,
  };

  const noTourYet = JSON.parse(JSON.stringify(good));
  delete noTourYet.bought[0].slate;   // unstamped, on a slate with entries left

  for (const bad of [fromTheFuture, noTourYet]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned", JSON.stringify(bad.bought[0].slate ?? null));
  }
});

test("a card cannot be stamped where the season has not been either", () => {
  const good = applyCard(openSeason(AT, slate()), card()).run;
  const fromTheFuture = JSON.parse(JSON.stringify(good));
  fromTheFuture.recent[0].slate = {
    idx: 3, venue: "THE DRAIN", host: "ghost-networks", sanction: null,
  };
  memoryStore({ [RUN_KEY]: JSON.stringify(fromTheFuture) });
  assert.equal(loadRun(AT).how, "orphaned");
});

test("a stored record cannot smuggle a field this module never writes", () => {
  // A purchase carrying `verb` is Tier 2 roster state sitting inside a
  // Tier 1 run — shaped like flair, and not flair (caught in review).
  const good = applyBuy(funded(openRun(AT), 1000), item(), "VESPER", AT).run;
  const armed = JSON.parse(JSON.stringify(good));
  armed.bought[0].verb = "dash";

  const richCard = JSON.parse(JSON.stringify(good));
  richCard.recent[0].roster = ["VESPER", "KOA"];

  for (const bad of [armed, richCard]) {
    memoryStore({ [RUN_KEY]: JSON.stringify(bad) });
    assert.equal(loadRun(AT).how, "orphaned");
  }
});

test("closing archives the rack whole, and the fresh run wears nothing", () => {
  const box = memoryStore();
  let run = applyBuy(funded(openSeason(AT, slate()), 1000), item(), "VESPER", AT).run;
  const { run: fresh, archived } = closeRun(run, AT);
  assert.equal(archived, true);
  const closed = readClosed();
  assert.equal(closed.spent, 300);
  assert.equal(closed.bought[0].name, "ASHEN HOOD");
  assert.equal(fresh.spent, 0);
  assert.deepEqual(fresh.bought, [], "the kit belongs to the run that bought it");
  assert.ok(box[CLOSED_KEY].includes("ASHEN HOOD"));
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
  assert.deepEqual(s.clocks, [["vesper", WOUND_CLOCK]]);
  assert.deepEqual(s.next, { venue: "THE COLD COURT", host: null, sanction: "covenant" });
});
