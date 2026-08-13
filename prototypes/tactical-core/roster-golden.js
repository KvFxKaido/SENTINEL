/* The roster golden — the second certified input, pinned as behavior.
   (`architecture/roster_in_the_match.md`.)

   The rules stamp is version-as-behavior: the fingerprint of fixed
   playouts under the rules actually running. The other two goldens field
   the canonical three at full strength, so neither can stamp what a
   ROSTER does — a change to how a fielded squad is named or carried in
   would move nothing, and old records would silently certify under new
   roster semantics. That is the same gap the showrunner golden closed for
   twists, and it is closed the same way.

   This playout is the deadbeef golden's twin: same seed, same no-input
   horizon, a different squad. VESPER carries a wound in, NIX is fielded
   where KOA would be, and SABLE is three hits from the floor — so the
   record exercises substituted names in the transcript AND a starting hp
   that changes when a body goes down. Held against its twin it is also
   the doctrine in one line:

     seed deadbeef, no input, canonical three → 39e8be71, 42 lines, rating 29
     seed deadbeef, no input, THIS roster     → d44833c0, 37 lines, rating 35

   Same seed. Same (empty) record. Different match. That is what "the
   roster is part of match identity" means, and rules.test.js asserts both
   halves so the claim is executed rather than described.

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
  key: "VESPER:6|NIX:10|SABLE:3",
  result: "loss",
  rating: 35,     // outcome constants are stamp inputs: rating is never a
  purse: 350,     // transcript line, so economics are pinned explicitly
  lines: 37,
  fingerprint: "d44833c0",
};
