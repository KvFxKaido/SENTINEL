# Art Style Audit — Cyberpunk Meets Dune

**Status:** Reference, v0.1 — audits every art surface against the stated
vibe. The portrait register fork is **decided** (2026-07-29, by audition:
`mocks/portrait_audition.html`) — see "The portrait finding"
**Date:** July 29, 2026
**Related:** `art_direction_gba_tactics.md` (sprite/UI/world law — this doc
audits, that doc legislates), `sentinel_circuit_design.md` (the institution
being staged), memory: the pokered-recomp product vision

## The vibe, named

Shawn's target: **Cyberpunk meets Dune.** The audit's first finding is that
this is not a pivot — it is the name of what the stack has been converging
on piecemeal. Split the vibe into its halves and look at where each lives:

- **Dune is the world.** Scarcity, dust, rust, feudal factions with mottos
  and oaths, and combat as *ritualized institution*. The Circuit's
  yield/spare/finish is structurally a Dune duel: mercy as public ritual,
  meaning carried by what is witnessed. The eleven factions read as houses.
- **Cyberpunk is the layer over the world.** The feed, the rating meter,
  blood as content, purse economics, neon as attention. Enhancement
  leverage, Nexus surveillance, the Witness record itself.

The art rules already implement this split without having named it: the
yard is desaturated olive/dust/rust **matter** (the SYN crew palette is
practically Arrakis), while the only saturated, glowing things on screen
are the **overlays and UI — the broadcast**. World = Dune; everything that
glows = cyberpunk.

The intersection has a name: **cassette futurism** — analog instruments
wrapping high stakes. Dune's no-computers austerity and cyberpunk's CRT
terminals meet in the LCD display mode, the phosphor sheet, the synth
beeps. That intersection is the register this project already speaks.

## The axes, in decidable terms

1. **Palette:** desaturated matter; saturation is reserved for the
   actionable and the broadcast (standing law). Phosphor green is the
   terminal's voice; amber is the warning/mercy voice (morale, overwatch,
   the yield decision). Knob per surface: how far toward amber/dust a
   surface may warm before the terminal identity blurs.
2. **Material language:** dust, rust, canvas, bone for the world; brass,
   CRT glass, phosphor for instruments; neon only where the feed is
   speaking (rating, range overlays, accents).
3. **Tech texture:** cassette futurism. Bezels, seams, scanlines, grain.
   No glossy holograms, no clean sci-fi chrome.
4. **Figure language:** decided and shipped — System A sprites, identity
   in the head, gear through silhouette, poses are frames.
5. **Registers are diegetic sources, not palettes** (fighter-sheet law):
   *the rig you own* (phosphor terminal) vs *the feed they watch*
   (broadcast). A surface must know which device is showing it.
6. **Institution vs street:** the Circuit is ritual (Dune); the yard grime
   is street (cyberpunk). This is a *writing and framing* knob as much as
   an art one — it lands hardest in match framing (roadmap step 3).

## Surface-by-surface

| Surface | Language today | Verdict |
|---|---|---|
| `tactical3d/` sprites (roster, kneel) | System A pixel, phosphor families | **Fits** — the audition-derived law working as intended |
| `tactical3d/` terrain + staging | voxel-extruded dust/olive/rust, diorama-in-void | **Fits** — this is the Dune half of the split, shipped |
| LCD / crunch / clean display modes | GBA cell grid, handheld color | **Fits** — cassette futurism's home appliance |
| UI (fighter sheet, panels, comms log) | SRW J grammar, phosphor (decided over chrome) | **Fits** — density-as-respect reads as institutional bureaucracy, which is Dune wearing a terminal |
| Prototype audio (synth beeps) | square/saw chiptune, no assets | **Fits** the register; shallow — sound roadmap doc not audited in depth here |
| 2D `tactical/` renderer | its own 16px idiom | **Exempt** — dev harness under the keep-earning clause; not a product surface |
| TUI / `sentinel-agent` | terminal text | **Exempt** — dev harness (platform direction: TS brain, TUI = harness) |
| **Portraits** | **three languages at once** | **Fights** — the one real casualty; see below |

## The portrait finding

The corpus contains three rendering languages simultaneously:

- `assets/portraits/npcs/*` (early batches): **painterly** digital
  illustration — e.g. Cipher, stylized cyberpunk portrait art.
- `sentinel-ui/.../axiom.png` (current agy pipeline): **full photoreal** —
  photograph-grade output, because that is where the generator is
  strongest. A tool-shaped decision, not a taste-shaped one, and the
  portrait skill's own style note admits it ("photoreal default").
- The yard: **pixel**, System A.

Two further content findings: every portrait background is a *neon alley*
— the corpus is pure cyberpunk with no Dune in it (no dust, no austerity,
no institution); and the portraits have no diegetic register — nothing in
the frame says what device or camera produced the image, which violates
axis 5.

This is about to become product-visible: the pre-match card (roadmap step
3) puts a portrait inside a phosphor sheet next to a 32px sprite. Raw
photoreal there reads as three different games sharing a screen.

**The candidate resolution — treatment, not replacement.** Keep photoreal
*source* (the tool's strength) and give it a diegetic register in
post-processing: the portrait as what a camera or terminal in the world
actually produced. Auditioned in `mocks/portrait_audition.html`, same
source image, five treatments:

- **Raw** — control; the current pipeline output.
- **Feed still** — broadcast camera grade: desaturated, split-toned,
  grained, scanlined. "The feed they watch." Keeps color and likeness.
- **Terminal phosphor** — duotone phosphor ramp, posterized, texel-scaled.
  "The rig you own": an ID record on your own instrument.
- **Terminal amber** — same pipeline, amber ramp. The Dune-warm variant.
- **Pixel quantize** — approximates the cost/look of committing to
  hand-pixel portraits (SRW J's own answer; a large ongoing art cost at
  portrait fidelity).

Note the treatments are not mutually exclusive: registers are diegetic, so
*the same source portrait* can legitimately appear as a feed still on the
match card and as a phosphor record on the fighter sheet. The decision is
which register(s) exist, not which single filter wins. What should NOT
survive the audit is untreated photoreal presented as an in-world surface,
and the accumulation of a third full rendering language (painted) without
a diegetic story.

**Decision (Shawn, 2026-07-29): the register pair.**

- **Feed still** on broadcast surfaces: the pre-match card, the feed,
  anything the crowd sees.
- **Terminal** on owned surfaces: the fighter sheet, roster records,
  anything your rig renders — **phosphor** as the default mood, **amber**
  as the second mood (opposition records, archives; exact assignment
  tunable in use).
- Photoreal is **source only** — the generator's strength, never presented
  untreated in-world.
- **No third rendering language**: hand-pixel portraits are declined (the
  quantize card made the cost argument), and the painterly batch is
  archive, not product.

## Follow-ups once the portrait register is decided

- Portrait skill grows a mandatory treatment step (generation stays agy;
  the grade is deterministic post-processing — scriptable, no model in the
  loop).
- Prompt guidance shifts backgrounds from default neon-alley toward the
  world's actual places (yard, sanctuary, market — dust and instrument
  light), so the Dune half exists in portraits at all.
- Fighter sheet and pre-match card consume the treated register(s).
- Existing corpus (painterly batch, raw axiom) either regenerates through
  the pipeline or is grandfathered as archive — not presented in-world
  untreated.
