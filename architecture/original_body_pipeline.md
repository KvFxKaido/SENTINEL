# SENTINEL: The Original Body — Roto as Choreographer

**Status: Current (2026-08-09)** — the migration off the licensed
Adventurer pack, binding until superseded. Drafted 2026-08-08 as a
Proposal from a Codex consult and the rig work landed in PR #97; its
own gate — the IDLE/WALK/KNEEL slice at 1× — was walked and passed on
2026-08-09, which is what flipped this line. Supersedes the
hybrid-canon decision of PR #91 **as direction**: the original body is
the destination. The hybrid remains the room's shipping roster until
the original roster covers its verbs — direction canon changed, the
staging default did not, and flipping the default early would stage a
roster that does not exist yet.

---

## Why this exists, and why now

The forcing function is not aesthetic. PR #89 untracked the licensed
pack because **it must never have been committed** — this repo ships
under CC BY-NC and the pack's license does not follow it. Every verb the
game consumes today is row-surgered from pack pixels, which means the
shipping art path runs through an asset we cannot ship. Getting off the
pack is legal hygiene with an art dividend, not the reverse. That is why
this migration should be *scheduled*, not aspirational.

The enabling fact is PR #97: the roto rig now holds a pose, validates it
geometrically (19 checks, CI-enforced via `roto-rig.yml`), and renders
it at canon scale with a recorded ground anchor. The rig is good at
*where things are* and useless at *what things look like*. This plan
uses it for exactly that.

## The pipeline, current and target

```
CURRENT
licensed pack → roster_mold → compose identity → pack sheets → game

TARGET
roto pose guides + original approved body
                ↓
       polished master strips
                ↓
semantic compositor → pack-shaped sheets → unchanged game
```

The game keeps consuming ordinary 96×80 PNG sheets. Blender stays an
offline authoring tool and never becomes a runtime dependency.

## Decisions proposed

Numbered so PRs can cite them.

**D1 — One shared master body, not five characters.** A neutral body
whose silhouette, coat, proportions and palette dialect get approved in
four idle facings. The seed is the LOCKED Cipher appearance — the
D1_darker roll recorded in `pixellab_cipher.json`, whose eight
rotations live at `assets/original/cipher/*.png` — and `cipher_render`
(64×64) is its proof in motion: that appearance wearing the template
walk and breathing idle. No canon-scale whole-generated body exists
yet; an earlier draft of this section claimed one did, having
misidentified the walkoff's HYBRID sheets (composed — pack frames under
a generated head, which is why they pass the body law: their body rows
ARE pack rows). D1's first concrete task is therefore the archive's
standing open question: regenerate idle + walk at 96×80 and learn
whether template mode holds at body-law scale (every proof so far ran
at 64–68px). Generate at scale or reject — D4 forbids resampling
`cipher_render` into compliance. If automated candidates stay uneven,
commission cleanup of this ONE reusable body, not a roster.

**Audition verdict (2026-08-08, designer, three-body walkoff in
motion):** the whole-generated render reads as fitting the room BETTER
than the pack body and the hybrid. PR #91's hybrid verdict was
economic, with motion quality the open worry; the motion worry is now
resolved in generation's favor, which upgrades this migration from
license-driven necessity to license-driven necessity the designer
prefers on sight.

Original art is TRACKED at `assets/original/` — carved out of the
`assets/sprites/` ignore. The boundary is licensing, drawn at the
directory: rotations, as-generated walk frames, .aseprite hand-work
and the `cipher_render` sheets are OURS and tracked (curated rolls and
hand edits do not rebuild; the render sheets technically re-download
while PixelLab's CDN holds them, and a CDN is not provenance).
COMPOSED sheets are not ours — pack frames under a generated head are
a pack derivative — and live with every other derivative in ignored
territory (`assets/sprites/hybrid/`). The first cut of this carve-out
vaulted the composed sheets as if they were generation output; the
walkoff's own slot comments caught it. Third-party packs are
quarantined under `assets/packs/`, ignored wholesale.

**D2 — The rig emits choreography: pose strips, part masks, anchors.**
The rig's flat-shaded, colour-separated, `filter_size=0` render is
already a semantic ID map — head, torso, each limb segment owns a
palette entry, which is why the tracing aid and the part mask are the
same idea. A dedicated ID pass with pure indexed colours is ~20 lines.
Anchors split by cost. `ground_{pose}_{facing}.json` already ships.
Hand and weapon sockets are NEW rig work, not an existing byproduct —
a hanging limb's origin sits on its top face, so `fore_L`'s origin is
the ELBOW, and a socket that exports it attaches the sword to the elbow
(caught in review; the validator's knee reads only worked because a
shin's origin IS the knee — no such child exists below a forearm). The
hand is the transformed centre of the forearm's bottom face, and a
usable socket is per-frame position AND orientation in anchored sheet
coordinates, plus handedness and draw order. Open item 1 gates the
armed verbs on exactly this export.

**Material masks are explicitly NOT the rig's — and they are per-strip
deliverables, not a one-time authoring.** Skin, cloth, steel, mark
colour — the rig is boxes and does not know where the coat ends. And a
mask authored on the static idle cannot stay pixel-aligned with a
generated WALK frame, so each accepted strip ships its material masks
as part of acceptance: seeded from the idle authoring, propagated
during cleanup, corrected by hand where propagation lies. The part-ID
render assists that propagation; it cannot substitute for it. One
deliverable in the consult, two sources and N strips in fact; PRs
should not ask the rig for materials, and D9's acceptance gate
includes the masks.

This deletes detective work rather than adding pipeline: the blade
classifier exists because compose must *infer* the sword from palette
and shape. A weapon socket makes that fact a declaration, and
`test_blade_classifier.py` guards a question the new path never asks.

**D3 — Whole strips, never isolated frames.** Generation happens per
animation: approved idle seed + the complete roto pose strip, generated
or edited together. Isolated frames recreate the identity and
proportion drift already paid for five times over
(`pixellab_cipher.json` dead_ends: same-side arms, facing drift, loop
seams). The skeleton constraint from PR #91 stands.

**D4 — The body law holds.** Generate at canon scale; anchor by
translation only. A body that lands at the wrong size is rejected, not
resampled into compliance. Row 57 is where the feet live (the pack's
last opaque row; `anchor_strip.py`'s ground *line* is 58 — both
conventions stated here so no future PR relitigates the off-by-one).

**D5 — New compositor beside compose_body.py, not inside it.**
`compose_body.py` is pack archaeology and stays as the frozen legacy
path. The original-body compositor consumes explicit masks and anchors
and produces the same contract the game already speaks:

```
<fighter>/<VERB>/<verb>_<facing>.png   96×80, feet on row 57,
                                       existing verb names,
                                       frame-count discovery unchanged
```

Same contract means no renderer rewrite; `pack_strip.py` survives
untouched.

**D6 — Four facings, pinned.** The roster consumes `down/left/right/up`
(rig: S/W/E/N). The rig's eight-compass support is a rendering
capability, not a roster obligation; nothing in this plan produces
diagonal sheets.

**D7 — The nudged views are canon.** The kneel's `down`/`up` guides are
the 12°-nudged camera of PR #97, by decision, because the cardinal view
of a sagittal fold projects to a shorter standing man (measured: 14px /
5-of-15 rows vs 19px / 9-of-15). Generated art for those facings
follows the guide. Nobody "fixes" this back to cardinal without
re-running that measurement.

**D8 — Missing sheets fault, loudly.** When the runtime switches roots,
a missing original sheet is a broken build, never a quiet fallback to
the licensed pack (design philosophy 3, and also the entire point of
the migration).

**D9 — Accepted strips are source art.** Once a strip passes at game
scale it is tracked and never regenerated on build. Generation is an
authoring step with an approval gate, not a pipeline stage.

## The vertical slice

Smallest honest audition — all four facings, viewed in the existing
walk-off and the actual room at 1×:

| verb | what it proves |
|---|---|
| IDLE | identity — the approved body IS this character |
| WALK | animation drift — the failure mode generation has already shown |
| KNEEL | the rig can add a verb the pack never had to teach it |

KNEEL alone would be a trap: a lovely action belonging to a character
who changes species on standing. IDLE first, always.

WALK is a real verb (folder exists, walkable registers it at 8fps
loop). The expansion order: RUN, DASH, AIM, FIRE, HURT, DEATH, HEAL,
ATTACK 1/2 — then the generated heads and mark palettes carry the
squad. **RUN landed 2026-08-09** (template-first, three facings at 1
gen each; north from the ladder in the record's run block — pin v3 to
a mid-cycle frame, never the rotation still). The armed verbs' gate,
the weapon-socket export, landed the same day (PR #106); AIM is next.

**VERDICT (2026-08-09, designer, walked at 1×): the slice passes.**
Both stagings ruled clean on the same walk — the three-body walk-off
with KNEEL on C-hold (PR #103) and the actual room staging the render
body on its three declared verbs (`?body=render96`, PR #104, sheets
from PR #101's translation-only re-frame). This was the doc's own gate,
and passing it moved the Status line above from Proposal to Current.
What it does NOT do: flip the room's default body — that waits for the
verb queue (the expansion order below, RUN first; the armed verbs
additionally gate on the socket export) and the squad.
`art_direction_gba_tactics.md` carries the lineage entry.

**Room staging (decided 2026-08-08):** the room admits the slice
through a declared-verb body source — `?body=render96` routes the
player's sheets to `assets/original/cipher_render/sheets96/`
(render_canvas96.py's translation-only re-frame) with a manifest that
declares exactly IDLE/WALK/KNEEL. The boot gate stays all-or-nothing
over the DECLARED set (a declared sheet that fails to load still
faults the room), RUN is covered by WALK as declared dialect, and
every undeclared verb is refused or labeled by name at the surface —
the walk-off's honest-absence grammar, now in the room. The squad
stays composed beside the slice body, which is the comparison the
staging exists to make. The composed roster's own gate is untouched:
for that body a missing verb is still a broken regeneration, never a
fallback case.

## Work-queue honesty

The rig holds 2 poses of 12 verbs. The kneel took one day *including*
the validation harness — and because the harness now exists (`settle()`,
`world_bounds()`, the sign convention, CI), the marginal verb is cheap.
It is still a queue, and this doc does not pretend otherwise.

The rig cannot manufacture polish. It provides anatomy, motion, facing,
contact and anchors; taste-level pixel clustering and costume live in
the master body and the generation/cleanup step. The BODY is authored
once; the material masks are not — every accepted strip carries its
own, per D2. Reduced, not eliminated.

## Open items

1. **Weapon socket before ATTACK/AIM/FIRE.** Those verbs need D2's
   socket EXPORT designed and landed first — per-frame position and
   orientation in anchored sheet coordinates, handedness, draw order.
   This is new rig work with its own PR, not a flag flip; sequence
   accordingly.
2. **Idle guide: static or breathing?** The pack's idle animates. A
   static mannequin guide may suffice for pose, with breath authored at
   the polish step — decide when the slice starts, not now.
3. **Render-path CI.** `--validate` returns before `place_camera()`, so
   the drift guard and per-pose directories are still unguarded
   (recorded in `roto-rig.yml`). A render job in CI is a separate,
   heavier decision.

## What this touches

- `VIDEO_GAME_REUSE_MAP.md` — updated on slice pass (2026-08-09), as
  this line used to instruct: the original body art and its records are
  now Tier 1 source IP.
- `art_direction_gba_tactics.md` (Reference) — palette dialect and
  register-pair decisions apply to the master body unchanged; the
  2026-08-09 lineage entry records this doc's supersession of PR #91.
- PR #91's hybrid canon — superseded as direction by the 2026-08-09
  verdict; the hybrid stays the shipping roster until the original
  roster covers its verbs. The exit path is now the exit, being walked.
