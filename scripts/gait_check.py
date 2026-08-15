#!/usr/bin/env python3
"""Gait check — does a locomotion strip hold its body through the cycle?

    python scripts/gait_check.py                 # survey everything, always exits 0
    python scripts/gait_check.py --gate          # non-zero exit if any strip fails
    python scripts/gait_check.py --verbs run --fighters cipher

WHY THIS EXISTS
---------------
The run reads goofy at 1x. That was on the record as a nit from the yard's
pre-merge walk-through, and the room worked around it by making the WALK the
default gait (PR #125) — which was the right call and cost zero generations,
but it treated a symptom. This measures the cause, so that a re-roll can be
DECIDED rather than eyeballed. A re-roll judged by eye is how we got here.

WHAT IT MEASURES, AND WHY THIS ONE THING
----------------------------------------
**Torso width — the widest span of the upper 45% of the body — must not step
within a strip.** In profile a torso is narrow; turned toward the camera it is
wide. So a strip whose torso width jumps mid-cycle is a body that ROTATED
partway through its own gait, which is exactly what "goofy" turned out to mean:

    cipher run right   13 13 13 13  16 16 16  13     <- steps to 16 for frames 4-6
    cipher walk right  12 12 12 12  12 13 13  12     <- never moves more than 1px

The tolerance is 1px, and it is not arbitrary: every idle strip in the roster
holds within 1px, and so does every walk strip. It is the measured behaviour of
the art that already reads right, not a number picked from animation theory.

WHAT WAS DELIBERATELY REJECTED
------------------------------
Three criteria that looked reasonable and are not, each killed by measurement:

- *Silhouette AREA varies <= 5-8%.* Rejected: the walk varies 15% and reads
  fine. Area conflates torso rotation with leg spread, so it fires on the good
  strip and the bad one alike and separates neither. Width above the waist
  isolates the rotation; area does not.
- *Planted foot within +/-1px of the ground row.* Rejected because the pipeline
  had already ruled on it: `render_canvas96.py` says "Locomotion frames dip
  below it; that is the gait." The row is measured off the STANDING pose. Idle
  sits at exactly 57, walk dips 1, run dips 2, dash rises 1 — a difference of
  degree in something declared normal, not a defect.
- *Require 1-2px of vertical body travel.* Rejected: every strip in the roster
  is perfectly flat, including the ones that read well. Mandating bounce would
  legislate a fix for a problem that only exists at run cadence, in the one
  surface (the yard) where nobody has complained.

Verbs whose silhouette legitimately changes — hurt, death, heal, fire, aim —
are out of scope by construction. The declared set is locomotion plus idle as
the control.

NOT A CI GATE YET, AND ON PURPOSE
---------------------------------
Run today, 18 of 20 run strips fail. Wiring `--gate` into CI would paint the
build red for a known, recorded, deliberately-unfixed state. It is a tool for
the re-roll: run it before, run it after, and the difference is the argument.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
# Where the render sheets live. cipher carries all ten verbs; the squad carries
# the seven the yard fields.
SHEET_ROOTS = {
    "cipher": ROOT / "assets/original/cipher_render/sheets96",
    "vesper": ROOT / "assets/original/squad_render/sheets96/vesper",
    "koa": ROOT / "assets/original/squad_render/sheets96/koa",
    "sable": ROOT / "assets/original/squad_render/sheets96/sable",
    "syn": ROOT / "assets/original/squad_render/sheets96/syn",
}
FACINGS = ("right", "left", "up", "down")
# idle is the control: it is a standing pose, so any step in ITS torso width
# would mean the measurement is wrong rather than the art.
DEFAULT_VERBS = ("idle", "walk", "run")
FRAME_W = 96
ALPHA = 8          # a pixel counts as body above this alpha
TORSO_FRACTION = 0.45   # the upper 45% of the body: shoulders to about the waist
TOLERANCE = 1      # px, measured off every idle and walk strip in the roster


def frames(path: Path, frame_w: int = FRAME_W) -> list[np.ndarray]:
    a = np.asarray(Image.open(path).convert("RGBA"))
    if a.shape[1] % frame_w:
        raise SystemExit(f"{path}: width {a.shape[1]} is not a multiple of {frame_w}")
    return [a[:, i * frame_w:(i + 1) * frame_w, :] for i in range(a.shape[1] // frame_w)]


def torso_widths(strip: list[np.ndarray]) -> list[int]:
    """Widest span of the upper TORSO_FRACTION of the body, per frame.

    Measured off the body's own bounding box each frame rather than a fixed
    row, so a strip that sits differently on the canvas is still compared
    like for like.
    """
    out = []
    for f in strip:
        solid = f[:, :, 3] > ALPHA
        ys, _ = np.nonzero(solid)
        if not len(ys):
            out.append(0)
            continue
        top, bottom = int(ys.min()), int(ys.max())
        cut = top + int((bottom - top) * TORSO_FRACTION)
        _, xs = np.nonzero(solid[top:cut, :])
        out.append(int(xs.max() - xs.min() + 1) if len(xs) else 0)
    return out


def check(fighter: str, verb: str, facing: str, tolerance: int, frame_w: int):
    path = SHEET_ROOTS[fighter] / f"{verb}_{facing}.png"
    if not path.exists():
        return None
    widths = torso_widths(frames(path, frame_w))
    spread = max(widths) - min(widths)
    # wrap-around: a loop's last frame hands back to its first
    step = max(abs(b - a) for a, b in zip(widths, widths[1:] + widths[:1]))
    return {
        "fighter": fighter, "verb": verb, "facing": facing,
        "widths": widths, "spread": spread, "step": step,
        "ok": spread <= tolerance,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fighters", nargs="+", default=list(SHEET_ROOTS))
    ap.add_argument("--verbs", nargs="+", default=list(DEFAULT_VERBS))
    ap.add_argument("--facings", nargs="+", default=list(FACINGS))
    ap.add_argument("--tolerance", type=int, default=TOLERANCE,
                    help="px of torso-width spread allowed across a strip (default 1)")
    ap.add_argument("--frame-width", type=int, default=FRAME_W)
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero if any strip fails; off by default because "
                         "the run currently fails by design (see the header)")
    args = ap.parse_args()

    unknown = set(args.fighters) - set(SHEET_ROOTS)
    if unknown:
        raise SystemExit(f"unknown fighter(s): {', '.join(sorted(unknown))}")

    rows = [r for r in (
        check(f, v, fa, args.tolerance, args.frame_width)
        for f in args.fighters for v in args.verbs for fa in args.facings
    ) if r]
    if not rows:
        raise SystemExit("no strips matched — check --fighters/--verbs/--facings")

    print(f"{'fighter':8s} {'verb':6s} {'facing':6s} {'torso width per frame':36s} "
          f"{'spread':>6s} {'step':>5s}  result")
    print("-" * 88)
    for r in rows:
        mark = "hold" if r["ok"] else "STEPS"
        print(f"{r['fighter']:8s} {r['verb']:6s} {r['facing']:6s} "
              f"{str(r['widths']):36s} {r['spread']:6d} {r['step']:5d}  {mark}")

    failed = [r for r in rows if not r["ok"]]
    by_verb: dict[str, list] = {}
    for r in rows:
        by_verb.setdefault(r["verb"], []).append(r)
    print()
    for verb, group in by_verb.items():
        bad = [r for r in group if not r["ok"]]
        print(f"  {verb:6s} {len(group) - len(bad):2d}/{len(group):2d} hold within "
              f"{args.tolerance}px" + (f"   ({len(bad)} step)" if bad else ""))
    print(f"\n{len(rows) - len(failed)}/{len(rows)} strips hold their torso through the cycle.")

    if failed and args.gate:
        print("\nFAIL — a body that changes width mid-cycle turned partway through "
              "its own gait.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
