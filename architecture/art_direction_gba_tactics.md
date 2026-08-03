# Art Direction Reference — GBA Tactics Chrome

**Status:** Reference, v0.1 — steers future sprite and UI work; not design-binding
as a whole; decided items are marked inline with their decision date
**Source:** Super Robot Wars J (Banpresto, GBA, 2005), viewed through RetroArch's
`lcd-grid-v2` + `gba-color` shader stack
**Related:** `Isometric Sprite System.md` (sprite budgets),
`sentinel_circuit_design.md` (broadcast framing)

## Why this reference

Not nostalgia. The GBA screen was 240×160, and SRW J still puts a dozen stats,
a portrait, a mech sprite, and three tabs on it without scrolling and without
ambiguity. That is a *discipline*, and it is the same discipline as design
philosophy rule #1: shared state must be visible. The SRW stat sheet is that
rule rendered as pixels — every number in its own labeled box, nothing implied,
nothing hidden behind a hover.

The display-level half of this look (LCD cell grid + handheld color) already
ships in `prototypes/tactical3d/` as the default display mode. This document
covers the other half: what the sprites and the UI themselves should do.

## Sprite language

- **Proportions are law (decided 2026-07-28): System A** — FFT-ish, ~2.3
  heads on a 32×32 canvas, displayed 1.10 world units tall in the yard,
  feet-anchored. Chosen by audition against a squat-military alternative
  (~3.6 heads): at combat distance identity lives in the head, and the head
  needs the pixels; gear reads through silhouette, which the drape slot
  owns anyway. Display size audited at three heights — +20% won: presence
  without out-growing the 1.5-tall walls that make cover height readable.
  **The yard roster shipped on this body (2026-07-29)** —
  `prototypes/tactical3d/sprites.js`, preview at `roster.html`: VESPER
  (crested helm), KOA (topknot, headband, the one permitted body edit:
  wider pauldrons), SABLE (cowl, goggles lit inside the shadow), and one
  SYN design worn by the whole crew, because a uniform crew is how "them"
  reads. Ops share the stance and the blue chest band — the audition's
  identity-lives-in-the-head claim, now practiced.
  Reference specimen: **Cipher**, `mocks/cipher_sprites.js` (the audition
  file is the decision record — both bodies, one palette, one ground line).
- **Silhouette first.** A unit must read from its outer shape alone — at map
  scale the silhouette IS the design. Detail lives inside the outline and never
  breaks it.
- **Heavy single-pixel outline** on everything that is a *thing* (units,
  interactables). Terrain gets edges from shading, not outlines — that is how
  units pop off the board without glow effects.
- **Dithered gradients, clustered darks.** No smooth ramps; two or three shades
  per hue plus dithering. Highlights are placed (rim light on a shoulder), not
  computed.
- **One dominant hue + one accent per unit.** Faction tells at a glance. The
  world stays dark and desaturated so unit hues carry the scene — the board is
  a stage, not a competitor.
- **One canvas, integer zoom** *(decided 2026-07-30 — supersedes the earlier
  "two scales, one silhouette" bullet, which anticipated large battle
  sprites as a separate budget)*: there are no large body sprites,
  anywhere. See **The body law** below.
- **Few frames, strong poses.** Impact frames and smears over interpolation.
  Twelve good frames beat sixty tweened ones, and are achievable solo.
- **Portraits** *(superseded 2026-07-29 by the register pair —
  `art_style_audit.md`: photoreal source graded into the feed and terminal
  registers, never quantized cel; kept here for the paper trail)*:
  painted-then-quantized, hard cel shading, outlined, expressive at ~48px
  box.

## The body law: one canvas, integer zoom (decided 2026-07-30)

Pixel art travels in one direction: **up**. Integer upscaling is lossless;
downscaling deletes decisions — and at 32×32 every pixel is one. So the
universe keeps a single body register, authored at the floor, consumed
everywhere:

- **One canvas.** 32×32, System A proportions, feet on the ground line —
  the same body on every surface that shows one: the tactical board, the
  walkable world, Close Contact's stage, and whatever comes after them.
  This formally supersedes `Isometric Sprite System.md` (48×48), now
  marked Historical.
- **Authored once, never resampled into being.** No asset is ever
  created by scaling another — 32×32 is the only authored form. On
  **flat surfaces** (Close Contact's stage, UI, cards, thumbnails) the
  canvas displays at integer magnification only — 1×, 2×, 3×, 4× —
  never fractional; the roster preview's 3× thumbnails are the pattern,
  the fighter at ~4× the plan. **World surfaces** (the board, the
  diorama) consume the same texture through a projective camera with
  nearest filtering, and the LCD pass quantizes everything to one texel
  grid — a camera is not a resample, and the board's ~21-target-pixel
  sprite is legal because nobody *authored* it. (Caught in review: the
  first draft claimed "integer zoom everywhere," which the shipped
  board already violated. The law is about authoring, and always was.)
- **Frames, never formats.** Surfaces add frame *sets* to the same canvas:
  the board has idle and kneel; the world adds directional walks; the
  fighter adds stances, limb commitments, and hitstun. Same palette, same
  outline rules, same ground-line contract, one `validate()` guarding all
  of it. A character is never re-rendered — only re-consumed.
- **The density agreement is the teeth — stated correctly.** Matter is
  authored at 1.10/16 world units per pixel (terrain voxels); bodies at
  1.10/32 — body pixels are exactly **twice as fine** as matter, a fixed
  2:1 ratio, because identity needs pixels and walls don't. (Caught in
  review: the first draft claimed one shared density, and the shipped
  constants refute it — 1.10/16 was never the sprite density. The
  arithmetic is now computed, not narrated.) The ratio is the coupling:
  renegotiate the canvas and either the 2:1 breaks visibly or the world
  re-extrudes. That bill is what makes this law instead of habit.
- **Faces are exempt, deliberately.** Close-up identity belongs to the
  portrait register pair (`art_style_audit.md`, 2026-07-29). Bodies never
  grow toward faces, and detail never smuggles downward between scales —
  the fighter's frame set may be large, but its pixels are never finer.

Costs, accepted on the record: Close Contact forgoes high-detail
animation — **a cost this law imposes and owns**. Its spec does not
mandate the cap (caught in review: the first draft pinned it on the
spec's non-goals, which actually renounce rosters, balance, cinematic
story, and netplay — not animation detail); the spec is merely
*compatible* with it, wanting readability-first animation and
hitstop-over-VFX impact. Hitboxes-from-art stay coarse (a game of three
rigid heights says that is the game). If a future surface truly cannot
live on the 32 canvas, this section gets a successor — by a PR that
says so, with the world-density bill attached.

### Successor: the body canvas is the pack's (walk-off verdict, 2026-07-31)

The escape hatch above was used the honest way: staged, not argued.
`prototypes/walkable/walkoff.html` fielded both bodies in COURT 01 on
one input — BODY A the 96×80 pack-mold Cipher, BODY B a 32×32 System A
Cipher that learned to walk for the audition
(`scripts/cipher32_walk.py`, pokered stand/step gait, its down face
being CIPHER_A rows 5–22 verbatim). Same room, same camera, same LCD
pass, same light. The designer walked both and called it: **the pack
body wins.** That closes both auditions the walkable room carried —
pack-format-vs-body-law, and selout-vs-ink with it, since the winning
body wears the selout dialect.

What changes:

- **The authored body canvas is the pack's 96×80 (~34px body), selout
  dialect.** The walkable Cipher lifts from provisional to canon. New
  body verbs (aim, fire, kneel, down — the yard's bill) are authored in
  this dialect by the deterministic-pass pipeline that minted the
  roster.
- **32×32 System A becomes the yard's legacy register.** The shipped
  board sprites stay until pack bodies grow the yard's poses; then the
  yard converges — one body per character across the seam, no second
  species at the door. The System A identity kits are not lost: the
  roster mold proved they translate deterministically (helm, topknot,
  cowl, lenses, dreads-and-band) onto the pack body.
- **The walk-off body stays on the record** as the decision's evidence:
  strips regenerate from `scripts/cipher32_walk.py`, the stage is
  `walkoff.html`, and this paragraph is why neither gets deleted.

What survives unchanged — the law's spine was never the number 32:

- **Authored once, never resampled.** The pack canvas is now the only
  authored body form; integer zoom on flat surfaces, projective camera
  + nearest filtering + LCD quantizer on world surfaces.
- **Frames, never formats.** The full pack's nine verbs (idle / walk /
  run / dash / two attacks / hurt / death / heal) are the frame set the
  pack shipped; aim / fire / kneel were synthesized onto the same canvas
  on 2026-08-01 (see "The yard's bill, paid" below), which is this rule
  working rather than an exception to it — every new verb joins the
  canvas, whoever authored it.
- **The 2:1 density agreement.** Bodies at 1.10/32 world per pixel,
  matter at 1.10/16. The pack body already obeyed it — that obedience
  is much of why it won under the same glass — so the coupling holds
  with no re-extrusion bill.
- **Faces are exempt.** The portrait register pair is untouched.

Cost accepted with the verdict: the ~2.3-head System A proportion pick
(2026-07-28) now governs only the legacy yard register; the world body
runs the pack's ~3.4 heads. Close Contact consumes the pack canvas
under the same integer-zoom rule when it grows sprites.

### The yard's bill, paid: aim / fire / kneel (decided 2026-08-01)

The successor above promised these three would be "authored in this
dialect by the deterministic-pass pipeline that minted the roster." They
are — `scripts/roster_mold.py` pass 3, twelve sheets a fighter, sixty
across the squad. The decisions worth keeping:

- **Synthesized verbs are ordinary sheets.** They are built as
  pack-palette *source* frames and then run through the same
  `build_frame` as every molded sheet. No consumer knows the difference,
  and none should: a verb the pack shipped and a verb we authored have
  to be the same kind of thing, or the canvas grows two classes of
  citizen and the law starts needing exceptions.
- **The mark-colour law was reused, not reimplemented.** The emitter's
  charge cell and muzzle bloom are drawn in the pack's *heal greens*,
  which the mold already swaps to each fighter's mark colour. Cipher's
  emitter vents cyan and SYN's vents red because of a rule written for
  something else entirely. A feature that needs no new law is evidence
  the old law was cut along the grain.
- **Aiming shows cold steel; only the shot lights.** The housing is
  drawn in the pack's steels, and the emitter's own cells are sheathed
  **by name** after the mold. The first cut left that to the blade pass,
  which finds blades in art it did not author by shape — and skips
  components under six pixels. The side emitter's housing happened to
  clear that gate; the down and up emitters (3px and 2px runs) did not,
  so the two facings that matter most shipped a *lit* barrel while the
  panel read `EMITTER COLD` (caught in review; measured before believed).
  Authored geometry should not be rediscovered by a classifier — and a
  rule that holds only because one case got lucky was never holding.
- **The poses are lifted, not invented.** Aim is the HEAL draw with the
  vial replaced, so the grip is still the pack artist's hand. Where the
  pack could not answer — a body turned away has no vial to convert
  (measured: `heal_up` frames 0–4 contain zero green) — the licensed
  thug pack did: the arm is the pose, the flash is the verb, and a shot
  fired away from the camera shows no weapon at all, only a bloom past
  the head. That is a reference pack earning its keep as *reference*,
  which is what the rejected gba-ify experiment (2026-07-31) bought us:
  body **language** cannot be LUT'd, but body **grammar** can be read.
- **Kneel is row surgery, and the hem is what sells it.** Torso rows are
  copied down, the boots never move (the ground contract is why), and
  the shin rows a crouch would hide are the ones dropped. Copying rows
  is not scaling, so "authored once, never resampled" holds. The first
  cut dropped four rows and read as a *shorter man*: on a body in a long
  coat, folding the legs edits something the coat already hides. Flaring
  the hem one pixel is the crouch; the height loss alone was not.

**Scale is measured, not eyeballed.** Counting mark-colour pixels per
frame, the shipped verbs run blade ignition 706 at peak and heal channel
38. The first muzzle bloom peaked at **21** — dimmer than a heal, which
on a ~34px body drawn ~28px tall is a flicker, not a gunshot. It looked
correct on a 6× contact sheet, which is exactly the trap: zoom flatters
everything. Resized against those numbers it peaks at 37, and the reach
was bought with spikes rather than area, because at this scale extent
carries further than mass. The rule this hands forward: **an effect's
readability is a number you can compute, and a zoomed contact sheet is
not that number.** The recipe is in `prototypes/walkable/README.md`.

### The yard converged (2026-08-01)

The successor's last clause — *"then the yard converges — one body per
character across the seam, no second species at the door"* — is now true.
`prototypes/tactical3d/` loads the same molded sheets the walkable room
does. One body crosses the door.

What the convergence cost and settled:

- **Facing is renderer-owned, and camera-relative.** The board never had
  unit facing; it had a horizontal mirror on movement. Bodies now pick one
  of four sheets from a world vector resolved against the camera, so a
  quarter turn re-faces them. Resolving it off world axes instead is the
  precise bug the mirror once shipped, and it is now the load-bearing
  assertion in `test_yard_bodies.mjs` — four quarter turns must produce
  four *distinct* facing sets. Two weaker versions of that check pass on
  the broken renderer, which is how the original survived review.
- **No fallback to the legacy register.** A missing sheet stops the yard
  at an explicit fault. A quiet substitution would put a 32×32 body on the
  board while the room shows a pack body — the two-species bug this work
  exists to kill, wearing a helpful face. `sprites.js` survives as the
  legacy register the walk-off named; nothing imports it any more.
- **The seam is now tested, not asserted.** Both surfaces alive at once,
  the door walked, the card played, the record read back. It fails on a
  DISPUTED verdict and tolerates an unreachable witness, because one of
  those is a bug and the other is weather.
- **Cost accepted:** bodies stand ~1.169 world units against the 1.5-tall
  walls that carry the cover read — 6% taller than the 32×32 register they
  replaced. Measured against the walls, cover still reads. The badge and
  overwatch ring moved up to clear them.

The legacy register is now unused rather than deleted. Retiring
`sprites.js` is a separate decision with its own paper trail; leaving a
dead file named in this document is worse than either, so whichever way it
goes, this paragraph goes with it.

### Cipher ships composed: the three-body walk-off (verdict, 2026-08-02)

COURT 01 staged again, three bodies on one input this time. BODY A, the
pack-mold Cipher — the canon body form, unchanged by anything here. BODY
C, the composed hybrid: pack frames, generated head, no sword
(`scripts/compose_body.py`). BODY B, the whole-generated PixelLab render
— the locked D1 appearance wearing mocap-template walks and a breathing
idle on its own 64×64 canvas (input record
`scripts/pixellab_walkoff_render.json`, molded by
`scripts/walkoff_render_sheets.py`). System A stood in B's slot before;
its 2026-07-31 verdict stands and its evidence stays regenerable.

The staging was made fair before anyone called it: B re-pointed to the
same locked head as C so identity stopped being a confound, side facings
molded from the 3/4 rotations because the pack's side sheets are 3/4
views, and a breathing idle added so B was not judged as a statue.

The verdict, called by walking (designer, Codex concurring): **Cipher
ships composed. C is canon.** A remains the animation and legibility
reference. B is a pipeline experiment — retained, instrumented, not
discarded.

The grounds are economic, which is what makes the designation stable
rather than a taste call to relitigate after the next model update: C's
costs amortize (one generated head per character, one item pass per
roster, because every character shares the pack body), while B's are
per-character-per-outfit-per-roll and nothing composes after the fact.
The audition agreed with the ledger — B's losses at game scale (a 46–48
baseline wobble across one cycle, one-pixel costume chatter, frame-to-
frame identity flicker) are each individually improvable, and were not
the reason to decide.

Costs accepted on the record:

- **Composed Cipher carries no sword.** The pack's attack verbs swing
  one. Whether a bladeless body may swing a blade is a design decision
  deferred until compose grows past idle/walk — flagged where the next
  author will trip over it (`compose_body.py::_back_sheathed`).
- **B's route lands 2px short of the pack's 34px body** — generation
  size steps by 4 and nothing lands 34. A property of the route, not a
  defect; it exists only where the two stand side by side.
- **The walk-off stays on the record as evidence**, same clause as its
  predecessor: `walkoff.html` is the stage, the input records and
  molders regenerate the bodies, and this paragraph is why none of it
  gets deleted.

## UI language

- **Every datum is a cell**: label plate + value box, adjacent, both boxed.
  Never a floating number.
- **Bevel emboss**: 1px light edge top-left, 1px dark edge bottom-right, on
  dark panels. Depth without gradients or shadows.
- **Tabs are physical.** Paged sheets with visible tab headers and arrow
  affordances ("Weapon Stats ▸ Pilot Stats ▸ Unit Stats"). Pagination the
  player can see and count, not an ellipsis menu.
- **Hex watermark backdrop.** A quiet honeycomb pattern on panel backgrounds —
  texture that reads "hardware" without adding noise. Low contrast, never
  behind body text.
- **Chunky outlined bitmap font.** White glyphs, dark outline/shadow — survives
  any background including the battle scene behind it.
- **Segmented bars, color-coded meaning.** HP green, resource yellow, morale
  amber (already in the prototypes); ticks every unit so exact values survive
  low resolution.
- **A portrait anchors every sheet.** The human face next to the machine
  numbers is what makes a stat sheet a *character* sheet. For the Circuit this
  is also where the insignia slot lives — claim next to face, exactly where a
  SRW pilot's affiliation sits.
- **Density is respect.** If a sheet needs scrolling at prototype resolution,
  the sheet is wrong, not the resolution.

## The view: 2.5D

**Decided (2026-07-28):** the tactical view's target is 2.5D — 2D sprites that
always face the camera, standing in simple 3D environments. This is the
Final Fantasy Tactics / Tactics Ogre chassis and its HD-2D revival
(Octopath, Triangle Strategy), and it is the only version of this that is
sustainable solo: characters get hand-authored sprite craft, environments
stay primitive geometry forever.

Why it fits this project specifically:

- **Everything the 3D port bought survives.** Rotate-to-read-cover, real
  terrain occlusion, walls casting the shadows that make directional cover
  legible — all environment, all still 3D. Billboarding removes only the part
  3D was worst at: characters with identity.
- **The sprite language above applies unmodified.** Silhouette-first outlined
  sprites are 2D craft; billboards let that craft stand inside the yard.
- **The LCD display mode is the unifier.** 2.5D's classic failure is crisp
  geometry clashing with chunky sprites; the post pass quantizes both to the
  same texel grid. HD-2D needs bloom and depth-of-field for this; a 350×222
  render target does it for free.

Implementation rules:

- **Y-axis billboarding, never full camera-facing.** A sprite that tilts back
  toward an elevated camera reads as leaning cardboard. Vertical quad, feet
  anchored to the tile, swivels around Y only. During eased camera rotation
  the swivel is continuous — a free moment where 2.5D looks better than
  either parent.
- **One facing + horizontal flip** until facing exists as a *rule*. Art never
  leads mechanics.
- **Blob shadows for units, real shadows for terrain.** A flat quad's cast
  shadow rotates with the camera; the load-bearing shadows are terrain's.
- **Occlusion ghost is the sprite itself,** translucent, not a proxy shape.
- **Poses are frames.** Yield, down, fire — each is a sprite frame when it
  earns one ("few frames, strong poses"); until then, tint and badges carry
  state. *The first one is earned (2026-07-29): the SYN kneel — hands up,
  two-thirds height, same ground line — swaps in with its own picking mask
  when a fighter yields. Down and fire still read through state.*

Open consequence: once `tactical3d/` wears the same authored sprites as
`tactical/`, the two renderers converge visually and the 2D build's
keep-earning clause (prototypes/README) comes due. Current lean: keep it —
cheapest determinism cross-check, and the immediate-mode teaching contrast —
but the question is now live.

### World staging (added 2026-07-29)

Second reference joins the file: the Pokémon Blue/Red recompilation's 3D
renderer — Shawn's stated image of the finished product. The two references
partition cleanly: **SRW J is the information language** (how the game talks
— sheets, cells, density), **the recomp is the world language** (how the
game is staged — a place you stand in). Phosphor over both makes them one
thing: a tactical broadcast you walk around inside. What it adds, all
shipped in `tactical3d/` the day it was decided:

- **Voxel-extruded tile art.** Cover is neither billboard nor model: 2D
  pixel art with every pixel extruded into a depth-spanning box. Front and
  back show the art; author a deliberate cap row (the lid), darker edge
  columns (the flanks), and full-width groove rows that read from every
  side. Seam pixels extrude shallower, so grooves catch the light for real.
- **One pixel density for all matter.** Terrain voxels are authored at
  1.10 world / 16 px; bodies at 1.10 / 32 — a fixed 2:1 ratio, matter
  coarse and bodies fine. *(Corrected 2026-07-30: this bullet originally
  called 1.10/16 "the sprite density," which the sprite constants
  refute — see the body law's density clause.)* One family of stuff, one
  deliberate ratio; nothing reads as belonging to a different game.
- **Diorama-in-void staging.** The yard is a lit stage on black — nothing
  outside the broadcast exists. (The LCD pass lifts the void to a faint
  panel glow; that is the handheld being honest about its panel, not a
  leak.)
- **The deck is a multiplier texture.** Floor plates are near-white detail
  multiplied under the per-instance tile colours, so the overlay hues
  (range, hover, covering) stay exact — worn, not repainted.

Scope note: the recomp screenshots show the *whole game* staged this way —
town, interiors, conversation. That is the destination (overworld and
campaign surfaces included), not just the yard's costume.

## The palette (decided: phosphor)

**Decided (2026-07-28):** green-phosphor terminal, everywhere. Settled by the
side-by-side in `mocks/fighter_sheet.html` — kept as the record of the
decision: same markup, two skins. The chrome sheet reads as a broadcast
graphic; the phosphor sheet reads as intel on your own rig — and SENTINEL is
played from your side of the glass. It just feels tactical.

The fiction squares itself: the feed exists, but the player is the fighter,
not the audience. Whatever the network airs, you see it re-encoded through
your own equipment. The broadcast is a register of *content* — fight cards,
tale of the tape, odds, the Witness certification line — never a palette.

The structural grammar above survives whole: beveled labeled cells, physical
tabs, hex watermark (phosphor tint, low contrast), outlined type, density as
respect. SRW J's structure wearing SENTINEL's color.

## Concrete next uses

- **Done (2026-07-30): Cipher's walkable body.** A licensed 4-direction
  pack (idle/run/two attacks, 8 frames each) molded into Cipher by a
  deterministic pipeline — `scripts/cipher_mold.py` (since promoted to
  `scripts/roster_mold.py`, 2026-07-31: one mold, five fighters,
  mark-color ignition and heal): 24-color
  hand-mapped LUT, columnar dread pass, solid visor band (nothing may
  read as an eye from any facing), and the energy blade — dormant dark
  steel sheathed, ignited to the visor's cyan family in attack frames,
  so the only lights on the body are his own tech and ignition itself
  is a readable event. Outputs (`assets/sprites/cipher/`) are
  regenerable and untracked; the source pack stays out of the public
  repo by license. **Status: canon body (walk-off verdict, 2026-07-31)**
  — both auditions this body carried (selout-vs-ink,
  pack-format-vs-body-law) were decided by the staged walk-off; see the
  body law's successor section. The full pack adds five more verbs
  (walk / dash / hurt / death / heal), molded by the same pipeline —
  **wired into the walkable room 2026-08-01**: hold-Shift walk, a dash
  that displaces through the same collision and door machinery as
  walking, a heal channel (cyan spill only — the effect is authored in
  the sheet), a hurt flinch, and a death that holds its last frame until
  a move key rises. The roster is stated on the panel (CANON / FULL vs
  CANON / CORE), a partial mold faults explicitly, and a lost card at
  the seam plays the hurt flinch on re-entry.

- Fight card / fighter sheet mock for the Circuit: tabs FIGHTER / LOADOUT /
  RECORD, portrait + insignia slot top-left, every stat in a beveled cell.
- ~~`/portrait` prompt guidance updated to the quantized cel style
  above~~ — overtaken (2026-07-29): the register pair decided otherwise,
  and the skill now grades photoreal sources into feed/terminal
  registers (the mandatory grading step in `.claude/skills/portrait/`).
- 2D renderer sprite pass: rework the 16×16 authored sprites toward
  silhouette-first with single-pixel outlines (they are close already).
- Panel CSS pass (hex watermark, beveled cells) once the palette fork is
  decided.
