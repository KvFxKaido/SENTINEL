# Tactical Encounter Prototype — 2D

One tactical encounter that feels good enough to replay twice. That's the whole scope.

The rules live in [`../tactical-core/`](../tactical-core/) and are shared with
the three.js renderer in [`../tactical3d/`](../tactical3d/). This file only
draws and takes input.

**Run it:**

```bash
python -m http.server -d prototypes 8080
# then open http://localhost:8080/tactical/
```

The server root is `prototypes/`, not this folder — `index.html` imports
`../tactical-core/rules.js` and has to be able to reach it.

> **This no longer opens from `file://`.** It used to, and that was a real
> property worth having. It was traded for a single tested source of truth
> for the rules: two copies of the AI and the RNG order were going to drift,
> and determinism is a design-binding invariant. Nothing else changed — still
> no npm, no bundler, no build step. Append `?seed=deadbeef` to pin a board.

## What's in the box

- 10×10 grid, hand-authored map (Kestrel Yard, a Lattice relay station)
- 3 operatives vs 3 Steel Syndicate hostiles
- Move (2 AP, blue = 1 AP range, amber = dash), shoot, overwatch
- Half cover (−20 to be hit) and full cover (−40, blocks line of sight)
- Directional cover: standing behind a crate only helps against fire from that side — flanked targets are marked and eat a 45% crit chance
- Visible hit percentages with the full breakdown (base aim / range / cover)
- Simple enemy AI: fires at ≥45%, or ≥30% when caught in the open after moving; otherwise advances toward cover with sightlines and holds overwatch once it gets there
- Win, lose, restart

## Determinism

Every roll comes from a seeded RNG (`mulberry32`). The seed is shown in the top
bar. `shift+R` replays the exact same encounter — same rolls in the same order —
so a loss can be re-attempted as a puzzle: same seed, better angles. `R` deals a
new encounter. This mirrors the engine invariant in `architecture/Sentinel 2D.md`:
determinism and turn authority win.

This is now enforced rather than hoped for: `../tactical-core/rules.test.js`
replays golden transcripts headlessly and runs in CI. A stray random draw
fails the build.

## Controls

| Input | Action |
|-------|--------|
| click | select operative / move / shoot hostile |
| `Tab` | cycle to next operative with AP |
| `F` | toggle shoot mode (shows hit % over every hostile) |
| `Y` | overwatch (ends unit's activation) |
| `Enter` | end turn |
| `R` / `shift+R` | new encounter / replay same seed |

## Deliberately not here

No campaign, no classes, no research tree, no soldier whose death ruins your
evening. The point of this slice is to have a recognizable genre chassis to
argue with. The organ-replacement questions — the ones that would make this
SENTINEL rather than XCOM-flavored — come after the chassis proves itself:

- What if turns are simultaneous?
- What if cover degrades?
- What if missed shots alter the map?
- What if **social energy** is the morale system — depletion, not death, ends fights?
- What if positioning creates team abilities instead of aim bonuses?
- What if hostiles surrender, and what you do next is a **hinge moment**?

The last two are where this stops being a clone. But first: replay it twice.
