// Executes the venue lens's two-sided claim in headless chromium.
//
// The claim (world/venues.json; the yard's venue-lens block): a dealt
// `?venue=` changes what a card LOOKS like and cannot change what a card
// IS. Both halves are executed, not argued:
//
//   VISIBLE — the same seed staged at two venues renders materially
//   different pixels (sampled off the stage as a downsampled color grid,
//   against a same-venue control for animation noise), because a lens
//   nobody can see is set dressing that failed (the invisible kit table
//   lesson: telemetry is not proof a player can SEE it).
//
//   INERT — the same seed played with the same commands at two venues
//   produces byte-identical certified text in the comms log. The rules'
//   rng and the air's rng never share a stream, and this is the test
//   that goes red if they ever do.
//
// Also under test: the unrecorded-venue path (house look, loaned OUT
// LOUD, card refusing to invent witnesses), and the atlas's boot-fault
// discipline (authored data that fails to validate names itself).
//
// Run:  cd prototypes/tactical3d/test
//       npm install && npx playwright install chromium
//       node test_yard_venue.mjs
import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const GEN = path.join(ROOT, "prototypes", "walkable", "test", "make_synthetic_sheets.py");
const FIGHTERS = ["cipher", "vesper", "koa", "sable", "syn"];
const SQUAD_FIGHTERS = ["vesper", "koa", "sable", "syn"];
const PY = process.platform === "win32" ? "python" : "python3";
const PORT = process.env.YARD_VENUE_TEST_PORT ?? "8095";
const URL = `http://localhost:${PORT}/prototypes/tactical3d/?seed=deadbeef`;

const sheetsDir = f => path.join(ROOT, "assets", "sprites", "composed", f);
const backupDir = f => sheetsDir(f) + ".harness-backup";
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

// ---- setup: preserve real sheets (yard_bodies' backup law, shared lock)
const LOCK = path.join(ROOT, "prototypes", "walkable", "test", ".harness-lock");
try {
  fs.mkdirSync(LOCK);
} catch {
  console.error(`another harness run appears live (${LOCK} exists) — `
    + "refusing to touch the backups; remove the dir if that run is dead");
  process.exit(1);
}
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
      console.error(`STRANDED sheets96 backup found at ${renderBak} — reinstating.`);
      fs.rmSync(renderDir, { recursive: true, force: true });
      fs.renameSync(renderBak, renderDir);
    }
    if (fs.existsSync(renderDir)) fs.renameSync(renderDir, renderBak);
  }
} catch (error) {
  // no rollback in the crash path — the next start's reinstate pass is
  // the recovery (the walkable harness's review-bought design)
  fs.rmSync(LOCK, { recursive: true, force: true });
  throw error;
}

let server = null;
let browser = null;
let page = null;

const ds = k => page.evaluate(k => document.getElementById("cv").dataset[k], k);

async function boot(query = "") {
  await page.goto(URL + query);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 15000 });
}
const beginCard = async () => {
  await page.keyboard.press("Enter");
  // settle on rendered frames, not wall clock: the card teardown and the
  // first stage frames are done when the page has painted a dozen more
  await page.evaluate(() => new Promise(res => {
    let n = 0;
    const step = () => (++n >= 12 ? res() : requestAnimationFrame(step));
    requestAnimationFrame(step);
  }));
};

// The stage, sampled: screenshot the canvas, decode it in-page (the
// browser is the PNG decoder), downsample to a coarse color grid. Coarse
// on purpose — the claim is "materially different look", not any exact
// pixel, and 24×16 mean cells are robust to sprite-frame phase.
async function stageGrid() {
  const box = await page.locator("#cv").boundingBox();
  const clip = {
    x: box.x + box.width * 0.10, y: box.y + box.height * 0.12,
    width: box.width * 0.80, height: box.height * 0.60,
  };
  const b64 = (await page.screenshot({ clip })).toString("base64");
  return page.evaluate(async b64 => {
    const img = new Image();
    await new Promise((res, rej) => {
      img.onload = res; img.onerror = rej;
      img.src = "data:image/png;base64," + b64;
    });
    const GW = 24, GH = 16;
    const c = document.createElement("canvas");
    c.width = GW; c.height = GH;
    const g = c.getContext("2d");
    g.drawImage(img, 0, 0, GW, GH);
    return Array.from(g.getImageData(0, 0, GW, GH).data);
  }, b64);
}
const gridDiff = (a, b) =>
  a.reduce((sum, v, i) => sum + Math.abs(v - b[i]), 0) / a.length;

// The certified text after N ended turns, with the ONE renderer-owned
// line stripped: the staging line is the log's word, not the record's,
// and it is SUPPOSED to differ across venues.
async function playRounds(rounds) {
  const ended = () => page.evaluate(() => !!document.querySelector("#overlay.show"));
  const opTurn = () => page.waitForFunction(
    () => /OPERATIVE TURN/.test(document.getElementById("turnlabel").textContent)
      || !!document.querySelector("#overlay.show"),
    null, { timeout: 20000 });
  for (let i = 0; i < rounds; i++) {
    if (await ended()) break;
    await page.keyboard.press("Enter");
    await opTurn();
  }
  const raw = await page.evaluate(() => document.getElementById("log").innerText);
  return raw.split("\n").filter(line => !/^— STAGED AT /.test(line)).join("\n");
}

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

  gen("full");
  gen("slice96");

  // ---- the house is a venue like any other --------------------------
  await boot();
  check("the bare yard is the house venue",
    (await ds("venue")) === "KESTREL YARD:house", await ds("venue"));
  const houseTitle = await page.textContent("#card h1");
  check("the house card carries the atlas's Kestrel lines",
    /KESTREL YARD — LATTICE RELAY STATION/.test(houseTitle), houseTitle);
  await beginCard();
  const houseGrid = await stageGrid();
  const houseLog = await playRounds(3);

  // same venue, fresh boot: the animation-phase noise floor that the
  // visible-difference claim has to clear
  await boot();
  await beginCard();
  const controlDiff = gridDiff(houseGrid, await stageGrid());

  // ---- a dealt venue is staged, said, and VISIBLE --------------------
  await boot("&venue=THE%20COLD%20COURT");
  check("a dealt venue is staged",
    (await ds("venue")) === "THE COLD COURT:staged", await ds("venue"));
  const stagedTitle = await page.textContent("#card h1");
  check("the card reads the dealt venue's lines",
    /THE COLD COURT — COVENANT SANCTUARY GROUND/.test(stagedTitle), stagedTitle);
  await beginCard();
  const stagedLog0 = await page.evaluate(() => document.getElementById("log").innerText);
  check("the log declares the staging in its own voice",
    /— STAGED AT THE COLD COURT/.test(stagedLog0), stagedLog0.slice(0, 120));
  const stagedGrid = await stageGrid();
  const venueDiff = gridDiff(houseGrid, stagedGrid);
  // The ratio to the same-venue control is the discriminating half (the
  // measured signal is ~30x the animation noise); the absolute floor
  // only guards the degenerate case where both stages render black and
  // everything trivially "matches". Calibrated against measurement, not
  // aspiration: house-vs-house noise ~0.07, house-vs-cold-court ~2.
  check("two venues render materially different stages",
    venueDiff > Math.max(controlDiff * 2.5, 0.8),
    `venue ${venueDiff.toFixed(2)} vs control ${controlDiff.toFixed(2)}`);

  // ---- ...and INERT: the certified text cannot see the weather -------
  const stagedLog = await playRounds(3);
  check("the same seed writes the same record at either venue",
    stagedLog === houseLog && stagedLog.length > 0,
    stagedLog === houseLog ? `${stagedLog.length} chars` : "logs diverged");

  // ---- an unrecorded venue borrows the look and says so --------------
  await boot("&venue=THE%20OLD%20PIT");
  check("an unrecorded venue does not refuse the card",
    (await ds("sprites")) === "ready" && (await ds("venue")) === "THE OLD PIT:unrecorded",
    await ds("venue"));
  const unrecTag = await page.textContent("#card .tag");
  check("the unrecorded card claims no sanction it cannot know",
    /UNRECORDED GROUND/.test(unrecTag), unrecTag);
  const unrecCard = await page.textContent("#card");
  check("the unrecorded card invents no witnesses",
    /NOBODY ON RECORD/.test(unrecCard) && !/ODDSMAKER/.test(unrecCard),
    unrecCard.replace(/\s+/g, " ").slice(0, 160));
  await beginCard();
  const unrecLog = await page.evaluate(() => document.getElementById("log").innerText);
  check("the loan is declared on the feed",
    /IS NOT IN THE ATLAS — THE HOUSE LOOK STANDS IN/.test(unrecLog),
    unrecLog.slice(0, 160));
  const unrecDiff = gridDiff(houseGrid, await stageGrid());
  check("the unrecorded stage really wears the house look",
    unrecDiff < Math.max(venueDiff / 3, controlDiff * 2),
    `unrecorded ${unrecDiff.toFixed(2)} vs venue ${venueDiff.toFixed(2)}`);

  // ---- a venue is a NAME, not markup --------------------------------
  // The unrecorded path prints the dealt name verbatim — onto the card
  // and the log, both innerHTML sinks — so a hostile name in a shared
  // URL was a script injection until it was escaped (both review bots,
  // this PR). Executed with real metacharacters: the name must render
  // as text, build no elements, and run nothing (a pageerror here would
  // also fail the run via the handler above).
  const hostile = `<img src=x onerror="document.title='owned'">`;
  await boot("&venue=" + encodeURIComponent(hostile));
  check("a hostile venue name still boots as unrecorded",
    (await ds("sprites")) === "ready" && (await ds("venue")) === `${hostile}:unrecorded`,
    await ds("venue"));
  check("the card renders the name as text, not as elements",
    (await page.$("#card img")) === null
      && (await page.textContent("#card h1")).includes(hostile));
  await beginCard();
  const hostileLog = await page.evaluate(() => document.getElementById("log").innerText);
  check("the log prints the name, the page does not execute it",
    hostileLog.includes(hostile) && (await page.title()) !== "owned",
    hostileLog.slice(0, 120));

  // ---- a name off Object.prototype is a stranger, not an entry ------
  // atlas.venues rides in on JSON.parse with its prototype attached, so
  // a plain `in` check read ?venue=constructor as a KNOWN venue, handed
  // applyVenueLook an inherited function, and boot-faulted — a lens
  // deciding whether the match exists, the exact forbidden outcome
  // (both bots; run-core drew this boundary first, against __proto__).
  for (const name of ["constructor", "toString", "__proto__"]) {
    await boot("&venue=" + name);
    check(`"${name}" falls back to unrecorded instead of faulting`,
      (await ds("sprites")) === "ready" && (await ds("venue")) === `${name}:unrecorded`,
      `${await ds("sprites")} / ${await ds("venue")}`);
  }

  // ---- the atlas keeps the people-file discipline --------------------
  // authored data that fails to load or validate is a boot FAULT that
  // names itself — served doctored over page.route, like the person file
  await page.route(/world\/venues\.json$/, route =>
    route.fulfill({ status: 500, body: "down" }));
  await boot();
  check("a missing atlas faults the boot",
    (await ds("sprites")) === "error", await ds("sprites"));
  const missFault = await page.textContent("#asset-detail").catch(() => "");
  check("the missing-atlas fault names the file",
    /venues\.json/.test(missFault), missFault);
  await page.unroute(/world\/venues\.json$/);

  await page.route(/world\/venues\.json$/, route => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({
      venues: {
        "KESTREL YARD": {
          title: "K", framing: "f", sanction: "s", present: [["a", "b"]],
          light: { ambient: "#8fb8a0", hemiSky: "#9fd8c0", hemiGround: "#0a1410", sun: "#dff0e2" },
          air: { count: -1, color: "#ffffff", size: 2, fall: 0.1, drift: 0.1, sway: 0.1, opacity: 0.5 },
        },
      },
    }),
  }));
  await boot();
  check("a malformed look faults the boot",
    (await ds("sprites")) === "error", await ds("sprites"));
  const lookFault = await page.textContent("#asset-detail").catch(() => "");
  check("the malformed-look fault names the venue and the reason",
    /KESTREL YARD/.test(lookFault) && /air\.count/.test(lookFault), lookFault);
  await page.unroute(/world\/venues\.json$/);
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
