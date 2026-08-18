/* ============================================================
   SENTINEL local chronicle — what survives without the Witness.

   This is not run state. It has its own stable storage key, no schema
   dependency on RUN_V, and no close/orphan verb. A claim may point here
   only after appendEntry has written and read back its target.

   localStorage can only replace a value, so the implementation writes a
   new array blob; the public operation is nevertheless append-only. It
   preserves every prior slot as parsed data, exposes no update or delete
   operation, assigns the next array index, and verifies the completed append
   by reading it back. A damaged slot remains in place as null from
   entries()/readEntry() rather than being filtered out and renumbering every
   later address.

   This prototype assumes one writer. localStorage has no synchronous lock or
   compare-and-swap, so concurrent same-origin tabs can still replace one
   another's append after read-back and LOSE an entry. The content key makes
   that race degrade honestly: a claim whose slot was replaced no longer
   resolves, but it can never open the different match now occupying that
   numeric address.
   ============================================================ */

export const LOG_KEY = "sentinel.chronicle";
export const LOG_CAP = 200;

const store = {
  read: () => null,
  write: () => {},
};

export function bindStore(next) { Object.assign(store, next); }

export class LogRefusal extends Error {
  constructor(code, message) {
    super(message);
    this.name = "LogRefusal";
    this.code = code;
  }
}

const exactKeys = (value, keys) => {
  const actual = Object.keys(value);
  return actual.length === keys.length && actual.every(key => keys.includes(key));
};

const intIn = (value, lo, hi) =>
  Number.isInteger(value) && value >= lo && value <= hi;

const nameValid = value =>
  typeof value === "string" && value.length > 0 && value.length <= 16
  && value !== "__proto__";

const CONTENT_KEY = /^[0-9a-f]{8}$/;

// FNV-1a over one canonical match identity. Rebuilding the roster objects is
// intentional: object insertion order from an untrusted caller is not part of
// the match, while fighter and command order are.
const contentKey = entry => {
  const roster = Array.isArray(entry?.roster)
    ? entry.roster.map(person => ({ name: person?.name, hp: person?.hp }))
    : entry?.roster;
  const record = Array.isArray(entry?.record)
    ? entry.record.map(command => Array.isArray(command) ? command.slice() : command)
    : entry?.record;
  const identity = JSON.stringify({ seed: entry?.seed, roster, record });
  let hash = 0x811c9dc5;
  for (let i = 0; i < identity.length; i++) {
    hash ^= identity.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
};

const TACTICAL_NAME = /^[A-Z0-9][A-Z0-9-]{0,15}$/;
const rosterValid = roster => Array.isArray(roster) && roster.length === 3
  && new Set(roster.map(person => person?.name)).size === roster.length
  && roster.every(person => person && typeof person === "object" && !Array.isArray(person)
    && exactKeys(person, ["name", "hp"])
    && typeof person.name === "string" && TACTICAL_NAME.test(person.name)
    && intIn(person.hp, 1, 10));

const scalarValid = value => value === null
  || typeof value === "string"
  || typeof value === "boolean"
  || (typeof value === "number" && Number.isFinite(value));

// The chronicle preserves a replayable-shaped record without interpreting
// any verb. Rules remain on the other side of the wall.
const recordValid = record => Array.isArray(record) && record.length <= 1024
  && record.every(command => Array.isArray(command)
    && command.length <= 16 && command.every(scalarValid));

const eventValid = event => !!event && typeof event === "object" && !Array.isArray(event)
  && exactKeys(event,
    ["kind", "actor", "beneficiary", "commandIndex", "underFire", "reached"])
  && event.kind === "extraction"
  && typeof event.actor === "string" && TACTICAL_NAME.test(event.actor)
  && typeof event.beneficiary === "string" && TACTICAL_NAME.test(event.beneficiary)
  && event.actor !== event.beneficiary
  && intIn(event.commandIndex, 0, 1023)
  && typeof event.underFire === "boolean"
  && event.reached === true;

const feedCutValid = cut => cut === null
  || (!!cut && typeof cut === "object" && !Array.isArray(cut)
    && exactKeys(cut, ["commandIndex"])
    && intIn(cut.commandIndex, 0, 1023));

const aftermathValid = aftermath => !!aftermath
  && typeof aftermath === "object" && !Array.isArray(aftermath)
  && exactKeys(aftermath, ["result", "rating", "purse", "feedCut"])
  && (aftermath.result === "win" || aftermath.result === "loss")
  && intIn(aftermath.rating, 0, 100)
  && intIn(aftermath.purse, 0, 10000)
  && feedCutValid(aftermath.feedCut);

const slateValid = slate => !!slate && typeof slate === "object" && !Array.isArray(slate)
  && exactKeys(slate, ["idx", "venue", "host", "sanction"])
  && intIn(slate.idx, 0, 31)
  && typeof slate.venue === "string" && slate.venue.length > 0 && slate.venue.length <= 24
  && (slate.host === null || nameValid(slate.host))
  && (slate.sanction === null || nameValid(slate.sanction));

const entryValid = (entry, expectedId) => {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) return false;
  const keys = entry.slate === undefined
    ? ["id", "key", "kind", "cert", "seed", "roster", "record", "derivedEvents", "aftermath", "at"]
    : ["id", "key", "kind", "cert", "seed", "roster", "record", "derivedEvents", "aftermath", "at", "slate"];
  if (!exactKeys(entry, keys)) return false;
  if (entry.id !== expectedId || entry.kind !== "match") return false;
  if (typeof entry.key !== "string" || !CONTENT_KEY.test(entry.key)) return false;
  if (entry.cert !== "dark" && entry.cert !== "unwitnessed") return false;
  if (typeof entry.seed !== "string" || !/^[0-9a-f]{1,8}$/.test(entry.seed)) return false;
  if (!rosterValid(entry.roster) || !recordValid(entry.record)) return false;
  if (entry.key !== contentKey(entry)) return false;
  if (!Array.isArray(entry.derivedEvents) || entry.derivedEvents.length > 1024
      || !entry.derivedEvents.every(eventValid)) return false;
  if (!aftermathValid(entry.aftermath)) return false;
  if (!entry.derivedEvents.every(event => event.commandIndex < entry.record.length)) return false;
  if (entry.aftermath.feedCut !== null
      && entry.aftermath.feedCut.commandIndex >= entry.record.length) return false;
  if (entry.cert === "dark" && entry.aftermath.feedCut === null) return false;
  if (entry.cert === "unwitnessed" && entry.aftermath.feedCut !== null) return false;
  if (typeof entry.at !== "string" || !entry.at) return false;
  return entry.slate === undefined || slateValid(entry.slate);
};

function rawEntries() {
  let raw;
  try { raw = store.read(LOG_KEY); }
  catch { return { ok: false, entries: [] }; }
  if (raw === null || raw === undefined) return { ok: true, entries: [] };
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? { ok: true, entries: parsed } : { ok: false, entries: [] };
  } catch {
    return { ok: false, entries: [] };
  }
}

export function appendEntry(entry) {
  const current = rawEntries();
  if (!current.ok) {
    throw new LogRefusal("damaged", "the log is damaged — nothing was overwritten");
  }
  if (current.entries.length >= LOG_CAP) {
    throw new LogRefusal("full", "the log is full — this prototype chronicle holds 200 entries");
  }
  const id = current.entries.length;
  const candidate = { id, ...entry };
  try { candidate.key = contentKey(candidate); }
  catch { throw new LogRefusal("invalid", "the log refused a malformed match entry"); }
  if (!entryValid(candidate, id)) {
    throw new LogRefusal("invalid", "the log refused a malformed match entry");
  }
  const next = [...current.entries, candidate];
  const blob = JSON.stringify(next);
  try {
    store.write(LOG_KEY, blob);
    if (store.read(LOG_KEY) !== blob) {
      throw new LogRefusal("unwritable", "the log refused the write — nothing was kept");
    }
  } catch (error) {
    if (error instanceof LogRefusal) throw error;
    throw new LogRefusal("unwritable", "the log refused the write — nothing was kept");
  }
  return { id, key: candidate.key };
}

export function readEntry(id) {
  if (!Number.isInteger(id) || id < 0) return null;
  const current = rawEntries();
  if (!current.ok || id >= current.entries.length) return null;
  const entry = current.entries[id];
  return entryValid(entry, id) ? structuredClone(entry) : null;
}

export function entries() {
  const current = rawEntries();
  if (!current.ok) return [];
  return current.entries.map((entry, id) =>
    entryValid(entry, id) ? structuredClone(entry) : null);
}
