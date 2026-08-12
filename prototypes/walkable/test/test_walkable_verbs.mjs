// Executes the walkable page's verb claims in headless chromium.
//
// Serves the repo root, boots the page against synthetic sheets, and
// drives the keyboard through every verb plus the roster fault states.
// Verb durations are measured IN PAGE via rAF: evaluate round-trips can
// be slower than a 4-frame flinch, so sleep-then-read checks lie —
// that lesson is why the watcher exists (caught building this harness).
//
// Real composed sheets for Cipher and the three fielded operatives, plus
// every tracked render96 destination, are backed up before the run and
// restored after — including when setup itself fails, and a
// backup stranded by a hard-killed run is reinstated on the next start.
//
// Run:  cd prototypes/walkable/test
//       npm install && npx playwright install chromium
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
import { S as RULES_S, restart as rulesRestart } from "../../tactical-core/rules.js";

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
    down, cert, rules: "test-rules", at: `2026-08-05T00:00:0${seed}Z`,
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
    (document.getElementById("cv").dataset.squadSprites ?? "").split(",").length === 3);
  const freshSquad = await ds("squad");
  const freshSprites = await ds("squadSprites");
  check("the three fielded operatives render in the room",
    (freshSprites ?? "").split(",").length === 3
      && ["vesper", "koa", "sable"].every(name => freshSprites.includes(`${name}:`)),
    freshSprites);
  check("a fresh run leaves the whole squad idle",
    freshSquad === "vesper:idle,koa:idle,sable:idle", freshSquad);

  // The room stages a body for every operative the yard fields, matched by
  // the slug/name relationship the room actually uses at runtime
  // (fighter.toUpperCase() === the op name in a card's `down`).
  rulesRestart(0xdeadbeef);
  const ops = RULES_S.units.filter(u => u.side === "op").map(u => u.name).sort();
  const staged = (freshSquad ?? "").split(",")
    .map(entry => entry.split(":")[0].toUpperCase()).sort();
  check("the room stages a body for every operative the yard fields",
    JSON.stringify(ops) === JSON.stringify(staged),
    `yard ${ops.join(",")} vs room ${staged.join(",")}`);

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
    aftermathSquad === "vesper:idle,koa:idle,sable:kneel", aftermathSquad);
  // The discrimination, stated as the claim rather than as a string: VESPER
  // went down on an EARLIER counted card, so she is in the cumulative tally
  // the panel shows and is NOT on a knee in the room. Order-independent on
  // purpose — summary() sorts wounded by count then name, which is run-core's
  // presentation choice and not something this suite should pin from here.
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
    struckSquad === "vesper:idle,koa:idle,sable:idle", struckSquad);

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

  // the door enforces what the panel says: unfit means no deal, said as
  // a cut rather than a dead trigger — and no seam frame ever exists
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const gated = await page.waitForFunction(() =>
    document.getElementById("cv").dataset.seam === "gated",
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  check("an unfit roster gates the door", gated);
  check("a gated door never opens the seam", !(await page.$("#seamframe")));
  const gateCut = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
  check("the refusal says why and what heals it",
    /THE DEAL IS GATED/.test(gateCut) && /SABLE 2/.test(gateCut)
      && /SHIFT\+P/.test(gateCut), gateCut);

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
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const gatedComplete = await page.waitForFunction(() =>
    document.getElementById("cv").dataset.seam === "gated",
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  check("a complete slate gates the door", gatedComplete);
  const completeCut = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
  check("and the cut says the slate is complete",
    /SLATE IS COMPLETE/.test(completeCut) && /NOTHING LEFT TO FIGHT/.test(completeCut),
    completeCut);
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
  check("a plain run's panel carries no slate line",
    !/SLATE /.test(await panelText()), await panelText());
  await pass();
  check("a plain run has nothing to pass and says so",
    /NOTHING TO PASS/.test(await panelText()), await panelText());

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

  await page.evaluate(() => localStorage.removeItem("sentinel.run"));
  await boot("?body=composed");

  // walk: hold shift + move (steady states)
  await page.keyboard.down("Shift");
  await page.keyboard.down("KeyW");
  check("shift+move walks", await waitAction("walk"));
  await page.keyboard.up("Shift");
  check("release shift runs", await waitAction("run"));
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
  check("moving cancels a held stance", await waitAction("run"));
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
  check("movement rises", await waitAction("run"));
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
  check("running before the fall", await waitAction("run"));
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
  check("a fresh press rises", await waitAction("run"));
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
    (document.getElementById("cv").dataset.squadSprites ?? "").split(",").length === 3);
  check("the render squad stands beside the render body",
    ((await ds("squadSprites")) ?? "").split(",").length === 3);

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

  // run owns a declared sheet: the input and staged verb stay aligned,
  // and no absence is noted on the moving state
  await page.keyboard.down("KeyW");
  check("slice moves as run", await waitAction("run"));
  check("run resolves to its own sheet", (await ds("verb")) === "run");
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
  const roseFromDeath = await waitAction("run");
  check("a fresh move press rises the render96 body",
    heldFirst !== null && roseFromDeath && (await ds("verb")) === "run");
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
    check("moving on from the probe refusal", await waitAction("run"));
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
