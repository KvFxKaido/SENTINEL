# SENTINEL: The Original Body — Roto as Choreographer

**Status: Proposal** — migration plan off the licensed Adventurer pack;
cite as intent, not law. Drafted 2026-08-08 from a Codex consult and the
rig work landed in PR #97. Amends the hybrid-canon decision of PR #91
(pack = reference, whole-generated render = retained experiment); does
not supersede it until the vertical slice passes.

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
four idle facings. The candidate seed is the retained whole-generated
Cipher render from PR #91 — that experiment was kept for exactly this
moment. If automated candidates stay uneven, commission cleanup of this
ONE reusable body, not a roster. The job at this step is art direction
and approval, not pixel labor.

**D2 — The rig emits choreography: pose strips, part masks, anchors.**
The rig's flat-shaded, colour-separated, `filter_size=0` render is
already a semantic ID map — head, torso, each limb segment owns a
palette entry, which is why the tracing aid and the part mask are the
same idea. A dedicated ID pass with pure indexed colours is ~20 lines.
Anchors likewise: `ground_{pose}_{facing}.json` already ships, and hand
and weapon sockets are the `fore_*` world positions the validator
already computes.

**Material masks are explicitly NOT the rig's.** Skin, cloth, steel,
mark colour — the rig is boxes and does not know where the coat ends.
Material masks are authored once on the approved master body and ride
the strips from there. One deliverable in the consult, two sources in
fact; PRs should not ask the rig for materials.

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
loop); RUN stays pack-only until its turn in the expansion order:
RUN, DASH, AIM, FIRE, HURT, DEATH, HEAL, ATTACK 1/2 — then the
generated heads and mark palettes carry the squad.

## Work-queue honesty

The rig holds 2 poses of 12 verbs. The kneel took one day *including*
the validation harness — and because the harness now exists (`settle()`,
`world_bounds()`, the sign convention, CI), the marginal verb is cheap.
It is still a queue, and this doc does not pretend otherwise.

The rig cannot manufacture polish. It provides anatomy, motion, facing,
contact and anchors; taste-level pixel clustering and costume live in
the master body and the generation/cleanup step. That burden is reduced
to one body, once.

## Open items

1. **Weapon socket before ATTACK/AIM/FIRE.** Those verbs need D2's
   socket emission landed first; sequence the rig work accordingly.
2. **Idle guide: static or breathing?** The pack's idle animates. A
   static mannequin guide may suffice for pose, with breath authored at
   the polish step — decide when the slice starts, not now.
3. **Render-path CI.** `--validate` returns before `place_camera()`, so
   the drift guard and per-pose directories are still unguarded
   (recorded in `roto-rig.yml`). A render job in CI is a separate,
   heavier decision.

## What this touches

- `VIDEO_GAME_REUSE_MAP.md` — the reuse story changes when the source
  is original; update on slice pass, not before.
- `art_direction_gba_tactics.md` (Reference) — palette dialect and
  register-pair decisions apply to the master body unchanged.
- PR #91's hybrid canon — remains in force until D1's body passes the
  slice; this doc is the exit path, not the exit.
