// Stages the three-body walk-off — pack (A, left), hybrid (C, centre),
// whole-generated render (B, right) — and captures it under the real
// camera, LCD pass and terrain, walking south.
//
// Not a CI test. This is an AUDITION harness: it produces frames a human
// judges, the same way the walk-off itself was decided. It asserts only
// the things a picture cannot show (did the sheets load, did each walk
// actually advance, does a missing-facing gap report itself) and leaves
// the verdict to the eye.
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
const URL = `http://localhost:${PORT}/prototypes/walkable/walkoff.html`;
const OUT = process.env.AUDITION_OUT ?? path.join(HERE, "audition-shots");
const PY = process.platform === "win32" ? "python" : "python3";

const serve = () =>
  spawn(PY, ["-m", "http.server", PORT], { cwd: ROOT, stdio: "ignore" });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  // Launch INSIDE the cleanup scope. If chromium is absent or playwright
  // rejects the launch (a provisioned-browser version mismatch does this),
  // an await out here throws past the finally and strands the python server
  // holding AUDITION_PORT — so the next run cannot bind, and the failure
  // looks like a port problem rather than a missing browser.
  const server = serve();
  const fails = [];
  let browser = null;
  let page = null;

  try {
    browser = await chromium.launch();
    page = await browser.newPage({ viewport: { width: 1100, height: 620 } });
    await sleep(900);
    await page.goto(URL);
    await page.waitForFunction(
      () => ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
      null, { timeout: 15000 });

    const ds = k => page.evaluate(k => document.getElementById("cv").dataset[k], k);
    const bodyState = await page.evaluate(() => document.getElementById("body-state").textContent);
    const genState = () => page.evaluate(() => document.getElementById("gen-state").textContent);
    const renState = () => page.evaluate(() => document.getElementById("ren-state").textContent);

    if (await ds("sprites") !== "ready") fails.push("sheets did not load");
    if (!bodyState.includes("HYBRID") || !bodyState.includes("RENDER")) {
      fails.push(`BODY readout lacks HYBRID/RENDER: ${bodyState}`);
    }

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
        return d.action === "run" && d.facing === "down"
          && d.genWalk === "1" && d.renWalk === "1";
      }, null, { timeout: 4000 })
      .catch(() => fails.push("never reached run+down+genWalk+renWalk while holding KeyS"));

    // Sample on a timer, not rAF: headless throttles animation frames hard
    // enough that an rAF sampler aliases against a 9fps cycle and reports
    // three frames out of eight (measured — it read 1,4,7 and called the
    // walk broken). The page's own clock is unaffected; only the observer
    // was wrong. Sampling runs CONCURRENTLY with the captures, inside the
    // same window of real southward travel. Both generated walks are
    // sampled in the same window: they share the clock, not the cycle.
    const sampler = page.evaluate(() => new Promise(res => {
      const cv = document.getElementById("cv");
      const gen = new Set(); const ren = new Set();
      const t0 = performance.now();
      const id = setInterval(() => {
        if (cv.dataset.genWalk === "1") gen.add(cv.dataset.frameGen);
        if (cv.dataset.renWalk === "1") ren.add(cv.dataset.frameRen);
        if (performance.now() - t0 > 3000) {
          clearInterval(id); res({ gen: [...gen], ren: [...ren] });
        }
      }, 20);
    }));

    for (let i = 0; i < 5; i++) {
      await page.screenshot({ path: path.join(OUT, `02-walk-south-${i}.png`) });
      await sleep(320);
    }
    // The floor is 3, not 4: headless renders ~5fps and the south run only
    // lasts ~2.3s before the fence stops it, so a 9fps 8-frame cycle yields
    // 3-5 distinct sampled frames depending on aliasing. 4 sat exactly on
    // that edge and false-faulted on two of four otherwise-identical runs
    // (measured 2026-08-02). Three distinct frames still proves the sheet
    // advances — a stuck sheet shows one — and smoothness is the eye's call
    // from the shots, not this counter's.
    const walked = await sampler;
    if (walked.gen.length < 3) {
      fails.push(`hybrid walk barely advanced: frames seen ${walked.gen}`);
    }
    if (walked.ren.length < 3) {
      fails.push(`render walk barely advanced: frames seen ${walked.ren}`);
    }

    // Every facing both generated bodies declare, they walk. The SOUTH
    // ONLY state this used to assert was a property of the v3 generated-
    // whole walk and no longer exists on either body; the render's
    // template walk was generated for all four cardinals.
    await page.keyboard.up("KeyS");
    await page.keyboard.down("KeyD");
    await sleep(600);
    const sidewaysGen = await genState();
    const sidewaysRen = await renState();
    if (!/WALK/.test(sidewaysGen)) {
      fails.push(`east-facing hybrid should walk, read: ${sidewaysGen}`);
    }
    if (!/WALK/.test(sidewaysRen)) {
      fails.push(`east-facing render should walk, read: ${sidewaysRen}`);
    }
    if (await ds("genWalk") !== "1") fails.push("genWalk not set while walking east");
    if (await ds("renWalk") !== "1") fails.push("renWalk not set while walking east");
    await page.screenshot({ path: path.join(OUT, "03-east-walk.png") });
    await page.keyboard.up("KeyD");

    console.log(`hybrid frames seen: ${walked.gen.sort().join(",")}`);
    console.log(`render frames seen: ${walked.ren.sort().join(",")}`);
    console.log(`east-facing readouts — hybrid: ${sidewaysGen}  render: ${sidewaysRen}`);
    console.log(`shots -> ${OUT}`);
  } finally {
    if (browser) await browser.close();
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
