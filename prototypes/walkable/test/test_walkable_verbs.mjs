// Executes the walkable page's verb claims in headless chromium.
//
// Serves the repo root, boots the page against synthetic sheets, and
// drives the keyboard through every verb plus the roster fault states.
// Verb durations are measured IN PAGE via rAF: evaluate round-trips can
// be slower than a 4-frame flinch, so sleep-then-read checks lie —
// that lesson is why the watcher exists (caught building this harness).
//
// Real composed sheets for Cipher and the owned crew's canvases, plus
// every tracked render96 destination, are backed up before the run and
// restored after — including when setup itself fails, and a
// backup stranded by a hard-killed run is reinstated on the next start.
//
// Run:  cd prototypes/walkable/test
//       npm install && npx playwright install chromium
//
// A door walk holds Shift. That is traversal, not a claim about gaits: the
// verbs harness owns the gait claims, and this needs the body at a
// threshold. It matters because `dt` is clamped at 0.05 in the room's frame
// loop and headless rAF runs ~5fps, so a body covers 0.25x its speed per
// REAL second. The walk becoming the default (PR #125) took the door walk
// from ~5.7s to ~12.6s against a 30s timeout, and that margin is what went
// red on a loaded runner (caught in CI on PR #127).
//       node test_walkable_verbs.mjs
import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openRun, openSeason, applyCard } from "../../run-core/run.js";
// The room may never import the rules; this harness may, and that asymmetry
// is the point. The room derives an operative's name from its sheet slug,
// so its two identifiers cannot drift from each other — but nothing inside
// the room can tell whether that name still matches the one the YARD reports
// in a card's `down`. If those drift, every card silently leaves the whole
// squad idle with no fault. Holding the two rosters against each other here
// makes that fail in CI instead of on a player's knee (caught in review).
import {
  S as RULES_S, restart as rulesRestart,
  rosterValid, CANON_ROSTER, OP_MAX_HP,
} from "../../tactical-core/rules.js";
import { DRAG_GOLDEN } from "../../tactical-core/drag-golden.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const GEN = path.join(HERE, "make_synthetic_sheets.py");
const FIGHTERS = ["cipher", "vesper", "koa", "sable"];
// syn rides the backup law too: the generator writes his tracked render
// dir since the squad-combat phase, though the ROOM never stages him.
const SQUAD_FIGHTERS = ["vesper", "koa", "sable", "syn"];
const sheetsDir = fighter => path.join(ROOT, "assets", "sprites", "composed", fighter);
const backupDir = fighter => sheetsDir(fighter) + ".harness-backup";
// The render sheets are TRACKED (assets/original is ours), which makes
// the backup discipline more binding, not less: an uncommitted local
// re-frame must survive a harness run exactly as the composed roster does
const RENDER96 = path.join(ROOT, "assets", "original", "cipher_render", "sheets96");
const squadRender96 = fighter => path.join(
  ROOT, "assets", "original", "squad_render", "sheets96", fighter);
const TRACKED_RENDER_DIRS = [RENDER96, ...SQUAD_FIGHTERS.map(squadRender96)];
const trackedBackup = dir => dir + ".harness-backup";
const PY = process.platform === "win32" ? "python" : "python3";
const PORT = process.env.WALKABLE_TEST_PORT ?? "8093";
const URL = `http://localhost:${PORT}/prototypes/walkable/`;

function chronicleKey(value) {
  const identity = JSON.stringify({
    seed: value.seed,
    roster: value.roster.map(person => ({ name: person.name, hp: person.hp })),
    record: value.record,
  });
  let hash = 0x811c9dc5;
  for (let i = 0; i < identity.length; i++) {
    hash ^= identity.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

function gen(mode) {
  const r = spawnSync(PY, [GEN, mode, FIGHTERS.join(",")], { stdio: "inherit" });
  if (r.status !== 0) throw new Error(`sheet generation failed (${mode})`);
}
const clearSheets = () => {
  for (const fighter of FIGHTERS) {
    fs.rmSync(sheetsDir(fighter), { recursive: true, force: true });
  }
};

function card(seed, down, cert = "certified") {
  return {
    seed, result: "loss", rating: 1, purse: 10,
    ledger: { walked: 0, finished: 0, lost: down.length },
    down, derivedEvents: [], cert,
    matchId: cert === "certified" ? "0123456789abcdef0123456789abcdef" : null,
    rules: "test-rules", at: `2026-08-05T00:00:0${seed}Z`,
  };
}

function runWith(cards) {
  let run = openRun("2026-08-05T00:00:00Z");
  for (const item of cards) {
    const out = applyCard(run, item);
    if (!out.accepted) throw new Error(`fixture card refused: ${out.why}`);
    run = out.run;
  }
  return run;
}

const STUB_FILED_AT = "2026-08-16T00:00:00.000Z";
function filedResponse(asked, {
  id,
  result,
  rating,
  purse,
  ledger,
  rules = "stub-rules",
  derivedEvents = [],
  includeDerivedEvents = true,
  fingerprint = asked.fingerprint,
  lines = 1,
  transcript = ["stub transcript"],
} = {}) {
  const certificate = {
    certified: true,
    rules,
    ledger,
    seed: asked.seed,
    roster: asked.roster,
    rosterHash: "00000000",
    result,
    rating,
    purse,
    commands: asked.record.length,
    lines,
    fingerprint,
    transcript,
  };
  if (includeDerivedEvents) certificate.derivedEvents = derivedEvents;
  return {
    filed: true,
    existing: false,
    id,
    filed_at: STUB_FILED_AT,
    ...certificate,
  };
}

// A playwright whose version tag doesn't match a pre-provisioned browser
// dir refuses to launch; fall back to scanning the provisioned root.
async function launch() {
  try {
    return await chromium.launch();
  } catch (err) {
    const roots = [process.env.PLAYWRIGHT_BROWSERS_PATH, "/opt/pw-browsers"].filter(Boolean);
    for (const root of roots) {
      if (!fs.existsSync(root)) continue;
      for (const d of fs.readdirSync(root)) {
        const exe = path.join(root, d, "chrome-linux", "chrome");
        if (d.startsWith("chromium") && fs.existsSync(exe)) {
          return chromium.launch({ executablePath: exe });
        }
      }
    }
    throw err;
  }
}

let failures = 0;
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures++;
}

// ---- setup: preserve real sheets ----------------------------------
// One harness at a time. Two overlapping runs would each claim the same
// backup dirs: the second would reinstate the first's live backup as
// "stranded", and after the first restores, the second's cleanup deletes
// the originals with no backup left — the gitignored sheets would be
// gone for good (caught in review). The lock is an atomic mkdir; a
// hard-killed run strands it, and the next run refuses with its name
// rather than guessing the coast is clear.
const LOCK = path.join(HERE, ".harness-lock");
try {
  fs.mkdirSync(LOCK);
} catch {
  console.error(`another harness run appears live (${LOCK} exists) — `
    + "refusing to touch the backups; remove the dir if that run is dead");
  process.exit(1);
}

// A backup left by a run that died before restoring IS the real
// artifact: reinstate it, never delete it. This also makes a hard-killed
// run (no finally) self-healing instead of data-destroying on the next
// start (caught in review: setup failures used to strand the backup,
// and the next run's cleanup would have eaten it).
//
// These renames run before the big try below, so a setup crash would
// strand the lock and block the very self-heal that fixes the rest —
// every later run would refuse at the door. A setup failure frees the
// lock on its way out; the stranded BACKUPS stay for the next start's
// reinstate, which is now reachable again (caught in review).
try {
  for (const fighter of FIGHTERS) {
    if (fs.existsSync(backupDir(fighter))) {
      fs.rmSync(sheetsDir(fighter), { recursive: true, force: true });
      fs.renameSync(backupDir(fighter), sheetsDir(fighter));
    }
    if (fs.existsSync(sheetsDir(fighter))) {
      fs.renameSync(sheetsDir(fighter), backupDir(fighter));
    }
  }
  for (const renderDir of TRACKED_RENDER_DIRS) {
    const renderBak = trackedBackup(renderDir);
    if (fs.existsSync(renderBak)) {
      // Louder than the composed reinstate on purpose: sheets96 is TRACKED,
      // so a run that died mid-flight left synthetic fixtures sitting in the
      // repo as commit-able source art until this line ran.
      console.error(`STRANDED sheets96 backup found at ${renderBak} — a previous run died `
        + "before restoring; reinstating the real strips now. Until this "
        + "moment the tracked sheets96 dir held synthetic fixtures.");
      fs.rmSync(renderDir, { recursive: true, force: true });
      fs.renameSync(renderBak, renderDir);
    }
    if (fs.existsSync(renderDir)) {
      fs.renameSync(renderDir, renderBak);
    }
  }
} catch (err) {
  fs.rmSync(LOCK, { recursive: true, force: true });
  throw err;
}

// From here on, every failure path — server, browser launch, the checks
// themselves — runs through the finally that restores the real sheets.
let server = null;
let browser = null;
let page = null;

async function boot(query = "") {
  await page.goto(URL + query);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites), null, { timeout: 10000 });
}
const ds = k => page.evaluate(k => document.getElementById("cv").dataset[k], k);

// Arm an in-page watcher for a verb, fire its key, and return how many
// ms the verb owned the body. -1: never started. -2: never ended.
async function measureVerb(key, name) {
  await page.evaluate(n => {
    const cv = document.getElementById("cv");
    window.__verbDone = new Promise(res => {
      let t0 = null;
      const begin = performance.now();
      function tick(t) {
        if (t0 === null && cv.dataset.action === n) t0 = t;
        else if (t0 !== null && cv.dataset.action !== n) return res(t - t0);
        if (t - begin > 8000) return res(t0 === null ? -1 : -2);
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, name);
  await page.keyboard.press(key);
  return page.evaluate(() => window.__verbDone);
}

// waitForFunction polls in-page, so steady states are race-free
const waitAction = (name, timeout = 3000) =>
  page.waitForFunction(n => document.getElementById("cv").dataset.action === n, name, { timeout })
    .then(() => true, () => false);

// Record EVERY rendered frame for a span, not just the steady states.
// Polling can only see where a verb ended up; a one-frame detour or a
// light that leads its own flash is invisible to it — both shipped past
// the polling tests and were caught in review instead.
async function recordFrames(key, ms) {
  await page.evaluate(d => {
    const cv = document.getElementById("cv");
    window.__trace = new Promise(res => {
      const seen = [];
      const begin = performance.now();
      function tick(t) {
        seen.push(`${cv.dataset.action}:${cv.dataset.frame}:${cv.dataset.light}`);
        if (t - begin > d) return res(seen);
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, ms);
  if (key) await page.keyboard.press(key);
  const raw = await page.evaluate(() => window.__trace);
  // collapse consecutive duplicates: what matters is the sequence of
  // distinct rendered states, not how many rAFs each one survived
  return raw.filter((v, i) => i === 0 || v !== raw[i - 1])
    .map(v => {
      const [a, f, l] = v.split(":");
      return { a, f: +f, l: +l, light: l };
    });
}

// The squad has no player-action dataset, so record one named body's
// published strip frame directly. An in-page rAF trace can prove the loop
// advances without guessing between Node-side polls.
async function recordSquadFrames(fighter, ms) {
  return page.evaluate(({ name, duration }) => new Promise(res => {
    const cv = document.getElementById("cv");
    const seen = [];
    const begin = performance.now();
    function tick(t) {
      const entry = (cv.dataset.squadSprites ?? "").split(",")
        .find(value => value.startsWith(`${name}:`));
      if (entry) {
        const [, action, facing, frame] = entry.split(":");
        seen.push({ t, action, facing, frame: +frame });
      }
      if (t - begin > duration) return res(seen);
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }), { name: fighter, duration: ms });
}

try {
  // ---- server + browser, inside the restoring scope ----------------
  server = spawn(PY, ["-m", "http.server", PORT], { cwd: ROOT, stdio: "ignore" });
  let up = false;
  for (let i = 0; i < 50 && !up; i++) {
    up = await fetch(`http://localhost:${PORT}/`).then(r => r.ok, () => false);
    if (!up) await new Promise(r => setTimeout(r, 200));
  }
  if (!up) throw new Error(`server never came up on :${PORT}`);

  browser = await launch();
  page = await browser.newPage();
  page.on("pageerror", e => { console.log("PAGEERROR " + e); failures++; });

  // ---- the composed roster -----------------------------------------
  gen("full");
  gen("slice96");
  await boot("?body=composed");
  check("composed roster boots", (await ds("sprites")) === "ready");
  check("roster reads composed", (await ds("roster")) === "composed");
  check("BODY cell says COMPOSED / READY",
    (await page.textContent("#body-state")) === "COMPOSED / READY");
  await page.waitForFunction(() =>
    (document.getElementById("cv").dataset.squadSprites ?? "").split(",").length === 4);
  const freshSquad = await ds("squad");
  const freshSprites = await ds("squadSprites");
  check("all four owned people render in the room, including the bench",
    (freshSprites ?? "").split(",").length === 4
      && ["vesper", "koa", "sable", "nix"].every(name => freshSprites.includes(`${name}:`)),
    freshSprites);
  check("a fresh run leaves the whole owned roster idle",
    freshSquad === "vesper:idle,koa:idle,sable:idle,nix:idle", freshSquad);

  // The room stages a body for every operative the yard fields, matched by
  // the slug/name relationship the room actually uses at runtime
  // (fighter.toUpperCase() === the op name in a card's `down`).
  rulesRestart(0xdeadbeef);
  const ops = RULES_S.units.filter(u => u.side === "op").map(u => u.name).sort();
  const staged = (freshSquad ?? "").split(",")
    .map(entry => entry.split(":")[0].toUpperCase()).sort();
  check("the room stages a body for every operative the yard fields",
    ops.every(name => staged.includes(name)),
    `yard ${ops.join(",")} vs room ${staged.join(",")}`);

  // ---- the roster the room DEALS ------------------------------------
  // `architecture/roster_in_the_match.md`. The room now deals WHO fights
  // rather than both sides happening to name the same three, so this
  // stops being a drift check and becomes the contract check: what the
  // room deals must be a roster the rules core would field, and — while
  // nothing has decided otherwise — the canonical three at full strength.
  //
  // The asymmetry is the point and it is unchanged: this file may import
  // the rules, the room may not. The room publishes its wire form and
  // the rules core says whether it is a roster.
  const fielded = (await ds("fielded")) ?? "";
  const dealt = fielded.split(",").map(part => {
    const [name, hp] = part.split(":");
    return { name, hp: Number(hp) };
  });
  check("the room publishes the squad it deals", /^[A-Z]+:\d+(,[A-Z]+:\d+){2}$/.test(fielded), fielded);
  check("and it is a roster the rules core would field",
    rosterValid(dealt), fielded);
  check("the dealt squad is the canonical three at full strength",
    JSON.stringify(dealt) === JSON.stringify(CANON_ROSTER.map(f => ({ ...f }))),
    `${fielded} vs ${CANON_ROSTER.map(f => `${f.name}:${f.hp}`).join(",")}`);
  check("the room's full-strength constant is the rules core's ceiling",
    dealt.every(f => f.hp === OP_MAX_HP), `${fielded} vs ${OP_MAX_HP}`);

  const freshPanel = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("the run publishes stable people, a lineup, and the bench",
    (await ds("lineup")) === "vesper,koa,sable"
      && (await ds("bench")) === "nix"
      && /nix:NIX:ember-winter-entry/.test(await ds("owned")),
    `${await ds("owned")} · ${await ds("lineup")} · ${await ds("bench")}`);
  check("the visible bench names NIX's authored faction entrance and reason",
    /BENCH · NIX · EMBER COLONIES/.test(freshPanel)
      && /north valley entered a defender because winter was bad/i.test(freshPanel),
    freshPanel);

  await page.keyboard.press("KeyB");
  const substituted = (await ds("fielded")).split(",").map(part => {
    const [name, hp] = part.split(":");
    return { name, hp: Number(hp) };
  });
  check("B makes a real lineup decision by stable id",
    (await ds("bench")) === "vesper" && (await ds("lineup")) === "koa,sable,nix",
    `${await ds("lineup")} · bench ${await ds("bench")}`);
  check("the substitute reaches the same exact three-entry yard contract",
    rosterValid(substituted)
      && substituted.map(person => person.name).join(",") === "KOA,SABLE,NIX"
      && substituted.every(person => Object.keys(person).length === 2),
    await ds("fielded"));
  // Return the live room to its authored opening lineup; later fixtures also
  // overwrite storage, but this proves the rotation is a closed decision.
  await page.keyboard.press("KeyB");
  await page.keyboard.press("KeyB");
  await page.keyboard.press("KeyB");
  check("the bench rotation returns to the authored opening lineup",
    (await ds("fielded")) === "VESPER:10,KOA:10,SABLE:10", await ds("fielded"));

  // newest first after these three: struck KOA, counted SABLE, old
  // counted VESPER. VESPER remains in cumulative wounds and KOA is the
  // newest visual aftermath, but only SABLE belongs on a knee.
  const aftermath = runWith([
    card("1", ["VESPER"]),
    card("2", ["SABLE"]),
    card("3", ["KOA"], "struck"),
  ]);
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)), aftermath);
  await boot("?body=composed");
  await page.waitForFunction(() => !!document.getElementById("cv").dataset.squadSprites);
  const aftermathSquad = await ds("squad");
  check("squad posture follows the last counted card",
    aftermathSquad === "vesper:idle,koa:idle,sable:kneel,nix:idle", aftermathSquad);
  // The discrimination, stated as the claim rather than as a string: VESPER
  // went down on an EARLIER counted card, so she is in the cumulative tally
  // the panel shows and is NOT on a knee in the room. Order-independent on
  // purpose — summary() sorts wounded by count then stable id, which is
  // run-core's telemetry choice and not something this suite should pin here.
  const aftermathPanel = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  const woundLine = (aftermathPanel.match(/DOWN · ([^\n]*?)(?:RECENT|OPENED|$)/) ?? [])[1] ?? "";
  check("an old wound is in the panel and NOT on the body",
    /VESPER/.test(woundLine) && /SABLE/.test(woundLine)
      && aftermathSquad.includes("vesper:idle"),
    `panel wounds "${woundLine.trim()}" · squad ${aftermathSquad}`);

  const struckOnly = runWith([card("4", ["KOA"], "struck")]);
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)), struckOnly);
  await boot("?body=composed");
  const struckSquad = await ds("squad");
  check("a run with only struck cards leaves the whole squad idle",
    struckSquad === "vesper:idle,koa:idle,sable:idle,nix:idle", struckSquad);

  // ---- the front office: the room surfaces the season ----------------
  // Beat 2 of season-lite. The slate, the position, the next entry's
  // framing, the clocks and the pass verb all reach the surface, and the
  // door enforces what the panel says. Fixtures are built with run-core
  // itself (openSeason + applyCard, the modules the room consumes), so
  // every claim here is about the SURFACE, not the arithmetic.
  const TOUR = {
    id: "test-tour",
    entries: [
      { venue: "FIRST YARD",   host: "steel-syndicate", sanction: null },
      { venue: "SECOND COURT", host: null,              sanction: "covenant" },
      { venue: "THIRD FLOOR",  host: "lattice",         sanction: "lattice" },
    ],
  };
  const sOut = applyCard(openSeason("2026-08-11T00:00:00Z", TOUR), card("a", ["SABLE"]));
  if (!sOut.accepted) throw new Error(`season fixture refused: ${sOut.why}`);
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)), sOut.run);
  await boot("?body=composed");
  const panelText = async () =>
    (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  const pass = async () => {
    await page.keyboard.down("Shift");
    await page.keyboard.press("KeyP");
    await page.keyboard.up("Shift");
  };

  check("a restored season reaches the surface machine-readably",
    (await ds("season")) === "1/3:0:unfit", await ds("season"));
  let sPanel = await panelText();
  check("the panel names the slate and the position",
    /SLATE TEST-TOUR/.test(sPanel) && /STOP 2 OF 3/.test(sPanel), sPanel);
  check("the next entry's framing is on the surface, nulls said out loud",
    /NEXT · SECOND COURT · UNCLAIMED · SANCTIONED BY COVENANT/.test(sPanel), sPanel);
  check("the clocks are on the surface with their stops",
    /ROSTER UNFIT/.test(sPanel) && /SABLE 2 STOPS/.test(sPanel), sPanel);
  check("without a debt no dedication is offered, and the plain pass remains",
    (await page.$$(".dedicated-pass")).length === 0
      && (await page.$$(".plain-pass")).length === 1
      && /EVERY RUNNING CLOCK RECOVERS 1/.test(sPanel), sPanel);

  // the door enforces what the panel says: unfit means no deal, said as
  // a cut rather than a dead trigger — and no seam frame ever exists
  // Shift = run. Traversal, not a gait claim — see the header.
  await page.keyboard.down("Shift");
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const gated = await page.waitForFunction(() =>
    document.getElementById("cv").dataset.seam === "gated",
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  await page.keyboard.up("Shift");
  check("an unfit roster gates the door", gated);
  check("a gated door never opens the seam", !(await page.$("#seamframe")));
  // the walked refusal and the door's PUBLISHED answer are the same
  // function: this is what lets the witness suite assert the settling
  // branch off the published value alone, where walking is a footrace
  check("the walked refusal is the door's own published answer",
    (await ds("dealGate")) === "unfit", await ds("dealGate"));
  const gateCut = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
  check("the refusal says why and what heals it",
    /THE DEAL IS GATED/.test(gateCut) && /SABLE 2/.test(gateCut)
      && /SHIFT\+P/.test(gateCut), gateCut);

  await page.keyboard.press("KeyB");
  await page.keyboard.press("KeyB");
  await page.keyboard.press("KeyB");
  sPanel = await panelText();
  check("benching the recovering person makes the substituted lineup fit",
    (await ds("season")) === "1/3:0:fit"
      && (await ds("bench")) === "sable"
      && (await ds("fielded")) === "VESPER:10,KOA:10,NIX:10",
    `${await ds("season")} · ${await ds("fielded")} · bench ${await ds("bench")}`);
  check("the benched recovery stays visible without claiming the deal is gated",
    /RECOVERING · SABLE 2 STOPS/.test(sPanel) && !/ROSTER UNFIT/.test(sPanel), sPanel);
  await page.keyboard.press("KeyB");
  check("rotating back to the authored lineup restores the honest wound gate",
    (await ds("season")) === "1/3:0:unfit"
      && (await ds("fielded")) === "VESPER:10,KOA:10,SABLE:10",
    `${await ds("season")} · ${await ds("fielded")}`);

  // the pass verb: always legal, ticks the clocks, banks the entry
  await pass();
  check("a pass advances the slate and ticks the clock",
    (await ds("season")) === "2/3:1:unfit", await ds("season"));
  sPanel = await panelText();
  check("the passed entry is on the record with its venue",
    /PASSED/.test(sPanel) && /SECOND COURT/.test(sPanel), sPanel);
  check("the ticked clock reads one stop",
    /SABLE 1 STOP\b/.test(sPanel), sPanel);
  await pass();
  check("passing out the slate completes it and clears the clock",
    (await ds("season")) === "3/3:2:complete", await ds("season"));
  sPanel = await panelText();
  check("a complete slate says so and points at the close verb",
    /COMPLETE/.test(sPanel) && /NOTHING LEFT TO FIGHT/.test(sPanel), sPanel);

  // a complete slate gates the door with its own sentence
  await page.evaluate(() => { document.getElementById("cv").dataset.seam = "reset"; });
  // Shift = run. Traversal, not a gait claim — see the header.
  await page.keyboard.down("Shift");
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const gatedComplete = await page.waitForFunction(() =>
    document.getElementById("cv").dataset.seam === "gated",
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  await page.keyboard.up("Shift");
  check("a complete slate gates the door", gatedComplete);
  const completeCut = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
  check("and the cut says the slate is complete",
    /SLATE IS COMPLETE/.test(completeCut) && /NOTHING LEFT TO FIGHT/.test(completeCut),
    completeCut);
  check("the complete gate is published under its own reason",
    (await ds("dealGate")) === "complete", await ds("dealGate"));
  await pass();
  check("a pass on a complete slate is refused in the run's own words",
    /NOTHING LEFT TO PASS/.test(await panelText()), await panelText());

  // the toured season survives a reload — passes, clocks and all
  await boot("?body=composed");
  check("the season survives a reload",
    (await ds("season")) === "3/3:2:complete", await ds("season"));

  // a plain stored run stays plain: no slate, no season surface, and the
  // pass verb refused rather than invented — nothing is silently migrated
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)),
    runWith([card("5", ["VESPER"])]));
  await boot("?body=composed");
  check("a plain run reads none on the season surface",
    (await ds("season")) === "none", await ds("season"));
  // a plain run's door is always live — the recorded liberty the
  // settling COUNT exists for: nothing positional rides a plain card
  check("a plain run's door is never gated",
    (await ds("dealGate")) === "live", await ds("dealGate"));
  check("a plain run's panel carries no slate line",
    !/SLATE /.test(await panelText()), await panelText());
  await pass();
  check("a plain run has nothing to pass and says so",
    /NOTHING TO PASS/.test(await panelText()), await panelText());

  // A plain run deliberately leaves the door live while a card settles:
  // nothing positional rides the card, so two may bank in either order.
  // Hold card A at the edge, deal card B, then let A land while B owns the
  // live seam. A's settlement must not erase B's fielded snapshot (caught
  // in review on PR #135).
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)),
    openRun("2026-08-16T00:00:00Z"));
  let heldFile = null;
  let fileRequests = 0;
  const fileReply = (route, options = {}) => {
    const asked = JSON.parse(route.request().postData() ?? "{}");
    return {
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(filedResponse(asked, {
        id: "11111111111111111111111111111111",
        result: "win",
        rating: 7,
        purse: 70,
        ledger: { walked: 0, finished: 0, lost: 0 },
        ...options,
      })),
    };
  };
  await page.route(/\/file$/, route => {
    fileRequests++;
    if (fileRequests === 1) {
      heldFile = route;   // card A stays at ASKING THE EDGE…
      return;
    }
    return route.fulfill(fileReply(route));
  });
  await boot("?body=composed&deal=6");

  const walkPlainDoor = async () => {
    await page.keyboard.down("Shift");
    await page.keyboard.down("KeyW");
    await page.keyboard.down("KeyD");
    const opened = await page.waitForFunction(() => !!document.getElementById("seamframe"),
      null, { timeout: 30000 }).then(() => true, () => false);
    await page.keyboard.up("KeyW");
    await page.keyboard.up("KeyD");
    await page.keyboard.up("Shift");
    if (!opened) return null;
    await page.waitForFunction(() =>
      document.getElementById("seamframe")?.contentWindow.location.pathname
        .endsWith("/prototypes/tactical3d/index.html"),
    null, { timeout: 12000 });
    return (await page.$("#seamframe")).contentFrame();
  };
  const plainRoster = (await ds("fielded")).split(",").map(person => {
    const [name, hp] = person.split(":");
    return { name, hp: Number(hp) };
  });
  const postPlainCard = (frame, fingerprint) => frame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result",
      seed: "6", record: [["end"]], result: "win", rating: 7, purse: 70,
      ledger: { walked: 0, finished: 0, lost: 0 }, down: [],
      derivedEvents: [],
      roster: value.roster, fingerprint: value.fingerprint, lines: 1,
    }, window.parent.location.origin);
  }, { roster: plainRoster, fingerprint });

  const frameA = await walkPlainDoor();
  check("a plain run deals card A", frameA !== null);
  if (!frameA) throw new Error("the plain door never dealt card A");
  const cardAAsked = page.waitForRequest(/\/file$/, { timeout: 10000 })
    .then(() => true, () => false);
  await postPlainCard(frameA, "plain-a");
  const aHeld = await page.waitForFunction(() =>
    document.getElementById("cv").dataset.settling === "1",
  null, { timeout: 10000 }).then(() => true, () => false);
  const aAsked = await cardAAsked;
  check("card A waits at the edge", aHeld && aAsked && heldFile !== null,
    `${await ds("settling")} settling · ${fileRequests} requests`);
  if (!heldFile) throw new Error("card A never asked the stubbed edge");

  const frameB = await walkPlainDoor();
  check("the plain door deals card B before A settles", frameB !== null,
    `${await ds("dealGate")} · ${await ds("settling")} settling`);
  if (!frameB) throw new Error("the plain door did not deal card B mid-settlement");

  await heldFile.fulfill(fileReply(heldFile));
  const aLandedInsideB = await page.waitForFunction(() => {
    const cv = document.getElementById("cv");
    return cv.dataset.settling === "0"
      && !!document.getElementById("seamframe")
      && (cv.dataset.seam === "open" || cv.dataset.seam === "live");
  }, null, { timeout: 10000 }).then(() => true, () => false);
  check("card A lands while card B owns the seam", aLandedInsideB,
    `${await ds("seam")} · ${await ds("settling")} settling`);

  await postPlainCard(frameB, "plain-b");
  const bFinished = await page.waitForFunction(() => {
    const cv = document.getElementById("cv");
    return cv.dataset.settling === "0"
      && (cv.dataset.seam === "closed" || cv.dataset.seam === "aborted");
  }, null, { timeout: 10000 }).then(() => true, () => false);
  const plainRaceRun = await ds("run");
  check("the first settlement cannot dispute the next honest plain card",
    bFinished && (await ds("seam")) === "closed"
      && /^2:2–0:140:0:0:0$/.test(plainRaceRun)
      && fileRequests === 2,
    `${await ds("seam")} · ${plainRaceRun} · ${fileRequests} requests`);
  const plainRacePanel = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  check("and the panel says the second card banked",
    /CERTIFIED AT THE EDGE/.test(plainRacePanel)
      && /BANKED TO THE RUN · 2 CARDS/.test(plainRacePanel)
      && !/DISPUTES|STRUCK|REFUSED/.test(plainRacePanel),
    plainRacePanel);
  await page.unroute(/\/file$/);

  // HTTP status is part of the verdict vocabulary. /file certifies before
  // it touches the archive, so its capacity and KV failures cannot be
  // collapsed into the 422 replay-dispute path.
  await page.route(/\/file$/, route => route.fulfill({
    status: 507,
    contentType: "application/json",
    body: JSON.stringify({
      filed: false,
      error: "the archive is full — this is a prototype ledger, not a product one",
    }),
  }));
  const fullFrame = await walkPlainDoor();
  check("a plain run deals a card to the full archive", fullFrame !== null);
  if (!fullFrame) throw new Error("the full-archive door never dealt");
  await postPlainCard(fullFrame, "archive-full");
  const fullSettled = await page.waitForFunction(() =>
    /CERTIFIED BUT NOT ARCHIVED/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 }).then(() => true, () => false);
  const fullPanel = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  check("a 507 banks unwitnessed and names the archive limit",
    fullSettled
      && /COUNTED UNWITNESSED/.test(fullPanel)
      && /THE ARCHIVE IS FULL/.test(fullPanel)
      && !/DISPUTES|STRUCK/.test(fullPanel)
      && /^3:3–0:210:0:0:0$/.test(await ds("run")),
    `${fullPanel} · ${await ds("run")}`);
  await page.unroute(/\/file$/);

  await page.route(/\/file$/, route => route.fulfill({
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({ error: "certify failed" }),
  }));
  const failedFrame = await walkPlainDoor();
  check("a plain run deals a card before a Worker failure", failedFrame !== null);
  if (!failedFrame) throw new Error("the Worker-failure door never dealt");
  await postPlainCard(failedFrame, "worker-failed");
  const failedSettled = await page.waitForFunction(() =>
    /WITNESS INFRASTRUCTURE FAILURE/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 }).then(() => true, () => false);
  const failedPanel = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  check("a 500 banks unwitnessed instead of inventing a dispute",
    failedSettled
      && /COUNTED UNWITNESSED/.test(failedPanel)
      && /certify failed/.test(failedPanel)
      && !/DISPUTES|STRUCK/.test(failedPanel)
      && /^4:4–0:280:0:0:0$/.test(await ds("run")),
    `${failedPanel} · ${await ds("run")}`);
  await page.unroute(/\/file$/);

  await page.route(/\/file$/, route => route.fulfill({
    status: 422,
    contentType: "application/json",
    body: JSON.stringify({
      filed: false, certified: false, error: "record does not replay",
      rules: "stub-rules", applied: 0, submitted: 1,
    }),
  }));
  const disputedFrame = await walkPlainDoor();
  check("a plain run deals a card to the disputing edge", disputedFrame !== null);
  if (!disputedFrame) throw new Error("the dispute door never dealt");
  await postPlainCard(disputedFrame, "record-diverged");
  const disputedSettled = await page.waitForFunction(() =>
    /EDGE DISPUTES THE FEED — STRUCK/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 }).then(() => true, () => false);
  const disputedPanel = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  check("a genuine 422 replay dispute remains struck",
    disputedSettled
      && /record does not replay/.test(disputedPanel)
      && /NOT BANKED — CARD STRUCK/.test(disputedPanel)
      && /^4:4–0:280:0:0:1$/.test(await ds("run")),
    `${disputedPanel} · ${await ds("run")}`);
  await page.unroute(/\/file$/);

  // A legacy /file response can attest and archive the match while saying
  // nothing about derived events. That is not evidence for an empty array,
  // and the yard's local array cannot be promoted into an edge-authored one.
  // The protocol gap is counted unwitnessed, not rewritten as a dispute.
  await page.route(/\/file$/, route => route.fulfill(fileReply(route, {
    id: "22222222222222222222222222222222",
    includeDerivedEvents: false,
  })));
  const legacyFrame = await walkPlainDoor();
  check("a plain run deals a card to the legacy edge", legacyFrame !== null);
  if (!legacyFrame) throw new Error("the legacy-edge door never dealt");
  await postPlainCard(legacyFrame, "legacy-edge");
  const legacySettled = await page.waitForFunction(() =>
    /CERTIFICATE EVENT ATTESTATION INCOMPLETE/.test(
      document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 }).then(() => true, () => false);
  const legacyPanel = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  check("a certificate without derivedEvents counts unwitnessed without minting an event",
    legacySettled && /derivedEvents missing/.test(legacyPanel)
      && /COUNTED UNWITNESSED/.test(legacyPanel)
      && !/DISPUTES|STRUCK/.test(legacyPanel)
      && /^5:5–0:350:0:0:1$/.test(await ds("run")),
    `${legacyPanel} · ${await ds("run")}`);
  await page.unroute(/\/file$/);

  // ---- the first relationship, end to end ----------------------------
  // One continuous §12 line of play: the golden yard card downs KOA,
  // SABLE drags them clear, the Worker files its replay-authored extraction,
  // the run names KOA's life debt, BACK resolves the raw drag, and the door
  // exposes repayment before commitment. The room never imports the rules;
  // this harness may, which is how it knows command 6 really is the drag.
  const DRAG_ID = "33333333333333333333333333333333";
  const RELATIONSHIP_TOUR = {
    id: "rescue-tour",   // isName bounds slate ids at 16 chars — a longer id nulls openSeason and the room silently falls back to the house slate (cost this suite four ghost failures)
    entries: [
      { venue: "RESCUE YARD", host: "steel-syndicate", sanction: "steel-syndicate" },
      { venue: "REPAYMENT COURT", host: "covenant", sanction: "covenant" },
      { venue: "AFTER COURT", host: "lattice", sanction: null },
      { venue: "LAST GROUND", host: null, sanction: null },
    ],
  };
  const dragReply = route => {
    const asked = JSON.parse(route.request().postData() ?? "{}");
    const transcript = Array.from(
      { length: DRAG_GOLDEN.lines }, (_, index) => `stub transcript ${index}`);
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(filedResponse(asked, {
        id: DRAG_ID,
        rules: "drag-rules",
        result: DRAG_GOLDEN.result,
        rating: DRAG_GOLDEN.rating,
        purse: DRAG_GOLDEN.purse,
        ledger: { walked: 0, finished: 0, lost: 3 },
        fingerprint: DRAG_GOLDEN.fingerprint,
        lines: DRAG_GOLDEN.lines,
        transcript,
        derivedEvents: DRAG_GOLDEN.derived,
      })),
    });
  };
  await page.route(/\/file$/, dragReply);
  await page.route(new RegExp(`/matches/${DRAG_ID}$`), route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: DRAG_ID,
      filed_at: "2026-08-16T00:00:00Z",
      record: DRAG_GOLDEN.record,
      certificate: {
        certified: true,
        rules: "drag-rules",
        ledger: { walked: 0, finished: 0, lost: 3 },
        seed: "1",
        roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
        rosterHash: "00000000",
        result: DRAG_GOLDEN.result,
        rating: DRAG_GOLDEN.rating,
        purse: DRAG_GOLDEN.purse,
        commands: DRAG_GOLDEN.record.length,
        derivedEvents: DRAG_GOLDEN.derived,
        lines: DRAG_GOLDEN.lines,
        fingerprint: DRAG_GOLDEN.fingerprint,
        transcript: Array.from(
          { length: DRAG_GOLDEN.lines }, (_, index) => `stub transcript ${index}`),
      },
    }),
  }));
  const acceptanceSeason = openSeason("2026-08-16T00:00:00Z", RELATIONSHIP_TOUR);
  if (acceptanceSeason === null) throw new Error("acceptance fixture refused: the tour is not a slate");
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)), acceptanceSeason);
  await boot("?body=composed&deal=1");
  const dragFrame = await walkPlainDoor();
  check("the room deals the certified extraction card", dragFrame !== null);
  if (!dragFrame) throw new Error("the relationship acceptance door never dealt");
  await dragFrame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result",
      seed: "1",
      record: value.record,
      result: value.result,
      rating: value.rating,
      purse: value.purse,
      ledger: { walked: 0, finished: 0, lost: 3 },
      down: ["VESPER", "KOA", "SABLE"],
      derivedEvents: value.derived,
      roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
      fingerprint: value.fingerprint,
      lines: value.lines,
    }, window.parent.location.origin);
  }, DRAG_GOLDEN);
  await page.waitForFunction(() =>
    /CERTIFIED AT THE EDGE/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 });
  const certifiedRun = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sentinel.run") ?? "null"));
  const certifiedEvent = certifiedRun?.eventLedger?.sable?.[0];
  const activeDebt = certifiedRun?.relationships?.[0];
  check("the completed drag banks a certified stable-id event",
    certifiedEvent?.beneficiary === "koa"
      && certifiedEvent?.grade === "certified"
      && certifiedEvent?.origin?.matchId === DRAG_ID
      && certifiedEvent?.origin?.commandIndex === 6,
    JSON.stringify(certifiedEvent));
  check("the run names the directional life debt from that exact source",
    certifiedRun?.relationships?.length === 1
      && activeDebt?.kind === "owes-a-life"
      && activeDebt?.from === "koa" && activeDebt?.to === "sable"
      && activeDebt?.status === "active"
      && activeDebt?.origin?.matchId === DRAG_ID
      && activeDebt?.origin?.commandIndex === 6
      && activeDebt?.slate?.venue === "RESCUE YARD",
    JSON.stringify(activeDebt));
  check("the event and named relationship are player-visible with their stamps",
    /SABLE EXTRACTED KOA UNDER FIRE/.test(await panelText())
      && /KOA OWES SABLE A LIFE · ACTIVE · MINTED AT RESCUE YARD/.test(await panelText())
      && /BACK TO FILE/.test(await panelText()), await panelText());
  const activeOptions = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("the door offers dedicated repayment beside the plain pass before commitment",
    (await page.$$(".plain-pass")).length === 1
      && (await page.$$(".dedicated-pass")).length === 1
      && /PASS — MOVE THE SLATE; EVERY RUNNING CLOCK RECOVERS 1/.test(activeOptions)
      && /PASS — KOA REPAYS THE LIFE: SABLE RECOVERS 2/.test(activeOptions),
    activeOptions);

  await page.click(`.relationship-back[data-match-id="${DRAG_ID}"]`);
  await page.waitForFunction(want =>
    document.getElementById("cv").dataset.source === want,
  `${DRAG_ID}:6`, { timeout: 10000 });
  const source = (await page.textContent("#sourceinfo")).replace(/\s+/g, " ").trim();
  check("BACK resolves the filed pointer and exposes the drag command",
    /POINTED COMMAND 6/.test(source)
      && source.includes(JSON.stringify(DRAG_GOLDEN.record[6])), source);

  // Commit the option the panel just spelled out. Every operative went down
  // on this golden card: SABLE is the creditor and clears a two-stop clock;
  // VESPER and KOA each receive the ordinary one stop.
  await page.click(".dedicated-pass");
  const repaidRun = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sentinel.run") ?? "null"));
  const fulfilledDebt = repaidRun?.relationships?.[0];
  check("REPAY THE LIFE advances only the creditor by two and the slate by one",
    repaidRun?.season?.pos === 2
      && repaidRun?.season?.clocks?.sable === undefined
      && repaidRun?.season?.clocks?.vesper === 1
      && repaidRun?.season?.clocks?.koa === 1
      && repaidRun?.season?.passed?.[0]?.dedication?.kind === "repay-the-life",
    JSON.stringify(repaidRun?.season));
  check("repayment fulfills the debt on the pass stamp without erasing history",
    fulfilledDebt?.status === "fulfilled"
      && fulfilledDebt?.fulfilledSlate?.venue === "REPAYMENT COURT"
      && fulfilledDebt?.origin?.matchId === DRAG_ID
      && fulfilledDebt?.origin?.commandIndex === 6,
    JSON.stringify(fulfilledDebt));
  let fulfilledPanel = await panelText();
  check("the fulfilled debt stays visible and the one-shot dedication leaves",
    /KOA OWES SABLE A LIFE · FULFILLED/.test(fulfilledPanel)
      && /REPAID AT REPAYMENT COURT/.test(fulfilledPanel)
      && /BACK TO FILE/.test(fulfilledPanel)
      && (await page.$$(".dedicated-pass")).length === 0
      && (await page.$$(".plain-pass")).length === 1,
    fulfilledPanel);

  await boot("?body=composed&deal=1");
  const reloadedDebt = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sentinel.run") ?? "null"));
  fulfilledPanel = await panelText();
  check("a reload preserves the source, fulfillment, clocks, and visible plain pass",
    reloadedDebt?.relationships?.[0]?.status === "fulfilled"
      && reloadedDebt?.relationships?.[0]?.origin?.matchId === DRAG_ID
      && reloadedDebt?.relationships?.[0]?.fulfilledSlate?.venue === "REPAYMENT COURT"
      && reloadedDebt?.season?.clocks?.sable === undefined
      && reloadedDebt?.season?.clocks?.vesper === 1
      && /KOA OWES SABLE A LIFE · FULFILLED/.test(fulfilledPanel)
      && (await page.$$(".plain-pass")).length === 1,
    `${JSON.stringify(reloadedDebt?.relationships)} · ${fulfilledPanel}`);

  // ---- the same relationship in chosen darkness ----------------------
  // This is the §12 sentence with the author changed, not the fact: a
  // faithful record cuts first, later completes the same under-fire DRAG,
  // and the yard returns the rules core's extraction. The room submits
  // nowhere. It appends the full local match, banks claim grade, reopens the
  // pointed command from LOG 0, and gives repayment exactly the same force.
  const DARK_DRAG = {
    record: [["cut", 0], ...DRAG_GOLDEN.record],
    derived: DRAG_GOLDEN.derived.map(event => ({ ...event, commandIndex: event.commandIndex + 1 })),
    // carried across the evaluate boundary — the page closure cannot see
    // node-side bindings like DRAG_GOLDEN
    lines: DRAG_GOLDEN.lines,
  };
  const darkSeason = openSeason("2026-08-18T00:00:00Z", RELATIONSHIP_TOUR);
  await page.evaluate(value => {
    localStorage.setItem("sentinel.run", JSON.stringify(value));
    localStorage.removeItem("sentinel.chronicle");
  }, darkSeason);
  await boot("?body=composed&deal=1");
  let darkRequests = 0;
  await page.unroute(/\/file$/);
  await page.route(/\/file$/, route => {
    darkRequests++;
    return route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
  });
  const darkFrame = await walkPlainDoor();
  check("the room deals the dark extraction card", darkFrame !== null);
  if (!darkFrame) throw new Error("the dark relationship door never dealt");
  await darkFrame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result", seed: "1", record: value.record,
      result: "loss", rating: 50, purse: 500,
      ledger: { walked: 0, finished: 0, lost: 3 },
      down: ["VESPER", "KOA", "SABLE"], derivedEvents: value.derived,
      roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
      fingerprint: "dark-drag", lines: value.lines,
    }, window.parent.location.origin);
  }, DARK_DRAG);
  await page.waitForFunction(() =>
    /CLAIM EVENTS BANKED/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 });
  const darkState = await page.evaluate(() => ({
    run: JSON.parse(localStorage.getItem("sentinel.run") ?? "null"),
    log: JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"),
  }));
  const darkEvent = darkState.run?.eventLedger?.sable?.[0];
  const darkDebt = darkState.run?.relationships?.[0];
  check("chosen darkness reaches neither edge endpoint and banks the verdict split",
    darkRequests === 0 && darkState.run?.dark === 1 && darkState.run?.unwitnessed === 0,
    `${darkRequests} requests · ${JSON.stringify(darkState.run)}`);
  check("the full dark match survives before the claim points at it",
    darkState.log?.length === 1
      && darkState.log[0]?.id === 0 && darkState.log[0]?.cert === "dark"
      && darkState.log[0]?.seed === "1"
      && JSON.stringify(darkState.log[0]?.record) === JSON.stringify(DARK_DRAG.record)
      && JSON.stringify(darkState.log[0]?.roster) === JSON.stringify([
        { name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 },
      ])
      && darkState.log[0]?.derivedEvents?.[0]?.commandIndex === 7
      && darkState.log[0]?.aftermath?.feedCut?.commandIndex === 0
      && /^[0-9a-f]{8}$/.test(darkState.log[0]?.key)
      && darkState.log[0]?.slate?.venue === "RESCUE YARD",
    JSON.stringify(darkState.log));
  check("the dark extraction mints OWES A LIFE at claim grade",
    darkEvent?.grade === "claim"
      && darkEvent?.origin?.logId === 0 && darkEvent?.origin?.commandIndex === 7
      && darkEvent?.origin?.key === darkState.log[0]?.key
      && darkDebt?.grade === "claim"
      && darkDebt?.origin?.logId === 0 && darkDebt?.origin?.commandIndex === 7
      && darkDebt?.origin?.key === darkState.log[0]?.key
      && darkDebt?.from === "koa" && darkDebt?.to === "sable"
      && /CLAIM · THE SQUAD'S WORD · LOG 0/.test(await panelText())
      && (await page.$$(".dedicated-pass")).length === 1,
    `${JSON.stringify(darkEvent)} · ${JSON.stringify(darkDebt)} · ${await panelText()}`);

  await page.click('.relationship-back[data-log-id="0"]');
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.source === "log:0:7",
  null, { timeout: 10000 });
  let darkSource = (await page.textContent("#sourceinfo")).replace(/\s+/g, " ").trim();
  check("BACK TO LOG resolves the preserved drag command",
    /LOG 0/.test(darkSource) && /POINTED COMMAND 7/.test(darkSource)
      && darkSource.includes(JSON.stringify(DARK_DRAG.record[7])), darkSource);

  // A same-origin tab can replace the whole array after appendEntry's
  // read-back. The numeric slot survives but its content does not; the claim
  // must fail closed on the content key instead of opening the new match.
  const replacement = { ...darkState.log[0], seed: "2" };
  const clobberedEntry = { ...replacement, key: chronicleKey(replacement) };
  await page.evaluate(entry => {
    localStorage.setItem("sentinel.chronicle", JSON.stringify([entry]));
  }, clobberedEntry);
  await boot("?body=composed&deal=1");
  await page.click('.relationship-back[data-log-id="0"]');
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.source === "unresolved",
  null, { timeout: 10000 });
  const clobberedSource = (await page.textContent("#sourceinfo")).replace(/\s+/g, " ").trim();
  check("a raced claim never opens the different valid match now in its slot",
    clobberedEntry.key !== darkDebt.origin.key
      && /THE SOURCE DOES NOT RESOLVE/.test(clobberedSource)
      && /THE LOG ENTRY IS NOT THE MATCH THIS CLAIM NAMES/.test(clobberedSource),
    `${JSON.stringify(clobberedEntry)} · ${clobberedSource}`);

  await page.evaluate(entry => {
    localStorage.setItem("sentinel.chronicle", JSON.stringify([entry]));
  }, darkState.log[0]);
  await boot("?body=composed&deal=1");

  await page.click(".dedicated-pass");
  let repaidClaim = await page.evaluate(() => ({
    run: JSON.parse(localStorage.getItem("sentinel.run") ?? "null"),
    log: JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"),
  }));
  check("REPAY THE LIFE fulfills claim grade with the same recovery force",
    repaidClaim.run?.relationships?.[0]?.status === "fulfilled"
      && repaidClaim.run?.relationships?.[0]?.grade === "claim"
      && repaidClaim.run?.relationships?.[0]?.fulfilledSlate?.venue === "REPAYMENT COURT"
      && repaidClaim.run?.season?.clocks?.sable === undefined
      && repaidClaim.run?.season?.clocks?.vesper === 1
      && repaidClaim.run?.season?.clocks?.koa === 1,
    JSON.stringify(repaidClaim.run));

  await boot("?body=composed&deal=1");
  repaidClaim = await page.evaluate(() => ({
    run: JSON.parse(localStorage.getItem("sentinel.run") ?? "null"),
    log: JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"),
  }));
  check("reload preserves the claimed source, fulfillment, and log target",
    repaidClaim.run?.relationships?.[0]?.status === "fulfilled"
      && repaidClaim.run?.relationships?.[0]?.origin?.logId === 0
      && repaidClaim.log?.[0]?.record?.[7]?.[0] === "drag"
      && /KOA OWES SABLE A LIFE · FULFILLED/.test(await panelText())
      && /THE SQUAD'S WORD · LOG 0/.test(await panelText()),
    `${JSON.stringify(repaidClaim)} · ${await panelText()}`);
  await page.click('.relationship-back[data-log-id="0"]');
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.source === "log:0:7",
  null, { timeout: 10000 });
  darkSource = (await page.textContent("#sourceinfo")).replace(/\s+/g, " ").trim();
  check("the claim source still resolves after reload",
    /POINTED COMMAND 7/.test(darkSource)
      && darkSource.includes(JSON.stringify(DARK_DRAG.record[7])), darkSource);
  await page.evaluate(() => localStorage.removeItem("sentinel.chronicle"));
  await page.click('.relationship-back[data-log-id="0"]');
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.source === "unresolved",
  null, { timeout: 10000 });
  const missingClaimSource = (await page.textContent("#sourceinfo")).replace(/\s+/g, " ").trim();
  check("a missing claim target says the source does not resolve",
    /THE SOURCE DOES NOT RESOLVE/.test(missingClaimSource), missingClaimSource);
  await page.unroute(/\/file$/);

  // The other negative gate: the debt exists, but a fit creditor creates no
  // option. It is absent, not disabled, and the plain pass still exists.
  const fitDebt = applyCard(
    openSeason("2026-08-16T00:00:00Z", RELATIONSHIP_TOUR),
    { ...card("b", []), derivedEvents: DRAG_GOLDEN.derived },
  );
  if (!fitDebt.accepted) throw new Error(`fit-debt fixture refused: ${fitDebt.why}`);
  await page.evaluate(value => {
    localStorage.setItem("sentinel.run", JSON.stringify(value));
    localStorage.removeItem("sentinel.chronicle");
  }, fitDebt.run);
  await boot("?body=composed&deal=1");
  const fitDebtPanel = await panelText();
  check("an active debt with a fit creditor offers no dedication and keeps plain pass",
    /KOA OWES SABLE A LIFE · ACTIVE/.test(fitDebtPanel)
      && (await page.$$(".dedicated-pass")).length === 0
      && (await page.$$(".plain-pass")).length === 1,
    fitDebtPanel);

  // Same yard fact, no Witness: the accident family still appends the full
  // local match first, then banks the yard's rules-derived account as the
  // squad's claim. The room never upgrades that claim to certification.
  await page.evaluate(value => {
    localStorage.setItem("sentinel.run", JSON.stringify(value));
    localStorage.removeItem("sentinel.chronicle");
  }, openRun("2026-08-16T00:00:00Z"));
  await boot("?body=composed&deal=1");
  await page.unroute(/\/file$/);
  await page.route(/\/file$/, route => route.abort("failed"));
  const unwitnessedFrame = await walkPlainDoor();
  check("the room deals an unwitnessed completed-drag card", unwitnessedFrame !== null);
  if (!unwitnessedFrame) throw new Error("the unwitnessed door never dealt");
  await unwitnessedFrame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result",
      seed: "1", record: value.record, result: value.result,
      rating: value.rating, purse: value.purse,
      ledger: { walked: 0, finished: 0, lost: 3 },
      down: ["VESPER", "KOA", "SABLE"], derivedEvents: value.derived,
      roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
      fingerprint: value.fingerprint, lines: value.lines,
    }, window.parent.location.origin);
  }, DRAG_GOLDEN);
  await page.waitForFunction(() =>
    /LOST THE FEED/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 });
  const unwitnessedRun = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sentinel.run") ?? "null"));
  const unwitnessedSeam = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  const allBankedEvents = Object.values(unwitnessedRun?.eventLedger ?? {}).flat();
  const unwitnessedLog = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"));
  check("LOST THE FEED logs and banks a claim in the accident family",
    allBankedEvents.length === 1
      && allBankedEvents[0]?.grade === "claim"
      && allBankedEvents[0]?.origin?.logId === 0
      && allBankedEvents[0]?.origin?.key === unwitnessedLog?.[0]?.key
      && unwitnessedRun?.relationships?.[0]?.grade === "claim"
      && unwitnessedRun?.relationships?.[0]?.origin?.key === unwitnessedLog?.[0]?.key
      && unwitnessedRun?.unwitnessed === 1
      && unwitnessedRun?.dark === 0
      && unwitnessedLog?.[0]?.cert === "unwitnessed"
      && unwitnessedLog?.[0]?.aftermath?.feedCut === null
      && /YARD DERIVED · SABLE → KOA/.test(unwitnessedSeam)
      && /LOST THE FEED/.test(unwitnessedSeam)
      && /CLAIM EVENTS BANKED — THE SQUAD'S WORD · LOG 0/.test(unwitnessedSeam),
    `${JSON.stringify(allBankedEvents)} · ${JSON.stringify(unwitnessedRun?.relationships)} · ${JSON.stringify(unwitnessedLog)} · ${unwitnessedSeam}`);
  await page.unroute(/\/file$/);

  // No extraction is still a record. Chosen darkness preserves the complete
  // card even when there is no rules-derived fact for the run to bank.
  await page.evaluate(value => {
    localStorage.setItem("sentinel.run", JSON.stringify(value));
    localStorage.removeItem("sentinel.chronicle");
  }, openRun("2026-08-18T00:00:00Z"));
  await boot("?body=composed&deal=1");
  const eventlessDarkFrame = await walkPlainDoor();
  check("the room deals an event-less dark card", eventlessDarkFrame !== null);
  if (!eventlessDarkFrame) throw new Error("the event-less dark door never dealt");
  const EVENTLESS_DARK = {
    seed: "1",
    roster: [
      { name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 },
    ],
    record: [["cut", 0], ["end"]],
    result: "win",
    rating: 9,
    purse: 90,
    ledger: { walked: 0, finished: 0, lost: 0 },
    down: [],
    derivedEvents: [],
    fingerprint: "eventless-dark",
    lines: ["eventless dark fixture"],
  };
  await eventlessDarkFrame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result",
      ...value,
    }, window.parent.location.origin);
  }, EVENTLESS_DARK);
  await page.waitForFunction(() =>
    /THE RECORD IS KEPT — LOG 0 · NOTHING TO BANK FROM IT/.test(
      document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 });
  const eventlessDark = await page.evaluate(() => ({
    run: JSON.parse(localStorage.getItem("sentinel.run") ?? "null"),
    log: JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"),
    panel: document.getElementById("seaminfo").textContent.replace(/\s+/g, " ").trim(),
  }));
  check("an event-less dark card keeps its full record and banks no fact",
    eventlessDark.run?.cards === 1 && eventlessDark.run?.dark === 1
      && Object.values(eventlessDark.run?.eventLedger ?? {}).flat().length === 0
      && eventlessDark.run?.relationships?.length === 0
      && eventlessDark.run?.recent?.[0]?.derivedEvents?.length === 0
      && eventlessDark.log?.length === 1
      && eventlessDark.log[0]?.id === 0
      && /^[0-9a-f]{8}$/.test(eventlessDark.log[0]?.key)
      && eventlessDark.log[0]?.seed === EVENTLESS_DARK.seed
      && JSON.stringify(eventlessDark.log[0]?.roster) === JSON.stringify(EVENTLESS_DARK.roster)
      && JSON.stringify(eventlessDark.log[0]?.record) === JSON.stringify(EVENTLESS_DARK.record)
      && eventlessDark.log[0]?.derivedEvents?.length === 0
      && eventlessDark.log[0]?.aftermath?.result === EVENTLESS_DARK.result
      && eventlessDark.log[0]?.aftermath?.rating === EVENTLESS_DARK.rating
      && eventlessDark.log[0]?.aftermath?.purse === EVENTLESS_DARK.purse
      && eventlessDark.log[0]?.aftermath?.feedCut?.commandIndex === 0
      && /THE RECORD IS KEPT — LOG 0 · NOTHING TO BANK FROM IT/.test(eventlessDark.panel),
    JSON.stringify(eventlessDark));

  // A replay dispute is the hard boundary. Even when the page supplies a
  // plausible extraction, 422 says the record diverged: no chronicle entry,
  // no claim, no relationship, and no ordinary card consequences.
  await page.evaluate(value => {
    localStorage.setItem("sentinel.run", JSON.stringify(value));
    localStorage.removeItem("sentinel.chronicle");
  }, openRun("2026-08-18T00:00:00Z"));
  await boot("?body=composed&deal=1");
  await page.route(/\/file$/, route => route.fulfill({
    status: 422,
    contentType: "application/json",
    body: JSON.stringify({
      filed: false, certified: false, error: "record does not replay",
      rules: "stub-rules", applied: 0, submitted: DRAG_GOLDEN.record.length,
    }),
  }));
  const struckDragFrame = await walkPlainDoor();
  check("the room deals the extraction claim to a disputing edge", struckDragFrame !== null);
  if (!struckDragFrame) throw new Error("the struck-claim door never dealt");
  await struckDragFrame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result", seed: "1", record: value.record,
      result: value.result, rating: value.rating, purse: value.purse,
      ledger: { walked: 0, finished: 0, lost: 3 }, down: ["VESPER", "KOA", "SABLE"],
      derivedEvents: value.derived,
      roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
      fingerprint: value.fingerprint, lines: value.lines,
    }, window.parent.location.origin);
  }, DRAG_GOLDEN);
  await page.waitForFunction(() =>
    /EDGE DISPUTES THE FEED — STRUCK/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 });
  const struckClaim = await page.evaluate(() => ({
    run: JSON.parse(localStorage.getItem("sentinel.run") ?? "null"),
    log: JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"),
  }));
  check("a struck extraction logs nothing and mints nothing",
    struckClaim.run?.cards === 0 && struckClaim.run?.struck === 1
      && Object.values(struckClaim.run?.eventLedger ?? {}).flat().length === 0
      && struckClaim.run?.relationships?.length === 0
      && struckClaim.log.length === 0,
    JSON.stringify(struckClaim));
  await page.unroute(/\/file$/);

  // Capacity is a refusal, not an eviction policy. Fill the independent
  // chronicle, return a real dark extraction, and prove the card still
  // counts while its event and debt do not appear.
  const fullLogSeed = Array.from({ length: 200 }, (_, id) => {
    const value = {
      id, kind: "match", cert: "unwitnessed", seed: "1",
      roster: [
        { name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 },
      ],
      record: [["drag", 2, 1, 4, 9], ["end"]],
      derivedEvents: [{
        kind: "extraction", actor: "SABLE", beneficiary: "KOA",
        commandIndex: 0, underFire: true, reached: true,
      }],
      aftermath: { result: "loss", rating: 1, purse: 10, feedCut: null },
      at: "2026-08-18T00:00:00Z",
    };
    return { ...value, key: chronicleKey(value) };
  });
  await page.evaluate(({ run, log }) => {
    localStorage.setItem("sentinel.run", JSON.stringify(run));
    localStorage.setItem("sentinel.chronicle", JSON.stringify(log));
  }, { run: openRun("2026-08-18T00:00:00Z"), log: fullLogSeed });
  await boot("?body=composed&deal=1");
  const fullLogFrame = await walkPlainDoor();
  check("the room deals a dark extraction against a full local log", fullLogFrame !== null);
  if (!fullLogFrame) throw new Error("the full-log door never dealt");
  await fullLogFrame.evaluate(value => {
    window.parent.postMessage({
      type: "sentinel-seam-result", seed: "1", record: value.record,
      result: "loss", rating: 50, purse: 500,
      ledger: { walked: 0, finished: 0, lost: 3 }, down: ["VESPER", "KOA", "SABLE"],
      derivedEvents: value.derived,
      roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
      fingerprint: "dark-drag", lines: value.lines,
    }, window.parent.location.origin);
  }, DARK_DRAG);
  await page.waitForFunction(() =>
    /THE LOG IS FULL — NOTHING KEPT/.test(document.getElementById("seaminfo").textContent),
  null, { timeout: 10000 });
  const refusedClaim = await page.evaluate(() => ({
    run: JSON.parse(localStorage.getItem("sentinel.run") ?? "null"),
    log: JSON.parse(localStorage.getItem("sentinel.chronicle") ?? "[]"),
    panel: document.getElementById("seaminfo").textContent.replace(/\s+/g, " ").trim(),
  }));
  check("a full log banks the dark card loudly and mints nothing",
    refusedClaim.run?.cards === 1 && refusedClaim.run?.dark === 1
      && Object.values(refusedClaim.run?.eventLedger ?? {}).flat().length === 0
      && refusedClaim.run?.relationships?.length === 0
      && refusedClaim.run?.recent?.[0]?.derivedEvents?.length === 0
      && refusedClaim.log.length === 200
      && /THE LOG IS FULL — NOTHING KEPT/.test(refusedClaim.panel),
    JSON.stringify(refusedClaim));
  await page.unroute(new RegExp(`/matches/${DRAG_ID}$`));

  // and a FRESH room opens on the house slate — the front office is the
  // default surface, not an opt-in
  await page.evaluate(() => localStorage.removeItem("sentinel.run"));
  await boot("?body=composed");
  check("a fresh room opens a season on the house slate",
    (await ds("season")) === "0/6:0:fit", await ds("season"));
  sPanel = await panelText();
  check("the house tour opens at its first entry, framed",
    /SLATE OPENING-CIRCUIT/.test(sPanel) && /STOP 1 OF 6/.test(sPanel)
      && /NEXT · KESTREL YARD · HELD BY STEEL-SYNDICATE/.test(sPanel), sPanel);
  await pass();
  check("the house tour can be passed from the door",
    (await ds("season")) === "1/6:1:fit", await ds("season"));

  // storage that accepts the one-byte probe but refuses the run: the
  // panel must say so from the very FIRST write — the fresh season's
  // boot save — and a later write that succeeds must clear the caveat,
  // because saveRun writes the whole run and one success means storage
  // caught up. A warning that outlives its truth is the surface lying
  // in the other direction (both caught in review, beat 2). The patch
  // throws only while the flag is set, so later sections keep an
  // honest store.
  await page.addInitScript(() => {
    const orig = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) {
      if (k === "sentinel.run"
          && this.getItem("sentinel.test.refuseRun") === "1") {
        throw new Error("quota, allegedly");
      }
      return orig.call(this, k, v);
    };
  });
  await page.evaluate(() => {
    localStorage.removeItem("sentinel.run");
    localStorage.setItem("sentinel.test.refuseRun", "1");
  });
  await boot("?body=composed");
  check("a refused first save is a caveat, not a silence",
    /STORAGE REFUSED/.test(await panelText()), await panelText());
  await page.evaluate(() => localStorage.removeItem("sentinel.test.refuseRun"));
  await pass();
  check("a later successful write clears the caveat",
    !/STORAGE REFUSED/.test(await panelText()) && (await ds("season")) === "1/6:1:fit",
    await panelText());

  // ---- the kit table: the purse spends -------------------------------
  // Beat 3 of season-lite. The shop is a PLACE — the surface opens when
  // the body reaches the table and closes when it leaves — and what it
  // sells is flair, because run-core's FLAIR_SLOTS is the whole register
  // a lite purse may buy. Fixtures are built with run-core again, so
  // every claim here is about the room.
  const paidCard = {
    seed: "b", result: "win", rating: 30, purse: 300,
    ledger: { walked: 0, finished: 0, lost: 0 }, down: [], cert: "certified",
    derivedEvents: [], matchId: "0123456789abcdef0123456789abcdef",
    rules: "test-rules", at: "2026-08-13T00:00:00Z",
  };
  const paid = applyCard(openSeason("2026-08-13T00:00:00Z", TOUR), paidCard);
  if (!paid.accepted) throw new Error(`purse fixture refused: ${paid.why}`);
  await page.evaluate(value =>
    localStorage.setItem("sentinel.run", JSON.stringify(value)), paid.run);
  await boot("?body=composed");
  const kitText = async () =>
    (await page.textContent("#kitinfo")).replace(/\s+/g, " ").trim();
  // Walking to the table rather than teleporting to it: the shop opening
  // IS the arrival, and a test that set the flag directly would not be
  // testing the thing the design is about. Waiting on the room's own
  // published state, never on a sleep.
  //
  // Movement is camera-relative in a 2:1 view: W+D is true north, and A
  // alone is the south-west diagonal that runs from the spawn straight at
  // the table. D alone walks back out of reach.
  const walkTo = async (keys, state) => {
    for (const key of keys) await page.keyboard.down(key);
    const got = await page.waitForFunction(want =>
      document.getElementById("cv").dataset.shop === want,
      state, { timeout: 30000 }).then(() => true, () => false);
    for (const key of keys) await page.keyboard.up(key);
    return got;
  };

  check("a run away from the table keeps the shop shut",
    (await ds("shop")) === "away" && await page.$eval("#kitbox", el => el.hidden),
    await ds("shop"));
  check("the kit is on the run panel even with the shop shut",
    /KIT · EVERY HOOK EMPTY/.test(await panelText()), await panelText());
  check("an unbought rack stands there empty",
    (await ds("rack")) === "8:0" && (await ds("worn")) === "none",
    `${await ds("rack")} · ${await ds("worn")}`);
  check("the purse says what was earned before anything is spent",
    /300c EARNED/.test(await panelText()) && !/ON HAND/.test(await panelText()),
    await panelText());

  check("walking to the kit table opens the shop", await walkTo(["KeyA"], "at"));
  check("and the box is on the panel", !(await page.$eval("#kitbox", el => el.hidden)));
  let kPanel = await kitText();
  check("the shop leads with what the purse can cover",
    /300c ON HAND/.test(kPanel), kPanel);
  check("the stock is priced, slotted and keyed",
    /1 ASHEN HOOD · DRAPE · 240c/.test(kPanel)
      && /3 LENGTH OF CHAIN · PATCH · 90c/.test(kPanel), kPanel);
  check("what the purse cannot cover says so rather than going quiet",
    /STORM CLOAK · DRAPE · 620c · TOO DEAR/.test(kPanel), kPanel);
  check("the shop names who the next purchase dresses",
    /DRESSING VESPER/.test(kPanel), kPanel);
  check("the panel says how to read the rack",
    /RACK READS VESPER · KOA · SABLE · NIX, LEFT TO RIGHT · DRAPE THEN PATCH/.test(kPanel), kPanel);

  await page.keyboard.press("Digit1");
  check("buying spends the balance and leaves the purse alone",
    (await ds("kit")) === "60:240:1", await ds("kit"));
  check("the bought item is on a named fighter's named hook",
    (await ds("worn")) === "VESPER/drape/ashen-hood", await ds("worn"));
  check("and a hook on the rack is no longer empty",
    (await ds("rack")) === "8:1", await ds("rack"));
  kPanel = await kitText();
  check("the shop says what was bought and for whom",
    /BOUGHT ASHEN HOOD FOR VESPER · 240c/.test(kPanel), kPanel);
  check("one purchase closes the rest of the case — the decision, visible",
    /LENGTH OF CHAIN · PATCH · 90c · TOO DEAR/.test(kPanel)
      && /PRESSED FLOWER · PATCH · 180c · TOO DEAR/.test(kPanel), kPanel);
  const boughtPanel = await panelText();
  check("the run panel splits what was won from what is left",
    /300c EARNED/.test(boughtPanel) && /240c SPENT/.test(boughtPanel)
      && /60c ON HAND/.test(boughtPanel), boughtPanel);
  check("the kit line names the wearer and the item",
    /KIT · VESPER ASHEN HOOD/.test(boughtPanel), boughtPanel);

  // The room gates, run-core banks — the same division the door runs on.
  // Both refusals below are conditions applyBuy would call accepted:false,
  // which is exactly why the SHOP has to catch them first: the module's
  // own words appearing here would mean the surface offered something it
  // should have refused.
  await page.keyboard.press("Digit1");
  kPanel = await kitText();
  check("a second drape on one fighter is refused at the surface",
    /VESPER ALREADY WEARS ASHEN HOOD/.test(kPanel)
      && !/ALREADY WEARS A DRAPE/.test(kPanel), kPanel);
  // A different refusal, and it has to be an item in a FREE slot: a
  // second drape is refused before its price is ever consulted, which is
  // the right order and would have made this claim about the wrong
  // branch (caught running it).
  await page.keyboard.press("Digit4");
  kPanel = await kitText();
  check("a purchase the purse cannot cover is refused at the surface",
    /PRESSED FLOWER IS 180c AND THE PURSE HAS 60c/.test(kPanel)
      && !/PURSE WILL NOT COVER/.test(kPanel), kPanel);
  check("and neither refusal moved the money",
    (await ds("kit")) === "60:240:1", await ds("kit"));

  await page.keyboard.press("KeyZ");
  kPanel = await kitText();
  check("Z chooses who wears the next thing",
    /DRESSING KOA/.test(kPanel), kPanel);
  check("the hood VESPER wears is not on KOA's hooks",
    /1 ASHEN HOOD · DRAPE · 240c · TOO DEAR/.test(kPanel), kPanel);

  check("walking away from the table shuts the shop", await walkTo(["KeyD"], "away"));
  check("and the box leaves the panel", await page.$eval("#kitbox", el => el.hidden));
  await page.keyboard.press("Digit3");
  check("buying across the room is refused with directions, not silence",
    /KIT TABLE IS ACROSS THE ROOM/.test(await panelText()), await panelText());
  check("and the refusal spent nothing", (await ds("kit")) === "60:240:1", await ds("kit"));
  check("the kit stays on the run panel away from the table",
    /KIT · VESPER ASHEN HOOD/.test(await panelText()), await panelText());

  await boot("?body=composed");
  check("the rack survives a reload",
    (await ds("kit")) === "60:240:1" && (await ds("rack")) === "8:1"
      && (await ds("worn")) === "VESPER/drape/ashen-hood",
    `${await ds("kit")} · ${await ds("rack")}`);
  check("a reloaded season still knows where it is on the tour",
    (await ds("season")) === "1/3:0:fit", await ds("season"));

  // ---- the people layer: NPCs with bodies ---------------------------
  // The seam `unauthored_history.md` names. The squad are bodies with no
  // people; a PERSON is authored world data with campaign identity, and
  // the join is that the archetype RESOLVES out of the campaign's own
  // faction file rather than being copied into the person. These claims
  // are about that resolution — that it happens, that it reaches the
  // surface, and that it FAILS LOUDLY when the campaign has never heard
  // of the role being claimed.
  const factionFile = JSON.parse(fs.readFileSync(path.join(
    ROOT, "sentinel-campaign/src/sentinel_campaign/data/factions/steel_syndicate.json"), "utf8"));
  const broker = factionFile.archetypes.find(a => a.role === "Broker");
  if (!broker) throw new Error("the Broker archetype vanished from the campaign data");

  check("the room stages a person",
    (await ds("people")) === "vance:steel_syndicate:Broker", await ds("people"));

  // the asymmetry, same as the fielded roster: the room DECLARES which
  // bodies it can draw, and only this file can check that against disk
  const stageable = ((await ds("stageable")) ?? "").split(",").filter(Boolean);
  const onDisk = fs.readdirSync(path.join(ROOT, "assets/original/squad_render/sheets96"))
    .filter(d => fs.statSync(path.join(ROOT, "assets/original/squad_render/sheets96", d)).isDirectory())
    .filter(d => !d.endsWith(".harness-backup"))   // this suite's own live backups
    .sort();
  check("every body the room declares stageable exists on disk",
    stageable.length > 0 && stageable.every(b => onDisk.includes(b)),
    `declared ${stageable.join(",")} vs on disk ${onDisk.join(",")}`);

  // the join, executed: the description on the shop panel is the
  // campaign's own words for that archetype, not a string in the room
  await walkTo(["KeyA"], "at");
  const keeperPanel = await kitText();
  check("the table names who keeps it, with faction and role",
    /VANCE KEEPS THIS TABLE · STEEL SYNDICATE BROKER/.test(keeperPanel), keeperPanel);
  check("and the role's description comes from the campaign file",
    keeperPanel.includes(broker.description), `looking for: ${broker.description}`);
  await walkTo(["KeyD"], "away");

  // ---- the boundary refuses, loudly --------------------------------
  // Authored world data is not a trusted input. Each of these serves a
  // doctored person file in place of the real one and expects a BOOT
  // FAULT naming the problem — never a room that quietly stages fewer
  // people, which is the silent fallback this gate exists to prevent.
  const servePerson = body => page.route(/world\/people\/vance\.json$/, route =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) }));
  const good = {
    id: "vance", name: "VANCE", faction: "steel_syndicate", archetype: "Broker",
    body: "syn", at: { x: 4, z: 4 }, facing: "down", keeps: "kit-table",
  };
  const faultText = async () =>
    (await page.textContent("#asset-gate")).replace(/\s+/g, " ").trim();

  for (const [label, doctored, wanted] of [
    ["a role the faction does not have", { ...good, archetype: "Cardinal" }, /no such role/i],
    ["a faction the campaign does not have", { ...good, faction: "hanseatic_league" }, /campaign does not have/i],
    ["a body this room cannot draw", { ...good, body: "godzilla" }, /not a person this room can stage/i],
    ["a person standing outside the room", { ...good, at: { x: 99, z: 4 } }, /not a person this room can stage/i],
    ["a file that disagrees with the index", { ...good, id: "someone-else" }, /the index and the file disagree/i],
    ["a facing that is not one of the four", { ...good, facing: "diagonal" }, /not a person this room can stage/i],
  ]) {
    await servePerson(doctored);
    await boot("?body=composed");
    const fault = await faultText();
    check(`${label} faults the room`, (await ds("sprites")) === "error", await ds("sprites"));
    check(`...and the fault says why (${label})`, wanted.test(fault), fault.slice(-160));
    check(`...and no people are staged behind it (${label})`,
      !(await ds("people")), (await ds("people")) ?? "(none)");
    await page.unroute(/world\/people\/vance\.json$/);
  }

  // ...and the honest file still boots, so the gate discriminates
  await boot("?body=composed");
  check("the real person file still stages after the refusals",
    (await ds("people")) === "vance:steel_syndicate:Broker", await ds("people"));

  // ---- the venue atlas is gated at the AUTHORING end ----------------
  // The room deals venue names through the door (the yard dresses for
  // them), so a house-slate entry naming a venue the atlas lacks must
  // fault HERE at boot — a typo caught in the front office, not
  // "UNRECORDED GROUND" discovered on the far side of a crossing.
  // Stored seasons are deliberately not gated (a save never bricks over
  // a look); that half lives in the yard's own venue suite.
  await page.route(/world\/venues\.json$/, route => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ venues: { "SOMEWHERE ELSE": {} } }),
  }));
  await boot("?body=composed");
  check("a house-slate venue missing from the atlas faults the room",
    (await ds("sprites")) === "error", await ds("sprites"));
  const atlasFault = await faultText();
  check("...and the fault names the missing venues and the atlas's own list",
    /KESTREL YARD/.test(atlasFault) && /SOMEWHERE ELSE/.test(atlasFault), atlasFault.slice(-200));
  await page.unroute(/world\/venues\.json$/);
  await boot("?body=composed");
  check("the real atlas still boots after the refusal",
    (await ds("sprites")) === "ready", await ds("sprites"));

  // ---- the air is live, and visibly so ------------------------------
  // dataset.air says the motes exist; the pixel pair says a player can
  // SEE them move (telemetry alone is how the kit table shipped
  // invisible). Sampled in an off-center crop away from the spawn so
  // the body's idle animation cannot be what changed, and separated by
  // RENDERED FRAMES rather than wall clock — this harness does not
  // sleep, and headless rAF pacing is not this test's business.
  check("the room air is live", (await ds("air")) === "live", await ds("air"));
  const airCrop = async () => {
    const box = await page.locator("#cv").boundingBox();
    return page.screenshot({ clip: {
      x: box.x + box.width * 0.08, y: box.y + box.height * 0.10,
      width: box.width * 0.26, height: box.height * 0.30,
    } });
  };
  const framesPass = n => page.evaluate(n => new Promise(res => {
    let k = 0;
    const step = () => (++k >= n ? res() : requestAnimationFrame(step));
    requestAnimationFrame(step);
  }), n);
  const airA = await airCrop();
  await framesPass(14);
  const airB = await airCrop();
  check("the dust visibly drifts between rendered frames",
    !airA.equals(airB), `${airA.length} vs ${airB.length} bytes`);

  // ---- the authored facing is a fact, not a field ------------------
  // It was validated, authored, and then ignored: worldFacing was copied
  // from the squad's point-at-spawn rule, so every facing value rendered
  // identically and a comment claimed otherwise (caught by both review
  // bots). Asserted by CHANGING it and watching the staged sheet move,
  // because a field nothing reads passes any test that only reads it.
  await page.waitForFunction(() => !!document.getElementById("cv").dataset.peopleSprites,
    null, { timeout: 5000 });
  const facingOf = async () =>
    ((await ds("peopleSprites")) ?? "").split(",")
      .find(e => e.startsWith("VANCE:"))?.split(":")[2];
  check("the authored facing reaches the sheet", (await facingOf()) === "down", await facingOf());

  for (const facing of ["up", "left", "right"]) {
    await servePerson({ ...good, facing });
    await boot("?body=composed");
    await page.waitForFunction(() => !!document.getElementById("cv").dataset.peopleSprites,
      null, { timeout: 5000 });
    check(`facing "${facing}" stages the ${facing} sheet`,
      (await facingOf()) === facing, await facingOf());
    await page.unroute(/world\/people\/vance\.json$/);
  }
  await boot("?body=composed");

  await page.evaluate(() => localStorage.removeItem("sentinel.run"));
  await boot("?body=composed");

  // the two gaits, and which one a BARE press gets. The default is the
  // walk since 2026-08-14: both sheets were always authored, the run
  // just reads goofy at 1× (the cosmetic nit PR #118 recorded), and
  // swapping which one is default costs nothing where re-rolling the
  // strip costs generations.
  await page.keyboard.down("Shift");
  await page.keyboard.down("KeyW");
  check("shift+move runs", await waitAction("run"));
  await page.keyboard.up("Shift");
  check("release shift walks", await waitAction("walk"));
  await page.keyboard.up("KeyW");
  check("release key idles", await waitAction("idle"));

  // dash: 6 frames @14fps ≈ 430ms, and it must displace the body.
  // Lower bounds are the real claim (ending early = frame-count bug);
  // upper bounds stay loose for headless rAF jank.
  const before = await ds("position");
  const dashMs = await measureVerb("KeyL", "dash");
  check("dash runs its 6 frames", dashMs > 300 && dashMs < 1000, `${Math.round(dashMs)}ms`);
  check("dash displaced the body", (await ds("position")) !== before,
    `${before} -> ${await ds("position")}`);
  check("dash ends in idle", await waitAction("idle"));

  // heal: 12 frames @10fps ≈ 1200ms — the longest sheet must run longest
  const healMs = await measureVerb("KeyH", "heal");
  check("heal channels its 12 frames", healMs > 1000 && healMs < 2500, `${Math.round(healMs)}ms`);

  // hurt: 4 frames @12fps ≈ 330ms — the shortest sheet
  const hurtMs = await measureVerb("KeyG", "hurt");
  check("hurt flinches its 4 frames", hurtMs > 220 && hurtMs < 900, `${Math.round(hurtMs)}ms`);
  // hurt-vs-dash differ by ~95ms nominal — inside headless rAF jank, so
  // the ordering claim is asserted against the 12-frame channel only
  check("short sheets run shorter than the 12-frame channel",
    hurtMs < healMs && dashMs < healMs,
    `${Math.round(hurtMs)}, ${Math.round(dashMs)} < ${Math.round(healMs)}`);

  // ---- the stances: held, not triggered, and standing-only -----------
  await page.keyboard.down("KeyR");
  check("hold R aims", await waitAction("aim"));
  await page.keyboard.down("KeyC");
  check("aim outranks kneel while both are held", (await ds("action")) === "aim");
  await page.keyboard.up("KeyR");
  check("releasing R falls through to kneel", await waitAction("kneel"));
  // a stance is a standing pose: no aim-walk sheets exist, so moving must
  // take the body OUT of it rather than play a stance over a moving body
  await page.keyboard.down("KeyW");
  check("moving cancels a held stance", await waitAction("walk"));
  await page.keyboard.up("KeyW");
  check("stopping returns to the still-held stance", await waitAction("kneel"));
  await page.keyboard.up("KeyC");
  check("releasing the stance idles", await waitAction("idle"));

  // fire: 5 frames @14fps ≈ 360ms, a one-shot that ends where it began
  // upper bound raised from 1000 after this very run measured 983ms on
  // CI — seventeen milliseconds is not headroom, it is a scheduled flake
  const fireMs = await measureVerb("KeyF", "fire");
  check("fire runs its 5 frames", fireMs > 240 && fireMs < 1400, `${Math.round(fireMs)}ms`);
  check("fire ends in idle", await waitAction("idle"));
  // and firing out of a held aim returns to the aim, not to idle — the
  // stance is a held state, so the lock releasing must fall back into it
  await page.keyboard.down("KeyR");
  check("aiming again", await waitAction("aim"));
  // Headless rAF skips frames, so one shot sees only some of the five.
  // Accumulate across shots until every frame index has been observed —
  // a light assertion that passes because it saw nothing is not a test.
  // Headless rAF runs around 5fps against a 500ms sheet, and the sample
  // phase cannot be walked: locked.started is stamped on the verb's first
  // RENDERED frame, so delaying the keypress shifts nothing. Frames 0 and
  // 2 are what this environment can see, and that is enough to judge —
  // the off-by-one being guarded moved BOTH of them (0: 0→3.4, 2: 2.2→1.1).
  const lit = {};
  let detour = null, sawFire = false;
  for (let shotN = 0; shotN < 6 && Object.keys(lit).length < 5; shotN++) {
    await page.waitForTimeout(120);
    const trace = await recordFrames("KeyF", 900);
    const first = trace.findIndex(s => s.a === "fire");
    if (first < 0) continue;
    sawFire = true;
    for (const s of trace) if (s.a === "fire") lit[s.f] = s.l;
    // the seam is one frame wide, so only a per-frame trace can see it
    const after = trace.slice(first);
    if (detour === null && after.some(s => s.a === "idle")) {
      detour = after.map(s => `${s.a}${s.f}`).join(" ");
    }
  }
  check("F fires from the aim", sawFire);
  check("no idle frame between the shot and the held aim",
    detour === null, detour ?? "");
  // The spill must ride the frames the bloom is actually drawn on:
  // fire_frames() puts stages on 1,2,3 — 0 is the pre-shot hold, 4 the
  // settle. This exact curve is the contract with the sheet; the Python
  // sweep test asserts the other half, that the bloom really is on 1-3.
  //
  // Every frame the trace DID catch must match, and the check must not be
  // able to pass by observing nothing — frame 0 above all, because the
  // off-by-one this guards lit frame 0 at full intensity before any bloom
  // was drawn.
  const EXPECT = [0, 3.4, 2.2, 1.1, 0];
  const seen = Object.keys(lit).map(Number).sort();
  check("enough shot frames observed to judge, including frame 0",
    seen.length >= 2 && lit[0] !== undefined, `saw ${seen.join(",")}`);
  const wrong = seen.filter(f => lit[f] !== EXPECT[f]).map(f => `f${f}: ${lit[f]}≠${EXPECT[f]}`);
  check("the spill lights exactly the bloom frames it belongs to",
    !wrong.length, wrong.length ? wrong.join(" ") : `f${seen.join(",f")} all match`);
  await page.keyboard.up("KeyR");
  check("releasing R after the shot idles", await waitAction("idle"));

  // death: plays through, holds the floor, only movement rises
  await page.keyboard.press("KeyX");
  check("X goes down", await waitAction("death"));
  await page.waitForTimeout(1200);
  check("death holds the floor", (await ds("action")) === "death");
  check("held frame is the last", (await ds("frame")) === "5");
  await page.keyboard.press("KeyF");
  await page.waitForTimeout(300);
  check("verbs don't reach the floor", (await ds("action")) === "death");
  await page.keyboard.down("KeyS");
  check("movement rises", await waitAction("walk"));
  await page.keyboard.up("KeyS");

  // ---- one missing render-squad sheet faults the room-wide gate -----
  const missingSquadSheet = path.join(squadRender96("sable"), "kneel_left.png");
  fs.rmSync(missingSquadSheet, { force: true });
  await boot();
  check("a missing squad sheet faults the room", (await ds("sprites")) === "error");
  const squadFault = await page.textContent("#asset-gate");
  check("the squad fault names its render regeneration path",
    squadFault.includes("squad_render_sheets.py")
      && squadFault.includes("squad_canvas96.py"));
  // The gate's static copy names every path; the DETAIL must name the fix
  // for the sheet actually missing. A squad sheet prescribing only the
  // player's regen — under ?body=composed, the licensed pipeline — would
  // send the user to a rebuild that cannot restore it (caught in review).
  const squadDetail = await page.textContent("#asset-detail");
  check("the fault DETAIL prescribes the squad regen for a squad sheet",
    squadDetail.includes("squad_render_sheets.py")
      && squadDetail.includes("squad_canvas96.py"),
    squadDetail);
  gen("slice96");

  // ---- PARTIAL Cipher roster is a fault -----------------------------
  clearSheets();
  gen("full");
  fs.rmSync(path.join(sheetsDir("cipher"), "HEAL"), { recursive: true, force: true });
  fs.rmSync(path.join(sheetsDir("cipher"), "DASH"), { recursive: true, force: true });
  await boot("?body=composed");
  check("partial roster faults", (await ds("sprites")) === "error");
  check("fault names the incomplete state",
    (await page.textContent("#asset-detail")).includes("composed roster incomplete"));

  // ---- rejection is not absence: bad geometry faults on its own ----
  clearSheets();
  gen("badgeom");
  await boot("?body=composed");
  check("wrong-height sheets fault rather than degrade",
    (await ds("sprites")) === "error");
  check("geometry fault names the sheet",
    (await page.textContent("#asset-detail")).includes("expected a row"));

  // ---- a held key's auto-repeat cannot revive a downed body ---------
  clearSheets();
  gen("full");
  await boot("?body=composed");
  await page.keyboard.down("KeyW");
  check("moving before the fall", await waitAction("walk"));
  await page.keyboard.press("KeyX");
  check("goes down while a key is held", await waitAction("death"));
  await page.waitForTimeout(1500);   // death plays through; W never released
  for (let i = 0; i < 5; i++) {      // playwright marks re-downs of a held key repeat=true
    await page.keyboard.down("KeyW");
    await page.waitForTimeout(60);
  }
  check("auto-repeat does not revive", (await ds("action")) === "death");
  await page.keyboard.up("KeyW");
  await page.keyboard.down("KeyW");  // the fresh press
  check("a fresh press rises", await waitAction("walk"));
  await page.keyboard.up("KeyW");

  // ---- the whole-generated body: ?body=render96 ---------------------
  // The render body declares the composed bill entire. The gate stays
  // all-or-nothing over that declared set, while the squad rides its own
  // tracked render sheets. Refusal for a future partial source is executed
  // against a probe below.
  clearSheets();
  gen("full");
  gen("slice96");
  const roomPath = path.join(ROOT, "prototypes", "walkable", "index.html");
  const roomSrc = fs.readFileSync(roomPath, "utf8");
  check("the squad cadence pin is declared beside its action bill",
    roomSrc.includes('const SQUAD_FPS = { idle: 4, kneel: 2 };'));
  const firePath = path.join(RENDER96, "fire_down.png");
  const firePng = fs.existsSync(firePath) ? fs.readFileSync(firePath) : null;
  const fireDimsOk = firePng !== null
    && firePng.readUInt32BE(16) === 5 * 96
    && firePng.readUInt32BE(20) === 80;
  check("slice fire fixture is 5 frames on the 96x80 canvas",
    fireDimsOk,
    firePng === null ? "missing fire_down.png" : fireDimsOk ? "" : "wrong dimensions");
  for (const [verb, frames] of Object.entries({ hurt: 4, death: 9, heal: 12 })) {
    const fixturePath = path.join(RENDER96, `${verb}_down.png`);
    const png = fs.existsSync(fixturePath) ? fs.readFileSync(fixturePath) : null;
    const geometryOk = png !== null
      && png.readUInt32BE(16) === frames * 96
      && png.readUInt32BE(20) === 80;
    check(`render96 ${verb} fixture is ${frames} frames on the 96x80 canvas`,
      geometryOk,
      png === null ? `missing ${verb}_down.png` : geometryOk ? "" : "wrong dimensions");
  }
  for (const fighter of SQUAD_FIGHTERS) {
    for (const [verb, frames] of Object.entries({ idle: 4, kneel: 2 })) {
      const fixturePath = path.join(squadRender96(fighter), `${verb}_down.png`);
      const png = fs.existsSync(fixturePath) ? fs.readFileSync(fixturePath) : null;
      const geometryOk = png !== null
        && png.readUInt32BE(16) === frames * 96
        && png.readUInt32BE(20) === 80;
      check(`${fighter} ${verb} fixture is ${frames} frames on the 96x80 canvas`,
        geometryOk,
        png === null ? `missing ${verb}_down.png` : geometryOk ? "" : "wrong dimensions");
    }
  }
  // THE DEFAULT: a plain URL now stages the render body — the doc's
  // default-flip (2026-08-09, after the designer's full-roster 1x walk),
  // executed rather than narrated. The composed PLAYER stays one query
  // away; the squad keeps its own render roster under both URLs.
  await boot();
  check("the plain URL stages the render body",
    (await ds("roster")) === "render96"
      && (await page.textContent("#body-state")) === "RENDER 96 / FULL ROSTER / READY",
    `roster ${await ds("roster")}`);
  await boot("?body=render96");
  check("slice roster boots", (await ds("sprites")) === "ready");
  check("roster reads render96", (await ds("roster")) === "render96");
  check("BODY cell names the full render roster",
    (await page.textContent("#body-state")) === "RENDER 96 / FULL ROSTER / READY");
  await page.waitForFunction(() =>
    (document.getElementById("cv").dataset.squadSprites ?? "").split(",").length === 4);
  check("the render squad stands beside the render body",
    ((await ds("squadSprites")) ?? "").split(",").length === 4);

  // Execute the pin through the public dataset too: the render squad's idle
  // must actually advance, not merely declare an fps map it never consults.
  // Do NOT assert an exact period here. This Windows headless run sampled
  // the old 7fps composed idle at a 283ms median because rAF skipped authored
  // transitions; that number would bless the wrong cadence. The source check
  // above pins the exact 4fps value, and this trace proves the loop consumes
  // a cadence and advances rather than freezing on frame zero.
  const squadTrace = await recordSquadFrames("vesper", 1200);
  const squadFrames = new Set(squadTrace
    .filter(state => state.action === "idle")
    .map(state => state.frame));
  check("render squad idle advances through its pinned cadence",
    squadFrames.size > 1, `saw frames ${[...squadFrames].join(",")}`);

  // the moving verb owns a declared sheet: the input and staged verb
  // stay aligned, and no absence is noted on the moving state. A bare
  // press is the WALK now; the run is still declared and still reachable
  // on shift, which the gait check above executes.
  await page.keyboard.down("KeyW");
  check("slice moves as walk", await waitAction("walk"));
  check("walk resolves to its own sheet", (await ds("verb")) === "walk");
  check("a declared moving verb carries no absence note", (await ds("note")) === "");
  await page.keyboard.up("KeyW");
  check("slice idles", await waitAction("idle"));
  check("idle resolves to itself", (await ds("verb")) === "idle");

  await page.keyboard.down("KeyC");
  check("the slice kneels — the verb the slice exists for", await waitAction("kneel"));
  check("kneel resolves to its own sheet", (await ds("verb")) === "kneel");
  await page.keyboard.up("KeyC");
  await waitAction("idle");

  // AIM owns a declared held stance at the render's pinned breath cadence.
  await page.keyboard.down("KeyR");
  check("holding R resolves the slice into aim", await waitAction("aim"));
  check("aim resolves to its own sheet", (await ds("verb")) === "aim");
  check("the declared aim carries no absence note", (await ds("note")) === "");

  // FIRE owns its five-frame lock at the render's pinned shot cadence.
  // same shape as dash's snapshot below, and like it, on the DEFAULT
  // waitForFunction budget: an explicit 1500ms here timed out on a loaded
  // CI runner while the shot itself ran 967ms (caught in CI)
  const fireDone = measureVerb("KeyF", "fire");
  const fireState = await page.waitForFunction(() => {
    const state = document.getElementById("cv").dataset;
    return state.action === "fire"
      ? { verb: state.verb, note: state.note, refused: state.refused }
      : false;
  }).then(handle => handle.jsonValue(), () => null);
  check("F starts the slice fire", fireState !== null);
  check("fire resolves to its own sheet", fireState?.verb === "fire");
  check("the declared fire carries no absence note", fireState?.note === "");
  check("the declared fire is not refused", fireState?.refused === "");
  const sliceFireMs = await fireDone;
  check("slice fire plays its 5 frames at 10fps",
    sliceFireMs > 350 && sliceFireMs < 1400, `${Math.round(sliceFireMs)}ms`);
  check("slice fire returns to the held aim", await waitAction("aim"));

  // Headless rAF skips frames. Accumulate across bounded shots until all
  // five have appeared, and trace the release seam rather than polling its
  // destination — one idle frame between fire and aim is still a broken seam.
  const renderLit = {};
  let fireDetour = null;
  let sawRenderFire = false;
  let sawAimResume = false;
  for (let shotN = 0;
    shotN < 6 && Object.keys(renderLit).length < 5;
    shotN++) {
    await page.waitForTimeout(120);
    // the window must outlast the SLOWEST shot plus its resume frame: CI
    // rAF stretched the 500ms sheet to 967ms, and a 900ms trace ended
    // before the aim ever appeared (caught in CI)
    const trace = await recordFrames("KeyF", 2200);
    const first = trace.findIndex(s => s.a === "fire");
    if (first < 0) continue;
    sawRenderFire = true;
    for (const state of trace) {
      if (state.a === "fire") renderLit[state.f] = state.light;
    }
    const after = trace.slice(first);
    const resumed = after.findIndex(s => s.a === "aim");
    if (resumed >= 0) {
      sawAimResume = true;
      const seam = after.slice(0, resumed + 1);
      if (fireDetour === null && seam.some(s => s.a === "idle")) {
        fireDetour = seam.map(s => `${s.a}${s.f}`).join(" ");
      }
    }
  }
  check("no idle frame between slice fire and the held aim",
    sawRenderFire && sawAimResume && fireDetour === null,
    fireDetour ?? `fire ${sawRenderFire}, resumed aim ${sawAimResume}`);
  const FIRE_EXPECT = [0, 3.4, 2.2, 1.1, 0].map(n => n.toFixed(2));
  const fireSeen = Object.keys(renderLit).map(Number).sort();
  check("slice fire exposes at least one lit-frame sample",
    fireSeen.length > 0, `saw ${fireSeen.join(",")}`);
  const fireWrong = fireSeen
    .filter(frame => renderLit[frame] !== FIRE_EXPECT[frame])
    .map(frame => `f${frame}: ${renderLit[frame]}≠${FIRE_EXPECT[frame]}`);
  check("slice spill rides every observed fire frame",
    fireWrong.length === 0,
    fireWrong.length ? fireWrong.join(" ") : `f${fireSeen.join(",f")} all match`);
  await page.keyboard.up("KeyR");
  check("releasing R after the slice shots idles", await waitAction("idle"));

  // HURT owns its four-frame lock at the render's pinned flinch cadence.
  // Snapshot while the lock is live: a destination poll can only prove
  // that it ended, not which sheet actually owned those frames.
  const hurtDone = measureVerb("KeyG", "hurt");
  const hurtState = await page.waitForFunction(() => {
    const state = document.getElementById("cv").dataset;
    return state.action === "hurt"
      ? { verb: state.verb, note: state.note, refused: state.refused }
      : false;
  }).then(handle => handle.jsonValue(), () => null);
  check("G starts the render96 hurt", hurtState !== null);
  check("hurt resolves to its own sheet", hurtState?.verb === "hurt");
  check("the declared hurt carries no absence note", hurtState?.note === "");
  check("the declared hurt is not refused", hurtState?.refused === "");
  const renderHurtMs = await hurtDone;
  check("render96 hurt plays its 4 frames at 12fps",
    renderHurtMs > 230 && renderHurtMs < 1000, `${Math.round(renderHurtMs)}ms`);
  check("render96 hurt returns to idle", await waitAction("idle"));

  // DEATH owns nine frames at 10fps, then transfers from its lock into
  // DOWNED. Its duration therefore ends at that transition, not at a
  // return to idle — there is no automatic return from the floor.
  await page.evaluate(() => {
    const cv = document.getElementById("cv");
    const label = document.getElementById("action-state");
    window.__downedDone = new Promise(res => {
      let t0 = null;
      const begin = performance.now();
      function tick(t) {
        if (t0 === null && cv.dataset.action === "death") t0 = t;
        if (t0 !== null && label.textContent.startsWith("DOWN —")) return res(t - t0);
        if (t - begin > 8000) return res(t0 === null ? -1 : -2);
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  });
  await page.keyboard.press("KeyX");
  const deathState = await page.waitForFunction(() => {
    const state = document.getElementById("cv").dataset;
    return state.action === "death"
      ? { verb: state.verb, note: state.note, refused: state.refused }
      : false;
  }).then(handle => handle.jsonValue(), () => null);
  check("X starts the render96 death", deathState !== null);
  check("death resolves to its own sheet", deathState?.verb === "death");
  check("the declared death carries no absence note", deathState?.note === "");
  check("the declared death is not refused", deathState?.refused === "");
  const renderDeathMs = await page.evaluate(() => window.__downedDone);
  check("render96 death reaches DOWNED after its 9 frames at 10fps",
    renderDeathMs > 700 && renderDeathMs < 2500, `${Math.round(renderDeathMs)}ms`);
  const heldFirst = deathState === null ? null : await page.waitForFunction(() => {
    const cv = document.getElementById("cv");
    return cv.dataset.verb === "death"
      && cv.dataset.frame === "8"
      && document.getElementById("action-state").textContent.startsWith("DOWN —")
      ? { verb: cv.dataset.verb, frame: cv.dataset.frame }
      : false;
  }).then(handle => handle.jsonValue(), () => null);
  await page.waitForTimeout(200);
  const heldSecond = heldFirst === null ? null : {
    verb: await ds("verb"),
    frame: await ds("frame"),
  };
  check("render96 death holds its last frame across the floor",
    heldFirst?.verb === "death" && heldFirst?.frame === "8"
      && heldSecond?.verb === "death" && heldSecond?.frame === "8",
    `${JSON.stringify(heldFirst)} -> ${JSON.stringify(heldSecond)}`);
  await page.keyboard.down("KeyS");
  const roseFromDeath = await waitAction("walk");
  check("a fresh move press rises the render96 body",
    heldFirst !== null && roseFromDeath && (await ds("verb")) === "walk");
  await page.keyboard.up("KeyS");
  await waitAction("idle");

  // HEAL owns twelve frames at 10fps. Headless rAF skips frames, so
  // accumulate every heal sample across bounded attempts; observing no
  // channel light at all must never count as proof that its floor held.
  const healDone = measureVerb("KeyH", "heal");
  const healState = await page.waitForFunction(() => {
    const state = document.getElementById("cv").dataset;
    return state.action === "heal"
      ? { verb: state.verb, note: state.note, refused: state.refused }
      : false;
  }).then(handle => handle.jsonValue(), () => null);
  check("H starts the render96 heal", healState !== null);
  check("heal resolves to its own sheet", healState?.verb === "heal");
  check("the declared heal carries no absence note", healState?.note === "");
  check("the declared heal is not refused", healState?.refused === "");
  const renderHealMs = await healDone;
  check("render96 heal plays its 12 frames at 10fps",
    renderHealMs > 900 && renderHealMs < 3000, `${Math.round(renderHealMs)}ms`);
  const healSamples = [];
  const healSeen = new Set();
  for (let attempt = 0; attempt < 4 && healSeen.size < 12; attempt++) {
    await page.waitForTimeout(120);
    const trace = await recordFrames("KeyH", 3400);
    for (const state of trace) {
      if (state.a !== "heal") continue;
      healSamples.push(state);
      healSeen.add(state.f);
    }
  }
  check("render96 heal exposes at least one channel-light sample",
    healSamples.length > 0, `saw frames ${[...healSeen].sort((a, b) => a - b).join(",")}`);
  // the floor is INCLUSIVE: the mechanism is 1.3 + sin*0.3, whose trough is
  // exactly 1.0 and publishes as "1.00" — a strict > here failed on a
  // legitimate trough frame (caught by the agent's own red run)
  const dimHeal = healSamples.filter(state => state.l < 1.0)
    .map(state => `f${state.f}:${state.light}`);
  check("render96 channel light stays at or above its flicker floor",
    healSamples.length > 0 && dimHeal.length === 0,
    dimHeal.length ? dimHeal.join(" ") : `${healSamples.length} samples at/above 1.0`);
  await waitAction("idle");

  // DASH is the slice's declared moving lock. Its 7-frame width and pinned
  // 14fps cadence spend the authored 500ms before the lock returns to idle.
  const dashPng = fs.readFileSync(path.join(RENDER96, "dash_down.png"));
  check("slice dash fixture is 7 frames on the 96x80 canvas",
    dashPng.readUInt32BE(16) === 7 * 96 && dashPng.readUInt32BE(20) === 80);
  const beforeDash = await ds("position");
  const dashDone = measureVerb("KeyL", "dash");
  const dashState = await page.waitForFunction(() => {
    const state = document.getElementById("cv").dataset;
    return state.action === "dash"
      ? { verb: state.verb, note: state.note, refused: state.refused }
      : false;
  }).then(handle => handle.jsonValue(), () => null);
  check("L starts the slice dash", dashState !== null);
  check("dash resolves to its own sheet", dashState?.verb === "dash");
  check("the declared dash carries no absence note", dashState?.note === "");
  check("the declared dash is not refused", dashState?.refused === "");
  const sliceDashMs = await dashDone;
  check("slice dash plays its 7 frames at 14fps",
    sliceDashMs > 400 && sliceDashMs < 1100, `${Math.round(sliceDashMs)}ms`);
  check("slice dash displaces the body", (await ds("position")) !== beforeDash,
    `${beforeDash} -> ${await ds("position")}`);
  check("slice dash returns to idle when the lock expires", await waitAction("idle"));

  // The pin, executed at its boundary: the future this guards against is
  // a SOURCE-CODE retune of the composed table (SHEETS is module-scoped,
  // deliberately out of evaluate's reach — the dataset hooks are the only
  // granted surface). So stage exactly that future: a probe copy of the
  // room whose SHEETS.dash.fps says 28, served from the same directory so
  // every relative path still resolves. The slice's dash must still spend
  // its authored 500ms, because the locked branch resolves through
  // SOURCE.fps first — before that fix this halves to ~250ms and fails
  // the floor.
  const retunedSrc = roomSrc.replace(
    'dash: { folder: "DASH", stem: "dash", fps: 14, loop: false },',
    'dash: { folder: "DASH", stem: "dash", fps: 28, loop: false },');
  if (retunedSrc === roomSrc) {
    throw new Error("retune probe found no composed dash line to edit — "
      + "the boundary this test executes has moved; update both");
  }
  const probePath = path.join(ROOT, "prototypes", "walkable",
    "index.retune-probe.html");
  fs.writeFileSync(probePath, retunedSrc);
  try {
    await boot("index.retune-probe.html?body=render96");
    const retunedMs = await measureVerb("KeyL", "dash");
    check("a composed dash retune cannot reach the slice's cadence",
      retunedMs > 400,
      `${Math.round(retunedMs)}ms with the composed table retuned to 28`);
  } finally {
    fs.unlinkSync(probePath);
  }
  await boot("?body=render96");

  // The full render roster leaves no live refusal target. Keep that
  // grammar executable against a future partial source by making one:
  // a same-directory room copy preserves every relative asset URL.
  const refusalProbePath = path.join(ROOT, "prototypes", "walkable",
    "index.refusal-probe.html");
  const fullRenderVerbs =
    'verbs: ["idle", "walk", "run", "dash", "hurt", "death", "heal", "kneel", "aim", "fire"],';
  const partialRenderVerbs =
    'verbs: ["idle", "walk", "run", "dash", "hurt", "death", "kneel", "aim", "fire"],';
  const refusalSrc = roomSrc.replace(fullRenderVerbs, partialRenderVerbs);
  if (refusalSrc === roomSrc) {
    throw new Error("refusal probe found no render96 verbs line to edit — "
      + "the future-partial boundary this test executes has moved; update both");
  }
  fs.writeFileSync(refusalProbePath, refusalSrc);
  try {
    await boot("index.refusal-probe.html?body=render96");
    await page.keyboard.down("KeyR");
    check("the refusal probe still owns its declared aim", await waitAction("aim"));
    await page.keyboard.press("KeyH");
    const composedRefusal = await page.waitForFunction(() =>
      document.getElementById("cv").dataset.refused === "heal")
      .then(() => true, () => false);
    const composedLabel = await page.textContent("#action-state");
    check("heal refusal composes beside the probe's real aim",
      composedRefusal && composedLabel === "AIM · NO HEAL SHEET", composedLabel);
    await page.keyboard.up("KeyR");
    await waitAction("idle");
    await page.keyboard.press("KeyH");
    const bareRefusal = await page.waitForFunction(() =>
      document.getElementById("cv").dataset.refused === "heal")
      .then(() => true, () => false);
    check("bare heal is refused by name on the probe",
      bareRefusal && (await ds("refused")) === "heal", await ds("refused"));
    await page.keyboard.down("KeyW");
    check("moving on from the probe refusal", await waitAction("walk"));
    check("the probe refusal clears on the next action", (await ds("refused")) === "");
    await page.keyboard.up("KeyW");
  } finally {
    await page.keyboard.up("KeyR").catch(() => {});
    fs.unlinkSync(refusalProbePath);
  }
  await boot("?body=render96");

  // the gate is all-or-nothing over the DECLARED set
  fs.rmSync(path.join(RENDER96, "kneel_left.png"));
  await boot("?body=render96");
  check("a missing declared slice sheet faults the room",
    (await ds("sprites")) === "error");
  check("the slice fault names the state and the regen path",
    (await page.textContent("#asset-detail")).includes("render96 roster incomplete"));

  // an unknown source is a fault, not a default
  await boot("?body=rneder96");
  check("an unknown body source faults rather than defaulting",
    (await ds("sprites")) === "error");
  check("the unknown-source fault names what the room stages",
    (await page.textContent("#asset-detail")).includes("unknown body source"));

  // and an INHERITED name is unknown too: ?body=constructor would fish a
  // function out of Object.prototype and crash past the fault branch
  await boot("?body=constructor");
  check("an inherited prototype name is refused like any unknown source",
    (await ds("sprites")) === "error"
      && (await page.textContent("#asset-detail")).includes("unknown body source"));
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server) server.kill();
  clearSheets();
  for (const renderDir of TRACKED_RENDER_DIRS) {
    fs.rmSync(renderDir, { recursive: true, force: true });
  }
  for (const fighter of FIGHTERS) {
    if (fs.existsSync(backupDir(fighter))) {
      fs.renameSync(backupDir(fighter), sheetsDir(fighter));
    }
  }
  for (const renderDir of TRACKED_RENDER_DIRS) {
    const renderBak = trackedBackup(renderDir);
    if (fs.existsSync(renderBak)) {
      fs.renameSync(renderBak, renderDir);
    }
  }
  fs.rmSync(LOCK, { recursive: true, force: true });
}

console.log(failures ? `\n${failures} FAILURES` : "\nALL PASS");
process.exit(failures ? 1 : 0);
