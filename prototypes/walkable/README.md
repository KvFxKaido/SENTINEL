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
| `WASD` / arrows | walk, camera-relative |
| `J` / `Space` | attack 1 |
| `K` | attack 2 |
| `Q` / `E` | orbit the room 90° |
| `P` | cycle LCD / crunch / clean |

The north doorway is **live**: walking through it is the seam.

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

The 16 local sheets are regenerable artifacts and are intentionally untracked.
If they are missing, the page stops at an explicit asset message instead of
substituting a placeholder:

```powershell
python scripts/cipher_mold.py
```

The licensed source pack must be present locally at
`prototypes/FREE_Adventurer 2D Pixel Art/`.

Cipher remains an audition body: the native 96×80 pack format and selout
dialect are provisional under
`architecture/art_direction_gba_tactics.md`. This room carries both open
questions — selout-vs-ink and pack-format-vs-body-law — without presenting
either as settled canon.
