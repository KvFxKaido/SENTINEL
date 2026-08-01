// The room's deadline on the WITNESS, not on the yard.
//
// certifySeam's catch already produced an honest "UNCERTIFIED — NO WITNESS
// REACHABLE" for an edge that REFUSES. An edge that ACCEPTS and never
// answers was a different story: the fetch had no deadline, so the ledger
// sat at "ASKING THE EDGE…" forever with no abort and nothing said. The
// room guards a dead yard behind the door with SEAM_BOOT_MS and an ESC
// abort; it was not guarding a dead edge in front of it.
//
// This drives that exact case. The witness request is intercepted and left
// hanging — never fulfilled, never aborted by the test — so the only thing
// that can settle the session is WITNESS_MS firing inside the page.
//
// Run:  cd prototypes/tactical3d/test && node test_witness_deadline.mjs
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
const PORT = process.env.WITNESS_TEST_PORT ?? "8096";
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

  // The black hole: the request is accepted and then simply never answered.
  // Never fulfilled and never aborted from out here, so if the session
  // settles, it settled because the PAGE gave up — which is the claim.
  let asked = 0;
  await page.route(/\/certify$/, () => { asked++; /* hang, deliberately */ });

  await page.goto(URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });

  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const opened = await page.waitForFunction(() => !!document.getElementById("seamframe"),
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  check("the door deals a card", opened);
  if (!opened) throw new Error("the door never dealt");

  const frame = await (await page.$("#seamframe")).contentFrame();
  await frame.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  await frame.press("body", "Enter");
  await page.waitForTimeout(900);

  // No overwatch here: the squad is meant to lose fast. This test is about
  // what happens AFTER the card, so the card should be cheap.
  let over = false;
  for (let round = 0; round < 40 && !over; round++) {
    over = await frame.evaluate(() => !!document.querySelector("#overlay.show"));
    if (over) break;
    await frame.press("body", "Enter");
    await page.waitForTimeout(900);
    over = await frame.evaluate(() => !!document.querySelector("#overlay.show"));
  }
  check("the card plays to a finish", over);
  if (!over) throw new Error("the match never ended");

  await frame.click("#ovwalk");
  await page.waitForFunction(() => !document.getElementById("seamframe"),
    null, { timeout: 15000 }).then(() => true, () => false);

  // the panel must pass THROUGH "asking" and come out the other side
  const asking = await page.textContent("#seaminfo");
  check("the room asks the edge first", /ASKING THE EDGE/.test(asking), asking.replace(/\s+/g, " ").trim().slice(-60));

  const t0 = Date.now();
  const settled = await page.waitForFunction(
    () => /CERTIFIED|UNCERTIFIED|STRUCK/.test(document.getElementById("seaminfo").textContent),
    null, { timeout: 30000 }).then(() => true, () => false);
  const waited = Date.now() - t0;
  const verdict = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();

  check("the witness request was actually made", asked > 0, `${asked} asked`);
  check("a hung witness still settles the session", settled, verdict);
  // the deadline is 8s in the page; a generous ceiling still proves that
  // SOMETHING gave up rather than the request eventually completing
  check("it settles on the page's own deadline", settled && waited < 20000, `${waited}ms`);
  check("and it says the edge was unreachable", /UNCERTIFIED/.test(verdict), verdict);
  // the card still counts — an unverified truth LABELED beats a lost one
  check("the unverified card still counts on the ledger",
    /1 CARD/.test(verdict), verdict);
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
