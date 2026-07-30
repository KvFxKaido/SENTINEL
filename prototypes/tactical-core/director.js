/* The house director — the reference chooser for showrunner twists.
   (Circuit roadmap step 4, the half that lives OUTSIDE the rules.)

   The rules core validates and resolves twists; it never chooses them.
   This module is the choosing, kept deliberately small: deterministic,
   reactive, no RNG — it reads the same visible state the player reads
   (design philosophy #1: shared state must be visible) and plays a card
   when the drama asks for one. Given the same board at the same window
   it always makes the same call, which is what makes it explainable
   during development and boring to debug. A fixed scripted schedule
   would be weather with better stationery; a random one would be a
   lottery. Neither is a showrunner.

   It is a CLIENT of the rules, exactly like the player-input adapter:
   it issues `playTwist` through the same doorway, the dispatcher can
   refuse it, and whatever it commits lands in S.record — so the witness
   protocol certifies its choices without ever knowing it exists. The
   campaign brain inherits this seat later; the interface is one
   function.

   Renderers call directorTick() whenever a between-rounds window opens
   (in practice: on the first changed() after the turn returns to the
   player — enemyTurn emits the turn event while S.busy still holds, so
   the event itself is too early). Tests script their own records
   instead; the director is product behavior, not test machinery. */

import { S, living, playTwist, twistWindow, MORALE } from "./rules.js";

// Priorities, in order — one card in the deck today, so one rule:
//
//   MERCY ODDS: a fighter is one bad beat from kneeling (a single crit
//   ends anyone at or below MORALE.crit). Price the mercy BEFORE it
//   lands: the card resolves next round, so the announcement reaches
//   the player while the yield is still a forecast, not a fact.
//
// Returns the cardId it committed, or null if the house stays quiet.
export function directorTick() {
  if (!twistWindow()) return null;
  if (S.record.some(c => c[0] === "twist")) return null;   // one card, already played
  if (living("ho").some(u => !u.yielded && u.morale <= MORALE.crit)) {
    playTwist(1);
    return S.pendingTwist;   // 1 if the card committed; null if refused
  }
  return null;
}
