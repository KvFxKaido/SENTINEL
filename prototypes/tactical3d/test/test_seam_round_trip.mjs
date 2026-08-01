// Walks the seam end to end, in one browser, with converged bodies.
//
// This is the claim the yard convergence exists to make: one body crosses
// the north door instead of changing species there. Nothing else in the
// suite can see it, because it is the only test where both surfaces are
// alive at once — the room, the yard inside its iframe, and the contract
// between them.
//
// It walks the room's north door, boots the yard in the seam frame, plays
// the card to a finish, takes WALK BACK OUT, and reads the verdict the
// room settles on. Synthetic sheets throughout: the record the witness
// replays is rules data and has nothing to do with the art, so this runs
// without the licensed pack.
//
// On the witness: CERTIFIED and UNCERTIFIED are both honest outcomes (the
// Worker may be unreachable from CI, and the room says so out loud). The
// verdict that must NEVER appear is STRUCK — the edge replaying the record
// and disagreeing means the match we just played does not reproduce.
//
// Run:  cd prototypes/tactical3d/test && node test_seam_round_trip.mjs
import { chromium } from "playwright";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const GEN = path.join(ROOT, "prototypes", "walkable", "test", "make_synthetic_sheets.py");
const FIGHTERS = ["cipher", "vesper", "koa", "sable", "syn"];
const PY = process.platform === "win32" ? "python" : "python3";
const PORT = process.env.SEAM_TEST_PORT ?? "8095";
// ?deal=6 pins the card the door deals, so a failure is reproducible
const URL = `http://localhost:${PORT}/prototypes/walkable/?deal=6`;

const sheetsDir = f => path.join(ROOT, "assets", "sprites", f);
const backupDir = f => sheetsDir(f) + ".harness-backup";
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

for (const f of FIGHTERS) {
  if (fs.existsSync(backupDir(f))) {
    fs.rmSync(sheetsDir(f), { recursive: true, force: true });
    fs.renameSync(backupDir(f), sheetsDir(f));
  }
  if (fs.existsSync(sheetsDir(f))) fs.renameSync(sheetsDir(f), backupDir(f));
}

let server = null;
let browser = null;

try {
  const g = spawnSync(PY, [GEN, "full", FIGHTERS.join(",")], { stdio: "inherit" });
  if (g.status !== 0) throw new Error("sheet generation failed");

  server = spawn(PY, ["-m", "http.server", PORT], { cwd: ROOT, stdio: "ignore" });
  let up = false;
  for (let i = 0; i < 50 && !up; i++) {
    up = await fetch(`http://localhost:${PORT}/`).then(r => r.ok, () => false);
    if (!up) await new Promise(r => setTimeout(r, 200));
  }
  if (!up) throw new Error(`server never came up on :${PORT}`);

  browser = await launch();
  const page = await browser.newPage();
  page.on("pageerror", e => { console.log("PAGEERROR " + e); failures++; });

  await page.goto(URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  check("the room boots", (await page.evaluate(() =>
    document.getElementById("cv").dataset.sprites)) === "ready");

  // W is camera-FORWARD, which is diagonal in this 2:1 view — held alone it
  // slides the body off the door span and pins it on the west wall. W+D is
  // true north, and the door only deals a card to a body inside its span.
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const opened = await page.waitForFunction(() => !!document.getElementById("seamframe"),
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  check("walking the north door opens the seam", opened);
  if (!opened) throw new Error("the door never dealt");

  const frame = await (await page.$("#seamframe")).contentFrame();
  await frame.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  // The room holds the cut until the yard proves it booted, and the yard now
  // has 140 sheets to load before it can say so. If that ever outgrows
  // SEAM_BOOT_MS the room aborts the hand-off and this check is what says so.
  check("the yard boots inside the seam",
    (await frame.evaluate(() => document.getElementById("cv").dataset.sprites)) === "ready");
  check("the yard fields the full molded roster",
    (await frame.evaluate(() => document.getElementById("cv").dataset.roster)) === "full");

  await frame.press("body", "Enter");   // begin the card
  await frame.waitForFunction(() =>
    (document.getElementById("cv").dataset.units ?? "").split(",").length === 6,
    null, { timeout: 15000 });
  const opening = await frame.evaluate(() => document.getElementById("cv").dataset.units);
  check("both sides render pack bodies across the door", (opening ?? "").split(",").length === 6, opening);
  check("the yard opens on the same verb vocabulary as the room",
    (opening ?? "").split(",").every(s => s.split(":")[1] === "idle"), opening);

  // Play to a finish the CHEAPEST way: end turns and let the squad lose.
  // This suite's claims are about the door and the record, not about
  // winning, and a loss certifies exactly as well as a win. Fighting back
  // with overwatch prolonged the match and made this the slowest job in
  // CI at 4m42s.
  //
  // It also waits on the game's own turn state instead of sleeping a worst
  // case — the same flaw that fed the seeded rules a different match on a
  // slower box and turned the yard suite's kneel check red in CI and green
  // locally. Fixed in one file first; the lesson is cheaper applied to all
  // three at once.
  const ended = () => frame.evaluate(() => !!document.querySelector("#overlay.show"));
  const opTurn = () => frame.waitForFunction(
    () => /OPERATIVE TURN/.test(document.getElementById("turnlabel").textContent)
      || !!document.querySelector("#overlay.show"),
    null, { timeout: 20000 }).then(() => true, () => false);
  let over = false;
  for (let round = 0; round < 40; round++) {
    over = await ended();
    if (over) break;   // through the door Enter IS the walk home once it ends
    await frame.press("body", "Enter");
    await opTurn();
  }
  check("the card plays to a finish", over);
  if (!over) throw new Error("the match never ended");

  const ending = await frame.evaluate(() => document.getElementById("cv").dataset.units);
  check("downed bodies hold the last death frame",
    (ending ?? "").split(",").some(s => s.split(":")[1] === "death"), ending);

  await frame.click("#ovwalk");
  const closed = await page.waitForFunction(() => !document.getElementById("seamframe"),
    null, { timeout: 15000 }).then(() => true, () => false);
  check("walking back out tears the frame down", closed);

  // Poll for a TERMINAL verdict rather than sleeping a fixed span. A slow
  // edge left the panel at "ASKING THE EDGE…" and failed the settlement
  // assertion, which made this suite flaky in exactly the way it claims to
  // tolerate (caught in review). The wait is bounded and says so when it
  // expires, instead of asserting against a half-written panel.
  const settled = await page.waitForFunction(
    () => /CERTIFIED|UNCERTIFIED|STRUCK/.test(document.getElementById("seaminfo").textContent),
    null, { timeout: 25000 }).then(() => true, () => false);
  const verdict = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
  check("the room takes the record back", /RATING|PURSE|SQUAD/.test(verdict), verdict);
  check("the room settles the session", settled, verdict);
  // The one verdict that is a bug rather than a circumstance: the edge
  // replayed what we played and got something else.
  check("the edge does not dispute the record", !/STRUCK/.test(verdict), verdict);
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server) server.kill();
  clearSheets();
  for (const f of FIGHTERS) {
    if (fs.existsSync(backupDir(f))) fs.renameSync(backupDir(f), sheetsDir(f));
  }
}

console.log(failures ? `\n${failures} FAILURES` : "\nALL PASS");
process.exit(failures ? 1 : 0);
