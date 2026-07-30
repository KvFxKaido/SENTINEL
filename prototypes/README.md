# prototypes

Playable prototypes of the universe's combat layers.

The squad layer: one tactical encounter — Kestrel Yard — that feels good
enough to replay twice. One rules layer, two renderers, one test suite.

```
tactical-core/   rules: rng, LOS, cover, firing solutions, movement, AI
                 no DOM — runs under `node --test`, guarded in CI
tactical/        2D canvas renderer (immediate-mode, pixel sprites)
tactical3d/      three.js renderer (retained-mode, 2:1 isometric)
```

And the 1v1 layer: `close-contact/` — the SENTINEL: Close Contact
fighting prototype (Godot 4.5, limb-mapped inputs, active defense). See
its own README; the rest of this file is about the tactical slice.

## Run it

Both renderers import `../tactical-core/rules.js`, so the server root has to
be **this** folder, not the individual prototype:

```sh
python -m http.server -d prototypes 8080
```

- 2D → <http://localhost:8080/tactical/>
- 3D → <http://localhost:8080/tactical3d/>

Or double-click `tactical3d/serve.cmd`, which does both and opens a browser.

Append `?seed=deadbeef` to pin a specific encounter.

## Run the tests

```sh
cd prototypes/tactical-core && node --test
```

## Why two renderers

Not indecision. Two renderers over one rules module is the cheapest ongoing
proof that the rules really are renderer-agnostic — if a rule ever leaks into
a renderer, the other one breaks and says so. They also make the immediate-mode
vs retained-mode contrast concrete, which is the whole reason the 3D port was
worth doing as a learning exercise.

If one of them stops earning its keep, delete it. Do not let them drift.

## Neither of these is the game

No campaign, no classes, no research tree, no soldier whose death ruins your
evening. This is a recognizable genre chassis to argue with. The questions
that would make it SENTINEL rather than XCOM-flavoured come after the chassis
proves itself:

- What if turns are simultaneous?
- What if cover degrades?
- What if missed shots alter the map?
- What if **social energy** is the morale system — depletion, not death, ends fights?
- What if positioning creates team abilities instead of aim bonuses?
- ~~What if hostiles surrender, and what you do next is a **hinge moment**?~~
  **Built.** Hostiles yield on morale, and the spare/finish call is the
  match's last move (Circuit roadmap step 1 — see `tactical-core/`).

That one was where this stopped being a clone. Depletion-not-death now exists
for hostiles; whether it becomes **social energy** on the player's side is
still open.
