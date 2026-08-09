#!/usr/bin/env python3
"""Re-frame the walk-off render's sheets onto the 96x80 body canvas (2026-08-08).

The migration doc (architecture/original_body_pipeline.md, D1) promised this
step: the whole-generated body already stands at pack-nominal scale on its own
64x64 canvas, so entering the canon 96x80 sheet contract is a re-frame, not a
regeneration. This performs it the only way the body law permits — translation
only — and the only way a STRIP permits: **one constant offset for every frame
of every verb**. pack_canvas.py's per-frame bbox centring is correct for lone
stills; applied per frame here it would re-centre away the authored sway and
land as sideways shimmy (walkoff_render_sheets.py records that lesson).

The offset is derived, not chosen:

    dy = FEET_Y - GROUND_ROW_64      # 57 - 47: standing feet onto the law's row
    dx = CENTER_X - (REN_CANVAS-1)/2 # 46.5 - 31.5: canvas centre onto the
                                     # pack's standing centre line

Both right-hand constants are measurements already on the books: FEET_Y and
CENTER_X are pack law (pack_canvas.py, measured off the molded roster), and
GROUND_ROW_64 is the render's standing last-opaque row, measured across all
four rotations by walkoff_render_sheets.py and hard-coded by walkoff.html as
REN_GROUND_ROW. Locomotion frames dip below it; that is the gait, and a
constant offset preserves it exactly.

Reads  assets/original/cipher_render/sheets/{idle,walk,run,kneel}_{facing}.png
Writes assets/original/cipher_render/sheets96/... same names, frames at 96x80.

Validated, then published (molder discipline): every strip is rebuilt in
memory and every check — frame size, pure-translation byte equality, the
per-frame ground-row shift — passes before a single file is written.
"""
import os
import sys

import numpy as np
from PIL import Image

from pack_canvas import CANVAS_H, CANVAS_W, CENTER_X, FEET_Y

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "assets", "original", "cipher_render", "sheets")
OUT = os.path.join(HERE, "..", "assets", "original", "cipher_render", "sheets96")

REN_CANVAS = 64
# Standing last-opaque row across all four rotations, measured by
# walkoff_render_sheets.py (pack_canvas semantics); walkoff.html hard-codes
# the same number as REN_GROUND_ROW. North stands 1px above it — shipped as
# generated there, shipped as generated here.
GROUND_ROW_64 = 47

# The molder's bill: which sheets a complete source set contains. The set
# is checked exactly — a missing name would rewrite fifteen strips and
# leave the sixteenth stale in sheets96, the partial-set lie the molder
# already refuses; an unexpected name is a verb this re-frame has never
# judged and must not silently launder onto the law's canvas.
EXPECTED = {f"{verb}_{facing}.png"
            for verb in ("idle", "walk", "run", "kneel")
            for facing in ("down", "up", "left", "right")}

DY = FEET_Y - GROUND_ROW_64
DX = CENTER_X - (REN_CANVAS - 1) / 2
if DX != int(DX):
    raise AssertionError(f"dx {DX} is not integer — translation-only forbids it")
DX = int(DX)


def last_opaque_row(img: Image.Image) -> int:
    box = img.getbbox()  # exclusive bottom: the row index is bbox[3] - 1
    if box is None:
        raise ValueError("frame is fully transparent")
    return box[3] - 1


def reframe(strip: Image.Image, name: str) -> tuple[Image.Image, list[int]]:
    w, h = strip.size
    if h != REN_CANVAS or w % REN_CANVAS:
        raise ValueError(f"{name} is {w}x{h}; expected Nx{REN_CANVAS} strip "
                         f"of {REN_CANVAS}x{REN_CANVAS} frames")
    n = w // REN_CANVAS
    standing = name.startswith("idle")
    # the whole source canvas must land inside the target — clipping a frame
    # would be a silent crop, which is a scaling cousin, not a translation
    if DX < 0 or DY < 0 or DX + REN_CANVAS > CANVAS_W or DY + REN_CANVAS > CANVAS_H:
        raise AssertionError(f"64-canvas at ({DX},{DY}) exceeds "
                             f"{CANVAS_W}x{CANVAS_H}")

    out = Image.new("RGBA", (CANVAS_W * n, CANVAS_H), (0, 0, 0, 0))
    rows = []
    for i in range(n):
        frame = strip.crop((REN_CANVAS * i, 0, REN_CANVAS * (i + 1), REN_CANVAS))
        out.paste(frame, (CANVAS_W * i + DX, DY))

        # The claim is "translated, never resampled" — execute it per frame.
        placed = np.array(out)[DY:DY + REN_CANVAS,
                               CANVAS_W * i + DX:CANVAS_W * i + DX + REN_CANVAS]
        if not np.array_equal(placed, np.array(frame)):
            raise AssertionError(f"{name} frame {i}: placed pixels differ "
                                 f"from source — this resampled")
        src_row = last_opaque_row(frame)
        # The shift check alone is a tautology — translation always moves
        # the row by DY. The claim that needs teeth is the ANCHOR: DY was
        # derived from GROUND_ROW_64, and the molder's own gate constrains
        # only cross-facing spread, so a remolded source whose standing
        # row moved would pass it and land here with its feet off the
        # law's line. The idle strips are the standing reference (a
        # breath never moves the feet; the molder's report shows ±1
        # across facings), so they are held to the recorded anchor
        # (caught in review, PR #101).
        if standing and abs(src_row - GROUND_ROW_64) > 1:
            raise AssertionError(
                f"{name} frame {i}: standing row {src_row} is not the "
                f"recorded anchor {GROUND_ROW_64}±1 — the source was "
                f"remolded with a different framing; remeasure "
                f"GROUND_ROW_64 against the molder's report")
        dst = out.crop((CANVAS_W * i, 0, CANVAS_W * (i + 1), CANVAS_H))
        if last_opaque_row(dst) != src_row + DY:
            raise AssertionError(f"{name} frame {i}: ground row did not "
                                 f"shift by exactly {DY}")
        rows.append(src_row + DY)
    return out, rows


def main() -> int:
    present = {n for n in os.listdir(SRC) if n.endswith(".png")} \
        if os.path.isdir(SRC) else set()
    missing = sorted(EXPECTED - present)
    extra = sorted(present - EXPECTED)
    if missing or extra:
        raise ValueError(
            f"source set is not the molder's bill — "
            f"missing: {missing or 'none'}, unexpected: {extra or 'none'} "
            f"— run walkoff_render_sheets.py, or extend EXPECTED if the "
            f"bill itself grew")

    built = []
    for name in sorted(EXPECTED):
        strip, rows = reframe(Image.open(os.path.join(SRC, name)).convert("RGBA"),
                              name)
        built.append((name, strip))
        print(f"{name:16s} {len(rows)} frames  rows {rows}")

    os.makedirs(OUT, exist_ok=True)
    for name, strip in built:
        strip.save(os.path.join(OUT, name))
    # sweep, so a renamed verb cannot leave its old strip staged as
    # current (roster_mold's remold discipline)
    for stale in sorted(set(os.listdir(OUT)) - EXPECTED):
        if stale.endswith(".png"):
            os.remove(os.path.join(OUT, stale))
            print(f"swept stale {stale}")
    print(f"offset dx={DX} dy={DY} (derived: CENTER_X {CENTER_X}, FEET_Y "
          f"{FEET_Y}, render standing row {GROUND_ROW_64}) — standing feet "
          f"now on row {GROUND_ROW_64 + DY}, the pack's own line")
    return 0


if __name__ == "__main__":
    sys.exit(main())
