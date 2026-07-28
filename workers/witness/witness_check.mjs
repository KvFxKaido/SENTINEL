// Execute the claim: the edge must answer with the golden fingerprints,
// including under concurrent load (the serialization mutex is a claim too).
const BASE = process.argv[2] ?? "http://localhost:8787";
const GOLDENS = [
  { seed: "deadbeef", lines: 42, fingerprint: "39e8be71", result: "loss" },
  { seed: "1", lines: 39, fingerprint: "bac5ad90", result: "loss" },
];

let failed = 0;
const get = async (seed) => (await fetch(`${BASE}/replay?seed=${seed}`)).json();

// sequential golden checks
for (const g of GOLDENS) {
  const r = await get(g.seed);
  const ok = r.fingerprint === g.fingerprint && r.lines === g.lines && r.result === g.result;
  console.log(`${ok ? "PASS" : "FAIL"} seed=${g.seed} fp=${r.fingerprint} lines=${r.lines} result=${r.result} rating=${r.rating} purse=${r.purse}`);
  if (!ok) failed++;
}

// concurrency: 8 interleaved requests, alternating seeds — every response
// must still match its own golden, or the mutex is fiction
const burst = await Promise.all(
  Array.from({ length: 8 }, (_, i) => get(GOLDENS[i % 2].seed))
);
burst.forEach((r, i) => {
  const g = GOLDENS[i % 2];
  const ok = r.fingerprint === g.fingerprint && r.lines === g.lines;
  console.log(`${ok ? "PASS" : "FAIL"} burst[${i}] seed=${g.seed} fp=${r.fingerprint}`);
  if (!ok) failed++;
});

// determinism of the non-transcript fields: same seed, same rating
const [a, b] = await Promise.all([get("deadbeef"), get("deadbeef")]);
const same = a.rating === b.rating && a.purse === b.purse;
console.log(`${same ? "PASS" : "FAIL"} rating deterministic: ${a.rating} === ${b.rating}`);
if (!same) failed++;

console.log(failed === 0 ? "ALL PASS" : `${failed} FAILURES`);
process.exit(failed === 0 ? 0 : 1);
