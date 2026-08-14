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
// Fixtures are built with the module the room consumes, so a seeded run
// is a run this schema actually produces rather than a hand-typed blob
// that happens to restore.
import { openSeason, applyCard } from "../../run-core/run.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const GEN = path.join(ROOT, "prototypes", "walkable", "test", "make_synthetic_sheets.py");
const FIGHTERS = ["cipher", "vesper", "koa", "sable", "syn"];
const PY = process.platform === "win32" ? "python" : "python3";
const PORT = process.env.SEAM_TEST_PORT ?? "8095";
// ?deal=6 pins the card the door deals, so a failure is reproducible
const ROOM_URL = `http://localhost:${PORT}/prototypes/walkable/?deal=6`;

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

  await page.goto(ROOM_URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  check("the room boots", (await page.evaluate(() =>
    document.getElementById("cv").dataset.sprites)) === "ready");

  // Beat 2 of season-lite: a fresh room is a front office. The season
  // surface is read the same way dataset.run is — off the page, because
  // what is asserted is what a player would see.
  const seasonOf = p => p.evaluate(() => document.getElementById("cv").dataset.season);
  check("a fresh room opens on the house slate, fit and at stop one",
    (await seasonOf(page)) === "0/6:0:fit", await seasonOf(page));

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

  const seamSrc = await page.getAttribute("#seamframe", "src");
  check("a plain room deals render96 through the seam",
    new URL(seamSrc, page.url()).searchParams.get("body") === "render96", seamSrc);
  // ---- the roster crosses the door ----------------------------------
  // `architecture/roster_in_the_match.md`: the law is now
  // `seed + roster + record = the match`, so the world deals WHO fights
  // beside WHICH card. This is the one suite that can watch the whole
  // chain — dealt, fielded, posted home, certified — in one crossing.
  const dealtRoster = new URL(seamSrc, page.url()).searchParams.get("roster");
  check("the world deals the squad beside the seed",
    dealtRoster === "VESPER:10,KOA:10,SABLE:10", dealtRoster);
  const cutFielding = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
  check("the cut card says who is fighting",
    /FIELDING VESPER · KOA · SABLE/.test(cutFielding), cutFielding);
  // the cut card carries the current entry's framing — the run's own
  // slate talking, since nothing seasonal crosses the seam itself
  const cut = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
  check("the cut card frames the deal from the run's own slate",
    /KESTREL YARD/.test(cut) && /HELD BY STEEL-SYNDICATE/.test(cut), cut);

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
  check("the yard stages the room's render96 body",
    (await frame.evaluate(() => document.getElementById("cv").dataset.body)) === "render96");
  // and it fields the squad the world dealt, in the rules core's own
  // canonical form — the yard's word about its own board, not the URL
  // read back to itself
  const yardFielded = await frame.evaluate(() =>
    document.getElementById("cv").dataset.fielded);
  check("the yard fields exactly the squad the world dealt",
    yardFielded === "VESPER:10|KOA:10|SABLE:10", yardFielded);
  // loading, not telemetry: the render idle is 4 frames where composed is 8
  const renderIdles = await frame.evaluate(() =>
    document.getElementById("cv").dataset.idleFrames ?? "");
  check("the forwarded body controls loading: render Cipher idles at 4",
    renderIdles.includes("cipher:4"), renderIdles);
  // the squad-combat flip: the fighters the card actually FIELDS carry
  // the render body through the door too
  check("the forwarded body controls the squad: render Koa idles at 4",
    renderIdles.includes("koa:4"), renderIdles);

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
  check("the room settles the run", settled, verdict);
  // The one verdict that is a bug rather than a circumstance: the edge
  // replayed what we played and got something else.
  check("the edge does not dispute the record", !/STRUCK/.test(verdict), verdict);
  // The room asks the edge for the aftermath too now — a mismatch on the
  // walked/finished/lost counts strikes the card the same way a rating
  // mismatch always has. Reaching CERTIFIED means those agreed.
  check("the card comes home with its aftermath",
    /WALKED/.test(verdict) && /FINISHED/.test(verdict) && /OF YOURS DOWN/.test(verdict), verdict);
  // A card the RUN refused is a bug in the room, not a dispute at the
  // edge — the room validated this payload before it ever got here, so
  // the two validators disagreeing is exactly what this catches.
  check("the run does not refuse a card the room accepted",
    !/RUN REFUSED/.test(verdict), verdict);
  check("the banked card says where it banked",
    /AT KESTREL YARD/.test(verdict), verdict);
  // the second input, on the surface: the card the room settles names the
  // squad that fought it, not only the seed that dealt it
  check("the settled card names the squad that fought it",
    /FIELDED VESPER 10\/10 · KOA 10\/10 · SABLE 10\/10/.test(verdict), verdict);

  // ---- the run outlives the tab -------------------------------------
  // The whole point of the run layer. dataset.run is the surface's own
  // numbers, not storage read back — what is asserted is what a player
  // would actually see in the panel.
  const runOf = p => p.evaluate(() => document.getElementById("cv").dataset.run);
  const banked = await runOf(page);
  // "cards:W–L:purse:walked:finished:struck". The dash is an en dash the
  // panel renders; matched with . so this file's encoding cannot decide
  // whether the suite passes.
  const [cards, record, purse] = (banked ?? "::").split(":");
  check("the card is banked on the run", +cards === 1, banked);
  check("the run knows it was a loss", /^0.1$/.test(record), banked);
  check("the run banks a purse", +purse > 0, banked);
  // a loss fires only when the op side is wiped (rules.js), so a banked
  // loss ALWAYS starts recovery clocks: the slate advanced and the deal
  // is now gated — the season's whole texture, executed in one string
  check("the banked loss advances the slate and gates the deal",
    (await seasonOf(page)) === "1/6:0:unfit", await seasonOf(page));

  await page.reload();
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  const survived = await runOf(page);
  check("the run survives a reload", survived === banked, `${survived} vs ${banked}`);
  const panel = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("the reloaded panel shows the banked card", /1 CARD\b/.test(panel), panel);
  check("the reloaded panel is not carrying a caveat it did not earn",
    !/STORAGE UNAVAILABLE|SET ASIDE|REFUSED/.test(panel), panel);
  check("the season survives the reload",
    (await seasonOf(page)) === "1/6:0:unfit", await seasonOf(page));
  check("the reloaded panel holds the front office",
    /STOP 2 OF 6/.test(panel) && /ROSTER UNFIT/.test(panel), panel);

  // ---- closing a run is destructive, and archives ---------------------
  await page.keyboard.down("Shift");
  await page.keyboard.press("KeyN");
  await page.keyboard.up("Shift");
  await page.waitForTimeout(150);
  const emptied = s => /^0:0.0:0:/.test(s ?? "");
  const afterClose = await runOf(page);
  check("closing the run empties it", emptied(afterClose), afterClose);
  check("closing says what the closed run held",
    /PREVIOUS RUN CLOSED/.test(await page.textContent("#runinfo")),
    (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim());
  const archived = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("sentinel.run.closed") ?? "null"));
  check("the closed run is archived, not dropped",
    archived !== null && archived.cards === 1, JSON.stringify(archived));
  check("the run is archived season and all",
    archived !== null && archived.season !== null
      && archived.season.pos === 1
      && archived.season.slate.id === "opening-circuit",
    JSON.stringify(archived?.season?.slate?.id ?? null));
  check("closing a season opens a fresh one on the house slate",
    (await seasonOf(page)) === "0/6:0:fit", await seasonOf(page));
  await page.reload();
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  check("the closed run stays closed across a reload",
    emptied(await runOf(page)), await runOf(page));

  // ---- a run this schema cannot read is set aside, never rendered -----
  // The live key is unversioned on purpose: a versioned one made this path
  // unreachable on a real RUN_V bump, because loadRun would read an empty
  // new key and leave the real run under one nothing looks at.
  await page.evaluate(() => localStorage.setItem("sentinel.run", '{"v":0,"purse":99999}'));
  await page.reload();
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  const orphanPanel = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("an unreadable run opens a fresh one and says so",
    /SET ASIDE/.test(orphanPanel), orphanPanel);
  check("the unreadable run's numbers never reach the surface",
    !/99999/.test(orphanPanel), orphanPanel);
  check("the unreadable run still exists",
    await page.evaluate(() => /99999/.test(localStorage.getItem("sentinel.run.orphan") ?? "")));

  // ---- and a set-aside that cannot be verified spends nothing ---------
  // The orphan write can throw under quota, or land in a store that
  // keeps nothing. loadRun reads the orphan back before clearing the
  // slot; when that fails, the room must not save a fresh run over the
  // live slot, because it holds the only copy of the old one (caught in
  // review). The patch drops writes to the orphan key only while the
  // flag is set, so the later sections keep an honest store.
  await page.addInitScript(() => {
    const orig = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) {
      if (k === "sentinel.run.orphan"
          && this.getItem("sentinel.test.dropOrphan") === "1") return;
      return orig.call(this, k, v);
    };
  });
  await page.evaluate(() => {
    localStorage.setItem("sentinel.run", '{"v":0,"purse":77777}');
    localStorage.setItem("sentinel.test.dropOrphan", "1");
  });
  await page.reload();
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  const stuckPanel = (await page.textContent("#runinfo")).replace(/\s+/g, " ").trim();
  check("a set-aside that cannot be verified says so",
    /COULD NOT BE SET ASIDE/.test(stuckPanel), stuckPanel);
  check("and the room does not save over the only copy",
    await page.evaluate(() => /77777/.test(localStorage.getItem("sentinel.run") ?? "")),
    await page.evaluate(() => localStorage.getItem("sentinel.run")));
  check("the stuck run's numbers never reach the surface",
    !/77777/.test(stuckPanel), stuckPanel);
  check("the unwritable page says the run is not persisted",
    /NOT PERSISTED/.test(stuckPanel), stuckPanel);
  await page.evaluate(() => localStorage.removeItem("sentinel.test.dropOrphan"));

  // ---- nothing bought crosses the door -------------------------------
  // Beat 3 of season-lite. The purse spends in the room, on flair, and
  // the whole tier boundary rests on that purchase being invisible to
  // the yard: `seed + record IS the match`, and a fighter in a new hood
  // has to fight precisely the card they would have fought naked.
  //
  // Executed rather than argued. ?deal=6 pins the seed, so a crossing
  // from a DRESSED room must produce the byte-identical iframe URL the
  // bare room produced at the top of this file — same seed, same body,
  // nothing appended. This suite is the only place both surfaces are
  // alive at once, which makes it the only place that claim can be run.
  const SHOP_TOUR = {
    id: "purse-tour",
    entries: [
      { venue: "KESTREL YARD", host: "steel-syndicate", sanction: "steel-syndicate" },
      { venue: "THE COLD COURT", host: "covenant", sanction: "covenant" },
    ],
  };
  const funded = applyCard(openSeason("2026-08-13T00:00:00Z", SHOP_TOUR), {
    seed: "a", result: "win", rating: 30, purse: 300,
    ledger: { walked: 0, finished: 0, lost: 0 }, down: [], cert: "certified",
    rules: "test-rules", at: "2026-08-13T00:00:00Z",
  });
  if (!funded.accepted) throw new Error(`purse fixture refused: ${funded.why}`);
  await page.evaluate(value => {
    localStorage.clear();
    localStorage.setItem("sentinel.run", JSON.stringify(value));
  }, funded.run);
  await page.goto(ROOM_URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });

  // The shop is a place: walk to it, never a key from across the room.
  // Waiting on the room's own published state, never on a sleep. A is the
  // south-west diagonal in this camera-relative 2:1 view, which runs from
  // the spawn straight at the table — the same reason the door walk takes
  // W+D rather than W alone.
  await page.keyboard.down("KeyA");
  const reached = await page.waitForFunction(() =>
    document.getElementById("cv").dataset.shop === "at",
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyA");
  check("the body reaches the kit table", reached, await page.evaluate(() =>
    document.getElementById("cv").dataset.position));
  await page.keyboard.press("Digit3");
  const dressed = await page.evaluate(() => document.getElementById("cv").dataset.worn);
  check("the purse buys flair in the room",
    dressed === "VESPER/patch/length-of-chain", dressed);

  // Back to the spawn before walking the door, and not for tidiness.
  // The walk to the table stops WHEREVER the reach check happens to fire,
  // which is a frame-timing question — so the body's x after shopping is
  // not a fact this suite knows. W+D is true north, holding x, and the
  // door only deals to a body inside its span: a shop stop half a unit
  // too far west never reaches it. That was luck passing, not a claim, and
  // it ran out in CI the moment the default gait got slower and moved
  // where the walk ends (caught in CI on the gait PR). The purchase is in
  // localStorage, so a reload keeps the dressed squad and puts the body
  // somewhere this suite can actually reason about.
  await page.goto(ROOM_URL);
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  check("the purchase survives the walk back to the door",
    (await page.evaluate(() => document.getElementById("cv").dataset.worn))
      === "VESPER/patch/length-of-chain",
    await page.evaluate(() => document.getElementById("cv").dataset.worn));

  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const dealtDressed = await page.waitForFunction(() =>
    !!document.getElementById("seamframe"),
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  check("a dressed squad still gets a card dealt", dealtDressed);
  if (dealtDressed) {
    const dressedSrc = await page.getAttribute("#seamframe", "src");
    check("the dressed room deals the yard exactly what the bare room dealt",
      dressedSrc === seamSrc, `${dressedSrc} vs ${seamSrc}`);
    // ...and the framing on the cut still comes from the run's OWN slate,
    // which is the beat-2 half of the same sentence: what crosses the
    // seam is a seed, and everything else is the room talking.
    const dressedCut = (await page.textContent("#seamcut")).replace(/\s+/g, " ").trim();
    check("the cut is framed by the restored run's own slate",
      /THE COLD COURT/.test(dressedCut) && /SANCTIONED BY COVENANT/.test(dressedCut),
      dressedCut);

    // ---- the room does not trust the edge about the squad either ------
    // The certificate reports what the REPLAY fielded. An edge that
    // ignored the roster and certified the canonical three would agree
    // on every other number for any card where the difference happened
    // not to change the outcome — so without this check it would look
    // exactly like agreement (caught in review).
    //
    // Driven by stubbing /certify rather than by playing a card: the
    // claim is about what the ROOM does with an answer, and a crafted
    // answer is the only way to produce the disagreement on demand. The
    // seam result is posted from INSIDE the frame because the room
    // refuses any message that is not its own iframe's.
    const DEALT = [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }];
    const stubCert = certRoster => page.route(/\/certify$/, route => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        certified: true, rules: "stub-rules", result: "loss", rating: 7, purse: 70,
        ledger: { walked: 0, finished: 0, lost: 0 }, roster: certRoster,
        rosterHash: "stub", fingerprint: "abc123", lines: 1, transcript: [],
      }),
    }));
    const postHome = frameHandle => frameHandle.evaluate(() => {
      window.parent.postMessage({
        type: "sentinel-seam-result",
        seed: "6", record: [["end"]], result: "loss", rating: 7, purse: 70,
        ledger: { walked: 0, finished: 0, lost: 0 }, down: [],
        roster: [{ name: "VESPER", hp: 10 }, { name: "KOA", hp: 10 }, { name: "SABLE", hp: 10 }],
        fingerprint: "abc123", lines: 1,
      }, location.origin);
    });
    const settledVerdict = async () => {
      await page.waitForFunction(
        () => /CERTIFIED|UNCERTIFIED|STRUCK|REFUSED/.test(
          document.getElementById("seaminfo").textContent),
        null, { timeout: 20000 }).catch(() => {});
      return (await page.textContent("#seaminfo")).replace(/\s+/g, " ").trim();
    };

    const dressedFrame = await (await page.$("#seamframe")).contentFrame();
    await stubCert([{ name: "VESPER", hp: 10 }, { name: "NIX", hp: 10 }, { name: "SABLE", hp: 10 }]);
    await postHome(dressedFrame);
    const wrongSquadVerdict = await settledVerdict();
    check("an edge certifying a squad the room did not deal is disputed",
      /STRUCK/.test(wrongSquadVerdict), wrongSquadVerdict);

    // ...and the same stub agreeing about the squad certifies, so the
    // check above is discriminating rather than merely strict
    await page.goto(ROOM_URL);
    await page.waitForFunction(() =>
      ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
      null, { timeout: 20000 });
    await page.keyboard.down("KeyW");
    await page.keyboard.down("KeyD");
    const reopened = await page.waitForFunction(() => !!document.getElementById("seamframe"),
      null, { timeout: 30000 }).then(() => true, () => false);
    await page.keyboard.up("KeyW");
    await page.keyboard.up("KeyD");
    if (reopened) {
      await stubCert(DEALT);
      await postHome(await (await page.$("#seamframe")).contentFrame());
      const rightSquadVerdict = await settledVerdict();
      check("and the same stub agreeing about the squad certifies",
        /CERTIFIED/.test(rightSquadVerdict) && !/STRUCK/.test(rightSquadVerdict),
        rightSquadVerdict);
      check("...and does not carry the not-attested caveat",
        !/SQUAD NOT ATTESTED/.test(rightSquadVerdict), rightSquadVerdict);
    } else {
      check("and the same stub agreeing about the squad certifies", false, "the door never re-dealt");
    }

    // The third case, and the one the live edge is in until the Worker is
    // redeployed: a certificate that says nothing about the squad. It
    // certified the match honestly and never spoke to who fought it —
    // counted, and LABELED, because requiring the field would strike
    // every honest card and assuming agreement would be the silent half
    // of the same mistake.
    //
    // On a FRESH run: the two-entry fixture tour is complete by now (the
    // stub card above banked its last entry), and a complete slate gates
    // the door — correctly, and unhelpfully for a third crossing.
    await page.evaluate(() => localStorage.clear());
    await page.goto(ROOM_URL);
    await page.waitForFunction(() =>
      ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
      null, { timeout: 20000 });
    await page.keyboard.down("KeyW");
    await page.keyboard.down("KeyD");
    const thirdDeal = await page.waitForFunction(() => !!document.getElementById("seamframe"),
      null, { timeout: 30000 }).then(() => true, () => false);
    await page.keyboard.up("KeyW");
    await page.keyboard.up("KeyD");
    if (thirdDeal) {
      await stubCert(undefined);
      await postHome(await (await page.$("#seamframe")).contentFrame());
      const silentVerdict = await settledVerdict();
      check("an edge that predates the roster counts, and says it did not attest the squad",
        /CERTIFIED/.test(silentVerdict) && /SQUAD NOT ATTESTED/.test(silentVerdict)
          && !/STRUCK/.test(silentVerdict),
        silentVerdict);
    } else {
      check("an edge that predates the roster counts, and says so", false, "the door never re-dealt");
    }
    await page.unroute(/\/certify$/);
  }

  // ---- the seam carries the OTHER body too ---------------------------
  // A seam that always forwarded render96 would pass everything above, and
  // the forwarded value must control ASSET LOADING, not just telemetry —
  // both halves executed here via the composed room and the 8-frame
  // composed idle where the render idle is 4 (caught in review).
  await page.evaluate(() => localStorage.clear());
  await page.goto(ROOM_URL + "&body=composed");
  await page.waitForFunction(() =>
    ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
    null, { timeout: 20000 });
  await page.keyboard.down("KeyW");
  await page.keyboard.down("KeyD");
  const composedOpened = await page.waitForFunction(() =>
    !!document.getElementById("seamframe"),
    null, { timeout: 30000 }).then(() => true, () => false);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("KeyD");
  check("the composed room's door still deals", composedOpened);
  if (composedOpened) {
    const composedSrc = await page.getAttribute("#seamframe", "src");
    check("a composed room deals composed through the seam",
      new URL(composedSrc, page.url()).searchParams.get("body") === "composed",
      composedSrc);
    const composedFrame = await (await page.$("#seamframe")).contentFrame();
    await composedFrame.waitForFunction(() =>
      ["ready", "error"].includes(document.getElementById("cv").dataset.sprites),
      null, { timeout: 20000 });
    check("the yard stages the room's composed body",
      (await composedFrame.evaluate(() =>
        document.getElementById("cv").dataset.body)) === "composed");
    const composedIdles = await composedFrame.evaluate(() =>
      document.getElementById("cv").dataset.idleFrames ?? "");
    check("the forwarded body controls loading: composed Cipher idles at 8",
      composedIdles.includes("cipher:8"), composedIdles);
    check("the forwarded body controls the squad: composed Koa idles at 8",
      composedIdles.includes("koa:8"), composedIdles);
  }
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
