// Executes the three-body walk-off's shared input grammar in headless
// chromium: pack (A, left), hybrid (C, centre), whole-generated render
// (B, right). The real audition assets are backed up and restored; the
// page boots against flat synthetic sheets at each body's real geometry.
//
// State changes are observed in-page through the canvas harness fields.
// A delayed read can skip a whole attack or sample a seeded cycle at a
// friendly phase, so none of the verb claims below use sleeps.
//
// Run:  cd prototypes/walkable/test
//       node audition_generated.mjs
import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const GEN = path.join(HERE, "make_synthetic_sheets.py");
async function probePort(port) {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once("error", err => {
      if (err.code === "EADDRINUSE") resolve(null);
      else reject(err);
    });
    probe.listen(port, "127.0.0.1", () => {
      const assigned = String(probe.address().port);
      probe.close(() => resolve(assigned));
    });
  });
}

const requestedPort = process.env.AUDITION_PORT;
let PORT = await probePort(Number(requestedPort ?? "8094"));
if (PORT === null && requestedPort) {
  throw new Error(`AUDITION_PORT ${requestedPort} is already in use`);
}
if (PORT === null) PORT = await probePort(0);
const URL = `http://127.0.0.1:${PORT}/prototypes/walkable/walkoff.html`;
const OUT = process.env.AUDITION_OUT ?? path.join(HERE, "audition-shots");
const PY = process.platform === "win32" ? "python" : "python3";
const ASSET_DIRS = [
  path.join(ROOT, "assets", "sprites", "cipher"),
  path.join(ROOT, "assets", "sprites", "hybrid", "cipher", "sheets"),
  path.join(ROOT, "assets", "original", "cipher_render", "sheets"),
];
const backupDir = dir => dir + ".walkoff-harness-backup";

let failures = 0;
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
  if (!ok) failures++;
}

function generateSheets() {
  const r = spawnSync(PY, [GEN, "walkoff"], { stdio: "inherit" });
  if (r.status !== 0) throw new Error("walkoff sheet generation failed");
}

function clearSheets() {
  for (const dir of ASSET_DIRS) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function preserveSheets() {
  // A backup left by a hard-killed run is the real artifact. Reinstate it
  // before staging another fixture, or the next cleanup would preserve
  // synthetic sheets and discard the thing this harness promised to save.
  for (const dir of ASSET_DIRS) {
    const backup = backupDir(dir);
    if (fs.existsSync(backup)) {
      fs.rmSync(dir, { recursive: true, force: true });
      fs.renameSync(backup, dir);
    }
    if (fs.existsSync(dir)) {
      fs.renameSync(dir, backup);
    }
  }
}

function restoreSheets() {
  clearSheets();
  for (const dir of ASSET_DIRS) {
    const backup = backupDir(dir);
    if (fs.existsSync(backup)) fs.renameSync(backup, dir);
  }
}

// A Playwright package can be newer than the browser provisioned in CI.
// Match the room harness's fallback instead of turning that into a game
// failure before the page has run a line of its own code.
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

let server = null;
let browser = null;
let page = null;

// One harness at a time — shared with test_walkable_verbs.mjs on
// purpose, since both drive the same generator and backup discipline.
// Two overlapping runs would each claim the same backups: the second
// reinstates the first's LIVE backup as stranded, and after the first
// restores, the second's cleanup deletes the originals with nothing
// left to restore from (caught in review, P1). Atomic mkdir; a
// hard-killed run strands the lock and the next run refuses by name
// instead of guessing the coast is clear.
const LOCK = path.join(HERE, ".harness-lock");
try {
  fs.mkdirSync(LOCK);
} catch {
  console.error(`another harness run appears live (${LOCK} exists) — `
    + "refusing to touch the backups; remove the dir if that run is dead");
  process.exit(1);
}

try {
  preserveSheets();
  generateSheets();
  check("synthetic hybrid declares no kneel sheet",
    !fs.existsSync(path.join(ASSET_DIRS[1], "kneel_down.png")));

  server = spawn(PY, ["-m", "http.server", PORT, "--bind", "127.0.0.1"],
    { cwd: ROOT, stdio: "ignore" });
  let up = false;
  for (let i = 0; i < 50 && !up; i++) {
    up = await fetch(`http://127.0.0.1:${PORT}/`).then(r => r.ok, () => false);
    if (!up) await new Promise(r => setTimeout(r, 200));
  }
  if (server.exitCode !== null) throw new Error(`http.server exited before binding :${PORT}`);
  if (!up) throw new Error(`server never came up on :${PORT}`);

  browser = await launch();
  page = await browser.newPage({ viewport: { width: 1100, height: 620 } });
  page.on("pageerror", e => {
    console.log("PAGEERROR " + e);
    failures++;
  });
  await page.goto(URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
  null, { timeout: 15000 });

  const ds = k => page.evaluate(k => document.getElementById("cv").dataset[k], k);
  const text = selector => page.textContent(selector);
  const waitAction = (name, timeout = 4000) =>
    page.waitForFunction(n => document.getElementById("cv").dataset.action === n,
      name, { timeout }).then(() => true, () => false);

  check("walk-off boots all three bodies", (await ds("sprites")) === "ready",
    await text("#body-state"));
  check("BODY readout names hybrid and render",
    (await text("#body-state")).includes("HYBRID")
      && (await text("#body-state")).includes("RENDER"),
    await text("#body-state"));
  fs.mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: path.join(OUT, "01-idle-down.png") });

  // Watch two changes and the return to the starting frame. That proves
  // both the 2-frame width and the one-second breathing cycle; merely
  // sampling one instant can make an eight-frame phantom strip look fine.
  await page.evaluate(() => {
    const cv = document.getElementById("cv");
    window.__kneelCycles = new Promise(res => {
      const packSeen = new Set();
      const renSeen = new Set();
      const packCounts = new Set();
      const renCounts = new Set();
      const packTimes = [];
      const renTimes = [];
      let lastPack = null;
      let lastRen = null;
      let begin = null;

      function result(timedOut = false) {
        return {
          timedOut,
          packSeen: [...packSeen], renSeen: [...renSeen],
          packCounts: [...packCounts], renCounts: [...renCounts],
          // The first sample can land midway through a frame. Measure
          // between equivalent boundaries after that seeded fragment.
          packCycle: packTimes.length >= 4 ? packTimes[3] - packTimes[1] : -1,
          renCycle: renTimes.length >= 4 ? renTimes[3] - renTimes[1] : -1,
        };
      }

      function tick(t) {
        if (begin === null) begin = t;
        if (cv.dataset.action === "kneel") {
          const pack = cv.dataset.frame;
          const ren = cv.dataset.frameRen;
          packSeen.add(pack); renSeen.add(ren);
          packCounts.add(cv.dataset.frameCount);
          renCounts.add(cv.dataset.frameCountRen);
          if (pack !== lastPack) { lastPack = pack; packTimes.push(t); }
          if (ren !== lastRen) { lastRen = ren; renTimes.push(t); }
          if (packTimes.length >= 4 && renTimes.length >= 4) return res(result());
        }
        if (t - begin > 5000) return res(result(true));
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  });
  await page.keyboard.down("KeyC");
  check("hold C takes BODY A into kneel", await waitAction("kneel"));
  const kneel = await page.evaluate(() => window.__kneelCycles);
  const packFrames = kneel.packSeen.sort().join(",");
  const renFrames = kneel.renSeen.sort().join(",");
  check("BODY A kneel is 2 frames at 2fps",
    !kneel.timedOut && packFrames === "0,1"
      && kneel.packCounts.join(",") === "2"
      && kneel.packCycle > 650 && kneel.packCycle < 1600,
    `frames ${packFrames}; cycle ${Math.round(kneel.packCycle)}ms`);
  check("BODY B kneel is 2 frames at 2fps",
    !kneel.timedOut && (await ds("renKneel")) === "1"
      && renFrames === "0,1" && kneel.renCounts.join(",") === "2"
      && kneel.renCycle > 650 && kneel.renCycle < 1600,
    `frames ${renFrames}; cycle ${Math.round(kneel.renCycle)}ms`);
  check("kneel telemetry uses the room dialect",
    (await text("#action-state")) === "KNEEL / STANCE");
  check("BODY C stands with honest missing-kneel telemetry",
    (await ds("genKneel")) === "0"
      && (await ds("frameCountGen")) === "8"
      && (await text("#gen-state")) === "NO KNEEL SHEET",
    await text("#gen-state"));
  await page.screenshot({ path: path.join(OUT, "02-kneel-down.png") });

  // KNEEL is a standing pose in the sibling room: motion owns the body,
  // then the still-held stance returns when movement stops.
  await page.keyboard.down("KeyW");
  check("movement cancels a held kneel", await waitAction("run"));
  check("generated bodies translate run through declared walk sheets",
    (await ds("genWalk")) === "1" && (await ds("renWalk")) === "1");
  await page.keyboard.up("KeyW");
  check("stopping resumes the held kneel", await waitAction("kneel"));

  // Record the ownership transition, not just both endpoints. The attack
  // must keep its eight-frame duration and fall straight back to the held
  // stance without an idle seam between them.
  await page.evaluate(() => {
    const cv = document.getElementById("cv");
    window.__attackTrace = new Promise(res => {
      const frames = new Set();
      const frameCounts = new Set();
      let beganAt = null;
      let begin = null;
      function tick(t) {
        if (begin === null) begin = t;
        if (cv.dataset.action === "attack1") {
          if (beganAt === null) beganAt = t;
          frames.add(cv.dataset.frame);
          frameCounts.add(cv.dataset.frameCount);
        } else if (beganAt !== null) {
          return res({
            timedOut: false, duration: t - beganAt,
            nextAction: cv.dataset.action,
            frames: [...frames], frameCounts: [...frameCounts],
          });
        }
        if (t - begin > 5000) return res({ timedOut: true, frames: [...frames] });
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  });
  await page.keyboard.press("KeyJ");
  check("attack outranks a held kneel", await waitAction("attack1"));
  const attacked = await page.evaluate(() => window.__attackTrace);
  check("the 8-frame attack still plays as eight",
    !attacked.timedOut && attacked.frameCounts?.join(",") === "8"
      && attacked.duration > 350 && attacked.duration < 1400,
    `${Math.round(attacked.duration ?? -1)}ms; frames seen ${(attacked.frames ?? []).join(",")}`);
  check("attack completion resumes kneel without an idle seam",
    attacked.nextAction === "kneel" && await waitAction("kneel"),
    attacked.nextAction ?? "no completion");

  await page.keyboard.up("KeyC");
  check("releasing C returns BODY A to stand", await waitAction("idle"));
  check("releasing C returns BODY B and C to stand",
    (await ds("renKneel")) === "0" && (await ds("genKneel")) === "0"
      && (await text("#ren-state")) === "IDLE"
      && (await text("#gen-state")) === "IDLE");

  console.log(`shots -> ${OUT}`);
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server) server.kill();
  restoreSheets();
  fs.rmSync(LOCK, { recursive: true, force: true });
}

console.log(failures ? `\n${failures} FAILURES` : "\nALL PASS");
process.exit(failures ? 1 : 0);
