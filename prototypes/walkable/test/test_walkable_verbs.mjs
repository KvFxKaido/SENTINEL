// Executes the walkable page's verb claims in headless chromium.
//
// Serves the repo root, boots the page against synthetic sheets, and
// drives the keyboard through every verb plus the three roster states.
// Verb durations are measured IN PAGE via rAF: evaluate round-trips can
// be slower than a 4-frame flinch, so sleep-then-read checks lie —
// that lesson is why the watcher exists (caught building this harness).
//
// Real molded sheets at assets/sprites/cipher are backed up before the
// run and restored after — the harness never destroys a real artifact.
//
// Run:  cd prototypes/walkable/test && npm install && node test_walkable_verbs.mjs
import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const GEN = path.join(HERE, "make_synthetic_sheets.py");
const SHEETS = path.join(ROOT, "assets", "sprites", "cipher");
const BACKUP = SHEETS + ".harness-backup";
const PY = process.platform === "win32" ? "python" : "python3";
const PORT = process.env.WALKABLE_TEST_PORT ?? "8093";
const URL = `http://localhost:${PORT}/prototypes/walkable/`;

function gen(mode) {
  const r = spawnSync(PY, [GEN, mode], { stdio: "inherit" });
  if (r.status !== 0) throw new Error(`sheet generation failed (${mode})`);
}
const clearSheets = () => fs.rmSync(SHEETS, { recursive: true, force: true });

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

// ---- setup: preserve real sheets, start server, boot browser -------
fs.rmSync(BACKUP, { recursive: true, force: true });
if (fs.existsSync(SHEETS)) fs.renameSync(SHEETS, BACKUP);

const server = spawn(PY, ["-m", "http.server", PORT], { cwd: ROOT, stdio: "ignore" });
let up = false;
for (let i = 0; i < 50 && !up; i++) {
  up = await fetch(`http://localhost:${PORT}/`).then(r => r.ok, () => false);
  if (!up) await new Promise(r => setTimeout(r, 200));
}
if (!up) { server.kill(); throw new Error(`server never came up on :${PORT}`); }

const browser = await launch();
const page = await browser.newPage();
page.on("pageerror", e => { console.log("PAGEERROR " + e); failures++; });

async function boot() {
  await page.goto(URL);
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

try {
  // ---- FULL roster -------------------------------------------------
  gen("full");
  await boot();
  check("full roster boots", (await ds("sprites")) === "ready");
  check("roster reads full", (await ds("roster")) === "full");
  check("BODY cell says CANON / FULL",
    (await page.textContent("#body-state")) === "CANON / FULL");

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

  // death: plays through, holds the floor, only movement rises
  await page.keyboard.press("KeyX");
  check("X goes down", await waitAction("death"));
  await page.waitForTimeout(1200);
  check("death holds the floor", (await ds("action")) === "death");
  check("held frame is the last", (await ds("frame")) === "5");
  await page.keyboard.press("KeyJ");
  await page.waitForTimeout(300);
  check("attacks don't reach the floor", (await ds("action")) === "death");
  await page.keyboard.down("KeyS");
  check("movement rises", await waitAction("run"));
  await page.keyboard.up("KeyS");

  // ---- CORE roster -------------------------------------------------
  clearSheets();
  gen("core");
  await boot();
  check("core roster boots", (await ds("sprites")) === "ready");
  check("roster reads core", (await ds("roster")) === "core");
  check("BODY cell says CANON / CORE",
    (await page.textContent("#body-state")) === "CANON / CORE");
  check("control surface labeled core-only",
    await page.evaluate(() => document.getElementById("control-surface").classList.contains("core-only")));
  const inertMs = await measureVerb("KeyL", "dash");
  check("dash inert on core roster", inertMs === -1, `watcher says ${inertMs}`);
  const atkMs = await measureVerb("KeyJ", "attack1");
  check("attacks still fire on core roster", atkMs > 450 && atkMs < 1500, `${Math.round(atkMs)}ms`);

  // ---- PARTIAL roster is a fault -----------------------------------
  clearSheets();
  gen("full");
  fs.rmSync(path.join(SHEETS, "HEAL"), { recursive: true, force: true });
  fs.rmSync(path.join(SHEETS, "DASH"), { recursive: true, force: true });
  await boot();
  check("partial roster faults", (await ds("sprites")) === "error");
  check("fault names the partial state",
    (await page.textContent("#asset-detail")).includes("partial full-pack roster"));

  // ---- rejection is not absence: bad geometry faults, never CORE ----
  clearSheets();
  gen("badfull");
  await boot();
  check("all-rejected extended sheets fault, not core roster",
    (await ds("sprites")) === "error");
  check("geometry fault names the sheet",
    (await page.textContent("#asset-detail")).includes("expected a row"));

  // ---- a held key's auto-repeat cannot revive a downed body ---------
  clearSheets();
  gen("full");
  await boot();
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
} finally {
  await browser.close();
  server.kill();
  clearSheets();
  if (fs.existsSync(BACKUP)) fs.renameSync(BACKUP, SHEETS);
}

console.log(failures ? `\n${failures} FAILURES` : "\nALL PASS");
process.exit(failures ? 1 : 0);
