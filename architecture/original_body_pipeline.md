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
roster that does not exist yet. **That condition was MET 2026-08-09
(ten of ten), the designer walked the full roster at 1× the same day
and ruled it clean, and the default FLIPPED: a plain URL now stages
the original body. The hybrid remains staged at `?body=composed` and
remained the squad's roster until the squad phase retired it — later
the same day: the squad now rides its own tracked render sheets, and a
plain URL boots the room with no pack-derived pixels anywhere.**

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
The declaration found its first consumer 2026-08-09: FIRE's molder
acceptance holds every bloom pixel to the aim sockets' hand point and
forearm direction (the record's fire block maps them onto the render's
canvas), and the check rejected all four of the ladder's dead rolls —
the flash on a face, an explosion, a flipped figure, a beam — before
any of them could ship.

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
the weapon-socket export, landed the same day (PR #106). **AIM landed
2026-08-09** — state-first at ONE state, zero repairs, the cleanest
ladder yet (the record's aim block carries the chirality decision and
the breath-boundary fact) — so the roster stood at five of ten.
**DASH landed 2026-08-09 the same day** — the first one-shot, and the
first verb generated by COMPOSING the paid-for doctrines rather than
extending them: a lunge state anchors the pose family, v3 rides the
state's own rotations, the back view takes surgery-then-pin (the
record's dash block carries the ladder). **FIRE landed 2026-08-09,
still the same day** — the first verb that buys no state: it rides the
Aim state's rotations (keep_first_frame makes the aim still the hold
frame, so the resume-into-aim seam is pixel-exact by construction), and
the scalpel cut TIME for the first time — the model put the burst on f2
in seven of seven rolls while the room's spill curve decays from f1, so
the record declares per-facing stage maps the molder executes. Its
acceptance CONSUMES the socket export: every bloom pixel is held to the
rig's declared muzzle line (the record's fire block carries the ladder,
the dedup finding, and the executed constants). **HURT, DEATH, and HEAL
landed 2026-08-09 in one push — THE ROSTER COMPLETES: ten of ten, the
render body covers the composed bill entire.** Sixteen generations for
the three: hurt and heal won every facing on the first roll (the back
view's first-ever first-roll poses), and death's ladder bought a new
doctrine line — the library's falling-back-death template ends MID-FALL,
and a held mid-fall frame reads as levitation, so **templates constrain
motion, not end state**; the v3 re-roll with the floor named won
four-for-four (the record's three blocks carry the ladders and the
executed acceptance constants: dark-verb cyan budgets, the flat-and-
grounded hold contract, heal's pulse bounds and device containment).
ATTACK 1/2 remain deliberately unbuilt: the room's own bill dropped
them (no rule consults melee — the gunplay verbs the rules use are aim
and fire), so they are not part of covering the composed roster; if a
walkoff comparison ever wants them, that is its own decision. The
frontier now is the squad — generated heads and mark palettes. **THE
SQUAD LANDED 2026-08-09, same day: VESPER / KOA / SABLE on the render
path, idle + kneel — the two verbs the room stages for them — from
their own D1-minted generated bodies, chosen by the designer from a
four-body lineup against the render cipher. A recorded DEVIATION from
D1's letter (one master body): the squad keeps its own bodies because
they already existed — the D1 pass minted four citizens for eight
generations — and the lineup ratified them; D1's compositor path
remains the plan for FUTURE characters. The phase cost 92 generations
(four states, twelve idle templates, zero bodies) and paid the D1
record's own vesper debt: the shell-brim helm re-rolled into the
crested dome its kit always named. Koa's wrong-facing kneel ships as
the molder-MIRRORED south-west — the composed era's cheat, declared in
the record and executed in code rather than hidden in a sheet. The
squad re-frame anchors each strip by its own measured ground row (the
states wobble ±2 where cipher's never did — the rule and its reasons
live in the squad record's anchor block). With this, the plain-URL
room is pack-free: only `?body=composed` still routes through the
licensed pipeline, player only.**

**VERDICT (2026-08-09, designer, walked at 1×): the slice passes.**
Both stagings ruled clean on the same walk — the three-body walk-off
with KNEEL on C-hold (PR #103) and the actual room staging the render
body on its three declared verbs (`?body=render96`, PR #104, sheets
from PR #101's translation-only re-frame). This was the doc's own gate,
and passing it moved the Status line above from Proposal to Current.
What it did NOT do: flip the room's default body — at the time this
verdict was recorded, the flip waited on the verb queue (the expansion
order below) and the squad. **Superseded in part, 2026-08-09: the verb
half of that gate was met (ten of ten) and the designer's full-roster
1× walk — with the composed squad standing beside the render player,
exactly the mixed staging this line worried about — ruled the flip
ready. The squad half is deliberately dropped from the GATE and kept
as WORK: vesper/koa/sable stay composed until the squad phase — which
landed later the same day (the squad entry below).**
`art_direction_gba_tactics.md` carries the lineage entry.

**VERDICT (2026-08-09, designer, walked at 1×): the FULL ROSTER passes
— and the default flips.** All ten verbs on the render body, walked in
the room on the day they completed and ruled clean. The plain URL now
stages the original body; the harness executes that claim (a plain
boot must report the render roster — red before the flip, green
after), and the composed roster remains staged one query away as the
squad's roster and the comparison body. This is the flip PR the Status
header required. **Known and deliberate (decided 2026-08-09, designer):
Cipher changes bodies at the north-door seam — the yard still stages
composed Cipher, because the yard has no body-source concept and the
render body has never been auditioned in the yard's own staging. The
yard follows only after its own 1× walk, in its own PR; the seam swap
is the honest cost of not bundling an unauditioned staging into a
decided one. CORRECTED later the same day, in review of the yard-body
PR: Cipher is not FIELDED on the yard's card at all — the rules field
VESPER/KOA/SABLE against three SYNs, and Cipher's sheets preload for
the boot gate but never draw. The 'swap' this note narrated was never
visible; the claim was inherited from a review comment and repeated
without checking the card's roster. What the yard-body PR actually
lands: the body-source concept, the seam carrying the choice, correct
preloads, and per-fighter cadence — the exact foundation the squad's
render combat verbs will stand on. The VISIBLE door inconsistency is
the SQUAD's: render bodies idle in the room, composed bodies fight in
the yard, and that retires only when vesper/koa/sable (and SYN) get
combat verbs on the render path — a real generation phase, the
designer's call. RETIRED 2026-08-10: the designer called it the next
day, the phase ran (the entry below), and the yard flip routes every
fighter to the render sheets — the last visible body swap at the door
is gone. The yard's own 1× verdict is recorded below — the designer
walked it before the merge.**

**THE SQUAD ARMS ITSELF (2026-08-10): run / aim / fire / hurt / death
for VESPER / KOA / SABLE, and SYN entire — his first render verbs
anywhere.** ~266 generations on the cipher roster's paid-for doctrines:
templates for the cycles (three of four fighters' runs were
four-for-four first rolls, including the honest backs that cost cipher
a ladder), states for the held aims (three landed in one rung each;
SYN's took four — his stocky D1 build and red accents fight every
prior, and the ladder proved the BUILD language and the FACING-DIALECT
language are separate guards), v3 with guard clauses for the reactions
(hurt and death mostly first-roll), and stage-mapped v3 for the shots.
FIRE bought the phase's new doctrine line: **the model's muzzle-flash
prior is warm yellow and it invents debris** — cipher's cyan palette
never had to fight it, so the squad's prompts now name the color ramp,
the per-facing position, and the invention classes the rungs met
(orb-on-head, lime star, ember-feet, a raised off-arm, a conjured
second pistol, a full-body white flash on a death frame — each named
dead in one re-roll). SYN's warm flash is the recorded exception:
rust IS his ramp. The molder's own execution forced two metric
corrections, both measured before recorded: two-tier decay (cipher's
spatial mask where the flash leaves the silhouette, bright-changed
where it does not) and flash-color containment (bright kit riding
authored recoil is not an invention). 112 strips validated and
published, 112 re-framed to 96×80 on the per-strip anchor; SYN's north
kneel is kneel_frames row surgery on his identity rotation, the pack's
own construction, executed by the molder from recorded bands. **With
the yard flip PR, every fighter on both surfaces stages the render
body from a plain URL; the composed pipeline survives only behind
`?body=composed`, whole-roster on both pages.**

**VERDICT (2026-08-10, designer, walked at 1× before the merge): the
yard passes.** The squad fights in their render bodies through the
door and the staging reads. One nit, recorded rather than hidden: the
RUN reads a bit wonky at 1× — ruled cosmetic by the designer, no gate
hangs on it. The fix is cheap whenever polish wants it: the run strips
are template rolls, so a facing that bothers the eye is a ~4-gen
re-roll against the same acceptance machinery, keeper-judged like
everything else in the squad record.

**SETTLED (2026-08-14, designer, on a second walk): the default gait in
the room is the WALK, and the re-roll is not owed.** Nothing was
regenerated and nothing was retired — both strips were always authored,
both still play, and only which one a bare move press gets has changed
(`Shift` holds the run). Zero generations against ~4, for a nit that was
only ever about which cycle the eye lands on by default. The yard keeps
the run, and not as an oversight: `tactical-core` exposes each path step
for 70ms, so a unit crosses a tile in a fourteenth of a second, and a
walk cycle carried at that pace would be the renderer lying about the
gait. The room is the only surface with a *choice* of gait to make.

**Room staging (decided 2026-08-08):** the room admits the slice
through a declared-verb body source — `?body=render96` routes the
player's sheets to `assets/original/cipher_render/sheets96/`
(render_canvas96.py's translation-only re-frame) with a manifest that
declared exactly IDLE/WALK/KNEEL at admission. The boot gate stays
all-or-nothing over the DECLARED set (a declared sheet that fails to
load still faults the room), and every undeclared verb is refused or
labeled by name at the surface — the walk-off's honest-absence
grammar, now in the room. RUN was covered by WALK as declared dialect
until its own sheets landed (#107, retiring the cover); the declared
set has grown verb by verb since, and the LIVE bill is the render96
manifest in index.html, not this paragraph — what is recorded here is
the admission decision and its gate, which have not moved. The squad
stays composed beside the slice body, which is the comparison the
staging exists to make. The composed roster's own gate is untouched:
for that body a missing verb is still a broken regeneration, never a
fallback case.

## Work-queue honesty

The rig holds 3 poses of 12 verbs. The kneel took one day *including*
the validation harness — and because the harness now exists (`settle()`,
`world_bounds()`, the sign convention, CI), the marginal verb is cheap:
the aim (2026-08-09) took a morning, eleven checks and three red tests
included.
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
  roster covers its verbs. That condition was met later the same day
  (ten of ten): the VERB migration is finished. Both of the Status
  header's requirements were met the same day — the full-roster 1×
  walk ruled clean, and the default-flip PR landed. The pack's pixels
  then shipped only through the hybrid at `?body=composed` and the
  yard's squad — and the squad-combat phase (2026-08-10) retired the
  latter: the composed pipeline is now opt-in comparison staging on
  both pages, whole-roster, and nothing else.
