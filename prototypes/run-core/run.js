/* ============================================================
   SENTINEL run layer — what survives the door.

   The third module, and deliberately a third one. `tactical-core` is
   trustworthy because it has no host; the walkable room is honest
   because it has no rules import. Run state smuggled into either would
   cost the property that makes both believable, so it lives here: no
   DOM, no rules import, no clock of its own, and storage arrives
   through a binding the way `io` does in the rules core.

   ---- What a run is, and what it deliberately is not ----------------

   A run accumulates the CONSEQUENCES of cards. It does not change what
   a card IS.

   That line is load-bearing. The witness Worker replays a match from
   its seed alone — `seed + record IS the match` is written into the
   rules core, the Worker's own docs, and the content-addressed key
   every filed record lives under. The moment a run hands a wounded
   roster into the yard, a certified card becomes a claim the edge
   cannot check, and the room's own verdict ("EDGE DISPUTES THE FEED —
   STRUCK") starts firing on honest play.

   So v1 persists purse, the mercy ledger, and who went down — and the
   next card is still fought by the canonical three at full strength.
   Wounds are a RECORD, not a modifier.

   Making them a modifier is a real and wanted fork, and it is a
   doctrine change rather than a feature: `restart(seed, roster)`,
   `replayMatch(seed, commands, roster)`, a roster in the certify body,
   the roster folded into the rules stamp and the content address.
   That decision deserves its own PR and its own argument. It is not
   something this module should smuggle in by being convenient.

   ---- The slate (season-lite) ---------------------------------------

   A run opened on a SLATE is a season (`architecture/
   circuit_season_loop.md`, Tier 1). The slate is an authored tour:
   an ordered list of entries, each carrying the faction framing that
   says what that particular card MEANS — who owns the venue, who
   sanctions the rules. The run holds the slate, points at the current
   entry, and banks what happened to each one: fought (a card), or
   passed (a declined entry, on the record with its framing).

   Nothing about this crosses the door. The card payload from the yard
   is unchanged; the witness certifies exactly what it certified
   yesterday. The framing banked with a fought card comes from the
   run's OWN slate, never from the payload — the seam does not get a
   new input to tamper with just because the season wants context.

   Wounds become CLOCKS, counted in slate positions — and passing is
   always legal. A fighter who went down is recovering; while any
   clock runs the roster is unfit and the deal is gated. What advances
   a clock is the SLATE, not the card: passing an entry advances the
   slate and every clock by one, at the entry's own cost (the purse
   not won, the framing on the record of the card you declined).
   Passing must stay legal precisely because clocks gate the deal —
   a clock counted in cards dealt would gate the only mechanism that
   heals it, and the season would deadlock (caught by both review
   bots on the season doc's first draft).

   Only BANKED cards advance the slate. A struck card is not a card:
   it moves no money, no mercy, no wounds — and no slate. The entry
   it was fought at remains the current entry, to be fought again or
   passed. Same reasoning as the rules stamp sitting below the struck
   return: what the edge disputed does not get to move the season.

   ---- What counts ---------------------------------------------------

   Inherited verbatim from the session ledger this replaces, because
   the policy was already right and only its lifetime was wrong:

     certified   — the edge replayed the record and agreed. Counts.
     unwitnessed — no witness reachable. Counts, and SAYS it counted
                   unwitnessed; an unverified truth labeled beats a
                   silent one.
     struck      — the edge replayed the record and disagreed. Does not
                   count, and is tallied so the surface can say how
                   often that happened.

   ---- The rules stamp -----------------------------------------------

   A certificate carries the fingerprint of the rules that produced it.
   If that changes mid-run, the numbers already banked were earned under
   different rules. This module notices and says so rather than
   presenting one continuous total across a rules boundary — the same
   refusal-to-round-off the yard makes when it labels the shared archive
   ARCHIVE instead of CAREER.
   ============================================================ */

// 2: the season joined the schema (slate, clocks, passes). A stored v1
// run takes the orphan path below — moved aside and said so, exactly the
// situation that path was built and tested for. Hydrating a v1 run with
// an empty season in place would be a silent migration wearing a default.
export const RUN_V = 2;
// The live key is deliberately NOT versioned. It used to be
// `sentinel.run.v${RUN_V}`, which made the orphan path below unreachable
// in the only situation it exists for: bumping RUN_V to 2 would point
// loadRun at an empty `sentinel.run.v2`, report a fresh run, and leave
// the real v1 run abandoned under a key nothing reads — never moved,
// never surfaced, and the README claiming otherwise (caught in review).
// One stable slot with the version carried IN the payload is what makes
// "nothing is silently dropped" a behaviour instead of a sentence.
export const RUN_KEY = "sentinel.run";
// A run closed by the player is archived here rather than dropped. One
// slot, last-closed-wins: enough that "I meant to keep that" is
// recoverable, not so much that this becomes an archive with no reader.
export const CLOSED_KEY = "sentinel.run.closed";
// A stored run from a DIFFERENT schema version is set aside under its own
// key instead of migrated or deleted. Silent migration is the failure the
// design philosophy names outright — if the shape changed, the honest move
// is a fresh run and a surface that says a run was set aside. One slot,
// same as CLOSED_KEY: a second orphan replaces the first.
export const ORPHAN_KEY = "sentinel.run.orphan";

// Bounds, so a malformed payload can enlarge a stat but never the state.
const MAX_NAME = 16;
const MAX_WOUNDED = 8;     // the yard fields three; this is slack, not a plan
const MAX_RATING = 100;    // rules.js clamps the crowd meter to 0..100
const MAX_PURSE = 10000;   // 100 rating x pursePerPoint 10, with an order of slack
const MAX_SIDE = 16;       // hostiles per card, generously
const RECENT = 12;         // cards kept in full on the run; older ones are totals only
const MAX_SLATE = 32;      // entries per season slate — a tour, not a calendar
const MAX_VENUE = 24;      // a venue name is a sign, not a paragraph
const MAX_CLOCK = 16;      // sanity bound for a stored clock, not the tuning

// How many slate positions a down fighter recovers for. This is the
// number the season doc says wants the lite prototype rather than the
// doc — tune it here, in one place, when play says so (open question 2:
// recovery economics).
export const WOUND_CLOCK = 2;

// ---- storage binding ---------------------------------------------
// Inert by default, exactly like the rules core's io: this module is
// fully usable — and fully testable — with no browser at all.
const store = {
  read: () => null,
  write: () => {},
  remove: () => {},
};
export function bindStore(next) { Object.assign(store, next); }

/* ---- shape -------------------------------------------------------
   `at` is always injected. Nothing here reads the clock, for the same
   reason the rules core does not: a module that consults the clock
   cannot be tested for what it does at a given moment, only observed. */
export function openRun(at) {
  return {
    v: RUN_V,
    opened: at,
    cards: 0,
    wins: 0,
    purse: 0,
    best: 0,            // best rating posted this run
    streak: 0,          // consecutive wins, current
    longest: 0,         // longest win streak this run
    mercy: { walked: 0, finished: 0 },
    wounds: {},         // NAME -> times that operative went down
    struck: 0,          // cards the edge disputed — banked by nobody
    unwitnessed: 0,     // cards counted without certification
    rules: null,        // the rules stamp this run's numbers were earned under
    drift: null,        // { from, to, at } once the stamp changes mid-run
    recent: [],         // newest first, capped at RECENT
    season: null,       // a slate, a position, clocks — or null: a plain run
  };
}

/* ---- the slate ----------------------------------------------------
   Authored data, validated at this boundary the way cards are: the run
   has to survive a slate it did not write. `host` and `sanction` are
   required-but-nullable on purpose — an author must SAY nobody owns the
   venue or nobody sanctions the card, not merely forget to mention it.
   Explicit over implicit; a missing key is a missing decision. */
function entryValid(e) {
  if (!e || typeof e !== "object") return false;
  if (typeof e.venue !== "string" || e.venue.length < 1 || e.venue.length > MAX_VENUE) return false;
  if (e.host !== null && !isName(e.host)) return false;
  if (e.sanction !== null && !isName(e.sanction)) return false;
  return true;
}

export function slateValid(slate) {
  if (!slate || typeof slate !== "object") return false;
  if (!isName(slate.id)) return false;
  if (!Array.isArray(slate.entries)) return false;
  if (slate.entries.length < 1 || slate.entries.length > MAX_SLATE) return false;
  return slate.entries.every(entryValid);
}

/* A season is a run opened on a slate — same shape, same storage, same
   close verb; season close IS run close. Returns null rather than a
   half-built season when the slate is not a slate: the surface loads
   authored data, and authored data is not a trusted input either.

   The entries are copied field-by-field so the season holds exactly the
   three facts an entry is allowed to carry, not whatever else rode in on
   the author's object. After this, the slate never changes — the season
   moves through it; it does not edit it. */
export function openSeason(at, slate) {
  if (!slateValid(slate)) return null;
  const run = openRun(at);
  run.season = {
    slate: {
      id: slate.id,
      entries: slate.entries.map(e => ({ venue: e.venue, host: e.host, sanction: e.sanction })),
    },
    pos: 0,        // the current entry; entries.length means the slate is complete
    passed: [],    // declined entries, each on the record with its framing
    clocks: {},    // NAME -> slate positions until that fighter is fit
  };
  return run;
}

const slateEntry = season =>
  season.pos < season.slate.entries.length ? season.slate.entries[season.pos] : null;

// The one copy of the season a reducer is allowed to write into. The
// slate itself is shared, not copied — it is immutable after openSeason
// and copying it per card would only make that sentence harder to check.
const copySeason = s => s === null ? null : {
  slate: s.slate,
  pos: s.pos,
  passed: s.passed.slice(),
  clocks: { ...s.clocks },
};

/* Advancing the slate is ONE thing, whichever verb did it: the position
   moves, and every clock ticks. "What advances the clock is the slate"
   is the season doc's law; keeping it in one helper is what keeps it a
   law instead of two agreeing coincidences. Cleared clocks are dropped,
   not stored as zeros — a zero clock is not a short clock, it is no
   clock, and sane() treats a stored zero as the junk it would be. */
function advance(season) {
  season.pos += 1;
  for (const name of Object.keys(season.clocks)) {
    const left = season.clocks[name] - 1;
    if (left > 0) season.clocks[name] = left;
    else delete season.clocks[name];
  }
}

/* Derived in one place, like summary(): the surface and the door both
   ask "may the deal happen", and they must get the same answer. */
export function fitness(run) {
  const clocks = run && run.season
    ? Object.entries(run.season.clocks)
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    : [];
  return { fit: clocks.length === 0, clocks };
}

const isName = s =>
  typeof s === "string" && s.length > 0 && s.length <= MAX_NAME;

const intIn = (n, lo, hi) =>
  Number.isInteger(n) && n >= lo && n <= hi;

// The slate stamp a banked (or struck) card carries in `recent`.
const stampValid = st =>
  st !== null && typeof st === "object"
  && intIn(st.idx, 0, MAX_SLATE - 1)
  && entryValid(st);

/* ---- what a card must look like before a run believes it ----------
   The room validates the seam payload before it gets here, and this
   validates again at its own boundary. That is not redundant: the room
   is checking "did the yard answer the question I asked", and this is
   checking "is this a thing a run can be built out of". Two different
   claims, and this module is the one that has to survive a caller it
   did not write. */
export function cardValid(card) {
  if (!card || typeof card !== "object") return false;
  if (typeof card.seed !== "string" || !/^[0-9a-f]{1,8}$/.test(card.seed)) return false;
  if (card.result !== "win" && card.result !== "loss") return false;
  if (!intIn(card.rating, 0, MAX_RATING)) return false;
  if (!intIn(card.purse, 0, MAX_PURSE)) return false;
  if (!["certified", "unwitnessed", "struck"].includes(card.cert)) return false;
  const l = card.ledger;
  if (!l || typeof l !== "object") return false;
  if (!intIn(l.walked, 0, MAX_SIDE)) return false;
  if (!intIn(l.finished, 0, MAX_SIDE)) return false;
  if (!intIn(l.lost, 0, MAX_SIDE)) return false;
  if (!Array.isArray(card.down) || card.down.length > MAX_WOUNDED) return false;
  if (!card.down.every(isName)) return false;
  // The yard counts the bodies and also names them. The count is what the
  // edge certifies; the names are the yard's own word (the certificate
  // carries `lost` as a number and nothing else). Requiring them to agree
  // is the only check available here, and it is worth having: a renderer
  // that miscounts its own dead fails closed instead of writing a run
  // whose wound tally disagrees with its own card count.
  if (card.down.length !== l.lost) return false;
  if (card.rules !== null && card.rules !== undefined && typeof card.rules !== "string") return false;
  if (typeof card.at !== "string" || !card.at) return false;
  return true;
}

/* ---- the reducer -------------------------------------------------
   Pure: takes a run, returns a new one. Never mutates its input, which
   is what lets a test assert on both sides of a single call and what
   keeps a rejected card from leaving a half-applied run behind.

   Two different negatives, kept apart on purpose:

     accepted:false — this is not a card. A caller bug or a tampered
                      payload; the run is returned untouched and the
                      surface should say something is wrong.
     counted:false  — this IS a card, and the edge struck it. Expected,
                      survivable, and tallied.

   Collapsing them into one boolean would make a renderer bug look
   exactly like an honest dispute, which is the failure the whole
   certification chain exists to prevent. */
export function applyCard(run, card) {
  if (!run || run.v !== RUN_V) {
    return { run, accepted: false, counted: false, why: "run is not this schema version" };
  }
  if (!cardValid(card)) {
    return { run, accepted: false, counted: false, why: "card is not a shape a run can bank" };
  }

  // Season gates, both of them accepted:false on purpose. The room gates
  // the deal at the door — a card arriving here while the slate is done
  // or the roster is unfit means the room dealt when the season said not
  // to, and that is a caller bug, not a countable outcome. Same contract
  // as a malformed payload: the run is returned untouched and the seam
  // harness's "the room never hits accepted:false" claim covers this too.
  if (run.season) {
    if (slateEntry(run.season) === null) {
      return { run, accepted: false, counted: false, why: "the slate is complete — nothing left to fight" };
    }
    if (!fitness(run).fit) {
      return { run, accepted: false, counted: false, why: "the deal was gated — the roster is unfit" };
    }
  }

  const next = {
    ...run,
    mercy: { ...run.mercy },
    wounds: { ...run.wounds },
    recent: run.recent.slice(),
    season: copySeason(run.season),
  };

  const entry = {
    seed: card.seed,
    result: card.result,
    rating: card.rating,
    purse: card.purse,
    cert: card.cert,
    walked: card.ledger.walked,
    finished: card.ledger.finished,
    down: card.down.slice(),
    at: card.at,
  };
  // The framing comes from the run's OWN slate, never from the payload.
  // A struck card is stamped too — it was fought at this entry, and the
  // run's record should say where — but only a banked card will move the
  // position below.
  if (run.season) {
    const e = slateEntry(run.season);
    entry.slate = { idx: run.season.pos, venue: e.venue, host: e.host, sanction: e.sanction };
  }
  next.recent = [entry, ...next.recent].slice(0, RECENT);

  if (card.cert === "struck") {
    // A disputed card is not a card. It moves no money, no mercy and no
    // wounds — but the run counts that it happened, because a run that
    // quietly discarded them would look identical to one that never had
    // any, and those are very different runs.
    next.struck += 1;
    return { run: next, accepted: true, counted: false, why: "the edge disputed this card" };
  }

  // The stamp is adopted from the first card that carries one, and after
  // that a change is recorded rather than absorbed. Only the FIRST drift
  // is kept: `from` must stay the stamp the run's banked numbers were
  // actually earned under, and overwriting it on every subsequent card
  // would quietly rewrite that history.
  //
  // BELOW the struck return, not above it (caught in review). A disputed
  // card banks nothing, so letting it define the run's provenance meant a
  // first struck card under stamp A set rules=A, and the first card that
  // actually counted — under B — then reported drift A→B, even though
  // every banked number in the run was earned under B. Only banked cards
  // get to say what the run's numbers were earned under.
  if (typeof card.rules === "string") {
    if (next.rules === null) next.rules = card.rules;
    else if (next.rules !== card.rules && next.drift === null) {
      next.drift = { from: next.rules, to: card.rules, at: card.at };
    }
  }

  next.cards += 1;
  next.purse += card.purse;
  next.best = Math.max(next.best, card.rating);
  next.mercy.walked += card.ledger.walked;
  next.mercy.finished += card.ledger.finished;
  for (const name of card.down) {
    next.wounds[name] = (next.wounds[name] ?? 0) + 1;
  }
  if (card.cert === "unwitnessed") next.unwitnessed += 1;
  if (card.result === "win") {
    next.wins += 1;
    next.streak += 1;
    next.longest = Math.max(next.longest, next.streak);
  } else {
    next.streak = 0;
  }

  // A banked card moves the season: the slate advances (a no-op for the
  // clocks — the fitness gate above means none were running), and THEN
  // the card's own dead start their clocks, so a fresh wound counts its
  // recovery from the position after the card that caused it.
  if (next.season) {
    advance(next.season);
    for (const name of card.down) next.season.clocks[name] = WOUND_CLOCK;
  }
  return { run: next, accepted: true, counted: true, why: null };
}

/* ---- passing ------------------------------------------------------
   The season's second verb, and the only one that is ALWAYS legal while
   the slate has entries left — fit or unfit, that is the point. Passing
   is how a wounded roster heals (the clocks tick on advance) and how a
   fit one rests, and its cost is the record itself: the entry's framing
   is banked with the pass, so the card you declined is a fact of the
   season, not an absence from it.

   Returns {run, accepted, why} — no `counted`, because there is no edge
   verdict to count. A pass is the run's own act; nothing about it can
   be disputed, so the two-negatives distinction has nothing to
   distinguish. */
export function applyPass(run, at) {
  if (!run || run.v !== RUN_V) {
    return { run, accepted: false, why: "run is not this schema version" };
  }
  if (!run.season) {
    return { run, accepted: false, why: "a run without a slate has nothing to pass" };
  }
  const entry = slateEntry(run.season);
  if (entry === null) {
    return { run, accepted: false, why: "the slate is complete — nothing left to pass" };
  }
  if (typeof at !== "string" || !at) {
    return { run, accepted: false, why: "a pass needs to know when it happened" };
  }
  const next = { ...run, season: copySeason(run.season) };
  next.season.passed = [
    ...next.season.passed,
    { idx: next.season.pos, venue: entry.venue, host: entry.host, sanction: entry.sanction, at },
  ];
  advance(next.season);
  return { run: next, accepted: true, why: null };
}

/* ---- reading a stored run ----------------------------------------
   Three outcomes, all of them named, none of them silent:

     fresh    — nothing stored; a run opens here
     restored — a stored run of this schema version
     orphaned — something stored that this schema cannot read. It is
                MOVED, not dropped, and the caller is told so it can
                say so on the surface. */
export function loadRun(at) {
  let raw;
  try { raw = store.read(RUN_KEY); } catch { raw = null; }
  if (raw === null || raw === undefined) return { run: openRun(at), how: "fresh" };

  let parsed = null;
  try { parsed = JSON.parse(raw); } catch { parsed = null; }
  if (parsed && parsed.v === RUN_V && sane(parsed)) {
    return { run: parsed, how: "restored" };
  }
  try {
    store.write(ORPHAN_KEY, typeof raw === "string" ? raw : JSON.stringify(raw));
    store.remove(RUN_KEY);
  } catch { /* a storage that refuses to write still gets a working run */ }
  return { run: openRun(at), how: "orphaned" };
}

// Structural check on a restored run. Storage is editable by hand and
// shared with every other page on the origin; a run that arrives with a
// string where a number belongs must be orphaned, not rendered.
//
// This goes all the way INTO the collections rather than stopping at
// "is it an array". Everything here reaches a surface, and a surface
// that renders whatever storage happened to contain is a surface that
// renders whatever anything on this origin decided to put there.
function sane(r) {
  const ints = ["cards", "wins", "purse", "best", "streak", "longest", "struck", "unwitnessed"];
  if (!ints.every(k => Number.isInteger(r[k]) && r[k] >= 0)) return false;
  if (typeof r.opened !== "string") return false;
  // non-negative, not merely integral: a hand-edited {walked:-1} restored
  // fine and rendered a -100% mercy rate, which is the made-up number this
  // module refuses to print elsewhere (caught in review)
  if (!r.mercy || !intIn(r.mercy.walked, 0, Number.MAX_SAFE_INTEGER)
      || !intIn(r.mercy.finished, 0, Number.MAX_SAFE_INTEGER)) return false;
  if (!r.wounds || typeof r.wounds !== "object" || Array.isArray(r.wounds)) return false;
  if (!Object.keys(r.wounds).every(isName)) return false;
  if (!Object.values(r.wounds).every(n => Number.isInteger(n) && n >= 0)) return false;
  if (!Array.isArray(r.recent) || r.recent.length > RECENT) return false;
  if (!r.recent.every(c =>
    c && typeof c === "object"
    && typeof c.seed === "string"
    && (c.result === "win" || c.result === "loss")
    && intIn(c.rating, 0, MAX_RATING)
    && intIn(c.purse, 0, MAX_PURSE)
    && ["certified", "unwitnessed", "struck"].includes(c.cert)
    && Array.isArray(c.down) && c.down.every(isName)
    && (c.slate === undefined || stampValid(c.slate))
  )) return false;
  // The season, when there is one, all the way in — same reasoning as the
  // collections above: every field here reaches the room's surface or
  // gates its door.
  if (!("season" in r)) return false;
  if (r.season !== null) {
    const s = r.season;
    if (typeof s !== "object" || Array.isArray(s)) return false;
    if (!slateValid(s.slate)) return false;
    if (!intIn(s.pos, 0, s.slate.entries.length)) return false;
    if (!Array.isArray(s.passed) || s.passed.length > s.pos) return false;
    if (!s.passed.every(p => p && typeof p === "object"
      && intIn(p.idx, 0, s.slate.entries.length - 1)
      && entryValid(p)
      && typeof p.at === "string" && p.at.length > 0)) return false;
    if (!s.clocks || typeof s.clocks !== "object" || Array.isArray(s.clocks)) return false;
    if (!Object.keys(s.clocks).every(isName)) return false;
    // 1, not 0: advance() drops a cleared clock, so a stored zero was
    // written by something other than this module
    if (!Object.values(s.clocks).every(n => intIn(n, 1, MAX_CLOCK))) return false;
    // The spine's own arithmetic. Every banked card and every pass moves
    // the position exactly once, and nothing else ever moves it — a run
    // whose books do not balance was not kept by this module.
    if (r.cards + s.passed.length !== s.pos) return false;
  }
  if (r.rules !== null && typeof r.rules !== "string") return false;
  if (r.drift !== null && (typeof r.drift !== "object"
    || typeof r.drift.from !== "string" || typeof r.drift.to !== "string")) return false;
  if (r.wins > r.cards) return false;
  return true;
}

export function saveRun(run) {
  try { store.write(RUN_KEY, JSON.stringify(run)); return true; }
  catch { return false; }   // private mode, quota, a user who said no
}

/* Close the run and open a fresh one. The closed run is archived rather
   than deleted: this is the one destructive verb the surface exposes, and
   it should not be the only thing here that cannot be walked back.

   Which is exactly why the archive is not best-effort. It used to be —
   the write was wrapped in a bare catch and the live slot was overwritten
   regardless, so a storage that accepted the one-byte startup probe but
   refused a second full run would lose the run from BOTH slots while the
   panel said "ARCHIVED" (caught in review). The destructive half now only
   happens if the preserving half actually worked.

   And "actually worked" is read back rather than inferred from the write
   not throwing. A store that silently drops writes — the inert default
   here is one — would otherwise report a successful archive of nothing. */
export function closeRun(run, at) {
  let archived = false;
  try {
    const blob = JSON.stringify({ ...run, closed: at });
    store.write(CLOSED_KEY, blob);
    archived = store.read(CLOSED_KEY) === blob;
  } catch { archived = false; }
  // refused: the run stays open and live, and the caller is told why.
  // A player who cannot archive is better off with the run they have.
  if (!archived) return { run, archived: false, closed: false };
  const fresh = openRun(at);
  return { run: fresh, archived: true, closed: true, saved: saveRun(fresh) };
}

export function readClosed() {
  try {
    const raw = store.read(CLOSED_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

/* ---- the surface's numbers, derived in one place -----------------
   The room renders these; it does not compute them. Anything that could
   be got wrong twice is got right once here. */
export function summary(run) {
  const losses = run.cards - run.wins;
  const wounded = Object.entries(run.wounds)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const f = fitness(run);
  return {
    cards: run.cards,
    record: `${run.wins}–${losses}`,
    purse: run.purse,
    best: run.best,
    streak: run.streak,
    longest: run.longest,
    walked: run.mercy.walked,
    finished: run.mercy.finished,
    // The run's whole thesis in one number: across every card, how often
    // a yield was honored rather than collected on. Null when nobody has
    // yielded yet — a 0/0 ratio rendered as a percentage is a made-up
    // fact, and this repo has already paid for one of those.
    mercyRate: (run.mercy.walked + run.mercy.finished) === 0
      ? null
      : run.mercy.walked / (run.mercy.walked + run.mercy.finished),
    wounded,
    struck: run.struck,
    unwitnessed: run.unwitnessed,
    drift: run.drift,
    // The season's numbers, or null for a plain run. `next` is the
    // current entry's framing — what the door's card display shows —
    // and null once the slate is complete. The room renders these and
    // gates the deal on `fit`; it computes neither.
    season: !run.season ? null : {
      slate: run.season.slate.id,
      pos: run.season.pos,
      length: run.season.slate.entries.length,
      complete: slateEntry(run.season) === null,
      passes: run.season.passed.length,
      passed: run.season.passed,
      next: slateEntry(run.season),
      fit: f.fit,
      clocks: f.clocks,
    },
  };
}
