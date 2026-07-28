# Art Direction Reference — GBA Tactics Chrome

**Status:** reference, v0.1 — steers future sprite and UI work; not design-binding
**Source:** Super Robot Wars J (Banpresto, GBA, 2005), viewed through RetroArch's
`lcd-grid-v2` + `gba-color` shader stack
**Related:** `Isometric Sprite System.md` (sprite budgets), `sentinel_warp_vision.md`
(current terminal identity), `sentinel_circuit_design.md` (broadcast framing)

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

## The palette fork (open — designer's call)

Current identity is green-phosphor terminal (`sentinel_warp_vision.md`). SRW J
is navy cockpit chrome. Options:

1. **Diegetic split (leaning):** the Circuit's broadcast overlay — fight cards,
   fighter sheets, the tactical layer — wears navy chrome with beveled cells
   and hex watermark, because in-fiction it *is* a different device: the feed,
   not your rig. Comms, campaign, and log surfaces keep green phosphor. Two
   devices, two skins, no muddle.
2. **Full switch** to chrome — cleanest, but abandons an identity the vision
   doc argues for.
3. **Structure only** — adopt the cells/tabs/density/bevels grammar but keep
   the phosphor palette everywhere.

Whichever way this lands, the *structural* language above (cells, tabs,
outlines, density) applies unchanged.

## Concrete next uses

- Fight card / fighter sheet mock for the Circuit: tabs FIGHTER / LOADOUT /
  RECORD, portrait + insignia slot top-left, every stat in a beveled cell.
- `/portrait` prompt guidance updated to the quantized cel style above.
- 2D renderer sprite pass: rework the 16×16 authored sprites toward
  silhouette-first with single-pixel outlines (they are close already).
- Panel CSS pass (hex watermark, beveled cells) once the palette fork is
  decided.
