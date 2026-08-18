// The room's deadline on the WITNESS, not on the yard.
//
// certifySeam's catch already produces an honest "LOST THE FEED — NO WITNESS
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
//
// A door walk holds Shift. That is traversal, not a claim about gaits: the
// verbs harness owns the gait claims, and this needs the body at a
// threshold. It matters because `dt` is clamped at 0.05 in the room's frame
// loop and headless rAF runs ~5fps, so a body covers 0.25x its speed per
// REAL second. The walk becoming the default (PR #125) took the door walk
// from ~5.7s to ~12.6s against a 30s timeout, and that margin is what went
// red on a loaded runner (caught in CI on PR #127).
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

const sheetsDir = f => path.join(ROOT, "assets", "sprites", "composed", f);
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
  await page.route(/\/file$/, () => { asked++; /* hang, deliberately */ });

  await page.goto(URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });

  // Shift = run. Traversal, not a gait claim — see the header.
  await page.keyboard.down("Shift");
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const opened = await page.waitForFunction(() => !!document.getElementById("seamframe"),
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  await page.keyboard.up("Shift");
  check("the door deals a card", opened);
  if (!opened) throw new Error("the door never dealt");

  const frame = await (await page.$("#seamframe")).contentFrame();
  await frame.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  await frame.press("body", "Enter");
  await frame.waitForFunction(() =>
    (document.getElementById("cv").dataset.units ?? "").split(",").length === 6,
    null, { timeout: 15000 });

  // No overwatch here: the squad is meant to lose fast. This test is about
  // what happens AFTER the card, so the card should be cheap — and waiting
  // on the turn state rather than sleeping is what makes it cheap.
  const ended = () => frame.evaluate(() => !!document.querySelector("#overlay.show"));
  const opTurn = () => frame.waitForFunction(
    () => /OPERATIVE TURN/.test(document.getElementById("turnlabel").textContent)
      || !!document.querySelector("#overlay.show"),
    null, { timeout: 20000 }).then(() => true, () => false);
  let over = false;
  for (let round = 0; round < 40; round++) {
    over = await ended();
    if (over) break;
    await frame.press("body", "Enter");
    await opTurn();
  }
  check("the card plays to a finish", over);
  if (!over) throw new Error("the match never ended");

  // Arm an IN-PAGE recorder before the card comes home. Everything the
  // next forty lines claim is true only inside the witness deadline, and
  // reading it from out here is a footrace with that deadline: the walked
  // version of this lost it once (beat 2), and the version that read the
  // PUBLISHED value lost it too (caught in CI on this PR) — later in the
  // window, but still inside it. Sampling every frame while the card is
  // in flight and asserting on the recording afterwards is the only shape
  // of this claim that does not depend on how fast the runner is.
  await page.evaluate(() => {
    const cv = document.getElementById("cv");
    const info = document.getElementById("runinfo");
    window.__inFlight = { gates: [], panelSaidLive: false, frames: 0 };
    const tick = () => {
      if (cv.dataset.settling === "1") {
        window.__inFlight.frames++;
        window.__inFlight.gates.push(cv.dataset.dealGate);
        if (/north door is live/.test(info.textContent)) window.__inFlight.panelSaidLive = true;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  await frame.click("#ovwalk");
  await page.waitForFunction(() => !document.getElementById("seamframe"),
    null, { timeout: 15000 }).then(() => true, () => false);

  // the panel must pass THROUGH "asking" and come out the other side
  const asking = await page.textContent("#seaminfo");
  check("the room asks the edge first", /ASKING THE EDGE/.test(asking), asking.replace(/\s+/g, " ").trim().slice(-60));

  // ---- the run cannot be closed out from under a card in flight -------
  // This suite owns the claim because it is the only place the settling
  // window is guaranteed wide: the witness here never answers, so there
  // are seconds of it rather than milliseconds. Closing mid-settlement
  // used to archive the run WITHOUT its final card and then bank that
  // card onto the freshly opened one (caught in review).
  check("a card is in flight", (await page.evaluate(() =>
    document.getElementById("cv").dataset.settling)) === "1");
  await page.keyboard.down("Shift");
  await page.keyboard.press("KeyN");
  await page.keyboard.up("Shift");
  await page.waitForTimeout(150);
  const midFlight = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("closing is refused while a card is settling",
    /STILL SETTLING/.test(midFlight), midFlight);
  check("and the refusal did not close it anyway",
    !/PREVIOUS RUN CLOSED/.test(midFlight)
    && await page.evaluate(() => localStorage.getItem("sentinel.run.closed") === null),
    midFlight);

  // Passing shares the guard, for the same reason with the season's own
  // teeth: the card in flight was dealt at the CURRENT entry, and a pass
  // under it would advance the slate before the card banks — stamping
  // the card with an entry it was never fought at.
  const seasonOf = () => page.evaluate(() =>
    document.getElementById("cv").dataset.season);
  await page.keyboard.down("Shift");
  await page.keyboard.press("KeyP");
  await page.keyboard.up("Shift");
  await page.waitForTimeout(150);
  const passMidFlight = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("passing is refused while a card is settling",
    /PASS ONCE IT LANDS/.test(passMidFlight), passMidFlight);
  check("and the refused pass moved nothing",
    (await seasonOf()) === "0/6:0:fit", await seasonOf());

  // And the DOOR shares the guard: the position a new card would be
  // stamped at is not final while one is in flight — if the settling
  // card banked first, the slate would advance underneath the new deal,
  // and the second card would be stamped at an entry it never fought or
  // refused by the run as a caller bug (caught in review, beat 2).
  //
  // Read off the in-page recording armed before the walk home, not
  // sampled live: the door's published answer is only "settling" INSIDE
  // the deadline, and a live read is a race with it — the walked version
  // lost that race in beat 2 and the live-read version lost it here,
  // eight seconds later in the same window but still inside it. Every
  // frame the card was in flight is in the recording, so the claim no
  // longer depends on how loaded the runner is.
  const inFlight = await page.evaluate(() => window.__inFlight);
  check("the door refused to deal on every frame the card was in flight",
    inFlight.frames > 0 && inFlight.gates.every(g => g === "settling"),
    `${inFlight.frames} frames, gates seen: ${[...new Set(inFlight.gates)].join(",")}`);
  // ...and the PANEL said the same thing the threshold did, for the same
  // frames. It used to rebuild the door's condition out of the season
  // fields and omit the settling gate, so a fresh season with a card in
  // flight kept "the north door is live" on screen for the whole witness
  // deadline while the door refused entry (caught by both review bots).
  // The panel and the door are one call now, and this is what says so.
  check("the panel never claimed a live door while the card was in flight",
    !inFlight.panelSaidLive, `${inFlight.frames} frames sampled`);

  const t0 = Date.now();
  const settled = await page.waitForFunction(
    () => /CERTIFIED|LOST THE FEED|STRUCK/.test(document.getElementById("seaminfo").textContent),
    null, { timeout: 30000 }).then(() => true, () => false);
  const waited = Date.now() - t0;
  const verdict = (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();

  check("the witness request was actually made", asked > 0, `${asked} asked`);
  check("a hung witness still settles the run", settled, verdict);
  // the deadline is 8s in the page; a generous ceiling still proves that
  // SOMETHING gave up rather than the request eventually completing
  check("it settles on the page's own deadline", settled && waited < 20000, `${waited}ms`);
  check("and it says the edge was unreachable", /LOST THE FEED/.test(verdict), verdict);
  // the card still counts — an unverified truth LABELED beats a lost one
  check("the unverified card still counts on the run",
    /1 CARD/.test(verdict), verdict);
  // ...and the run says it was counted unwitnessed. Counting it quietly
  // would make an unverified run indistinguishable from a certified one,
  // which is the whole distinction the deadline exists to preserve.
  const runPanel = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("the run carries the caveat rather than absorbing it",
    /COUNTED UNWITNESSED/.test(runPanel), runPanel);
  check("an unwitnessed card is not also struck",
    !/STRUCK/.test(runPanel), runPanel);
  // counted means counted: an unwitnessed card moves the season exactly
  // as a certified one would — the caveat rides the run, not the slate
  check("the unwitnessed card still moves the season",
    (await seasonOf()) === "1/6:0:unfit", await seasonOf());
  // and the door's answer changes reason rather than opening: the card
  // that was in flight is now a banked loss, so the gate that was
  // "settling" is "unfit" — the same door, refusing for the reason that
  // outlived the window
  // A live read is right HERE and only here: the window has closed, so
  // this value is stable rather than racing anything.
  const gateNow = await page.evaluate(() =>
    document.getElementById("cv").dataset.dealGate);
  check("the settled card leaves the door gated for its own reason",
    gateNow === "unfit", gateNow);
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
