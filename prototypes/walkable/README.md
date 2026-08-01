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
| `Q` / `E` | orbit the room 90° |
| `P` | cycle LCD / crunch / clean |

† Full-pack verbs — inert (and labeled so on the control surface) when
only the free pack's core four are molded.

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
  that put you back in the room if the far side never answers.

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
`prototypes/FULL_Adventurer 2D Pixel Art/` for all nine verbs (36 sheets),
or the FREE pack for the core four (16 sheets). Frame counts are read from
sheet width, never assumed: the full pack varies them per verb (heal runs
12 frames, hurt 4).

The roster is stated, never guessed at. The core four verbs are required
to boot; the extended five are all-or-nothing:

- all 20 extended sheets load → **CANON / FULL** on the panel;
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
