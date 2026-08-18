/* The chronicle's own edges, tested at the module. run.test.js covers the
 * banking integration (append precedes pointers, refusals mint nothing);
 * this file pins the storage discipline those guarantees stand on: ids
 * that never move, damage that never spreads, and refusals that name
 * their cause instead of half-writing.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  LOG_KEY, LOG_CAP, bindStore, appendEntry, readEntry, entries, LogRefusal,
} from "./log.js";

function memoryStore(seed = {}) {
  const box = { ...seed };
  bindStore({
    read: k => (k in box ? box[k] : null),
    write: (k, v) => { box[k] = v; },
  });
  return box;
}

const extraction = (over = {}) => ({
  kind: "extraction", actor: "SABLE", beneficiary: "KOA",
  commandIndex: 6, underFire: true, reached: true, ...over,
});

const entry = (over = {}) => ({
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
  at: "2026-08-18T00:00:00Z",
  ...over,
});

test("ids are monotonic array addresses and appends preserve every prior slot", () => {
  memoryStore();
  assert.equal(appendEntry(entry()), 0);
  assert.equal(appendEntry(entry({ seed: "1" })), 1);
  assert.equal(appendEntry(entry({ seed: "2" })), 2);
  assert.deepEqual(entries().map(e => e.seed), ["deadbeef", "1", "2"]);
  assert.equal(readEntry(1).seed, "1");
});

test("the cap refuses loudly and writes nothing", () => {
  const full = Array.from({ length: LOG_CAP }, (_, id) => ({ ...entry(), id }));
  const box = memoryStore({ [LOG_KEY]: JSON.stringify(full) });
  const before = box[LOG_KEY];
  assert.throws(() => appendEntry(entry()), refusal =>
    refusal instanceof LogRefusal && refusal.code === "full");
  assert.equal(box[LOG_KEY], before, "a refused append must not touch storage");
  assert.equal(entries().length, LOG_CAP);
});

test("a malformed slot reads null in place — later addresses never renumber", () => {
  const tampered = [
    { ...entry(), id: 0 },
    { bogus: true },
    { ...entry({ seed: "2" }), id: 2 },
  ];
  memoryStore({ [LOG_KEY]: JSON.stringify(tampered) });
  assert.equal(readEntry(1), null, "damage reads as null, not as garbage");
  assert.equal(readEntry(2).seed, "2", "the address AFTER the damage still resolves");
  assert.deepEqual(entries().map(e => e && e.seed), ["deadbeef", null, "2"]);
});

test("a damaged blob refuses appends and is never overwritten", () => {
  const box = memoryStore({ [LOG_KEY]: "{not json" });
  assert.throws(() => appendEntry(entry()), refusal =>
    refusal instanceof LogRefusal && refusal.code === "damaged");
  assert.equal(box[LOG_KEY], "{not json", "the evidence of damage is preserved");
  assert.deepEqual(entries(), []);
  assert.equal(readEntry(0), null);
});

test("a malformed candidate is refused as invalid before anything is written", () => {
  const box = memoryStore();
  for (const bad of [
    entry({ cert: "certified" }),                        // certified grade lives in the archive, not here
    entry({ aftermath: { result: "win", rating: 62, purse: 620, feedCut: null } }), // dark without a cut
    entry({ seed: "NOT-HEX" }),
    entry({ derivedEvents: [extraction({ commandIndex: 99 })] }),  // points past the record
    entry({ extra: "field" }),
  ]) {
    assert.throws(() => appendEntry(bad), refusal =>
      refusal instanceof LogRefusal && refusal.code === "invalid",
      `accepted a malformed entry: ${JSON.stringify(bad).slice(0, 80)}`);
  }
  assert.equal(box[LOG_KEY], undefined, "refusals wrote nothing");
});

test("a write that throws or silently drops is an unwritable refusal, not a minted id", () => {
  bindStore({ read: () => null, write: () => { throw new Error("quota"); } });
  assert.throws(() => appendEntry(entry()), refusal =>
    refusal instanceof LogRefusal && refusal.code === "unwritable");

  // the sharper case: the write "succeeds" but the read-back disagrees —
  // the id must not be returned, because the target did not survive
  bindStore({ read: () => null, write: () => {} });
  assert.throws(() => appendEntry(entry()), refusal =>
    refusal instanceof LogRefusal && refusal.code === "unwritable");
});

test("returned entries are copies — a caller cannot mutate the chronicle", () => {
  memoryStore();
  const id = appendEntry(entry());
  const first = readEntry(id);
  first.record.push(["forged"]);
  first.aftermath.purse = 9999;
  assert.deepEqual(readEntry(id), {
    ...entry(), id,
  }, "mutating a returned copy must not reach storage");
});
