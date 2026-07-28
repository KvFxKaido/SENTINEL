/* ============================================================
   SENTINEL tactical slice — rules layer.

   No DOM, no canvas, no audio, no timers of its own. Everything the
   outside world needs to know arrives as an event; everything it needs
   to provide arrives through `io`. That is what lets this run in Node,
   which is what lets determinism be a test instead of a habit.

   Determinism and turn authority are the invariants (see
   architecture/Sentinel 2D.md). Every random draw comes from the seeded
   stream in `S.rng`, in a fixed order. Nothing here may consult the
   clock, the platform, or Math.random — a single stray draw desyncs the
   whole encounter and `shift+R` stops meaning anything.
   ============================================================ */

export const W = 10, H = 10;
export const FLOOR = 0, HALF = 1, FULL = 2;

// hand-authored: walls (█) split the yard, crates (▪) seed the lanes
const MAP_SRC = [
  "..........",
  "..▪...█...",
  ".....▪█.▪.",
  ".█▪.......",
  ".█...▪....",
  "....▪...█.",
  ".......▪█.",
  ".▪.█▪.....",
  "...█...▪..",
  "..........",
];

// ---- seeded rng -------------------------------------------------
export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---- shared mutable encounter state -----------------------------
// One encounter at a time, deliberately. Forkable state (needed for a
// "preview this action's consequences" mode) is a real future want, but
// nothing asks for it yet and the design philosophy is explicit that
// complexity gets justified before it gets built.
export const S = {
  seed: 0,
  rng: null,
  map: [],
  units: [],
  turn: "op",          // "op" | "ho"
  selectedId: null,
  targetMode: false,   // shoot mode armed
  busy: false,         // input locked during animation / AI
  gameOver: null,      // null | "win" | "loss"
  decision: false,     // every living hostile has yielded — match holds for spare/finish
  rating: 50,          // crowd meter, 0–100 — pays out at match end (sentinel_circuit_design.md §5)
  gen: 0,              // restart generation — stale async turns check this and bail
};

// ---- host bindings ----------------------------------------------
// The renderer supplies these. Defaults are inert so the rules layer is
// usable (and testable) with no host at all.
const io = {
  sleep: () => Promise.resolve(),
  emit: () => {},
  changed: () => {},
};
export function bindIO(next) { Object.assign(io, next); }

const roll100 = () => Math.floor(S.rng() * 100) + 1;
const rollRange = (lo, hi) => lo + Math.floor(S.rng() * (hi - lo + 1));

// ---- map / units ------------------------------------------------
function buildMap() {
  S.map = MAP_SRC.map(row => [...row].map(c => c === "█" ? FULL : c === "▪" ? HALF : FLOOR));
}
function makeUnits() {
  S.units = [
    { id: 0, side: "op", name: "VESPER", x: 1, y: 9, hp: 10, maxHp: 10, aim: 75, mobility: 4, ap: 2, overwatch: false, alive: true },
    { id: 1, side: "op", name: "KOA",    x: 4, y: 9, hp: 10, maxHp: 10, aim: 75, mobility: 4, ap: 2, overwatch: false, alive: true },
    { id: 2, side: "op", name: "SABLE",  x: 7, y: 9, hp: 10, maxHp: 10, aim: 75, mobility: 4, ap: 2, overwatch: false, alive: true },
    { id: 3, side: "ho", name: "SYN-1",  x: 2, y: 0, hp: 8,  maxHp: 8,  aim: 65, mobility: 4, ap: 2, overwatch: false, alive: true },
    { id: 4, side: "ho", name: "SYN-2",  x: 5, y: 0, hp: 8,  maxHp: 8,  aim: 65, mobility: 4, ap: 2, overwatch: false, alive: true },
    { id: 5, side: "ho", name: "SYN-3",  x: 8, y: 0, hp: 8,  maxHp: 8,  aim: 65, mobility: 4, ap: 2, overwatch: false, alive: true },
  ];
  // Only hostiles carry morale. The player's operatives don't quit under
  // the player — they hold or they fall; conceding is a player verb, and
  // it doesn't exist yet.
  for (const u of S.units) {
    if (u.side === "ho") { u.morale = MORALE.start; u.maxMorale = MORALE.start; u.yielded = false; }
  }
}
export const inBounds = (x, y) => x >= 0 && x < W && y >= 0 && y < H;
export const passable = (x, y) => inBounds(x, y) && S.map[y][x] === FLOOR;
export const unitAt = (x, y) => S.units.find(u => u.alive && u.x === x && u.y === y);
export const living = side => S.units.filter(u => u.alive && u.side === side);
export const selected = () => S.units.find(u => u.id === S.selectedId && u.alive);

// ---- line of sight (Bresenham; FULL blocks, endpoints excluded) --
export function los(x0, y0, x1, y1) {
  let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
  let sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, err = dx + dy;
  let x = x0, y = y0;
  while (true) {
    if (!(x === x0 && y === y0) && !(x === x1 && y === y1) && S.map[y][x] === FULL) return false;
    if (x === x1 && y === y1) return true;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x += sx; }
    if (e2 <= dx) { err += dx; y += sy; }
  }
}

// ---- cover ------------------------------------------------------
// Cover objects orthogonally adjacent to the defender protect against
// attackers on that side (positive dot with the attacker direction).
export function coverBonus(def, att) {
  let best = 0;
  const vx = att.x - def.x, vy = att.y - def.y;
  for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
    const nx = def.x + dx, ny = def.y + dy;
    if (!inBounds(nx, ny) || S.map[ny][nx] === FLOOR) continue;
    if (dx * vx + dy * vy > 0) best = Math.max(best, S.map[ny][nx] === FULL ? 40 : 20);
  }
  return best;
}

// which adjacent cover tiles are actually shielding `def` from `att` —
// presentation uses this to light the protecting face
export function coveringTiles(def, att) {
  const out = [];
  const vx = att.x - def.x, vy = att.y - def.y;
  for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
    const nx = def.x + dx, ny = def.y + dy;
    if (!inBounds(nx, ny) || S.map[ny][nx] === FLOOR) continue;
    if (dx * vx + dy * vy > 0) out.push([nx, ny]);
  }
  return out;
}

// ---- firing solution -------------------------------------------
export function solution(att, def) {
  if (!los(att.x, att.y, def.x, def.y)) return null;
  const dist = Math.hypot(def.x - att.x, def.y - att.y);
  const range = dist <= 3 ? Math.round((3 - dist) * 4) : -Math.round((dist - 3) * 4);
  const cover = coverBonus(def, att);
  const pct = Math.max(5, Math.min(95, att.aim + range - cover));
  const critPct = cover === 0 ? 45 : 15;
  return { pct, base: att.aim, range, cover, flanked: cover === 0, critPct };
}

// ---- movement (BFS, 4-directional) ------------------------------
export function reachable(u, maxCost) {
  const cost = new Map(), parent = new Map();
  const key = (x, y) => x + "," + y;
  cost.set(key(u.x, u.y), 0);
  const q = [[u.x, u.y]];
  while (q.length) {
    const [x, y] = q.shift();
    const c = cost.get(key(x, y));
    if (c >= maxCost) continue;
    for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
      const nx = x + dx, ny = y + dy, k = key(nx, ny);
      if (!passable(nx, ny) || unitAt(nx, ny) || cost.has(k)) continue;
      cost.set(k, c + 1); parent.set(k, [x, y]); q.push([nx, ny]);
    }
  }
  return { cost, parent };
}
export function pathTo(parent, x, y) {
  const path = [];
  let cur = [x, y];
  while (cur) { path.unshift(cur); cur = parent.get(cur[0] + "," + cur[1]); }
  return path.slice(1); // drop start tile
}

// ---- rating -----------------------------------------------------
// The crowd meter (sentinel_circuit_design.md §5): flashy, risky play
// builds it, safe play bleeds it, and it pays out at match end whether
// you won or not — a watchable loss still sells. Deliberately the
// opposite of XCOM's incentive structure: the Circuit pays you to be
// worth watching, and makes you decide what that costs.
//
// Same discipline as morale: pure arithmetic on events that already
// happen — no RNG draws — and rating events are never log lines, so the
// golden transcripts captured before the meter existed replay untouched.
// The meter is visible on the panel, not in the comms log.
//
// The knife in the numbers: ANY down is +3, including your own people.
// Blood is content. "Playing to the crowd versus keeping your people
// safe" is the design's named loop, and this is it, running live.
export const RATING = {
  start: 50,
  hit: 2, crit: 2, longShot: 2, flank: 2, open: 1,   // landed op fire, itemized
  overwatch: -2,       // the player's turtle verb; the AI's overwatch is not your meter
  stalledAp: -1,       // per unspent AP at end of turn — stalling isn't content
  down: 3,             // anyone. the crowd did not come for chess
  yield: 2, finish: 4, spare: -2,                    // mercy costs purse
  pursePerPoint: 10,   // credits per rating point at match end
};

function addRating(delta) {
  if (S.gameOver || delta === 0) return;
  // emit what actually happened, not what was asked for: at the clamp
  // bounds the applied delta shrinks, and a change the clamp fully ate is
  // not an event — consumers that sum deltas must never drift from total
  const next = Math.max(0, Math.min(100, S.rating + delta));
  const applied = next - S.rating;
  if (applied === 0) return;
  S.rating = next;
  io.emit({ type: "rating", delta: applied, total: S.rating });
  io.changed();
}

// ---- morale -----------------------------------------------------
// Hostiles fight for a purse, not a cause (sentinel_circuit_design.md §5:
// "surrender, on camera"). Morale only moves down, and only for things a
// fighter can perceive: fire that lands on them, a squadmate dropping, a
// squadmate quitting. Perception is squad-wide by design, not gated on
// sightlines — the yard is small and gunfire carries, and morale is meant
// to be legible squad state, not a per-witness simulation the player has
// to audit unit by unit. (Per-witness morale is a real future fork — an
// execution as a performance wants an audience — but it belongs to the
// rating/witness layer, not before it.) Zero is a yield — deterministic,
// no roll — because a collapse the player can see coming is one they can
// play around, or play for. None of this touches the RNG stream, which is
// why the golden transcripts captured before this mechanic existed still
// replay byte-for-byte.
export const MORALE = { start: 8, hit: 2, crit: 4, mateDown: 3, mateYield: 2 };

function drainMorale(u, amt) {
  if (u.morale === undefined || !u.alive || u.yielded) return;
  u.morale = Math.max(0, u.morale - amt);
  if (u.morale === 0) unitYields(u);
}

function unitYields(u) {
  u.yielded = true;
  u.overwatch = false;
  u.ap = 0;
  io.emit({ type: "yield", unit: u });
  addRating(RATING.yield);   // someone breaking on camera is content
  // one fighter quitting makes it easier for the next to quit
  for (const v of living("ho")) if (v !== u) drainMorale(v, MORALE.mateYield);
  checkEnd();
}

// ---- combat -----------------------------------------------------
async function fireShot(att, def, aimMod = 0, label = "") {
  const g = S.gen;
  const sol = solution(att, def);
  if (!sol) return false;
  const pct = Math.max(5, Math.min(95, sol.pct + aimMod));
  io.emit({ type: "fire", att, def });
  io.changed();
  await io.sleep(280);
  if (g !== S.gen) return false;  // restarted mid-shot: don't touch the fresh RNG stream
  const r = roll100();
  if (r <= pct) {
    let dmg = rollRange(3, 5);
    const crit = roll100() <= sol.critPct;
    if (crit) dmg += 3;
    def.hp = Math.max(0, def.hp - dmg);
    io.emit({ type: "shot", hit: true, att, def, dmg, crit, pct, roll: r, label });
    // the crowd scores the player's marksmanship, itemized for flash:
    // distance, a flanked target, standing in the open to take the shot
    if (att.side === "op") {
      addRating(RATING.hit
        + (crit ? RATING.crit : 0)
        + (sol.range < 0 ? RATING.longShot : 0)
        + (sol.flanked ? RATING.flank : 0)
        + (coverBonus(att, def) === 0 ? RATING.open : 0));
    }
    if (def.hp === 0) {
      def.alive = false;
      def.overwatch = false;
      io.emit({ type: "down", unit: def });
      addRating(RATING.down);   // anyone's blood — including yours
      // the drain no-ops for operatives, who have no morale to lose
      for (const v of living(def.side)) drainMorale(v, MORALE.mateDown);
    } else {
      drainMorale(def, crit ? MORALE.crit : MORALE.hit);
    }
  } else {
    io.emit({ type: "shot", hit: false, att, def, pct, roll: r, label });
  }
  io.changed();
  checkEnd();
  return true;
}

// overwatch: fires once per watcher at the first hostile step it sees
async function overwatchCheck(mover) {
  const watchers = S.units.filter(u => u.alive && u.overwatch && u.side !== mover.side);
  for (const w of watchers) {
    if (!mover.alive) break;
    if (los(w.x, w.y, mover.x, mover.y)) {
      w.overwatch = false;
      io.emit({ type: "overwatch-trigger", unit: w });
      await fireShot(w, mover, -15, "reaction-");
    }
  }
}

async function animateMove(u, path) {
  const g = S.gen;
  for (const [x, y] of path) {
    u.x = x; u.y = y;
    io.changed();
    await io.sleep(70);
    if (g !== S.gen) return;
    await overwatchCheck(u);
    // a mover who yields under overwatch fire stops in their tracks
    if (g !== S.gen || !u.alive || u.yielded || S.gameOver || S.decision) break;
  }
}

function checkEnd() {
  if (S.gameOver) return;
  const ho = living("ho");
  if (ho.length === 0) { endGame("win"); return; }
  if (living("op").length === 0) { endGame("loss"); return; }
  // Every hostile still standing has yielded: the fight is settled, the
  // match is not. Hold here — the spare/finish call is the player's, and
  // it is the whole point of the mechanic.
  if (!S.decision && ho.every(u => u.yielded)) {
    S.decision = true;
    S.turn = "op";
    S.targetMode = false;
    io.emit({ type: "yield-decision", count: ho.length });
    io.changed();
  }
}

function endGame(result) {
  S.gameOver = result;
  // the payout: rating converts to purse whether you won or not — a
  // watchable loss still sells (sentinel_circuit_design.md §5)
  io.emit({ type: "end", result, rating: S.rating, purse: S.rating * RATING.pursePerPoint });
  io.changed();   // spare() ends the match with no action following — the panel must not go stale
}

// ---- player actions ---------------------------------------------
export function selectUnit(u) {
  if (!u || u.side !== "op" || !u.alive) return;
  S.selectedId = u.id; S.targetMode = false;
  io.emit({ type: "select", unit: u });
  io.changed();
}

export function cycleSelect() {
  const ops = living("op").filter(u => u.ap > 0);
  const pool = ops.length ? ops : living("op");
  if (!pool.length) return;
  const i = pool.findIndex(u => u.id === S.selectedId);
  selectUnit(pool[(i + 1) % pool.length]);
}

export async function tryMove(u, x, y) {
  if (S.decision) return;
  const { cost, parent } = reachable(u, u.mobility * u.ap);
  const c = cost.get(x + "," + y);
  if (c === undefined || c === 0) return;
  S.busy = true;
  u.ap -= c <= u.mobility ? 1 : 2;
  S.targetMode = false;
  await animateMove(u, pathTo(parent, x, y));
  S.busy = false;
  io.changed();
  autoAdvance();
}

export async function tryShoot(att, def) {
  if (def.yielded) return tryFinish(att, def);   // you don't roll dice at a kneeling fighter
  if (S.decision || att.ap <= 0 || !solution(att, def)) return;
  S.busy = true;
  att.ap = 0;            // firing ends the unit's activation
  S.targetMode = false;
  await fireShot(att, def);
  S.busy = false;
  io.changed();
  autoAdvance();
}

// An execution is a choice, not a gamble: no roll, no crit, no miss.
// Mid-fight it is still an activation — it costs the action and needs the
// sightline. Once every hostile has yielded (S.decision) the fight is
// over, the economy with it, and the only cost left is the one on record.
export async function tryFinish(att, def) {
  // turn authority is enforced here, not left to the renderer: this verb
  // is only ever the player's, on the player's turn, one at a time
  if (S.busy || S.gameOver || S.turn !== "op") return;
  if (!att || !def || !att.alive || att.side !== "op") return;
  if (!def.alive || !def.yielded) return;
  if (!S.decision) {
    if (att.ap <= 0 || !los(att.x, att.y, def.x, def.y)) return;
    att.ap = 0;
  }
  const g = S.gen;
  S.busy = true;
  S.targetMode = false;
  io.emit({ type: "fire", att, def });
  io.changed();
  await io.sleep(280);
  if (g !== S.gen) return;                     // restarted: the new encounter owns S.busy now
  if (S.gameOver) { S.busy = false; return; }  // ended out from under us: release the lock
  def.hp = 0;
  def.alive = false;
  io.emit({ type: "finish", att, def });
  addRating(RATING.finish);   // the crowd came for a finish
  // a surrendered mate dying breaks the ones still fighting — heard as much as seen
  for (const v of living("ho")) drainMorale(v, MORALE.mateDown);
  S.busy = false;
  io.changed();
  checkEnd();
  autoAdvance();
}

// accept every standing yield and end the match
export function spare() {
  if (!S.decision || S.gameOver || S.busy) return;
  io.emit({ type: "spared", units: living("ho").filter(u => u.yielded) });
  addRating(RATING.spare);   // mercy costs purse — what it buys lives elsewhere
  endGame("win");
}

export function setOverwatch(u) {
  if (S.decision || u.ap <= 0) return;
  u.overwatch = true;
  u.ap = 0;
  S.targetMode = false;
  io.emit({ type: "overwatch-set", unit: u });
  // the player's turtle verb bleeds the meter; the AI holding an angle is
  // not the player's show (enemy overwatch is set directly in enemyTurn)
  if (u.side === "op") addRating(RATING.overwatch);
  io.changed();
  autoAdvance();
}

function autoAdvance() {
  if (S.gameOver || S.decision || S.turn !== "op") return;
  const cur = selected();
  if (cur && cur.ap > 0) return;
  const next = living("op").find(u => u.ap > 0);
  if (next) selectUnit(next);
}

// ---- enemy turn -------------------------------------------------
function bestShotFrom(u) {
  let best = null;
  for (const t of living("op")) {
    const sol = solution(u, t);
    if (!sol) continue;
    if (!best || sol.pct > best.sol.pct || (sol.pct === best.sol.pct && t.hp < best.target.hp)) {
      best = { target: t, sol };
    }
  }
  return best;
}

function bestMoveTile(u) {
  // score reachable tiles: want LOS + good shot, cover from nearest threat, closing distance
  const { cost, parent } = reachable(u, u.mobility);
  let best = null;
  const ops = living("op");
  if (!ops.length) return null;
  for (const k of cost.keys()) {
    const [x, y] = k.split(",").map(Number);
    if (x === u.x && y === u.y) continue;
    const ghost = { ...u, x, y };
    const near = ops.reduce((a, b) =>
      Math.hypot(a.x - x, a.y - y) < Math.hypot(b.x - x, b.y - y) ? a : b);
    const dist = Math.hypot(near.x - x, near.y - y);
    const shot = bestShotFrom(ghost);
    let score = -dist * 2 + coverBonus(ghost, near) * 0.6;
    score += shot ? shot.sol.pct * 0.5 : -25;
    if (!best || score > best.score) best = { x, y, score, parent };
  }
  return best;
}

function nearestOp(u) {
  const ops = living("op");
  if (!ops.length) return null;
  return ops.reduce((a, b) =>
    Math.hypot(a.x - u.x, a.y - u.y) < Math.hypot(b.x - u.x, b.y - u.y) ? a : b);
}

export async function enemyTurn() {
  const g = S.gen;
  S.busy = true;
  S.turn = "ho";
  S.targetMode = false;
  io.emit({ type: "turn", side: "ho" });
  io.changed();
  await io.sleep(400);
  if (g !== S.gen) return;

  for (const u of S.units.filter(v => v.side === "ho")) {
    if (g !== S.gen) return;
    if (!u.alive || u.yielded || S.gameOver || S.decision) continue;
    u.ap = 2; u.overwatch = false;
    let guard = 0;
    while (u.ap > 0 && u.alive && !S.gameOver && g === S.gen && guard++ < 4) {
      const shot = bestShotFrom(u);
      if (shot && shot.sol.pct >= 45) {
        u.ap = 0;
        await fireShot(u, shot.target);
        break;
      }
      // second action, no confident shot: hold in cover on overwatch
      // rather than potshotting; only fire marginal shots when caught in the open
      if (u.ap === 1) {
        const near = nearestOp(u);
        if (near && coverBonus(u, near) > 0) {
          u.overwatch = true; u.ap = 0;
          io.emit({ type: "overwatch-set", unit: u });
          break;
        }
        if (shot && shot.sol.pct >= 30) {
          u.ap = 0;
          await fireShot(u, shot.target);
          break;
        }
      }
      const mv = bestMoveTile(u);
      if (mv) {
        u.ap -= 1;
        await animateMove(u, pathTo(mv.parent, mv.x, mv.y));
      } else if (shot) {
        u.ap = 0;
        await fireShot(u, shot.target);
      } else {
        u.overwatch = true; u.ap = 0;
        io.emit({ type: "overwatch-set", unit: u });
      }
      await io.sleep(150);
    }
    await io.sleep(200);
  }
  if (g !== S.gen) return;

  // if the decision moment arrived mid-turn (overwatch broke them), the
  // turn cycle is over — checkEnd already handed control to the player
  if (!S.gameOver && !S.decision) {
    S.turn = "op";
    for (const u of living("op")) { u.ap = 2; u.overwatch = false; }
    io.emit({ type: "turn", side: "op" });
    const first = living("op")[0];
    if (first) S.selectedId = first.id;
  }
  S.busy = false;
  io.changed();
}

export function endPlayerTurn() {
  if (S.busy || S.gameOver || S.decision || S.turn !== "op") return;
  // unspent AP is dead air — the crowd bleeds off while you stall
  const stalled = living("op").reduce((n, u) => n + u.ap, 0);
  if (stalled > 0) addRating(RATING.stalledAp * stalled);
  for (const u of living("op")) u.ap = 0;
  return enemyTurn();
}

// ---- lifecycle --------------------------------------------------
export function restart(seed) {
  S.gen++;   // abandon any in-flight animation or AI turn
  S.seed = seed >>> 0;
  S.rng = mulberry32(S.seed);
  buildMap();
  makeUnits();
  S.turn = "op"; S.selectedId = 0; S.targetMode = false; S.busy = false; S.gameOver = null; S.decision = false; S.rating = RATING.start;
  io.emit({ type: "reset" });
  io.emit({ type: "mission" });
  io.emit({ type: "turn", side: "op" });
  io.changed();
}

/* ---- one formatter, two skins ----------------------------------
   The browser wraps fragments in <span class>; the headless test passes
   them straight through. Keeping a single formatter is what lets the
   test assert against exactly the text a player sees in the comms log. */
export function formatEvent(ev, wrap = t => t) {
  const n = u => wrap(u.name, u.side);
  switch (ev.type) {
    case "mission":
      return wrap("— KESTREL YARD — clear the Syndicate crew —", "sys");
    case "turn":
      return wrap(ev.side === "op" ? "— OPERATIVE TURN —" : "— HOSTILE TURN —", "sys");
    case "shot":
      return ev.hit
        ? `${n(ev.att)} ${ev.label}hits ${n(ev.def)} — ` +
          wrap(`${ev.dmg} dmg${ev.crit ? " CRIT" : ""}`, "hit") +
          ` (${ev.pct}%, rolled ${ev.roll})`
        : `${n(ev.att)} ${ev.label}misses ${n(ev.def)} (${ev.pct}%, rolled ${ev.roll})`;
    case "down":
      return `${n(ev.unit)} is ${wrap("down", ev.unit.side === "op" ? "ho" : "hit")}.`;
    case "overwatch-set":
      return `${n(ev.unit)} sets ${wrap("overwatch", "sys")}`;
    case "overwatch-trigger":
      return `${n(ev.unit)} ${wrap("overwatch triggered", "sys")}`;
    case "yield":
      return `${n(ev.unit)} ${wrap("yields", "sys")} — weapon down, hands up.`;
    case "yield-decision":
      return wrap("— THE FIGHT IS OVER — spare them [⏎] or finish them [click] —", "sys");
    case "finish":
      return `${n(ev.att)} ${wrap("finishes", "hit")} ${n(ev.def)}. The yard sees it.`;
    case "spared":
      return `${ev.units.map(u => n(u)).join(", ")} ${wrap("spared", "sys")} — they walk.`;
    default:
      return null;   // fire / select / reset / end / rating are not log lines
      // (rating deliberately so: the meter lives on the panel, and keeping
      // it out of the log is what lets the pre-meter golden transcripts
      // replay untouched)
  }
}
