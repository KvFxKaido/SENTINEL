// Executes the walkable page's verb claims in headless chromium.
//
// Serves the repo root, boots the page against synthetic sheets, and
// drives the keyboard through every verb plus the roster fault states.
// Verb durations are measured IN PAGE via rAF: evaluate round-trips can
// be slower than a 4-frame flinch, so sleep-then-read checks lie —
// that lesson is why the watcher exists (caught building this harness).
//
// Real composed sheets for Cipher and the three fielded operatives are
// backed up before the run and restored after — including when setup
// itself fails, and a
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
import { openRun, applyCard } from "../../run-core/run.js";
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
const sheetsDir = fighter => path.join(ROOT, "assets", "sprites", "composed", fighter);
const backupDir = fighter => sheetsDir(fighter) + ".harness-backup";
// the slice's sheets are TRACKED (assets/original is ours), which makes
// the backup discipline more binding, not less: an uncommitted local
// re-frame must survive a harness run exactly as the composed roster does
const RENDER96 = path.join(ROOT, "assets", "original", "cipher_render", "sheets96");
const RENDER96_BAK = RENDER96 + ".harness-backup";
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
  if (fs.existsSync(RENDER96_BAK)) {
    // Louder than the composed reinstate on purpose: sheets96 is TRACKED,
    // so a run that died mid-flight left synthetic fixtures sitting in the
    // repo as commit-able source art until this line ran.
    console.error("STRANDED sheets96 backup found — a previous run died "
      + "before restoring; reinstating the real strips now. Until this "
      + "moment the tracked sheets96 dir held synthetic fixtures.");
    fs.rmSync(RENDER96, { recursive: true, force: true });
    fs.renameSync(RENDER96_BAK, RENDER96);
  }
  if (fs.existsSync(RENDER96)) {
    fs.renameSync(RENDER96, RENDER96_BAK);
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
    .map(v => { const [a, f, l] = v.split(":"); return { a, f: +f, l: +l }; });
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
  await boot();
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
  await boot();
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
  await boot();
  const struckSquad = await ds("squad");
  check("a run with only struck cards leaves the whole squad idle",
    struckSquad === "vesper:idle,koa:idle,sable:idle", struckSquad);
  await page.evaluate(() => localStorage.removeItem("sentinel.run"));
  await boot();

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
  const fireMs = await measureVerb("KeyF", "fire");
  check("fire runs its 5 frames", fireMs > 240 && fireMs < 1000, `${Math.round(fireMs)}ms`);
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

  // ---- one missing squad sheet faults the same room-wide gate -------
  clearSheets();
  gen("full");
  fs.rmSync(path.join(sheetsDir("sable"), "KNEEL", "kneel_left.png"));
  await boot();
  check("a missing squad sheet faults the room", (await ds("sprites")) === "error");
  check("the squad fault names the missing sheet",
    (await page.textContent("#asset-detail")).includes("sable/kneel_left"));

  // ---- PARTIAL Cipher roster is a fault -----------------------------
  clearSheets();
  gen("full");
  fs.rmSync(path.join(sheetsDir("cipher"), "HEAL"), { recursive: true, force: true });
  fs.rmSync(path.join(sheetsDir("cipher"), "DASH"), { recursive: true, force: true });
  await boot();
  check("partial roster faults", (await ds("sprites")) === "error");
  check("fault names the incomplete state",
    (await page.textContent("#asset-detail")).includes("composed roster incomplete"));

  // ---- rejection is not absence: bad geometry faults on its own ----
  clearSheets();
  gen("badgeom");
  await boot();
  check("wrong-height sheets fault rather than degrade",
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

  // ---- the slice: ?body=render96 ------------------------------------
  // The render body enters with four DECLARED verbs. The gate stays
  // all-or-nothing over the declared set, undeclared verbs are refused
  // or labeled — never silently substituted — and the squad stays
  // composed beside it, which is the comparison the staging is for.
  clearSheets();
  gen("full");
  gen("slice96");
  await boot("?body=render96");
  check("slice roster boots", (await ds("sprites")) === "ready");
  check("roster reads render96", (await ds("roster")) === "render96");
  check("BODY cell names the slice",
    (await page.textContent("#body-state")) === "RENDER 96 / 4-VERB SLICE / READY");
  await page.waitForFunction(() =>
    (document.getElementById("cv").dataset.squadSprites ?? "").split(",").length === 3);
  check("the composed squad still stands beside the slice body",
    ((await ds("squadSprites")) ?? "").split(",").length === 3);

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

  // an undeclared STANCE is labeled, not substituted
  await page.keyboard.down("KeyR");
  check("holding R still reports the aim request", await waitAction("aim"));
  check("the aim request stages idle", (await ds("verb")) === "idle");
  check("and says so", (await ds("note")) === "NO AIM SHEET");
  // aim-and-fire with neither declared: the refusal shows BESIDE the
  // stance absence, not behind it — both names on the one surface
  await page.keyboard.press("KeyF");
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.refused === "fire");
  const bothAbsent = await page.textContent("#action-state");
  check("a refused lock is published beside the stance absence",
    bothAbsent.includes("NO AIM SHEET") && bothAbsent.includes("NO FIRE SHEET"),
    bothAbsent);
  await page.keyboard.up("KeyR");
  await waitAction("idle");

  // an undeclared LOCK is refused at entry: no lock starts, the name is
  // published, and the next action change clears it
  await page.keyboard.press("KeyL");
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.refused === "dash");
  check("dash is refused, not faked", (await ds("action")) === "idle");
  await page.keyboard.press("KeyX");
  await page.waitForFunction(() =>
    document.getElementById("cv").dataset.refused === "death");
  check("death cannot reach the slice body", (await ds("action")) === "idle");
  await page.keyboard.down("KeyW");
  check("moving on", await waitAction("run"));
  check("the refusal clears on the next action", (await ds("refused")) === "");
  await page.keyboard.up("KeyW");

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
  fs.rmSync(RENDER96, { recursive: true, force: true });
  for (const fighter of FIGHTERS) {
    if (fs.existsSync(backupDir(fighter))) {
      fs.renameSync(backupDir(fighter), sheetsDir(fighter));
    }
  }
  if (fs.existsSync(RENDER96_BAK)) {
    fs.renameSync(RENDER96_BAK, RENDER96);
  }
  fs.rmSync(LOCK, { recursive: true, force: true });
}

console.log(failures ? `\n${failures} FAILURES` : "\nALL PASS");
process.exit(failures ? 1 : 0);
