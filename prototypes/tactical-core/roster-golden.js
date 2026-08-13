/* The roster golden — the second certified input, pinned as behavior.
   (`architecture/roster_in_the_match.md`.)

   The rules stamp is version-as-behavior: the fingerprint of fixed
   playouts under the rules actually running. The other two goldens field
   the canonical three at full strength, so neither can stamp what a
   ROSTER does — a change to how a fielded squad is named or carried in
   would move nothing, and old records would silently certify under new
   roster semantics. That is the same gap the showrunner golden closed for
   twists, and it is closed the same way.

   This playout is the deadbeef golden's twin: same seed, same all-ends
   play, a different squad. VESPER carries a wound in, NIX is fielded
   where KOA would be, and SABLE is three hits from the floor — so it
   exercises substituted names in the transcript AND a starting hp that
   changes when a body goes down. Held against its twin:

     seed deadbeef, ends only, canonical three → 39e8be71, 42 lines, rating 29, 8 ends
     seed deadbeef, ends only, THIS roster     → d44833c0, 37 lines, rating 35, 7 ends

   Same seed, same play, different squad, different match — and note the
   record LENGTHS differ, because the impaired squad is wiped a round
   sooner. Do not read that table as "identical records": the identical-
   record version of this claim is a pure SUBSTITUTION, where no roll
   changes at all, and it lives in `workers/witness/witness_check.mjs`
   where the edge files it as a second match (an earlier draft of this
   comment overclaimed exactly that, and review caught it).

   It carries a RECORD rather than being replayed as a no-input playout,
   and that is the load-bearing part: the Worker's stamp runs this through
   `replayMatch(seed, record, roster)` — the same path certification
   takes. Stamping it through `restart` instead left the forwarding
   unstamped, so a `replayMatch` that dropped its roster argument moved
   nothing (caught in review, executed as a mutation). The record is all
   ends because the squad never acts; the point is which function carries
   the roster there.

   The numbers below were CAPTURED by executing the playout. If roster
   behavior changes on purpose, re-capture deliberately and say so in the
   PR — these constants are the paper trail, not a cache. NIX is a fixture
   name, not a citizen: nothing in the roster's shape says who the squad
   IS, which is the room's business and not the rules core's. */
export const ROSTER_GOLDEN = {
  seed: 0xdeadbeef,
  roster: [
    { name: "VESPER", hp: 6 },
    { name: "NIX", hp: 10 },
    { name: "SABLE", hp: 3 },
  ],
  // seven, where the canonical twin records eight: this squad is wiped a
  // round sooner, which is the roster changing the match in one integer
  record: [["end"], ["end"], ["end"], ["end"], ["end"], ["end"], ["end"]],
  key: "VESPER:6|NIX:10|SABLE:3",
  result: "loss",
  rating: 35,     // outcome constants are stamp inputs: rating is never a
  purse: 350,     // transcript line, so economics are pinned explicitly
  lines: 37,
  fingerprint: "d44833c0",
};
