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

   So the run persists purse, the mercy ledger, and who went down — and
   the next card is still fought at full strength. The run may now choose
   WHICH three owned people cross the door, but wounds remain a RECORD,
   not a modifier.

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
   always legal. A recovering fighter makes a LINEUP unfit only while
   fielded; benching them is now a real front-office choice. What
   advances a clock is the SLATE, not the card: passing or banking an
   entry advances every clock by one. Passing must stay legal because
   a run without a fit replacement still needs a way to heal rather
   than deadlock (caught by both review bots on the season doc's first
   draft).

   Only BANKED cards advance the slate. A struck card is not a card:
   it moves no money, no mercy, no wounds — and no slate. The entry
   it was fought at remains the current entry, to be fought again or
   passed. Same reasoning as the rules stamp sitting below the struck
   return: what the edge disputed does not get to move the season.

   ---- Pairwise mercy ------------------------------------------------

   An extraction is a rules-derived fact. Its grade says who vouches: the
   edge's filed replay, or the squad's claim backed by a preserved local
   record. What that fact MEANS after the card is the run's policy: the
   rescued person OWES the rescuer A LIFE. The relationship points back to
   the command, stays directional, and has a lifecycle rather than a score.
   Repeated rescues do not climb a meter or replace the first active origin.

   Its first obligation lives entirely in the room. A debtor may dedicate
   an otherwise ordinary pass to a recovering creditor: that clock moves
   two stops, every other clock moves one, and the debt becomes fulfilled
   on the pass's authored slate stamp. The plain pass remains legal. No
   relationship state crosses the door or changes the `{name, hp}` card.

   ---- The purse spends (season-lite) --------------------------------

   Purse stopped being a scoreboard the moment there was somewhere to
   spend it. A run now carries what it has BOUGHT, and the only thing
   it is allowed to buy is flair.

   That is not a content decision, it is the tier boundary, and this
   module is where it stops being a promise. `sentinel_circuit_design.md`
   splits gear by slot: head, torso, legs, primary and sidearm carry
   VERBS; drape and patch carry none, by law, because "the two most
   socially loud slots being mechanically silent makes cosmetic power
   creep impossible by architecture instead of by discipline". A verb
   is roster state the yard would have to be told about, and roster
   state crossing the door is the doctrine change season-lite exists
   NOT to make. So FLAIR_SLOTS is the whole shop, and an item declaring
   any other slot is refused at this boundary — the same refusal a
   malformed card gets, for a much bigger reason.

   Nothing bought crosses the seam either. The yard is dealt a seed and
   nothing else; a fighter in a new hood fights precisely the card they
   would have fought naked, and the witness certifies exactly what it
   certified yesterday.

   Purse is kept as TOTAL EARNED and spending is tracked beside it, so
   the balance is derived rather than stored. A run that decremented
   purse could not tell you what it had won — the season's headline
   number would quietly become "what you have left", and every card that
   paid for a hood would look like a card that never paid at all.

   A purchase is permanent and a slot is bought once per fighter. There
   is no resale, because the point of the register is history: "the
   squad you dress is the squad you protect", and gear you can liquidate
   for the purse back is inventory, not history. An empty hook is
   information too — it says you never bought one.

   ---- What counts ---------------------------------------------------

   The original session-ledger policy remains, with one banking-time split
   so chosen witness loss cannot masquerade as an accident:

     certified   — the edge replayed the record and agreed. Counts.
     dark        — the squad deliberately withheld the record. Counts,
                   but chosen darkness remains distinct from an accident.
     unwitnessed — no durable filed attestation is available: the witness
                   was unreachable, its infrastructure failed, or the
                   archive refused the write. Counts, and SAYS it counted
                   unwitnessed; an unverified truth labeled beats a silent
                   one.
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

// 2: the season joined the schema (slate, clocks, passes).
// 3: the purse joined it (spent, bought).
// 4: the faction door joined it (owned people, origins, lineup).
// 5: replay-derived pairwise events joined it (stable ids + certified source).
// 6: named pairwise relationships joined it (lifecycle + room obligation).
// 7: chosen darkness, the independent chronicle, and claim-grade provenance.
// A stored run of any older
// version takes the orphan path below — moved aside and said so, exactly
// the situation that path was built and tested for. Hydrating a v6 run
// with invented dark counts and provenance would be a silent migration
// wearing defaults, same as it was one version ago.
export const RUN_V = 7;
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
const MAX_LABEL = 24;      // an item's name is a label on a hook, not a paragraph
const MAX_STOCK = 12;      // items a shop may offer at once — a case, not a catalogue
const MAX_BOUGHT = 24;     // purchases per run — a rack, not a warehouse
const MAX_ROSTER = 4;      // this slice proves one real bench behind three slots
const MAX_PERSON_ID = 24;  // stable authored ids stay diffable and URL-safe
const MAX_REASON = 160;    // one authored sentence about why this person is here
const MAX_DERIVED_PER_CARD = 1024; // one event per command is the hard wire ceiling

// The certified match still fields exactly three. This copy belongs to the
// run boundary and is pinned against tactical-core's ROSTER_SLOTS in the seam
// harness; importing the rules here would erase the wall this module exists
// to keep.
export const LINEUP_SLOTS = 3;
export const FULL_STRENGTH = 10;

// How many slate positions a down fighter recovers for. This is the
// number the season doc says wants the lite prototype rather than the
// doc — tune it here, in one place, when play says so (open question 2:
// recovery economics).
export const WOUND_CLOCK = 2;
export const DEDICATED_RECOVERY = 2;

/* The entire shop, and the reason it is short. `sentinel_circuit_design.md`
   sorts gear slots by whether they carry VERBS: head (sensing), torso
   (defense, sponsor rigs), legs (movement), primary (ammo) and sidearm
   all do; drape and patch are "mechanically inert by law". A verb is
   roster state, and roster state reaching the yard is the doctrine change
   this tier is defined by not making — so these two are what a purse may
   buy, and every other slot is a Tier 2 item wearing a lite item's shape.

   Frozen because it is law rather than configuration: a caller that could
   push "torso" onto this array could buy a verb, which is the one thing
   the boundary below exists to refuse. */
export const FLAIR_SLOTS = Object.freeze(["drape", "patch"]);

// ---- storage binding ---------------------------------------------
// Inert by default, exactly like the rules core's io: this module is
// fully usable — and fully testable — with no browser at all.
const store = {
  read: () => null,
  write: () => {},
  remove: () => {},
};
export function bindStore(next) { Object.assign(store, next); }

/* ---- the owned roster ---------------------------------------------
   The yard knows tactical names. The run knows people.

   A person id is the durable key future pairwise history will point at;
   `name` is only the alias dealt to a particular match. `origin` is copied
   into the run when that person enters it, so a later content edit cannot
   rewrite why they were here. `body` is presentation metadata: the room
   needs it to stage an owned person, while the certified snapshot below
   deliberately strips it back to exactly {name, hp}.

   The default is the prototype's authored Court 01 crew. A host may provide
   another roster seed to openRun/openSeason/loadRun; it must pass the same
   boundary. NIX's SYN canvas is an explicit body loan until original art
   exists, not an asset fallback — the identity and the loan are both stored. */
const DEFAULT_ROSTER = Object.freeze({
  people: Object.freeze([
    Object.freeze({
      id: "vesper", name: "VESPER", body: "vesper",
      origin: Object.freeze({
        source: "kestrel-founding-lineup", faction: null,
        reason: "Opened Court 01 with the house.",
      }),
    }),
    Object.freeze({
      id: "koa", name: "KOA", body: "koa",
      origin: Object.freeze({
        source: "kestrel-founding-lineup", faction: null,
        reason: "Opened Court 01 with the house.",
      }),
    }),
    Object.freeze({
      id: "sable", name: "SABLE", body: "sable",
      origin: Object.freeze({
        source: "kestrel-founding-lineup", faction: null,
        reason: "Opened Court 01 with the house.",
      }),
    }),
    Object.freeze({
      id: "nix", name: "NIX", body: "syn",
      origin: Object.freeze({
        source: "ember-winter-entry", faction: "ember_colonies",
        reason: "The north valley entered a defender because winter was bad.",
      }),
    }),
  ]),
  lineup: Object.freeze(["vesper", "koa", "sable"]),
});

const PERSON_ID = /^[a-z][a-z0-9-]{0,23}$/;
const BODY_ID = /^[a-z][a-z0-9-]{0,23}$/;
const FACTION_ID = /^[a-z][a-z0-9_]{0,23}$/;
const TACTICAL_NAME = /^[A-Z0-9][A-Z0-9-]{0,15}$/;
const PERSON_KEYS = ["id", "name", "body", "origin"];
const ORIGIN_KEYS = ["source", "faction", "reason"];
const ROSTER_KEYS = ["people", "lineup"];

const exactKeys = (obj, keys) =>
  Object.keys(obj).length === keys.length && Object.keys(obj).every(k => keys.includes(k));

const isPersonId = id =>
  typeof id === "string" && id.length <= MAX_PERSON_ID && PERSON_ID.test(id);

function personValid(person) {
  if (!person || typeof person !== "object" || Array.isArray(person)) return false;
  if (!exactKeys(person, PERSON_KEYS)) return false;
  if (!isPersonId(person.id)) return false;
  if (typeof person.name !== "string" || !TACTICAL_NAME.test(person.name)) return false;
  if (typeof person.body !== "string" || !BODY_ID.test(person.body)) return false;
  const origin = person.origin;
  return !!origin && typeof origin === "object" && !Array.isArray(origin)
    && exactKeys(origin, ORIGIN_KEYS)
    && typeof origin.source === "string" && PERSON_ID.test(origin.source)
    && (origin.faction === null
      || (typeof origin.faction === "string" && FACTION_ID.test(origin.faction)))
    && typeof origin.reason === "string"
    && origin.reason.length > 0 && origin.reason.length <= MAX_REASON;
}

export function rosterValid(roster) {
  if (!roster || typeof roster !== "object" || Array.isArray(roster)) return false;
  if (!exactKeys(roster, ROSTER_KEYS)) return false;
  if (!Array.isArray(roster.people) || roster.people.length !== MAX_ROSTER) return false;
  if (!roster.people.every(personValid)) return false;
  const ids = roster.people.map(person => person.id);
  const names = roster.people.map(person => person.name);
  if (new Set(ids).size !== ids.length || new Set(names).size !== names.length) return false;
  return Array.isArray(roster.lineup)
    && roster.lineup.length === LINEUP_SLOTS
    && roster.lineup.every(id => typeof id === "string" && ids.includes(id))
    && new Set(roster.lineup).size === roster.lineup.length;
}

function copyRoster(roster) {
  return {
    people: roster.people.map(person => ({
      id: person.id,
      name: person.name,
      body: person.body,
      origin: {
        source: person.origin.source,
        faction: person.origin.faction,
        reason: person.origin.reason,
      },
    })),
    lineup: roster.lineup.slice(),
  };
}

export function personOf(run, id) {
  return run?.roster?.people?.find(person => person.id === id) ?? null;
}

export function fieldedRoster(run) {
  if (!run || !rosterValid(run.roster)) return null;
  return run.roster.lineup.map(id => {
    const person = personOf(run, id);
    return { name: person.name, hp: FULL_STRENGTH };
  });
}

export function setLineup(run, lineup) {
  if (!run || run.v !== RUN_V) {
    return { run, accepted: false, why: "run is not this schema version" };
  }
  const candidate = { people: run.roster.people, lineup };
  if (!rosterValid(candidate)) {
    return { run, accepted: false, why: "a lineup is three different people this run owns" };
  }
  return {
    run: { ...run, roster: { people: run.roster.people, lineup: lineup.slice() } },
    accepted: true,
    why: null,
  };
}

/* ---- shape -------------------------------------------------------
   `at` is always injected. Nothing here reads the clock, for the same
   reason the rules core does not: a module that consults the clock
   cannot be tested for what it does at a given moment, only observed. */
export function openRun(at, roster = DEFAULT_ROSTER) {
  if (!rosterValid(roster)) return null;
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
    wounds: {},         // stable person id -> times that person went down
    eventLedger: {},    // stable actor id -> rules-derived events, graded by author
    relationships: [],  // named directional facts, each pointing at one event
    struck: 0,          // cards the edge disputed — banked by nobody
    unwitnessed: 0,     // accidental witness/archive failures that still counted
    dark: 0,            // cards deliberately withheld from the Witness
    rules: null,        // the rules stamp this run's numbers were earned under
    drift: null,        // { from, to, at } once the stamp changes mid-run
    recent: [],         // newest first, capped at RECENT
    season: null,       // a slate, a position, clocks — or null: a plain run
    spent: 0,           // of the purse, on flair. purse stays TOTAL EARNED
    bought: [],         // the rack, in the order it filled
    roster: copyRoster(roster), // people + authored origins + current lineup ids
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
export function openSeason(at, slate, roster = DEFAULT_ROSTER) {
  if (!slateValid(slate)) return null;
  const run = openRun(at, roster);
  if (run === null) return null;
  run.season = {
    slate: {
      id: slate.id,
      entries: slate.entries.map(e => ({ venue: e.venue, host: e.host, sanction: e.sanction })),
    },
    pos: 0,        // the current entry; entries.length means the slate is complete
    passed: [],    // declined entries, each on the record with its framing
    clocks: {},    // stable person id -> slate positions until that person is fit
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
function advance(season, dedicatedRecovery = null) {
  season.pos += 1;
  for (const id of Object.keys(season.clocks)) {
    // A dedicated life-debt pass is recovery economics, not combat
    // arithmetic: this one clock advances by two while every other clock
    // still advances by the slate's ordinary one.
    const left = season.clocks[id] - (id === dedicatedRecovery ? DEDICATED_RECOVERY : 1);
    if (left > 0) season.clocks[id] = left;
    else delete season.clocks[id];
  }
}

/* Derived in one place, like summary(): the surface and the door both
   ask "may the deal happen", and they must get the same answer. */
export function fitness(run) {
  const clocks = run && run.season
    ? Object.entries(run.season.clocks)
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    : [];
  const fielded = new Set(run?.roster?.lineup ?? []);
  const fieldedClocks = clocks.filter(([id]) => fielded.has(id));
  return { fit: fieldedClocks.length === 0, clocks, fieldedClocks };
}

// "__proto__" is refused at the name-based wire too: it is an accessor on
// Object.prototype, not a tactical name. The durable ledgers below are keyed
// by stricter person ids, but refusing the hostile spelling at every authored
// or wire boundary keeps it from becoming somebody else's unsafe key.
const isName = s =>
  typeof s === "string" && s.length > 0 && s.length <= MAX_NAME
  && s !== "__proto__";

const MATCH_ID = /^[0-9a-f]{32}$/;
const DERIVED_KEYS = ["kind", "actor", "beneficiary", "commandIndex", "underFire", "reached"];

// The tactical wire stays tactical: names, not stable ids. The yard returns
// this array from its own completed session. A Worker replay authors
// certified grade; a surviving local chronicle entry lets the squad author
// claim grade. Translation happens once, in applyCard. The run never replays.
function derivedEventValid(event) {
  return !!event && typeof event === "object" && !Array.isArray(event)
    && exactKeys(event, DERIVED_KEYS)
    && event.kind === "extraction"
    && isName(event.actor) && isName(event.beneficiary)
    && event.actor !== event.beneficiary
    && intIn(event.commandIndex, 0, MAX_DERIVED_PER_CARD - 1)
    && typeof event.underFire === "boolean"
    && event.reached === true;
}

const matchIdValid = id => typeof id === "string" && MATCH_ID.test(id);

const intIn = (n, lo, hi) =>
  Number.isInteger(n) && n >= lo && n <= hi;

// The slate stamp a banked (or struck) card carries in `recent`.
const stampValid = st =>
  st !== null && typeof st === "object"
  && intIn(st.idx, 0, MAX_SLATE - 1)
  && entryValid(st);

/* A stored record must carry EXACTLY the fields this module writes. The
   field checks above say the required ones are right; this says nothing
   else rode along. It matters most on a purchase: one that restored
   carrying `verb: "dash"` would be Tier 2 roster state sitting inside a
   Tier 1 run, which is the boundary this whole register exists to hold
   (caught in review). Cards get the same treatment for the same reason —
   storage is one editable blob, not two. */
const CARD_KEYS = ["seed", "result", "rating", "purse", "cert",
  "walked", "finished", "down", "derivedEvents", "matchId", "at", "slate"];
const BOUGHT_KEYS = ["id", "name", "slot", "color", "who", "cost", "at", "slate"];
const EVENT_KEYS = ["kind", "beneficiary", "underFire", "reached", "grade", "origin", "at", "slate"];
const RELATIONSHIP_KEYS = ["kind", "from", "to", "grade", "origin", "status", "at"];
const PASS_KEYS = ["idx", "venue", "host", "sanction", "at"];
const DEDICATION_KEYS = ["kind", "from", "to"];
const onlyKeys = (obj, allowed) => Object.keys(obj).every(k => allowed.includes(k));

const originValid = (grade, origin) => {
  if (!origin || typeof origin !== "object" || Array.isArray(origin)) return false;
  if (grade === "certified") {
    return exactKeys(origin, ["matchId", "commandIndex"])
      && matchIdValid(origin.matchId)
      && intIn(origin.commandIndex, 0, MAX_DERIVED_PER_CARD - 1);
  }
  return grade === "claim"
    && exactKeys(origin, ["logId", "commandIndex"])
    && Number.isInteger(origin.logId) && origin.logId >= 0
    && intIn(origin.commandIndex, 0, MAX_DERIVED_PER_CARD - 1);
};

const originKey = (grade, origin) => grade === "certified"
  ? `certified:${origin.matchId}@${origin.commandIndex}`
  : `claim:${origin.logId}@${origin.commandIndex}`;

const sameOrigin = (aGrade, aOrigin, bGrade, bOrigin) =>
  aGrade === bGrade && originKey(aGrade, aOrigin) === originKey(bGrade, bOrigin);

// Framing equality against the authored entry. Restore uses this to
// enforce what the reducers wrote: every stamp and every pass carries
// the slate's own word at its index, because that is the only place
// applyCard and applyPass ever take framing from. A stored record that
// says otherwise was not written by this module.
const sameFraming = (rec, entry) =>
  rec.venue === entry.venue
  && rec.host === entry.host
  && rec.sanction === entry.sanction;

const sameStamp = (a, b) => !!a && !!b
  && a.idx === b.idx && sameFraming(a, b);

const dedicationShapeValid = dedication => !!dedication
  && typeof dedication === "object" && !Array.isArray(dedication)
  && exactKeys(dedication, DEDICATION_KEYS)
  && dedication.kind === "repay-the-life"
  && isPersonId(dedication.from) && isPersonId(dedication.to)
  && dedication.from !== dedication.to;

const copyRelationship = relationship => ({
  kind: relationship.kind,
  from: relationship.from,
  to: relationship.to,
  grade: relationship.grade,
  origin: { ...relationship.origin },
  status: relationship.status,
  at: relationship.at,
  ...(relationship.slate ? { slate: { ...relationship.slate } } : {}),
  ...(relationship.status === "fulfilled" ? {
    fulfilledAt: relationship.fulfilledAt,
    fulfilledSlate: { ...relationship.fulfilledSlate },
  } : {}),
});

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
  if (!["certified", "dark", "unwitnessed", "struck"].includes(card.cert)) return false;
  const l = card.ledger;
  if (!l || typeof l !== "object") return false;
  if (!intIn(l.walked, 0, MAX_SIDE)) return false;
  if (!intIn(l.finished, 0, MAX_SIDE)) return false;
  if (!intIn(l.lost, 0, MAX_SIDE)) return false;
  if (!Array.isArray(card.down) || card.down.length > MAX_WOUNDED) return false;
  if (!card.down.every(isName)) return false;
  if (!Array.isArray(card.derivedEvents)
      || card.derivedEvents.length > MAX_DERIVED_PER_CARD
      || !card.derivedEvents.every(derivedEventValid)) return false;
  // Certified grade is impossible without a filed origin. Dark and
  // unwitnessed cards have no public archive id; a struck card may have
  // reached /file before another field disagreed, but none of its facts
  // bank below.
  if (card.cert === "certified" && !matchIdValid(card.matchId)) return false;
  if ((card.cert === "dark" || card.cert === "unwitnessed") && card.matchId !== null) return false;
  if (card.cert === "struck" && card.matchId !== null && !matchIdValid(card.matchId)) return false;
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
export function applyCard(run, card, claimLogId = null) {
  if (!run || run.v !== RUN_V) {
    return { run, accepted: false, counted: false, why: "run is not this schema version" };
  }
  if (!cardValid(card)) {
    return { run, accepted: false, counted: false, why: "card is not a shape a run can bank" };
  }
  const hasClaimOrigin = claimLogId !== null && claimLogId !== undefined;
  if (hasClaimOrigin && (!Number.isInteger(claimLogId) || claimLogId < 0
      || !["dark", "unwitnessed"].includes(card.cert)
      || card.derivedEvents.length === 0)) {
    return { run, accepted: false, counted: false, why: "claim origin does not belong to this card" };
  }
  const dealt = fieldedRoster(run) ?? [];
  const idByDealtName = new Map(dealt.map((person, i) =>
    [person.name, run.roster.lineup[i]]));
  if (card.down.some(name => !idByDealtName.has(name))) {
    return { run, accepted: false, counted: false, why: "the card names someone this run did not field" };
  }
  if (card.derivedEvents.some(event =>
    !idByDealtName.has(event.actor) || !idByDealtName.has(event.beneficiary))) {
    return { run, accepted: false, counted: false, why: "a derived event names someone this run did not field" };
  }
  const downIds = card.down.map(name => idByDealtName.get(name));
  const translatedEvents = card.derivedEvents.map(event => ({
    event,
    actor: idByDealtName.get(event.actor),
    beneficiary: idByDealtName.get(event.beneficiary),
  }));

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
    eventLedger: Object.fromEntries(
      Object.entries(run.eventLedger).map(([id, events]) => [id, events.slice()])),
    relationships: run.relationships.map(copyRelationship),
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
    // Receipts keep the tactical wire. A certified event has a filed source;
    // a claim event is retained only after the caller supplies the id already
    // returned by the independent chronicle. A refused log append and every
    // struck card therefore retain an empty event receipt.
    derivedEvents: (card.cert === "certified" || hasClaimOrigin)
      ? card.derivedEvents.map(event => ({ ...event }))
      : [],
    matchId: card.matchId,
    at: card.at,
  };
  // `recent[].down` preserves the tactical names exactly as the card crossed
  // the yard wire. Only the durable wound and recovery ledgers translate that
  // receipt through the fielded lineup to stable person ids.
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

  // Bank rules-authored events; never compute one here and never replay the
  // record. Who vouches is the grade. The Worker authored the certified
  // array; on counted darkness/accident paths the yard authored the same
  // rules-core output and the supplied log id proves only that its full
  // record survived before this pointer was minted. A forged seam post can
  // therefore bank a CLAIM that the preserved record later falsifies. It can
  // never bank certification.
  const eventGrade = card.cert === "certified" ? "certified" : "claim";
  const bankableEvents = card.cert === "certified" || hasClaimOrigin ? translatedEvents : [];
  for (const { event, actor, beneficiary } of bankableEvents) {
    const origin = card.cert === "certified"
      ? { matchId: card.matchId, commandIndex: event.commandIndex }
      : { logId: claimLogId, commandIndex: event.commandIndex };
    const banked = {
      kind: event.kind,
      beneficiary,
      underFire: event.underFire,
      reached: event.reached,
      grade: eventGrade,
      origin,
      at: card.at,
    };
    if (run.season) {
      const e = slateEntry(run.season);
      banked.slate = { idx: run.season.pos, venue: e.venue, host: e.host, sanction: e.sanction };
    }
    next.eventLedger[actor] = [...(next.eventLedger[actor] ?? []), banked];

    /* The relationship IS computed here, deliberately. The rules core
       derives the replay fact (`extraction`); the run owns the banking
       policy that says what that graded fact means after the card.
       Keeping those two derivations named and separate prevents either
       side from quietly taking ownership of the other.

       Direction matters: the rescued beneficiary owes the actor a life.
       While that directed debt is active, another rescue mints nothing —
       no repetition treadmill, and the first source remains the origin.
       A source already used by a fulfilled debt cannot mint twice either;
       a later debt needs a later rescue with its own origin. */
    const activeAlready = next.relationships.some(relationship =>
      relationship.kind === "owes-a-life"
      && relationship.from === beneficiary
      && relationship.to === actor
      && relationship.status === "active");
    const originAlreadyUsed = next.relationships.some(relationship =>
      sameOrigin(relationship.grade, relationship.origin, eventGrade, origin));
    if (!activeAlready && !originAlreadyUsed) {
      const relationship = {
        kind: "owes-a-life",
        from: beneficiary,
        to: actor,
        grade: eventGrade,
        origin: { ...origin },
        status: "active",
        at: card.at,
      };
      if (run.season) {
        const e = slateEntry(run.season);
        relationship.slate = {
          idx: run.season.pos, venue: e.venue, host: e.host, sanction: e.sanction,
        };
      }
      next.relationships.push(relationship);
    }
  }

  next.cards += 1;
  next.purse += card.purse;
  next.best = Math.max(next.best, card.rating);
  next.mercy.walked += card.ledger.walked;
  next.mercy.finished += card.ledger.finished;
  for (const id of downIds) {
    next.wounds[id] = (next.wounds[id] ?? 0) + 1;
  }
  if (card.cert === "unwitnessed") next.unwitnessed += 1;
  if (card.cert === "dark") next.dark += 1;
  if (card.result === "win") {
    next.wins += 1;
    next.streak += 1;
    next.longest = Math.max(next.longest, next.streak);
  } else {
    next.streak = 0;
  }

  // A banked card moves the season: the slate advances and every existing
  // clock ticks. A recovering BENCHED person can therefore heal while a fit
  // lineup fights. THEN the card's own dead start their clocks, so a fresh
  // wound counts recovery from the position after the card that caused it.
  if (next.season) {
    advance(next.season);
    for (const id of downIds) next.season.clocks[id] = WOUND_CLOCK;
  }
  return { run: next, accepted: true, counted: true, why: null };
}

/* ---- passing ------------------------------------------------------
   The season's second verb. Its plain form is ALWAYS legal while the
   slate has entries left — fit or unfit, that is the point. Passing
   is how a wounded roster heals (the clocks tick on advance) and how a
   fit one rests, and its cost is the record itself: the entry's framing
   is banked with the pass, so the card you declined is a fact of the
   season, not an absence from it.

   Returns {run, accepted, why} — no `counted`, because there is no edge
   verdict to count. A pass is the run's own act; nothing about it can
   be disputed, so the two-negatives distinction has nothing to
   distinguish. */
export function applyPass(run, at, dedication = null) {
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
  let relationshipIndex = -1;
  if (dedication !== null && dedication !== undefined) {
    const owned = new Set(run.roster.people.map(person => person.id));
    if (!dedicationShapeValid(dedication)
        || !owned.has(dedication.from) || !owned.has(dedication.to)) {
      return {
        run, accepted: false,
        why: "a dedicated pass must name the real owned debtor and creditor — wrong person",
      };
    }
    relationshipIndex = run.relationships.findIndex(relationship =>
      relationship.kind === "owes-a-life"
      && relationship.from === dedication.from
      && relationship.to === dedication.to
      && relationship.status === "active");
    if (relationshipIndex < 0) {
      return { run, accepted: false, why: "that pair has no active life debt to repay" };
    }
    if (!Object.prototype.hasOwnProperty.call(run.season.clocks, dedication.to)) {
      return {
        run, accepted: false,
        why: "the named creditor has no running recovery clock for this dedication",
      };
    }
  }

  const next = {
    ...run,
    relationships: run.relationships.map(copyRelationship),
    season: copySeason(run.season),
  };
  const pass = {
    idx: next.season.pos,
    venue: entry.venue,
    host: entry.host,
    sanction: entry.sanction,
    at,
  };
  if (relationshipIndex >= 0) {
    pass.dedication = {
      kind: dedication.kind, from: dedication.from, to: dedication.to,
    };
    const relationship = next.relationships[relationshipIndex];
    next.relationships[relationshipIndex] = {
      ...relationship,
      status: "fulfilled",
      fulfilledAt: at,
      fulfilledSlate: {
        idx: pass.idx, venue: pass.venue, host: pass.host, sanction: pass.sanction,
      },
    };
  }
  next.season.passed = [...next.season.passed, pass];
  advance(next.season, relationshipIndex >= 0 ? dedication.to : null);
  return { run: next, accepted: true, why: null };
}

/* ---- the shop -----------------------------------------------------
   Authored data again, validated at the same boundary and for the same
   reason as the slate: the run has to survive a catalogue it did not
   write. `color` rides along because a bought thing has to keep looking
   like itself — the shop restocks, the run does not, and a hood that
   changed colour when the house catalogue changed would be the surface
   rewriting history to match the present. Same rule as the slate a
   restored season keeps: what you bought is what you own. */
export function itemValid(item) {
  if (!item || typeof item !== "object") return false;
  if (!isName(item.id)) return false;
  if (typeof item.name !== "string" || item.name.length < 1 || item.name.length > MAX_LABEL) return false;
  // The law, enforced rather than asserted: any slot that carries verbs is
  // Tier 2 roster state, and this module does not sell roster state.
  if (!FLAIR_SLOTS.includes(item.slot)) return false;
  if (!intIn(item.cost, 0, MAX_PURSE)) return false;
  if (typeof item.color !== "string" || !/^#[0-9a-f]{6}$/.test(item.color)) return false;
  return true;
}

/* A shop's whole stock, for a surface that wants to validate at boot the
   way the room validates its slate. Ids must be unique: two different
   items under one id makes a purchase record ambiguous about what was
   actually bought. */
export function stockValid(stock) {
  if (!Array.isArray(stock)) return false;
  if (stock.length < 1 || stock.length > MAX_STOCK) return false;
  if (!stock.every(itemValid)) return false;
  return new Set(stock.map(i => i.id)).size === stock.length;
}

/* What a fighter is wearing, derived from the purchase ledger rather than
   stored beside it. One array is the record AND the kit; two would be two
   things that can disagree, and the disagreement would be invisible
   (a rack showing a hood the ledger never bought). */
export function kitOf(run, who) {
  const worn = {};
  if (!run || !Array.isArray(run.bought)) return worn;
  for (const b of run.bought) if (b.who === who) worn[b.slot] = b;
  return worn;
}

/* ---- buying -------------------------------------------------------
   The third verb, and the only one that touches neither the slate nor
   the card. That is worth saying out loud: a purchase cannot be
   invalidated by a card still settling at the edge, because it spends
   money that is already banked and moves nothing a settlement will
   move. Closing refuses mid-settlement and passing refuses
   mid-settlement; buying does not need to, and the room should not
   invent a gate this module does not have.

   Returns {run, accepted, why} — no `counted`, same as applyPass: there
   is no edge verdict to count. Both refusals are accepted:false because
   the SURFACE is the gate. The room prices the stock, knows the balance,
   and knows what each fighter already wears; a purchase that arrives
   here unaffordable or into a filled slot means the shop offered
   something it should have refused, which is a caller bug in exactly the
   sense the two-negatives contract means. */
export function applyBuy(run, item, who, at) {
  if (!run || run.v !== RUN_V) {
    return { run, accepted: false, why: "run is not this schema version" };
  }
  if (!itemValid(item)) {
    return { run, accepted: false, why: "that is not a thing a purse may buy" };
  }
  // A purchase belongs to an owned person. The ledger still carries the
  // tactical name because flair predates stable ids; checking it against the
  // owned roster prevents the room from dressing a name with no person behind
  // it while leaving the wire and old rack surface unchanged.
  if (!isName(who) || !run.roster.people.some(person => person.name === who)) {
    return { run, accepted: false, why: "that is not a fighter this run can dress" };
  }
  if (typeof at !== "string" || !at) {
    return { run, accepted: false, why: "a purchase needs to know when it happened" };
  }
  if (run.bought.length >= MAX_BOUGHT) {
    return { run, accepted: false, why: "the rack is full" };
  }
  if (kitOf(run, who)[item.slot]) {
    return { run, accepted: false, why: `${who} already wears a ${item.slot}` };
  }
  if (item.cost > run.purse - run.spent) {
    return { run, accepted: false, why: "the purse will not cover it" };
  }

  const next = { ...run, bought: run.bought.slice() };
  const record = {
    id: item.id,
    name: item.name,
    slot: item.slot,
    color: item.color,
    who,
    cost: item.cost,
    at,
  };
  // Where on the tour it was bought, from the run's OWN slate — the same
  // stamp a card carries, for the same reason. Trophies have provenance
  // in grades (Circuit §6): a hood bought after the Cold Court is a
  // different object from the same hood bought in week one, and the only
  // place that fact can live is the record of the purchase.
  if (next.season) {
    const e = slateEntry(next.season);
    if (e) record.slate = { idx: next.season.pos, venue: e.venue, host: e.host, sanction: e.sanction };
  }
  next.bought = [...next.bought, record];
  next.spent += item.cost;
  return { run: next, accepted: true, why: null };
}

/* ---- reading a stored run ----------------------------------------
   Three outcomes, all of them named, none of them silent:

     fresh    — nothing stored; a run opens here
     restored — a stored run of this schema version
     orphaned — something stored that this schema cannot read. It is
                MOVED, not dropped, and the caller is told so it can
                say so on the surface. */
export function loadRun(at, roster = DEFAULT_ROSTER) {
  const fresh = openRun(at, roster);
  if (fresh === null) return { run: null, how: "invalid-roster" };
  let raw;
  try { raw = store.read(RUN_KEY); } catch { raw = null; }
  if (raw === null || raw === undefined) return { run: fresh, how: "fresh" };

  let parsed = null;
  try { parsed = JSON.parse(raw); } catch { parsed = null; }
  if (parsed && parsed.v === RUN_V && sane(parsed)) {
    return { run: parsed, how: "restored" };
  }
  // Setting aside is not best-effort, for the same reason closing is not:
  // the read-back is what makes "moved, never dropped" a behaviour. The
  // write can throw under quota, and a store that silently drops writes —
  // the inert default is one — does not throw at all; either way, saying
  // "orphaned" while the orphan slot holds nothing invites the caller to
  // save a fresh run over the only copy, which is exactly what the room
  // does on that answer (caught in review, on the schema bump that made
  // this path hot for every v1 run).
  let preserved = false;
  try {
    const blob = typeof raw === "string" ? raw : JSON.stringify(raw);
    store.write(ORPHAN_KEY, blob);
    preserved = store.read(ORPHAN_KEY) === blob;
  } catch { preserved = false; }
  if (!preserved) {
    // The unreadable run keeps the live slot — it is the only copy, and
    // the slot is not this page's to spend. The fresh run plays in
    // memory, and the caller is told to write nothing.
    return { run: fresh, how: "unpreserved" };
  }
  try { store.remove(RUN_KEY); } catch { /* the orphan copy is already safe */ }
  return { run: fresh, how: "orphaned" };
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
  const ints = ["cards", "wins", "purse", "best", "streak", "longest", "struck", "unwitnessed", "dark"];
  if (!ints.every(k => Number.isInteger(r[k]) && r[k] >= 0)) return false;
  if (typeof r.opened !== "string") return false;
  if (!rosterValid(r.roster)) return false;
  const ownedIds = new Set(r.roster.people.map(person => person.id));
  const ownedNames = new Set(r.roster.people.map(person => person.name));
  // non-negative, not merely integral: a hand-edited {walked:-1} restored
  // fine and rendered a -100% mercy rate, which is the made-up number this
  // module refuses to print elsewhere (caught in review)
  if (!r.mercy || !intIn(r.mercy.walked, 0, Number.MAX_SAFE_INTEGER)
      || !intIn(r.mercy.finished, 0, Number.MAX_SAFE_INTEGER)) return false;
  if (!r.wounds || typeof r.wounds !== "object" || Array.isArray(r.wounds)) return false;
  if (!Object.keys(r.wounds).every(isPersonId)) return false;
  if (!Object.keys(r.wounds).every(id => ownedIds.has(id))) return false;
  if (!Object.values(r.wounds).every(n => Number.isInteger(n) && n >= 0)) return false;
  if (!r.eventLedger || typeof r.eventLedger !== "object" || Array.isArray(r.eventLedger)) return false;
  if (!Object.keys(r.eventLedger).every(isPersonId)) return false;
  if (!Object.keys(r.eventLedger).every(id => ownedIds.has(id))) return false;
  if (!Object.values(r.eventLedger).every(events => Array.isArray(events) && events.length > 0)) return false;
  const allEvents = Object.entries(r.eventLedger)
    .flatMap(([actor, events]) => events.map(event => ({ actor, event })));
  if (allEvents.length > r.cards * MAX_DERIVED_PER_CARD) return false;
  if (!allEvents.every(({ actor, event }) => {
    if (!event || typeof event !== "object" || Array.isArray(event)) return false;
    if (!onlyKeys(event, EVENT_KEYS)) return false;
    if (event.kind !== "extraction" || event.reached !== true
        || typeof event.underFire !== "boolean") return false;
    if (!isPersonId(event.beneficiary) || !ownedIds.has(event.beneficiary)
        || event.beneficiary === actor) return false;
    if (typeof event.at !== "string" || !event.at) return false;
    return (event.grade === "certified" || event.grade === "claim")
      && originValid(event.grade, event.origin);
  })) return false;
  const certifiedEvents = allEvents.filter(({ event }) => event.grade === "certified").length;
  const claimEvents = allEvents.length - certifiedEvents;
  if (certifiedEvents > (r.cards - r.unwitnessed - r.dark) * MAX_DERIVED_PER_CARD) return false;
  if (claimEvents > (r.unwitnessed + r.dark) * MAX_DERIVED_PER_CARD) return false;
  if (!Array.isArray(r.relationships) || r.relationships.length > allEvents.length) return false;
  const relationshipOrigins = new Set();
  const activePairs = new Set();
  if (!r.relationships.every(relationship => {
    if (!relationship || typeof relationship !== "object" || Array.isArray(relationship)) return false;
    const base = relationship.slate === undefined
      ? RELATIONSHIP_KEYS
      : [...RELATIONSHIP_KEYS, "slate"];
    const expected = relationship.status === "fulfilled"
      ? [...base, "fulfilledAt", "fulfilledSlate"]
      : base;
    if (!exactKeys(relationship, expected)) return false;
    if (relationship.kind !== "owes-a-life") return false;
    if (!ownedIds.has(relationship.from) || !ownedIds.has(relationship.to)
        || relationship.from === relationship.to) return false;
    if (relationship.status !== "active" && relationship.status !== "fulfilled") return false;
    if (typeof relationship.at !== "string" || !relationship.at) return false;
    if (relationship.slate !== undefined && !stampValid(relationship.slate)) return false;
    if ((relationship.grade !== "certified" && relationship.grade !== "claim")
        || !originValid(relationship.grade, relationship.origin)) return false;
    const sourceKey = originKey(relationship.grade, relationship.origin);
    if (relationshipOrigins.has(sourceKey)) return false;
    relationshipOrigins.add(sourceKey);
    if (relationship.status === "active") {
      const pair = `${relationship.from}->${relationship.to}`;
      if (activePairs.has(pair)) return false;
      activePairs.add(pair);
    } else if (typeof relationship.fulfilledAt !== "string" || !relationship.fulfilledAt
        || !stampValid(relationship.fulfilledSlate)) return false;

    // A relationship is banking policy over a banked event, not an
    // unsupported sentence. Its stable-id direction, grade, pointer, time
    // and slate stamp must all resolve to the extraction it names. Whether a
    // claim log id still resolves is deliberately outside sane(): the
    // chronicle is independent state over which RUN_V has no jurisdiction.
    // The room checks that target when it renders the source.
    return allEvents.some(({ actor, event }) =>
      actor === relationship.to
      && event.kind === "extraction"
      && event.beneficiary === relationship.from
      && sameOrigin(event.grade, event.origin, relationship.grade, relationship.origin)
      && event.at === relationship.at
      && (event.slate === undefined
        ? relationship.slate === undefined
        : sameStamp(event.slate, relationship.slate)));
  })) return false;
  const relationshipsByPair = new Map();
  for (const relationship of r.relationships) {
    const pair = `${relationship.from}->${relationship.to}`;
    const history = relationshipsByPair.get(pair) ?? [];
    history.push(relationship);
    relationshipsByPair.set(pair, history);
  }
  if (!Array.isArray(r.recent) || r.recent.length > RECENT) return false;
  if (!r.recent.every(c =>
    c && typeof c === "object"
    && onlyKeys(c, CARD_KEYS)
    && typeof c.seed === "string"
    && (c.result === "win" || c.result === "loss")
    && intIn(c.rating, 0, MAX_RATING)
    && intIn(c.purse, 0, MAX_PURSE)
    && ["certified", "dark", "unwitnessed", "struck"].includes(c.cert)
    // bounded because the mercy ledger is re-derived from them below —
    // a card carrying a string here would make that sum garbage
    && intIn(c.walked, 0, MAX_SIDE) && intIn(c.finished, 0, MAX_SIDE)
    // Receipts retain the tactical names carried by the card; unlike the
    // durable wound and clock ledgers, they are a record of the yard wire.
    && Array.isArray(c.down) && c.down.every(name => isName(name) && ownedNames.has(name))
    && Array.isArray(c.derivedEvents) && c.derivedEvents.length <= MAX_DERIVED_PER_CARD
    && c.derivedEvents.every(event =>
      derivedEventValid(event) && ownedNames.has(event.actor) && ownedNames.has(event.beneficiary))
    // A struck receipt never carries an event. Counted uncertified receipts
    // may carry claim events, but only applyCard with a prior log id writes
    // them; sane() validates the corresponding ledger origin shape below.
    && (c.cert !== "struck" || c.derivedEvents.length === 0)
    && (c.cert === "certified" ? matchIdValid(c.matchId)
      : c.cert === "dark" || c.cert === "unwitnessed" ? c.matchId === null
      : c.matchId === null || matchIdValid(c.matchId))
    && (c.slate === undefined || stampValid(c.slate))
  )) return false;
  /* The totals are not free-floating either, and since there is now
     somewhere to SPEND them, a forged purse is forged money — a
     hand-edited fresh run with `purse: 10000` used to restore and buy a
     hood with it (caught in review, beat 3).

     `recent` is the run's own receipt for everything it claims. Every
     applyCard pushes exactly one entry, banked or struck, so `cards +
     struck === recent.length` is precisely "nothing has scrolled off" —
     and while that holds, every total that is a sum or a count must BE
     that sum or count.

     Not `recent.length < RECENT`, which was the first cut: a run of
     exactly RECENT cards has evicted nothing either, and testing the
     buffer's fullness instead of its completeness dropped that run into
     the loose branch — where a hand-edited purse restored and became
     spendable balance, the exact hole this check exists to close (caught
     by BOTH review bots, independently).

     Once events really have scrolled off, the receipts for them are gone
     by design and the totals cannot be re-derived. What is still visible
     is a FLOOR, and each vanished card can have paid at most MAX_PURSE —
     which also means inflating `cards` to buy headroom for a forged purse
     buys exactly MAX_PURSE per claimed card, not a free pass. A run that
     claims a hundred cards can claim the purse of a hundred cards; that
     is the honest limit of what a 12-entry receipt can prove, and this
     says so rather than pretending otherwise.

     `best`, `streak` and `longest` are order-derived rather than summed
     and stay on their existing bounds — they can be lied about, but a lie
     there buys nothing. */
  const banked = r.recent.filter(c => c.cert !== "struck");
  const sum = (list, of) => list.reduce((n, c) => n + of(c), 0);
  const wins = banked.filter(c => c.result === "win").length;
  const unwitnessed = banked.filter(c => c.cert === "unwitnessed").length;
  const dark = banked.filter(c => c.cert === "dark").length;
  const recentCertifiedEvents = sum(banked.filter(c => c.cert === "certified"), c => c.derivedEvents.length);
  const recentClaimEvents = sum(
    banked.filter(c => c.cert === "dark" || c.cert === "unwitnessed"),
    c => c.derivedEvents.length);
  if (r.cards + r.struck === r.recent.length) {
    if (banked.length !== r.cards) return false;
    if (wins !== r.wins) return false;
    if (unwitnessed !== r.unwitnessed) return false;
    if (dark !== r.dark) return false;
    if (sum(banked, c => c.purse) !== r.purse) return false;
    // The mercy ledger is the run's actual thesis, so it gets the same
    // treatment: a forged rate buys nothing, but it is a lie about who
    // you have been, which is worse than a lie about money.
    if (sum(banked, c => c.walked) !== r.mercy.walked) return false;
    if (sum(banked, c => c.finished) !== r.mercy.finished) return false;
    if (certifiedEvents !== recentCertifiedEvents) return false;
    if (claimEvents !== recentClaimEvents) return false;
  } else {
    // The only way an event can be missing is the buffer being full.
    if (r.cards + r.struck <= RECENT || r.recent.length !== RECENT) return false;
    const gone = r.cards - banked.length;
    if (gone < 0) return false;
    if (r.purse > sum(banked, c => c.purse) + gone * MAX_PURSE) return false;
    if (r.wins < wins || r.unwitnessed < unwitnessed || r.dark < dark) return false;
    if (r.struck < r.recent.length - banked.length) return false;
    if (r.mercy.walked < sum(banked, c => c.walked)) return false;
    if (r.mercy.finished < sum(banked, c => c.finished)) return false;
    if (certifiedEvents < recentCertifiedEvents) return false;
    if (claimEvents < recentClaimEvents) return false;
  }
  // The season, when there is one, all the way in — same reasoning as the
  // collections above: every field here reaches the room's surface or
  // gates its door.
  if (!("season" in r)) return false;
  if (r.season !== null) {
    const s = r.season;
    if (typeof s !== "object" || Array.isArray(s)) return false;
    if (!slateValid(s.slate)) return false;
    const entries = s.slate.entries;
    if (!intIn(s.pos, 0, entries.length)) return false;
    if (!Array.isArray(s.passed) || s.passed.length > s.pos) return false;
    // A pass is bound to its authored entry, not merely shaped like one:
    // the idx must land on the real slate, the framing must be that
    // entry's own word, and the indices must strictly climb — applyPass
    // banks the current position and advances, so equal or regressing
    // indices cannot come from this module (caught in review: a
    // syntactically valid pass with forged framing restored fine and
    // summary() reported a venue the slate never said).
    if (!s.passed.every((p, i) => p && typeof p === "object"
      && (p.dedication === undefined
        ? exactKeys(p, PASS_KEYS)
        : exactKeys(p, [...PASS_KEYS, "dedication"])
          && dedicationShapeValid(p.dedication)
          && ownedIds.has(p.dedication.from) && ownedIds.has(p.dedication.to))
      && intIn(p.idx, 0, entries.length - 1)
      && entryValid(p)
      && sameFraming(p, entries[p.idx])
      && (i === 0 || p.idx > s.passed[i - 1].idx)
      && typeof p.at === "string" && p.at.length > 0)) return false;
    // Cards are bound the same way: every card banked on a season was
    // stamped by applyCard, so a season card with no stamp, a stamp off
    // the real slate, or framing the slate never said is storage talking,
    // not this module.
    // ...including WHEN: a stamp records the position the card was fought
    // at, and the position only ever climbs, so a record stamped at an
    // entry the season has not reached yet is not something this module
    // could have written (caught in review, beat 3). A banked card stamps
    // below the current position and a struck one stamps at it, so the
    // bound is `<= pos` for both.
    if (!r.recent.every(c => c.slate
      && intIn(c.slate.idx, 0, entries.length - 1)
      && c.slate.idx <= s.pos
      && sameFraming(c.slate, entries[c.slate.idx]))) return false;
    // Derived events are banked facts, never struck attempts: every one
    // points behind the current position and carries the slate's own word.
    for (const events of Object.values(r.eventLedger)) {
      let last = -1;
      for (const event of events) {
        if (!event.slate || !stampValid(event.slate)) return false;
        if (event.slate.idx >= s.pos || event.slate.idx < last) return false;
        if (!sameFraming(event.slate, entries[event.slate.idx])) return false;
        last = event.slate.idx;
      }
    }
    let lastRelationship = -1;
    for (const relationship of r.relationships) {
      // Every relationship on a season was minted by a banked card, so its
      // source is behind the current position and cannot regress through the
      // append-only ledger. Fulfillment is a banked pass and obeys the same
      // authored-stamp law.
      if (!relationship.slate || relationship.slate.idx >= s.pos
          || relationship.slate.idx < lastRelationship
          || !sameFraming(relationship.slate, entries[relationship.slate.idx])) return false;
      lastRelationship = relationship.slate.idx;
      if (relationship.status === "fulfilled"
          && (relationship.fulfilledSlate.idx >= s.pos
            || relationship.fulfilledSlate.idx < relationship.slate.idx
            || !sameFraming(
              relationship.fulfilledSlate, entries[relationship.fulfilledSlate.idx]))) return false;
    }
    // A directed pair's history is a sequence of non-overlapping active
    // intervals, not merely a collection with one active entry at restore.
    // Order by the mint point the reducer actually writes. The command
    // index is only a deterministic tie-break inside one card; applyCard
    // cannot mint the same pair twice there because the first debt is
    // already active.
    //
    // The bound is strict. applyPass fulfills at the current position and
    // then advances it, so the earliest card capable of re-minting that
    // pair is stamped at the following slate index. A successor at or
    // before the fulfillment index was rescued while its predecessor was
    // still active and could not have been minted by applyCard.
    for (const history of relationshipsByPair.values()) {
      const byMint = history.slice().sort((a, b) =>
        a.slate.idx - b.slate.idx
        || a.origin.commandIndex - b.origin.commandIndex);
      for (let i = 1; i < byMint.length; i++) {
        const predecessor = byMint[i - 1];
        const successor = byMint[i];
        if (predecessor.status !== "fulfilled"
            || successor.slate.idx <= predecessor.fulfilledSlate.idx) return false;
      }
    }
    const dedicatedPasses = s.passed.filter(pass => pass.dedication !== undefined);
    const fulfilled = r.relationships.filter(relationship => relationship.status === "fulfilled");
    // Repayment history is two views of one run-owned act: the pass says
    // which debt it dedicated, and the relationship says where it became
    // fulfilled. Either side without the other is a hand-edited story.
    if (!dedicatedPasses.every(pass => fulfilled.filter(relationship =>
      relationship.from === pass.dedication.from
      && relationship.to === pass.dedication.to
      && relationship.fulfilledAt === pass.at
      && sameStamp(relationship.fulfilledSlate, pass)).length === 1)) return false;
    if (!fulfilled.every(relationship => dedicatedPasses.filter(pass =>
      pass.dedication.from === relationship.from
      && pass.dedication.to === relationship.to
      && pass.at === relationship.fulfilledAt
      && sameStamp(pass, relationship.fulfilledSlate)).length === 1)) return false;
    // Completeness matters as much as refusing invented entries. Walk every
    // graded extraction through the relationship intervals it could have
    // observed: the first event in an inactive interval must be the source of
    // a relationship; later rescues are covered by that active debt until its
    // dedicated pass. Deleting the ledger (or moving its origin to a later
    // rescue) therefore cannot restore as an apparently honest run.
    if (!allEvents.every(({ actor, event }) => r.relationships.some(relationship => {
      if (relationship.from !== event.beneficiary || relationship.to !== actor) return false;
      const startsBefore = relationship.slate.idx < event.slate.idx
        || (relationship.slate.idx === event.slate.idx
          && relationship.origin.commandIndex <= event.origin.commandIndex);
      const stillActive = relationship.status === "active"
        || event.slate.idx < relationship.fulfilledSlate.idx;
      return startsBefore && stillActive;
    }))) return false;
    if (!s.clocks || typeof s.clocks !== "object" || Array.isArray(s.clocks)) return false;
    if (!Object.keys(s.clocks).every(isPersonId)) return false;
    if (!Object.keys(s.clocks).every(id => ownedIds.has(id))) return false;
    // 1, not 0: advance() drops a cleared clock, so a stored zero was
    // written by something other than this module
    if (!Object.values(s.clocks).every(n => intIn(n, 1, MAX_CLOCK))) return false;
    // The spine's own arithmetic. Every banked card and every pass moves
    // the position exactly once, and nothing else ever moves it — a run
    // whose books do not balance was not kept by this module.
    if (r.cards + s.passed.length !== s.pos) return false;
  } else {
    // And a plain run's cards carry no stamp at all — a stamp with no
    // slate to answer to is unfalsifiable, so it does not restore. Its
    // `at` strings are caller-authored labels, not an ordered clock, and
    // applyPass is unavailable without a season. The honest lifecycle
    // claim here is therefore only what applyCard can write: at most one
    // active relationship per pair, whose origin precedes every later
    // same-pair event in that actor's append-only event ledger.
    if (!r.recent.every(c => c.slate === undefined)) return false;
    if (!allEvents.every(({ event }) => event.slate === undefined)) return false;
    if (!r.relationships.every(relationship =>
      relationship.slate === undefined && relationship.status === "active")) return false;
    for (const [actor, events] of Object.entries(r.eventLedger)) {
      for (let i = 0; i < events.length; i++) {
        const event = events[i];
        if (!r.relationships.some(relationship => {
          if (relationship.from !== event.beneficiary || relationship.to !== actor) return false;
          const sourceIndex = events.findIndex(candidate =>
            sameOrigin(
              candidate.grade, candidate.origin, relationship.grade, relationship.origin));
          return sourceIndex >= 0 && sourceIndex <= i;
        })) return false;
      }
    }
  }
  // The rack, all the way in, same as everything else that reaches a
  // surface. A stored purchase is the one record here that can move
  // MONEY on restore, so its books are checked rather than trusted.
  if (!Number.isInteger(r.spent) || r.spent < 0) return false;
  if (!Array.isArray(r.bought) || r.bought.length > MAX_BOUGHT) return false;
  // itemValid covers id, name, slot, cost and colour — including the slot
  // law, so a stored purchase of a TORSO rig orphans the run rather than
  // restoring a verb nobody could have bought.
  if (!r.bought.every(b => b && typeof b === "object"
    && onlyKeys(b, BOUGHT_KEYS)
    && itemValid(b)
    && isName(b.who) && ownedNames.has(b.who)
    && typeof b.at === "string" && b.at.length > 0)) return false;
  // A slot is bought once per fighter, so a run wearing two drapes on one
  // body was not written by applyBuy — and the derived kit would silently
  // pick one of them and drop the other, which is money on the record
  // with nothing on the rack to show for it.
  const hooks = r.bought.map(b => `${b.who}@${b.slot}`);
  if (new Set(hooks).size !== hooks.length) return false;
  // The purse's own arithmetic, the same way the slate's position is
  // checked against cards+passes: `spent` IS the sum of the rack, and a
  // run whose books do not balance is storage talking. And you cannot
  // have spent what you never earned.
  if (r.bought.reduce((n, b) => n + b.cost, 0) !== r.spent) return false;
  if (r.spent > r.purse) return false;
  if (r.season !== null) {
    const entries = r.season.slate.entries;
    // A purchase is stamped when there was an entry to stamp it with, so
    // an unstamped one means the tour was already complete — which is
    // terminal, and therefore nothing stamped may follow it, and the
    // slate must still be complete NOW. Where a stamp exists it is bound
    // to the authored slate exactly as a card's is, it never points past
    // where the season has got to, and the indices never regress, because
    // the position never does.
    let last = -1;
    let ended = false;
    for (const b of r.bought) {
      if (b.slate === undefined) { ended = true; continue; }
      if (ended) return false;
      if (!stampValid(b.slate)) return false;
      if (b.slate.idx > entries.length - 1) return false;
      if (b.slate.idx > r.season.pos) return false;
      if (!sameFraming(b.slate, entries[b.slate.idx])) return false;
      if (b.slate.idx < last) return false;
      last = b.slate.idx;
    }
    // An unstamped purchase can only exist on a tour that is over, and a
    // tour that is over stays over (caught in review, beat 3: one on a
    // half-finished slate restored fine, claiming a purchase applyBuy
    // could not have made).
    if (ended && r.season.pos !== entries.length) return false;
  } else {
    // Same as a plain run's cards: a stamp with no slate to answer to is
    // unfalsifiable, so it does not restore.
    if (!r.bought.every(b => b.slate === undefined)) return false;
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
  const fresh = openRun(at, run.roster);
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
  // The rack, grouped by who wears it and sorted so the surface renders a
  // stable order without inventing one. A Map, not an object literal:
  // isName already refuses "__proto__", and this keeps the derivation from
  // depending on that being true twice.
  const byWho = new Map();
  for (const b of run.bought) {
    if (!byWho.has(b.who)) byWho.set(b.who, {});
    byWho.get(b.who)[b.slot] = b;
  }
  const kit = [...byWho.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  const lineupIds = new Set(run.roster.lineup);
  const people = run.roster.people.map(person => ({
    id: person.id,
    name: person.name,
    body: person.body,
    origin: { ...person.origin },
  }));
  const derivedEvents = people.flatMap(person =>
    (run.eventLedger[person.id] ?? []).map(event => ({
      actor: person.id,
      kind: event.kind,
      beneficiary: event.beneficiary,
      underFire: event.underFire,
      reached: event.reached,
      grade: event.grade,
      origin: { ...event.origin },
      at: event.at,
      ...(event.slate ? { slate: { ...event.slate } } : {}),
    })));
  const relationships = run.relationships.map(copyRelationship);
  // These are the dedicated choices the door may render NOW. The room
  // does not rebuild the debt + running-creditor-clock gate; summary is
  // the one read model for both the visible offer and applyPass's policy.
  const dedicatedPasses = run.season === null ? [] : relationships
    .filter(relationship => relationship.status === "active"
      && Object.prototype.hasOwnProperty.call(run.season.clocks, relationship.to))
    .map(relationship => ({
      kind: "repay-the-life",
      from: relationship.from,
      to: relationship.to,
      recovers: DEDICATED_RECOVERY,
    }));
  return {
    cards: run.cards,
    record: `${run.wins}–${losses}`,
    purse: run.purse,
    spent: run.spent,
    // What a purse can actually be spent on right now. Derived, never
    // stored: purse stays total earned, so the season can still say what
    // it won after the money is gone.
    balance: run.purse - run.spent,
    bought: run.bought,
    kit,
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
    dark: run.dark,
    derivedEvents,
    relationships,
    drift: run.drift,
    roster: {
      people,
      lineup: run.roster.lineup.map(id => people.find(person => person.id === id)),
      bench: people.filter(person => !lineupIds.has(person.id)),
    },
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
      fieldedClocks: f.fieldedClocks,
      dedicatedPasses,
    },
  };
}
