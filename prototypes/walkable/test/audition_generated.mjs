// Stages BODY C — the generated Cipher — in walkoff.html and captures it
// under the real camera, LCD pass and terrain, walking south.
//
// Not a CI test. This is an AUDITION harness: it produces frames a human
// judges, the same way the walk-off itself was decided. It asserts only
// the things a picture cannot show (did the sheets load, did the walk
// actually advance, does the south-only gap report itself) and leaves the
// verdict to the eye.
//
// Chrome throttles requestAnimationFrame in a hidden tab, so the render
// loop stalls and any rAF-based measurement hangs — headless playwright
// keeps the page visible, which the browser extension could not.
//
// Run:  cd prototypes/walkable/test
//       node audition_generated.mjs
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const PORT = process.env.AUDITION_PORT ?? "8094";
const URL = `http://localhost:${PORT}/prototypes/walkable/walkoff.html?generated=1`;
const OUT = process.env.AUDITION_OUT ?? path.join(HERE, "audition-shots");
const PY = process.platform === "win32" ? "python" : "python3";

const serve = () =>
  spawn(PY, ["-m", "http.server", PORT], { cwd: ROOT, stdio: "ignore" });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const server = serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1100, height: 620 } });
  const fails = [];

  try {
    await sleep(900);
    await page.goto(URL);
    await page.waitForFunction(
      () => ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
      null, { timeout: 15000 });

    const ds = k => page.evaluate(k => document.getElementById("cv").dataset[k], k);
    const bodyState = await page.evaluate(() => document.getElementById("body-state").textContent);
    const genState = () => page.evaluate(() => document.getElementById("gen-state").textContent);

    if (await ds("sprites") !== "ready") fails.push("sheets did not load");
    if (!bodyState.includes("GEN")) fails.push(`BODY readout lacks GEN: ${bodyState}`);

    await page.screenshot({ path: path.join(OUT, "01-idle-down.png") });

    // Walk south. Frames are sampled in-page across held movement so the
    // capture cannot land on one stale frame and call it a cycle.
    // Capture WHILE it is genuinely walking south. The page derives facing
    // from clamped actual movement, so once the body reaches the south
    // bound the movement collapses toward zero and the facing flips to a
    // side — a shot taken late reads FACING RIGHT and shows the idle. Gate
    // on the sprite facing rather than on the key that was pressed.
    // Back up to the north end first. From the spawn point the south wall
    // is under half a second away, and once the body is fenced there the
    // clamped movement collapses and the facing flips off "down" — so a
    // capture that starts from spawn photographs the idle.
    await page.keyboard.down("KeyW");
    await sleep(2100);
    await page.keyboard.up("KeyW");
    await sleep(150);

    await page.keyboard.down("KeyS");
    await page.waitForFunction(
      () => {
        const d = document.getElementById("cv").dataset;
        return d.action === "run" && d.facing === "down" && d.genWalk === "1";
      }, null, { timeout: 4000 })
      .catch(() => fails.push("never reached run+down+genWalk while holding KeyS"));

    // Sample on a timer, not rAF: headless throttles animation frames hard
    // enough that an rAF sampler aliases against a 9fps cycle and reports
    // three frames out of eight (measured — it read 1,4,7 and called the
    // walk broken). The page's own clock is unaffected; only the observer
    // was wrong. Sampling runs CONCURRENTLY with the captures, inside the
    // same window of real southward travel.
    const sampler = page.evaluate(() => new Promise(res => {
      const cv = document.getElementById("cv");
      const seen = new Set(); const t0 = performance.now();
      const id = setInterval(() => {
        if (cv.dataset.genWalk === "1") seen.add(cv.dataset.frameGen);
        if (performance.now() - t0 > 3000) { clearInterval(id); res([...seen]); }
      }, 20);
    }));

    for (let i = 0; i < 5; i++) {
      await page.screenshot({ path: path.join(OUT, `02-walk-south-${i}.png`) });
      await sleep(320);
    }
    const walked = await sampler;
    if (walked.length < 4) fails.push(`generated walk barely advanced: frames seen ${walked}`);

    // BODY C is composed from the pack's own frames, so every facing the
    // pack walks, it walks. The SOUTH ONLY state this used to assert was a
    // property of the generated-whole walk and no longer exists; asserting
    // it now would be pinning a limitation we removed.
    await page.keyboard.up("KeyS");
    await page.keyboard.down("KeyD");
    await sleep(600);
    const sideways = await genState();
    if (!/WALK/.test(sideways)) {
      fails.push(`east-facing BODY C should walk, read: ${sideways}`);
    }
    if (await ds("genWalk") !== "1") fails.push("genWalk not set while walking east");
    await page.screenshot({ path: path.join(OUT, "03-east-walk.png") });
    await page.keyboard.up("KeyD");

    console.log(`frames seen in the generated walk: ${walked.sort().join(",")}`);
    console.log(`east-facing BODY C readout: ${sideways}`);
    console.log(`shots -> ${OUT}`);
  } finally {
    await browser.close();
    server.kill();
  }

  if (fails.length) {
    console.error("AUDITION FAULTS:\n  " + fails.join("\n  "));
    process.exitCode = 1;
  } else {
    console.log("audition staged clean — judge the shots");
  }
}

main();
