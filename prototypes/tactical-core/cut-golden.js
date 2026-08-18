/* The darkness golden — the integrity verb, pinned as behavior
   (`what_we_owe_each_other.md` §9 and §10 step 5, half A).

   The base golden cannot exercise CUT because nobody on its player side
   acts. This seed-24 record is organic play from the dealt board. The first
   round reaches rating 80; at the top of the second, VESPER spends their
   whole activation to commit:

     VESPER CUTS THE FEED — RATING 80 FROZEN. THE REST GOES DARK.

   The local record continues. After the cut, KOA fires, SABLE sets
   overwatch, the crew fires back, both remaining operatives shoot, SYN-1
   yields, and the squad spares them. Every one of those public-meter
   opportunities scores nothing: final rating is still the 80 that aired,
   and the unchanged purse formula pays 800 credits. The aftermath points
   straight back to command 6 so a settled holder need not rediscover the
   fact independently.

   The numbers below were CAPTURED by replaying the record through the
   public dispatcher. If CUT behavior changes on purpose, re-capture
   deliberately and say so in the PR — these constants are the paper trail,
   not a cache. */
export const CUT_GOLDEN = {
  seed: 24,
  record: [
    ["move", 0, 2, 6], ["shoot", 0, 4],
    ["move", 1, 5, 6], ["shoot", 1, 5], ["shoot", 2, 5], ["end"],
    ["cut", 0],
    ["move", 1, 3, 4], ["shoot", 1, 3],
    ["move", 2, 6, 6], ["ow", 2], ["end"],
    ["move", 0, 2, 4], ["shoot", 0, 3], ["shoot", 1, 3], ["spare"],
  ],
  result: "win",
  rating: 80,
  purse: 800,
  lines: 21,
  fingerprint: "3fd1ffac",
  aftermath: { feedCut: { commandIndex: 6 } },
  ledger: { walked: 1, finished: 0, lost: 0 },
};
