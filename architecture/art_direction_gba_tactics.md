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
- **Two scales, one silhouette.** Map sprites (small, ~48px per the sprite doc)
  and sheet/battle sprites (large, detailed) are the same silhouette at
  different budgets. If the big one doesn't shrink into the small one, the big
  one is wrong.
- **Few frames, strong poses.** Impact frames and smears over interpolation.
  Twelve good frames beat sixty tweened ones, and are achievable solo.
- **Portraits:** painted-then-quantized, hard cel shading, outlined, expressive
  at ~48px box. This is the target style for `/portrait` generation prompts:
  "GBA-era tactical RPG portrait, hard cel shading, 1px outline, limited
  palette, quantized" — not painterly, not anime-gloss.

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
  state.

Open consequence: once `tactical3d/` wears the same authored sprites as
`tactical/`, the two renderers converge visually and the 2D build's
keep-earning clause (prototypes/README) comes due. Current lean: keep it —
cheapest determinism cross-check, and the immediate-mode teaching contrast —
but the question is now live.

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

- Fight card / fighter sheet mock for the Circuit: tabs FIGHTER / LOADOUT /
  RECORD, portrait + insignia slot top-left, every stat in a beveled cell.
- `/portrait` prompt guidance updated to the quantized cel style above.
- 2D renderer sprite pass: rework the 16×16 authored sprites toward
  silhouette-first with single-pixel outlines (they are close already).
- Panel CSS pass (hex watermark, beveled cells) once the palette fork is
  decided.
