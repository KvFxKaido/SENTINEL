/* The extraction golden — the first explicit two-person record verb,
   pinned as behavior (`what_we_owe_each_other.md` §4 and §10 step 2).

   The base golden cannot exercise DRAG: nobody on its player side acts.
   This seed-1 record is organic play from the dealt board. KOA falls at
   (2,9), SYN-3 takes overwatch, and the next round commits exactly the
   sentence the vocabulary was built to say:

     SABLE DRAGS KOA CLEAR — (2,9) → (3,9)

   SYN-3 fires on the first shared step and lands a critical hit. SABLE
   gets KOA one tile over, survives the reaction, then falls in the
   hostile turn. The drag did not heal anybody or save the match. It
   still changed the board, spent the activation and safety, paid its
   one modest crowd beat, and stayed worth recording.

   The numbers below were CAPTURED by replaying the record through the
   public dispatcher. Transcript, outcome, rating, and final positions
   are all pinned because each is a different part of what DRAG means;
   a line without the moved body would be theater, and moved state
   without the line would be a hidden verb. */
export const DRAG_GOLDEN = {
  seed: 1,
  record: [
    ["move", 1, 2, 9], ["move", 2, 3, 9],
    ["end"], ["end"], ["end"], ["end"],
    ["drag", 2, 1, 4, 9], ["end"],
  ],
  result: "loss",
  rating: 41,
  purse: 410,
  lines: 30,
  fingerprint: "e9e0a018",
  derived: [
    {
      kind: "extraction",
      actor: "SABLE",
      beneficiary: "KOA",
      commandIndex: 6,
      underFire: true,
      reached: true,
    },
  ],
  positions: [
    { name: "VESPER", x: 1, y: 9, hp: 0, alive: false },
    { name: "KOA", x: 3, y: 9, hp: 0, alive: false },
    { name: "SABLE", x: 4, y: 9, hp: 0, alive: false },
  ],
};
