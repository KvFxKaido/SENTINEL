"""Anchor a rendered strip to the pack's ground line — ONCE per strip.

Per-frame anchoring (pack_canvas.py, which is right for a static rotation)
is wrong for an animation: it pins each frame's own silhouette to the same
row, which subtracts a different amount per frame and so edits the gait.
Measured on the first attempt: south shifted 0,0,+1,0,0,0,+1,0 and east
shifted -2,-1,0,-1,-2,-1,0,-1 — the bob was not hidden, it was rewritten,
differently per facing.

So the anchor comes from the RIG's ground origin projected into the render
(recorded by mannequin.py), not from any frame's pixels. One translation
per strip; every frame keeps its position relative to the ground.

Usage: python anchor_strip.py SRC_DIR DST_DIR ground_NAME.json [--ground-row 58]
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image

CANON_GROUND_ROW = 58          # canon's last opaque row is 57; ground is 58


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("meta")
    ap.add_argument("--ground-row", type=int, default=CANON_GROUND_ROW)
    a = ap.parse_args()

    with open(a.meta) as fh:
        meta = json.load(fh)
    # half-up, matching pack_canvas: banker's rounding alternates on .5 and
    # would shift some facings a pixel differently from others for no reason
    dy = math.floor(a.ground_row - meta["ground_row"] + 0.5)
    os.makedirs(a.dst, exist_ok=True)

    names = sorted(n for n in os.listdir(a.src) if n.lower().endswith(".png"))
    moved = []
    for n in names:
        src = Image.open(os.path.join(a.src, n)).convert("RGBA")
        arr = np.array(src)
        out = np.zeros_like(arr)
        h = arr.shape[0]
        # one shared translation — the whole strip moves together
        if dy >= 0:
            out[dy:h] = arr[0:h - dy] if dy else arr
        else:
            out[0:h + dy] = arr[-dy:h]
        img = Image.fromarray(out)
        img.save(os.path.join(a.dst, n))
        b = img.getbbox()
        moved.append(b[3] - 1 if b else None)

    print(f"{meta['facing']}: dy={dy:+d} applied to all {len(names)} frames; "
          f"last opaque rows now {moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
