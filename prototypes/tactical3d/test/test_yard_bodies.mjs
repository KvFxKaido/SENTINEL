// Executes the yard's converged-body claims in headless chromium.
//
// The yard used to draw hand-authored 32×32 grids with no facing, no
// frames and one kneel swap. It now fields the same molded 96×80 pack
// bodies the walkable room does, which means it grew four facings, a
// verb state machine, async sheet loading and alpha picking — all of it
// previously untested, in a file whose only prior coverage was the rules
// module underneath it.
//
// The match is DRIVEN BY THE GAME, not by clicking pixels: Tab selects,
// F toggles target mode, and Enter ends the turn so the hostile AI plays
// itself. That reaches fire / hurt / death / kneel without the harness
// ever needing to know where a body is on screen — the one thing a
// headless test cannot see.
//
// Real molded canvases for all five bodies are backed up before the run
// and restored after, including when setup itself fails; a backup
// stranded by a hard-killed run is reinstated on the next start.
//
// Run:  cd prototypes/tactical3d/test
//       npm install && npx playwright install chromium
//       node test_yard_bodies.mjs
import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as packSprites from "../pack_sprites.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
// shared with the walkable harness on purpose: both pages load the SAME
// molded bodies, so faking them two different ways would let the fixtures
// drift exactly where the convergence says they must not
const GEN = path.join(ROOT, "prototypes", "walkable", "test", "make_synthetic_sheets.py");
const FIGHTERS = ["cipher", "vesper", "koa", "sable", "syn"];
const SQUAD_FIGHTERS = ["vesper", "koa", "sable", "syn"];
const PY = process.platform === "win32" ? "python" : "python3";
const PORT = process.env.YARD_TEST_PORT ?? "8094";
const URL = `http://localhost:${PORT}/prototypes/tactical3d/?seed=deadbeef`;

const sheetsDir = f => path.join(ROOT, "assets", "sprites", "composed", f);
const backupDir = f => sheetsDir(f) + ".harness-backup";
// slice96 writes tracked source art, so it gets the walkable harness's same
// backup law: Cipher plus every squad destination the generator touches.
const RENDER96 = path.join(ROOT, "assets", "original", "cipher_render", "sheets96");
const squadRender96 = fighter => path.join(
  ROOT, "assets", "original", "squad_render", "sheets96", fighter);
const TRACKED_RENDER_DIRS = [RENDER96, ...SQUAD_FIGHTERS.map(squadRender96)];
const trackedBackup = dir => dir + ".harness-backup";

function gen(mode) {
  const r = spawnSync(PY, [GEN, mode, FIGHTERS.join(",")], { stdio: "inherit" });
  if (r.status !== 0) throw new Error(`sheet generation failed (${mode})`);
}
const clearSheets = () => {
  for (const f of FIGHTERS) fs.rmSync(sheetsDir(f), { recursive: true, force: true });
};

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

// ---- pack routing: execute the module without a browser ------------
let rejected = false;
try {
  packSprites.configureBody?.("rneder96");
} catch (error) {
  rejected = /rneder96/.test(error.message);
}
check("configureBody rejects an unknown source",
  typeof packSprites.configureBody === "function" && rejected);

packSprites.configureBody?.("render96");
const cipherRenderUrl = packSprites.sheetUrl("cipher", "idle", "down");
const koaRenderUrl = packSprites.sheetUrl("koa", "fire", "down");
const synRenderUrl = packSprites.sheetUrl("syn", "death", "left");
const nixRenderUrl = packSprites.sheetUrl("nix", "idle", "down");
// URLs end in the per-load cache buster (the room's stale-sheet lesson,
// paid for here by CI), so the assertions pin the path and the buster's
// shape rather than an exact string.
check("render96 routes Cipher to the flat render sheet",
  cipherRenderUrl.startsWith("../../assets/original/cipher_render/sheets96/idle_down.png?v="),
  cipherRenderUrl);
// The squad-combat phase armed the whole board: render96 is every
// fighter's body now, squad and SYN from the squad re-frame.
check("render96 routes the squad to their render sheets",
  koaRenderUrl.startsWith("../../assets/original/squad_render/sheets96/koa/fire_down.png?v="),
  koaRenderUrl);
check("render96 routes SYN to his render sheets",
  synRenderUrl.startsWith("../../assets/original/squad_render/sheets96/syn/death_left.png?v="),
  synRenderUrl);
check("NIX's declared prototype body loan routes to the tracked SYN canvas",
  packSprites.fighterSlug("NIX") === "nix"
    && packSprites.fighterCanvas("nix") === "syn"
    && nixRenderUrl.startsWith("../../assets/original/squad_render/sheets96/syn/idle_down.png?v="),
  nixRenderUrl);

packSprites.configureBody?.("composed");
const cipherComposedUrl = packSprites.sheetUrl("cipher", "idle", "down");
const koaComposedUrl = packSprites.sheetUrl("koa", "idle", "down");
check("composed leaves Cipher on the composed sheet",
  cipherComposedUrl.startsWith("../../assets/sprites/composed/cipher/IDLE/idle_down.png?v="),
  cipherComposedUrl);
check("composed leaves the squad on composed sheets",
  koaComposedUrl.startsWith("../../assets/sprites/composed/koa/IDLE/idle_down.png?v="),
  koaComposedUrl);

packSprites.configureBody?.("render96");
const cipherIdleFps = packSprites.sheetFps?.("cipher", "idle");
const koaRenderFps = packSprites.sheetFps?.("koa", "idle");
packSprites.configureBody?.("composed");
const koaComposedFps = packSprites.sheetFps?.("koa", "idle");
packSprites.configureBody?.("render96");
check("cadence follows the staged body for every fighter",
  cipherIdleFps === 4 && koaRenderFps === 4 && koaComposedFps === 7,
  `cipher ${cipherIdleFps}; koa render ${koaRenderFps} composed ${koaComposedFps}`);

// ---- setup: preserve real sheets ----------------------------------
// Use the walkable harness's lock too: both suites move the same tracked
// render dirs, so overlapping them would make each mistake the other's
// live backup for a stranded one.
const LOCK = path.join(ROOT, "prototypes", "walkable", "test", ".harness-lock");
try {
  fs.mkdirSync(LOCK);
} catch {
  console.error(`another harness run appears live (${LOCK} exists) — `
    + "refusing to touch the backups; remove the dir if that run is dead");
  process.exit(1);
}

// A backup left by a run that died before restoring IS the real artifact:
// reinstate it, never delete it (the walkable harness bought this lesson).
try {
  for (const f of FIGHTERS) {
    if (fs.existsSync(backupDir(f))) {
      fs.rmSync(sheetsDir(f), { recursive: true, force: true });
      fs.renameSync(backupDir(f), sheetsDir(f));
    }
    if (fs.existsSync(sheetsDir(f))) fs.renameSync(sheetsDir(f), backupDir(f));
  }
  for (const renderDir of TRACKED_RENDER_DIRS) {
    const renderBak = trackedBackup(renderDir);
    if (fs.existsSync(renderBak)) {
      console.error(`STRANDED sheets96 backup found at ${renderBak} — a previous run died `
        + "before restoring; reinstating the real strips now. Until this "
        + "moment the tracked sheets96 dir held synthetic fixtures.");
      fs.rmSync(renderDir, { recursive: true, force: true });
      fs.renameSync(renderBak, renderDir);
    }
    if (fs.existsSync(renderDir)) fs.renameSync(renderDir, renderBak);
  }
} catch (error) {
  // Deliberately NO rollback here — the walkable harness's review-bought
  // design, inherited with its reasons: a rollback inside a crash path can
  // itself fail halfway and compound the damage, while freeing the lock
  // makes the NEXT start's reinstate pass (above) reachable, and that pass
  // restores every stranded backup before touching anything else. The cost
  // is a partial tree between crash and next start; the self-heal is the
  // recovery, and it runs first.
  fs.rmSync(LOCK, { recursive: true, force: true });
  throw error;
}

let server = null;
let browser = null;
let page = null;

const ds = k => page.evaluate(k => document.getElementById("cv").dataset[k], k);
// dataset.units is "id:action:facing:frame,..." — the yard's whole visible
// body state in one string, which is what makes this testable at all
const units = async () => {
  const raw = (await ds("units")) ?? "";
  return raw.split(",").filter(Boolean).map(s => {
    const [id, action, facing, frame] = s.split(":");
    return { id: +id, action, facing, frame: +frame };
  });
};

async function boot(query = "") {
  await page.goto(URL + query);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 15000 });
}
const idleFrames = async () => Object.fromEntries(
  ((await ds("idleFrames")) ?? "").split(",").filter(Boolean).map(entry => {
    const [fighter, frames] = entry.split(":");
    return [fighter, +frames];
  })
);
const beginCard = async () => {
  await page.keyboard.press("Enter");          // the card holds the match
  await page.waitForTimeout(300);
};

// wait until some unit reaches an action, polling in-page
const waitVerb = (action, timeout = 6000) =>
  page.waitForFunction(a => (document.getElementById("cv").dataset.units ?? "")
    .split(",").some(s => s.split(":")[1] === a), action, { timeout })
    .then(() => true, () => false);

try {
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

  // ---- the roster boots ---------------------------------------------
  gen("full");
  gen("slice96");
  await boot();
  check("yard roster boots", (await ds("sprites")) === "ready", await ds("sprites"));
  check("roster reads full", (await ds("roster")) === "full");
  check("the yard defaults to render96", (await ds("body")) === "render96", await ds("body"));
  const defaultFrames = await idleFrames();
  check("default Cipher idle loads the four-frame render sheet",
    defaultFrames.cipher === 4, JSON.stringify(defaultFrames));
  // the flip's loading proof: before the squad-combat phase this asserted
  // koa STAYED on the eight-frame composed sheet
  check("default Koa idle loads the four-frame render sheet",
    defaultFrames.koa === 4, JSON.stringify(defaultFrames));
  check("default SYN idle loads the four-frame render sheet",
    defaultFrames.syn === 4, JSON.stringify(defaultFrames));
  await beginCard();

  const start = await units();
  check("all six units render bodies", start.length === 6, `${start.length}`);
  check("every unit starts idle", start.every(u => u.action === "idle"),
    start.map(u => u.action).join(","));
  // the two sides face each other across the board — the operatives are
  // south of the crew, so they look up-screen and the crew looks down
  const ops = start.filter(u => u.id < 3), hos = start.filter(u => u.id >= 3);
  check("operatives face the crew", ops.every(u => u.facing === "up"),
    ops.map(u => u.facing).join(","));
  check("the crew faces the operatives", hos.every(u => u.facing === "down"),
    hos.map(u => u.facing).join(","));

  // ---- facing is camera-relative ------------------------------------
  // The sprite that a body shows must follow the SCREEN, not the world:
  // the old renderer's mirror-on-move used world X alone and pointed the
  // wrong way after a quarter turn (caught in review on the 32×32 pass).
  // Four quarter-turns must return the exact starting facings.
  const seen = [];
  for (let turn = 0; turn < 4; turn++) {
    await page.keyboard.press("q");
    await page.waitForTimeout(450);            // the camera eases into place
    seen.push((await units()).map(u => u.facing).join(","));
  }
  // The sharp form: a camera-relative renderer produces FOUR DISTINCT
  // facing sets across four quarter turns. A world-axis one produces four
  // identical sets and still satisfies both weaker claims below — which is
  // how the original bug survived review. Keep all three; only this one
  // has teeth, and the other two say what "correct" also has to look like.
  check("each quarter turn shows a distinct facing set",
    new Set(seen).size === 4, seen.join(" | "));
  check("four quarter turns restore the starting facings",
    seen[3] === start.map(u => u.facing).join(","), `${seen[3]} vs ${start.map(u => u.facing).join(",")}`);
  check("opposed sides never share a facing",
    seen.every(s => { const f = s.split(","); return f[0] !== f[3]; }), seen.join(" | "));

  // ---- aim is a stance the target mode owns -------------------------
  await page.keyboard.press("Tab");
  await page.waitForTimeout(200);
  await page.keyboard.press("f");
  check("target mode raises the emitter", await waitVerb("aim"));
  const aiming = (await units()).filter(u => u.action === "aim");
  check("exactly the selected operative aims", aiming.length === 1, `${aiming.length} aiming`);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(250);
  check("leaving target mode lowers it",
    !(await units()).some(u => u.action === "aim"),
    (await units()).map(u => u.action).join(","));

  // ---- the hostile turn drives the rest -----------------------------
  // Ending turns hands the board to the AI, which shoots, hits, downs and
  // eventually breaks. Every remaining verb is reached by the GAME rather
  // than by the harness pretending to be a player.
  // Overwatch is the keyboard-only way to actually SHOOT the crew: a squad
  // that never fires never breaks their morale, and kneel is a morale verb.
  //
  // Two things make this deterministic enough to assert on, and the first
  // CI run proved both were needed — it polled every 110ms for a fixed 16
  // rounds, and missed the yield entirely on a slower box.
  //
  //  * an in-page rAF observer records every action it EVER renders, so a
  //    verb that lives four frames cannot fall between two polls;
  //  * the loop waits on the game's own turn state rather than on sleeps,
  //    so the input sequence — and therefore the match the seeded rules
  //    play out — is the same on a fast machine and a slow one.
  await page.evaluate(() => {
    window.__seen = new Set();
    const cv = document.getElementById("cv");
    (function tick() {
      for (const s of (cv.dataset.units ?? "").split(",")) {
        const a = s.split(":")[1];
        if (a) window.__seen.add(a);
      }
      requestAnimationFrame(tick);
    })();
  });
  const opTurn = () => page.waitForFunction(
    () => /OPERATIVE TURN/.test(document.getElementById("turnlabel").textContent)
      || !!document.querySelector("#overlay.show"),
    null, { timeout: 20000 }).then(() => true, () => false);
  const ended = () => page.evaluate(() => !!document.querySelector("#overlay.show"));

  for (let round = 0; round < 30; round++) {
    if (await ended()) break;
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press("Tab");
      await page.keyboard.press("y");
    }
    if (await ended()) break;
    await page.keyboard.press("Enter");
    await opTurn();            // the hostile turn resolves before the next input
  }
  const played = await page.evaluate(() => [...window.__seen].sort());
  check("a shot plays the fire verb", played.includes("fire"), played.join(","));
  check("a hit plays the hurt verb", played.includes("hurt"), played.join(","));
  check("a downed body plays the death verb", played.includes("death"), played.join(","));
  check("a yielded body kneels", played.includes("kneel"), played.join(","));

  // ---- the filed aftermath carries a durable command pointer --------
  // This is a surface claim, not a replay test: witness_check owns the
  // Worker's authorship. Here the edge answers with one replay-derived
  // event and the yard must put its filed address on the post-match card.
  const filedId = "44444444444444444444444444444444";
  await page.route("https://sentinel-witness.ishawnd.workers.dev/file", route => {
    const asked = JSON.parse(route.request().postData() ?? "{}");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        filed: true,
        existing: false,
        id: filedId,
        filed_at: "2026-08-16T00:00:00.000Z",
        certified: true,
        rules: "stub-rules",
        ledger: { walked: 0, finished: 0, lost: 0 },
        seed: asked.seed,
        roster: asked.roster,
        rosterHash: "00000000",
        result: "loss",
        rating: 0,
        purse: 0,
        commands: asked.record.length,
        derivedEvents: [{
          kind: "extraction", actor: "SABLE", beneficiary: "KOA",
          commandIndex: 6, underFire: true, reached: true,
        }],
        lines: 0,
        fingerprint: asked.fingerprint,
        transcript: [],
      }),
    });
  });
  if (await ended()) {
    await page.click("#ovfile");
    await page.waitForFunction(id =>
      document.getElementById("ovderived").dataset.pointer === `${id}:6`, filedId);
    const filedMoment = await page.textContent("#ovderived");
    check("the filed extraction renders its match and command pointer",
      filedMoment.includes(filedId) && /COMMAND 6/.test(filedMoment), filedMoment);
  } else {
    check("the filed extraction renders its match and command pointer", false,
      "the driven match did not reach its post-match card");
  }
  await page.unroute("https://sentinel-witness.ishawnd.workers.dev/file");

  // ---- a roster this yard cannot STAGE faults at the door -----------
  // Two different questions, and only one is the rules core's:
  // `rosterValid` says who may FIGHT, this page says who it can DRAW.
  // `?roster=RUNE:10,…` passes the first and fails the second — it
  // validate, field, and then throw inside fighterSlug on the first
  // frame, AFTER the boot guard, so the yard died silently and a room
  // waiting on the hand-off sat there until its own timer gave up
  // (caught in review). A body with no sheets is a fault, named.
  await boot("&roster=RUNE:10,KOA:10,SABLE:10");
  check("a roster this yard cannot stage faults", (await ds("sprites")) === "error", await ds("sprites"));
  const rosterFault = await page.textContent("#asset-detail").catch(() => "");
  check("the roster fault names who it cannot draw, and who it can",
    /RUNE/.test(rosterFault) && /vesper/.test(rosterFault) && /nix/.test(rosterFault), rosterFault);
  check("no bodies are drawn behind the roster fault",
    !((await ds("units")) ?? "").includes(":idle:"), (await ds("units")) ?? "");
  // ...and a roster it CAN stage boots exactly as the default does
  await boot("&roster=VESPER:10,KOA:7,SABLE:10");
  check("a stageable roster boots", (await ds("sprites")) === "ready", await ds("sprites"));
  check("and the yard fields exactly it",
    (await ds("fielded")) === "VESPER:10|KOA:7|SABLE:10", await ds("fielded"));
  await boot("&roster=VESPER:10,NIX:10,SABLE:10");
  check("the authored substitute is stageable through its declared body loan",
    (await ds("sprites")) === "ready"
      && (await ds("fielded")) === "VESPER:10|NIX:10|SABLE:10",
    `${await ds("sprites")} · ${await ds("fielded")}`);
  await boot();

  // ---- a missing verb faults; it never falls back to the old grids ---
  // This is the whole point of the convergence: a quiet fallback would
  // put a 32×32 body back on the board while the room shows a pack body,
  // which is the two-species bug the change exists to kill. Since the
  // flip the default boot reads the RENDER sheets, so the missing verb
  // is a squad render96 strip; the composed path keeps its own fault
  // coverage under ?body=composed below.
  fs.rmSync(path.join(squadRender96("koa"), "aim_down.png"), { force: true });
  await boot();
  check("a missing render verb faults the yard", (await ds("sprites")) === "error", await ds("sprites"));
  const detail = await page.textContent("#asset-detail").catch(() => "");
  check("the fault names the sheet that failed", /koa/i.test(detail) && /aim/i.test(detail), detail);
  check("no bodies are drawn behind the fault",
    !((await ds("units")) ?? "").includes(":idle:"), (await ds("units")) ?? "");
  gen("slice96");   // restore the fixture strip for the legs below

  // ---- the composed path faults its own absences --------------------
  clearSheets();
  gen("full");
  fs.rmSync(path.join(sheetsDir("koa"), "AIM"), { recursive: true, force: true });
  await boot("&body=composed");
  check("a missing composed verb faults the composed yard",
    (await ds("sprites")) === "error", await ds("sprites"));
  const composedDetail = await page.textContent("#asset-detail").catch(() => "");
  check("the composed fault names the sheet that failed",
    /koa/i.test(composedDetail) && /aim/i.test(composedDetail), composedDetail);

  // ---- a wrong-geometry sheet is a fault, not an absence ------------
  // badgeom writes composed sheets, which only the composed body reads
  // since the flip.
  clearSheets();
  gen("badgeom");
  await boot("&body=composed");
  check("wrong sheet geometry faults", (await ds("sprites")) === "error", await ds("sprites"));
  check("the geometry fault says so",
    /expected a row/.test(await page.textContent("#asset-detail").catch(() => "")));

  // ---- the body query is staged, visible, and strict ----------------
  clearSheets();
  gen("full");
  await boot("&body=composed");
  const composedFrames = await idleFrames();
  check("the composed query stages the composed body",
    (await ds("body")) === "composed", await ds("body"));
  check("composed Cipher idle loads eight frames",
    composedFrames.cipher === 8, JSON.stringify(composedFrames));
  check("composed Koa idle loads eight frames",
    composedFrames.koa === 8, JSON.stringify(composedFrames));

  await boot("&body=rneder96");
  check("an unknown body source faults the yard",
    (await ds("sprites")) === "error", await ds("sprites"));
  const bodyFault = await page.textContent("#asset-detail").catch(() => "");
  check("the body fault names the unknown source and the yard's choices",
    /rneder96/.test(bodyFault) && /unknown body source/i.test(bodyFault)
      && /composed/.test(bodyFault) && /render96/.test(bodyFault),
    bodyFault);
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server) server.kill();
  clearSheets();
  for (const renderDir of TRACKED_RENDER_DIRS) {
    fs.rmSync(renderDir, { recursive: true, force: true });
  }
  for (const f of FIGHTERS) {
    if (fs.existsSync(backupDir(f))) fs.renameSync(backupDir(f), sheetsDir(f));
  }
  for (const renderDir of TRACKED_RENDER_DIRS) {
    const renderBak = trackedBackup(renderDir);
    if (fs.existsSync(renderBak)) fs.renameSync(renderBak, renderDir);
  }
  fs.rmSync(LOCK, { recursive: true, force: true });
}

console.log(failures ? `\n${failures} FAILURES` : "\nALL PASS");
process.exit(failures ? 1 : 0);
