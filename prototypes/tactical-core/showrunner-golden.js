/* The showrunner golden — the twist grammar, pinned as behavior.
   (Circuit roadmap step 4.)

   The rules stamp is version-as-behavior: the fingerprint of a fixed
   playout under the rules actually running. The deadbeef golden alone
   cannot stamp twist behavior — a no-input playout never plays a card,
   so a balance patch to MERCY ODDS would move nothing and old records
   would silently certify under new card math. This record closes that
   gap: seed 6's organic auto-played spare match with ["twist", 1]
   played at the first between-rounds window. It exercises the announce
   line, the round-start resolution, and the replaced spare payout, so
   any change to any of them moves the stamp.

   The numbers below were CAPTURED by executing the record (rules.test.js
   asserts them; the witness Worker folds the fingerprint into its
   stamp). If twist behavior changes on purpose, re-capture deliberately
   and say so in the PR — these constants are the paper trail, not a
   cache. MERCY ODDS has no board effect and draws no RNG, which is what
   lets a twist be spliced into an organic record without disturbing a
   single downstream command. */
export const SHOWRUNNER_GOLDEN = {
  seed: 6,
  record: [
    ["twist", 1],
    ["move", 0, 2, 6], ["shoot", 0, 4], ["shoot", 1, 4], ["shoot", 2, 5], ["end"],
    ["move", 1, 5, 6], ["ow", 1], ["shoot", 2, 5], ["end"],
    ["move", 1, 6, 3], ["ow", 1], ["shoot", 2, 5], ["end"],
    ["shoot", 2, 5], ["end"],
    ["shoot", 2, 5], ["end"],
    ["shoot", 2, 5], ["end"],
    ["shoot", 2, 5], ["end"],
    ["shoot", 2, 3], ["spare"],
  ],
  result: "win",
  rating: 92,     // pre-spare 86, MERCY ODDS pays +6 — unclamped on purpose
  purse: 920,     // outcome constants are stamp inputs: rating is never a
                  // transcript line, so economics are pinned here explicitly
  lines: 52,
  fingerprint: "6495eab3",
};
