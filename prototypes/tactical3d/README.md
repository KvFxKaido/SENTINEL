# Tactical Encounter Prototype — 3D

The same encounter as `../tactical/`, rendered with three.js instead of a 2D
canvas. Same map, same rules, same seeded RNG, same replay guarantee.

**Run it:** double-click `serve.cmd`, or:

```sh
python -m http.server -d prototypes 8080
# then open http://localhost:8080/tactical3d/
```

It will not run from `file://` — see [Why it needs a server](#why-it-needs-a-server).
Append `?seed=deadbeef` to pin a specific encounter.

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
- **No sprite pipeline.** `Isometric Sprite System.md` concedes that 64×64
  four-direction walk cycles are unsustainable for a solo dev. Primitives
  rotate for free.

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
| click | select operative / move / shoot hostile |
| `Tab` | cycle to next operative with AP |
| `F` | toggle shoot mode (hit % over every hostile) |
| `Y` | overwatch (ends unit's activation) |
| `Enter` | end turn |
| `Q` / `E` | rotate camera 90° |
| `P` | toggle pixel crunch |
| `R` / `shift+R` | new encounter / replay same seed |

## Projection

45° azimuth, 30° elevation, orthographic. That is exactly the 2:1 dimetric
ratio `architecture/Isometric Sprite System.md` specifies — 30° is the angle
where a unit grid step projects to a 2:1 screen slope. Rotation snaps to 90°
so the board never sits at an off-axis angle.

`P` toggles pixel crunch: the renderer draws at 0.6× and CSS upscales it with
`image-rendering: pixelated`. That is the whole retro-crunch treatment — a
pixel look without a pixel pipeline. Off, it renders crisp.

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

## Notable renderer decisions

- **Floor is one `InstancedMesh`.** 100 tiles, one draw call. The movement
  range, hover highlight and cover callout are all per-instance colours, so
  no geometry is created or destroyed as state changes.
- **Picking raycasts the floor, not the world.** `instanceId` *is* the tile
  index, so there is no screen-to-grid maths, and a click that lands on a
  wall still resolves to the tile beneath it — matching 2D behaviour exactly.
- **`draw()` kept its name.** Every call site from the 2D version still calls
  `draw()`; it now just sets a dirty flag that the frame loop reconciles.
  That is the immediate-mode → retained-mode shift, isolated to one function.
- **Tracers are cylinders, not lines.** WebGL clamps line width to 1px on
  effectively every platform.
- **HP is a segmented bar, not pips.** Ten discrete pips smear into an
  unreadable dash at crunch resolution.
- **Ambient light is kept low** so shadows survive. Bright fill washes out
  the exact cue that makes cover direction readable.

## Still deliberately not here

Everything the 2D README already ruled out — no campaign, no classes, no
research tree. Plus, specific to this build: no unit facing, no move-path
preview arc, no camera zoom, no hit/miss reaction animation.

The organ-replacement questions are unchanged and still the actual point:
simultaneous turns, degrading cover, social energy as the morale system,
positioning that creates team abilities, hostiles who surrender.
