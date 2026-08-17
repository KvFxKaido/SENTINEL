# Tactical Encounter Prototype — 3D

The same encounter as `../tactical/`, rendered with three.js instead of a 2D
canvas. Same map, same rules, same seeded RNG, same replay guarantee.

**Run it:** double-click `serve.cmd`, or:

```sh
python -m http.server -d prototypes 8080
# then open http://localhost:8080/tactical3d/
```

It will not run from `file://` — see [Why it needs a server](#why-it-needs-a-server).
Append `?seed=deadbeef` to pin a specific encounter. Append
`&venue=THE COLD COURT` to stage it somewhere from `world/venues.json` —
light, weather and the card's venue lines change; the match does not,
and `test/test_yard_venue.mjs` replays one seed at two venues to hold
that line. A venue the atlas lacks gets the house look and says so on
the feed; without the param the yard is its own ground, unchanged.

The world may also deal an exact three-person snapshot with
`&roster=VESPER:10,KOA:10,SABLE:10`. The yard accepts only the existing
`{name, hp}` contract and never sees run-owned ids, origins, or the bench.
NIX is stageable as a tactical identity and explicitly borrows SYN's tracked
canvas in this prototype; that mapping is registered in `pack_sprites.js`,
not chosen as a fallback after an asset fails.

## What this port is

A renderer swap, not a rewrite. The 2D prototype split cleanly in half: a
rules layer with no canvas calls, and a drawing layer underneath it. That
rules layer now lives in [`../tactical-core/`](../tactical-core/) and is
shared — this file only draws and takes input. Nothing here decides anything
about the game.

That split is the reason the port is trustworthy: the game was already proven,
so any bug found here belongs to the renderer.

**Determinism is enforced, not hoped for.** The golden transcripts in
`../tactical-core/rules.test.js` were captured from the browser build *before*
the rules were extracted, and three independent paths now reproduce them
byte-for-byte: the pre-extraction build, the headless Node suite, and both
renderers. The suite runs in CI.

## What 3D actually bought

Not spectacle. Two specific things:

- **Directional cover became spatial.** In the 2D build, "this crate only
  helps against fire from that side" had to be communicated with a flank
  marker. Here the crate is physically on one side of the unit, it casts a
  shadow, and in shoot mode the tile that is *currently* shielding each
  hostile lights amber. You can also rotate the board and look.
- **Sprites without a sprite pipeline.** `Isometric Sprite System.md` concedes
  that 64×64 four-direction walk cycles are unsustainable for a solo dev.
  Units here are the 2D build's authored 16×16 sprites on Y-billboarded
  quads — one facing plus a horizontal flip — while the environment stays
  primitive geometry that rotates for free. That is the 2.5D shape
  `architecture/art_direction_gba_tactics.md` commits to ("The view").

## What it cost

- **Occlusion.** Full-cover walls are 1.5 units tall and will hide a unit
  standing behind them — a problem a top-down board cannot have. Mitigated
  two ways: `Q`/`E` rotate the camera in 90° steps, and any occluded unit
  renders as an X-ray silhouette so it is never simply absent.
- **A server.** See below. This cost got charged to the 2D build too when the
  rules were extracted — it no longer opens from `file://` either. That was a
  deliberate trade: one tested source of truth beat two copies that were going
  to drift.

## Controls

| Input | Action |
|-------|--------|
| click | select operative / move / shoot hostile / finish a yielded hostile / select an adjacent down operative then a drag destination |
| `Tab` | cycle to next operative with AP |
| `F` | toggle shoot mode (hit % over every hostile) |
| `Y` | overwatch (ends unit's activation) |
| `Enter` | end turn — or **spare them**, once every hostile has yielded |
| `Q` / `E` | rotate camera 90° |
| `P` | cycle display: LCD / crunch / clean |
| `R` / `shift+R` | new encounter / replay same seed |

## Projection

45° azimuth, 30° elevation, orthographic. That is exactly the 2:1 dimetric
ratio `architecture/Isometric Sprite System.md` specifies — 30° is the angle
where a unit grid step projects to a 2:1 screen slope. Rotation snaps to 90°
so the board never sits at an off-axis angle.

`P` cycles three display treatments:

- **LCD** (default) — the scene renders to a 350×222 target, then a post pass
  draws every texel as a discrete LCD cell with darkened seams and applies
  handheld color: desaturated toward luma, warmed, shadows lifted because a
  real LCD never reaches true black. Modeled on RetroArch's
  `lcd-grid-v2` + `gba-color` treatment (the shader stack that makes GBA
  tactics games look right on modern screens — the direct inspiration was
  Super Robot Wars J under exactly that stack). The target is exactly half
  the 700×444 canvas and the mode snaps device pixel ratio to an integer, so
  each texel lands on a clean 2×2 (4×4 at DPR 2) cell — non-integer scales
  turn the seams into moiré, which is also why the canvas height is even.
- **crunch** — the original trick: render at 0.6× and let
  `image-rendering: pixelated` upscale. A pixel look without a pixel pipeline.
- **clean** — native resolution, no treatment.

## Why it needs a server

three.js no longer ships a non-module build, so `index.html` uses
`<script type="module">`, and browsers block module imports over `file://`.
The 2D prototype's "no build step, no dependencies, no install" promise
survives otherwise: three.js is vendored in `vendor/`, nothing is fetched at
runtime, and there is still no npm and no bundler. It just has to come off a
static server. The page detects `file://` and says so rather than showing a
black canvas.

`vendor/three.module.js` + `vendor/three.core.js` are three.js r0.185.1,
unmodified, MIT.

Since the convergence the server root is the **repository**, not
`prototypes/` — the page loads molded sheets from `assets/`. `serve.cmd`
does this for you; by hand it is `python -m http.server 8080` at the repo
root, then <http://localhost:8080/prototypes/tactical3d/>. Regenerate the
sheets with `python scripts/roster_mold.py` (the licensed source pack must
be present locally); without them the page stops at an explicit fault.

## Tests

`test/` holds two headless suites, both wired into the `walkable-harness`
CI job:

```sh
cd prototypes/tactical3d/test
npm install && npx playwright install chromium
node test_yard_bodies.mjs        # roster boot, facing, verbs, asset faults
node test_seam_round_trip.mjs    # the door, the card, and the verdict
node test_witness_deadline.mjs   # an edge that accepts and never answers
```

Both run against **synthetic sheets** at the pack's real geometry (shared
generator with the walkable harness — the two pages load the same bodies,
so faking them two different ways would let the fixtures drift exactly
where the convergence says they must not). Real sheets are backed up and
restored around every run, including on setup failure.

The body suite drives the match through the *game* — `Tab` selects, `F`
takes target mode, overwatch plus `Enter` hands the board to the AI — so
it reaches fire / hurt / death / kneel without needing to know where a
body is on screen, which is the one thing a headless test cannot see.
It also stubs a successful `/file` response and pins the post-match display of
a replay-derived extraction with its filed match id and command index.

The seam suite is the only test where both surfaces are alive at once. It
tolerates an unreachable witness (`UNCERTIFIED` is an honest outcome and
the room says so out loud) and fails on `STRUCK` — the edge replaying the
record and disagreeing means the match does not reproduce.

It also owns the run layer's end-to-end claim, because this is the only
place a card can actually be *earned*: the returned card is banked, the
run survives a reload, `Shift`+`N` closes and archives it, and a stored
run from an unreadable schema is set aside rather than rendered. What it
asserts on is `dataset.run` — the panel's own numbers, not storage read
back — so what passes is what a player would see.

This page posts the **aftermath** home beside the outcome (`ledger`:
walked / finished / lost, and `down`: the names of your dead). Those
counts are read off the same final board the post-match ledger line is
drawn from, so the number on screen and the number the world banks cannot
diverge — and the witness certificate carries the same three, so the room
strikes a card whose aftermath the edge disagrees with.

It also posts the rules core's local `derivedEvents` array. That array is
useful for the yard's immediate aftermath but is not retained by the run when
no Witness can answer or the archive cannot store the card. Claim grade waits
for an append-only local event target; the rolling recent-card buffer cannot
back it. The local array is not the authority on a certified card. **FILE THE
RECORD** calls `/file`, and after filing the post-match card replaces the local
display with the Worker's own replay-authored array, rendering every event
beside its durable `(match id, command index)` address.

The deadline suite covers the case that tolerance was hiding. A witness
that *refuses* has always landed in `certifySeam`'s catch and been
labelled; a witness that *accepts and never answers* used to leave the
ledger at `ASKING THE EDGE…` forever, with no abort and nothing said —
the room guarded a dead yard behind the door and not a dead edge in front
of it. The request is intercepted and left hanging, so only the room's own
`WITNESS_MS` can settle the session. Reverting that deadline fails four of
its checks and pins the panel at `settling…` for the full test timeout.

## Notable renderer decisions

- **Floor is one `InstancedMesh`.** 100 tiles, one draw call. The movement
  range, hover highlight and cover callout are all per-instance colours, so
  no geometry is created or destroyed as state changes.
- **Picking is units-first, then the floor.** Unit bodies resolve to their
  own tile — at 30° elevation a body projects above its tile, so floor-only
  picking would send a click on a visible chest to the tile behind it.
  Everything else falls to the floor `InstancedMesh`, whose `instanceId`
  *is* the tile index — no screen-to-grid maths, and a click on a wall
  still resolves to the tile beneath it, matching 2D behaviour. Down
  operatives remain pickable for DRAG; hostile corpses remain scenery.
- **`draw()` kept its name.** Every call site from the 2D version still calls
  `draw()`; it now just sets a dirty flag that the frame loop reconciles.
  That is the immediate-mode → retained-mode shift, isolated to one function.
- **Units are the walkable world's bodies.** Since the convergence
  (2026-08-01) the board loads the same molded 96×80 pack sheets the
  walkable room does, from `assets/sprites/<fighter>/` — four facings, a
  verb per game state, frame counts read from sheet width. There is no
  fallback to the retired 32×32 grids: a missing sheet stops the page at
  an explicit fault, because a quiet substitution would put a different
  species back on the board while the room shows a pack body, which is
  the exact bug the convergence exists to kill. Facing is chosen
  camera-relative, so a quarter turn re-faces every body instead of
  pointing them the wrong way.
- **A dragged body stays in DEATH.** The rules advance its position through
  the same 70ms path steps as its actor, so the retained scene already slides
  the fallen quad. There is no carry state and no renderer-side revival.
- **Picking reads the sheet's alpha at the current frame.** Mesh
  raycasting ignores `alphaTest`, so without a mask the whole quad —
  3.30 × 2.75 world units, mostly empty — would be clickable. The mask
  is the PNG's own alpha, indexed by the frame on screen, so a body is
  clickable exactly where it is drawn *this frame*.
- **Units are vertical billboards, not camera-facing sprites.** A
  `THREE.Sprite` tilts back toward the 30°-elevated camera and reads as
  leaning cardboard; a vertical quad swiveling around Y only stays standing
  on its tile, and swivels smoothly through the eased 90° camera rotations.
  Unit shadows are grounded blobs — a flat quad's cast shadow would swing as
  the camera rotates, and the load-bearing shadows here are the terrain's.
  The occlusion ghost is the sprite itself, translucent, not a proxy shape.
- **Tracers are cylinders, not lines.** WebGL clamps line width to 1px on
  effectively every platform.
- **HP is a segmented bar, not pips.** Ten discrete pips smear into an
  unreadable dash at crunch resolution.
- **Ambient light is kept low** so shadows survive. Bright fill washes out
  the exact cue that makes cover direction readable.

## Still deliberately not here

Everything the 2D README already ruled out — no campaign, no classes, no
research tree. Plus, specific to this build: no move-path preview arc and
no camera zoom.

(Unit facing and hit/miss reaction animation used to be on that list. The
convergence took them off it — bodies face four ways and flinch, because
the molded sheets that arrived from the walkable side had the frames.)

The organ-replacement questions are still the actual point: simultaneous
turns, degrading cover, social energy as the morale system, positioning that
creates team abilities. The first one is answered — hostiles yield on morale
now, and the spare/finish call is the match's last move. It lives in the
rules core, which is why this file barely changed to get it.
