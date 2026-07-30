# Walkable World Prototype

One room, one character, walking. This is a pure three.js renderer toy: no
game rules, no `tactical-core`, and no witness calls.

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

The doorway is visibly open but collision stops Cipher at its threshold. This
prototype promises one room; the black beyond it is staging, not an implied
second space.

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
