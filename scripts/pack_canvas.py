#!/usr/bin/env python3
"""Re-canvas a generated sprite onto the pack's 96x80 body canvas (2026-08-02).

PixelLab emits square canvases sized to its own framing (a 40px character
lands on 60x60). The canon body canvas is the pack's 96x80 with the feet
on the ground line — so a generated sprite that is otherwise at the right
scale still cannot enter the pipeline until it is re-framed.

This does the re-framing the only way the body law permits: **translation
only**. No asset here is ever created by scaling another (art_direction
"one canvas, integer zoom"), so this pads and shifts, and then proves it
by byte-comparing the placed pixels against the source crop. If the body
does not fit the target canvas the run fails rather than shrinking it —
a sprite that needs scaling is a sprite that was generated at the wrong
size, and the fix belongs upstream at generation time.

Ground line measured off the molded roster, not chosen: canon Cipher's
standing verbs (idle/aim/fire/heal/attack1) put their LAST OPAQUE ROW at
y=57 with a 19x34 body centred on x=46.5. Locomotion verbs dip a pixel
to y=58 mid-stride, which is the gait, not the anchor. Note getbbox()
reports an exclusive bottom, so those frames read as bbox[3]=58 — the
row index is one less, and mixing the two puts every sprite a pixel
into the floor.

Usage:
    python pack_canvas.py IN.png OUT.png [--feet 58] [--cx 46.5]
    python pack_canvas.py IN_DIR OUT_DIR            (every *.png in dir)
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image

CANVAS_W, CANVAS_H = 96, 80
FEET_Y = 57      # last opaque ROW of the pack's standing verbs (not bbox[3])
CENTER_X = 46.5  # bbox centre of the pack's standing verbs


def place(src: Image.Image, feet_y: int = FEET_Y, cx: float = CENTER_X) -> Image.Image:
    src = src.convert("RGBA")
    box = src.getbbox()
    if box is None:
        raise ValueError("source is fully transparent")
    body = src.crop(box)
    w, h = body.size
    if w > CANVAS_W or h > CANVAS_H:
        raise ValueError(
            f"body {w}x{h} does not fit {CANVAS_W}x{CANVAS_H} — regenerate smaller, "
            "do not scale (body law: one canvas, integer zoom)")

    # Half-up, not round(): Python rounds halves to even, so on a centre of
    # 46.5 the even widths alternate 46.0 / 47.0 as w steps 16, 18, 20 — a
    # full pixel of horizontal swing between frames. Body width changes
    # frame to frame across an animation, so that lands as sideways shimmy
    # in the cycle. Half-up pins every width to 46.5 or 47.0, which is the
    # irreducible spread when placing an even-width body on a .5 centre.
    x0 = math.floor(cx - w / 2 + 0.5)
    y0 = feet_y - h + 1
    if x0 < 0 or y0 < 0 or x0 + w > CANVAS_W or y0 + h > CANVAS_H:
        raise ValueError(f"body {w}x{h} at ({x0},{y0}) falls outside the canvas")

    out = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    out.paste(body, (x0, y0))

    # The claim is "translated, never resampled" — execute it.
    placed = np.array(out)[y0:y0 + h, x0:x0 + w]
    if not np.array_equal(placed, np.array(body)):
        raise AssertionError("placed pixels differ from source — this resampled")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--feet", type=int, default=FEET_Y)
    ap.add_argument("--cx", type=float, default=CENTER_X)
    a = ap.parse_args()

    pairs = []
    if os.path.isdir(a.src):
        os.makedirs(a.dst, exist_ok=True)
        for n in sorted(os.listdir(a.src)):
            if n.lower().endswith(".png"):
                pairs.append((os.path.join(a.src, n), os.path.join(a.dst, n)))
    else:
        pairs.append((a.src, a.dst))

    for s, d in pairs:
        img = place(Image.open(s), a.feet, a.cx)
        img.save(d)
        b = Image.open(s).convert("RGBA").getbbox()
        print(f"{os.path.basename(s):24s} {b[2]-b[0]:2d}x{b[3]-b[1]:2d} "
              f"-> {CANVAS_W}x{CANVAS_H}  feet_y={a.feet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
