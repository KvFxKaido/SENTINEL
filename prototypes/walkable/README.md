# Walkable World Prototype

One room, one character, walking — and one door that is somewhere else's
problem. This is a pure three.js renderer toy: no game rules and no
`tactical-core` import. Its only network call is asking the witness to
certify what the yard reports back through the seam (below).

Cipher stands inside a voxel-extruded Kestrel interior staged as a lit diorama
in the void. The room reuses `tactical3d/`'s terrain density, Y-billboard,
quarter-turn camera, lighting discipline, blob shadow, and LCD display pass so
the audition is against the same visual machinery rather than a friendly mock.

## Run it

Serve the **repository root**:

```powershell
cd C:\dev\SENTINEL
python -m http.server 8082
```

Then open <http://localhost:8082/prototypes/walkable/>.

The root matters. Cipher's sheets load from
`../../assets/sprites/cipher/`, which only resolves correctly when the page is
served in repository context. The ES-module import also means this page does
not run from `file://`.

## Controls

| Input | Action |
|-------|--------|
| `WASD` / arrows | run, camera-relative |
| `Shift` + move | walk † |
| `L` | dash, current facing † |
| `J` / `Space` | attack 1 |
| `K` | attack 2 |
| `H` | heal channel † |
| `G` | hurt flinch † |
| `X` | down — any move key rises † |
| `R` hold | aim — emitter up † |
| `F` | fire † |
| `C` hold | kneel † |
| `Q` / `E` | orbit the room 90° |
| `P` | cycle LCD / crunch / clean |

† Full-pack verbs — inert (and labeled so on the control surface) when
only the free pack's core four are molded.

`R` and `C` are **stances**: held, not triggered, and standing-only.
There are no aim-walk or crouch-walk sheets, so moving takes the body
out of a stance rather than playing one over a moving body — releasing
the key, or stopping again, puts it back. Holding both is a real thing a
player does, so the tie is decided rather than left to key order: aim
wins, because aim is the stance with a verb attached to it. `F` fires
from anywhere, and because the shot begins and ends in the aim pose it
reads standalone *and* falls back into a held aim without a seam.

The north doorway is **live**: walking through it is the seam — and the
dash moves through the same collision and door machinery, so dashing the
doorway deals the card too. On the full roster, walking back out of a
**lost** card plays the hurt flinch: the record comes back with you, and
it shows.

## The seam

Crossing the north door hands the feed to `tactical3d/` in a fullscreen
iframe with a seed this room dealt (`?seam=1&seed=…`). The yard plays
exactly one card — its own re-deal verbs are disabled in seam mode — and
when you take **WALK BACK OUT** on the post-match overlay, it posts
`{seed, record, result, rating, purse, fingerprint}` home and the frame
is torn down. You return standing just inside the walls; walking the
door again deals a fresh card.

The room does not take the yard's word for it:

- the returned **seed must match the one it dealt**, and the payload must
  be shaped like a replayable record — anything else is refused;
- the record is sent to the witness Worker, whose **replay settles the
  session ledger**: `CERTIFIED AT THE EDGE`, `EDGE DISPUTES THE FEED —
  STRUCK` (the card never counts), or `UNCERTIFIED — NO WITNESS
  REACHABLE` (counted, and labeled as taken on the yard's word);
- the hand-off has a readiness handshake: the cut card holds until the
  yard proves it booted, with a 7s timeout and an <kbd>ESC</kbd> abort
  that put you back in the room if the far side never answers;
- the certify request has a deadline of its own (8s). A witness that
  refuses was always labelled `NO WITNESS REACHABLE`; a witness that
  *accepts and never answers* used to leave the ledger at `ASKING THE
  EDGE…` forever. A hang is unreachable too, and the room says so and
  counts the card (caught in review — this room guarded a dead yard
  behind the door and was not guarding a dead edge in front of it).

Query params: `?deal=6` pins the seed the door deals (the same
pin-a-board move as tactical3d's `?seed=`); `?witness=http://localhost:8787`
passes through to the yard and is used for certification here.

## Cipher assets

The local sheets are regenerable artifacts and are intentionally untracked.
If they are missing, the page stops at an explicit asset message instead of
substituting a placeholder:

```powershell
python scripts/roster_mold.py
```

The licensed source pack must be present locally —
`prototypes/FULL_Adventurer 2D Pixel Art/` for all nine molded verbs (36
sheets), or the FREE pack for the core four (16 sheets). Frame counts are
read from sheet width, never assumed: the full pack varies them per verb
(heal runs 12 frames, hurt 4, and synthesized kneel 2).

On the full pack the mold also **synthesizes** three verbs the pack does
not ship — `AIM`, `FIRE`, `KNEEL`, 12 more sheets — so a fighter carries
48. They are ordinary sheets on the same canvas; nothing in this page
knows the difference. What makes them the pack's own rather than
imported: aim lifts the HEAL draw (the frame where the held object sits
at the chest, hand already closed on it) and replaces the vial with the
emitter, so the grip is still the pack artist's; the emitter's charge and
its muzzle bloom are drawn in the pack's heal greens, which the mold
already swaps to each fighter's mark color; and the housing is drawn in
the pack's steels, which the blade pass already sheathes on any
non-attack sheet. **Aiming shows cold steel; only the shot lights** —
the blade's law, read onto a barrel. Kneel is row surgery on IDLE: the
torso is copied down, the boots never move, and the coat hem flares a
pixel, because on a body in a long coat the height loss alone read as a
shorter man rather than a crouching one.

The roster is stated, never guessed at. The core four verbs are required
to boot; the extended eight are all-or-nothing:

- all 32 extended sheets load → **CANON / FULL** on the panel;
- none present → **CANON / CORE**, with the extended rows on the control
  surface dimmed and labeled `not molded`;
- anything in between is a broken regeneration and stops at an explicit
  asset fault naming the partial state — there is no silent subset.

This body is **canon**. The walk-off (2026-07-31, `walkoff.html` — both
bodies fielded in this room on one input) decided the two questions this
room carried: the pack format beat the 32×32 body-law canvas, and the
selout dialect won with it. The verdict and its costs are recorded in
the body law's successor section,
`architecture/art_direction_gba_tactics.md`.

## Tests

`test/` holds the headless harness that guards this page's claims — the
"caught in test" comments in `index.html` point at it:

```sh
cd prototypes/walkable/test
npm install                        # the playwright library
npx playwright install chromium    # the browser itself (skip if one is provisioned)
node test_walkable_verbs.mjs       # 47 checks: verbs, stances, light, roster states, regressions
python test_roster_sweep.py        # the roster mold's remold sweep (pillow + numpy)
```

What it does and deliberately does not touch:

- The browser harness drives the page against **synthetic sheets** at the
  pack's real geometry (no licensed pack needed), measuring verb
  durations in-page against per-sheet frame counts. Real molded sheets
  at `assets/sprites/cipher/` are backed up before the run and restored
  after.
- The mold test runs the actual `scripts/roster_mold.py` twice against
  fake packs — **fully sandboxed in a temp dir** via the mold's
  `ROSTER_MOLD_PACKS` / `ROSTER_MOLD_OUT` test hooks, so the real
  licensed packs and molded outputs are never touched. On synthetic
  input the pinned cipher golden is EXPECTED to fire; the test asserts
  that it does.

Two claims are split deliberately across the suites, because neither
runner can see the whole thing. The room's `FIRE_SPILL` curve must light
exactly the frames that carry a muzzle bloom — but headless rAF runs
around 5fps against a 500ms sheet, so the browser can only ever observe
a couple of frames (and the phase cannot be walked: `locked.started` is
stamped on the verb's first *rendered* frame, so delaying the keypress
shifts nothing). So the browser asserts light-per-frame on whatever it
catches, refusing to pass if it caught too little; the Python suite
asserts the other half — that the bloom really is drawn on frames 1–3 —
where every frame is visible.

Both run in CI (`walkable-harness` job), alongside the yard's two suites —
including `prototypes/tactical3d/test/test_seam_round_trip.mjs`, which
walks this room's north door, plays the card, and reads the verdict this
room settles on. The seam round trip **is** covered now; it stopped being
somebody else's problem when the yard started fielding these same bodies.

Not covered: anything about how the sheets *look* — pixels are judged by
walking, not asserted.

One thing about looks *is* worth measuring, because eyes lie about scale:
the count of mark-colour pixels a verb lights at its peak. The shipped
verbs run blade ignition 706 and heal channel 38; the muzzle bloom's
first cut peaked at 21, which on a ~34px body drawn ~28px tall is a
flicker rather than a gunshot. It was resized against those numbers, not
against a zoomed contact sheet where everything reads fine:

```sh
python - <<'PY'
from PIL import Image; import numpy as np, os
R, E = 'assets/sprites/cipher', [(0xea,0xff,0xff),(0xa5,0xec,0xff),(0x5c,0xcf,0xff),(0x21,0x96,0xd8),(0x1d,0x7f,0xc0)]
for rel in ['ATTACK 1/attack1_right.png','HEAL/heal_right.png','FIRE/fire_right.png']:
    a = np.array(Image.open(os.path.join(R, rel)).convert('RGBA'))
    pk = [int(sum(((f[:,:,0]==c[0])&(f[:,:,1]==c[1])&(f[:,:,2]==c[2])&(f[:,:,3]>0)).sum() for c in E))
          for f in (a[:, i*96:(i+1)*96] for i in range(a.shape[1]//96))]
    print(f'{rel:26} peak={max(pk)}')
PY
```
