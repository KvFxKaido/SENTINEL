#!/usr/bin/env python3
"""Pack numbered frame PNGs into one horizontal sheet (2026-08-02).

The demos consume the pack's sheet format — N frames laid left to right in
a single PNG, `<verb>_<facing>.png` — because that is what the licensed
pack ships and what roster_mold.py emits. Generated animations arrive as
loose per-frame files instead. Rather than teach a renderer a second,
generated-only layout, the frames get packed into the format everything
already reads.

Deliberately generic: it takes a directory of frames and a target, and
knows nothing about Cipher, walks, or any particular character.

Frames must all share one canvas size — a sheet has a fixed stride, so a
mismatch is an error, not something to paper over by padding. Output is
byte-verified against the inputs: nothing here is permitted to resample.

Usage:
    python pack_strip.py FRAME_DIR OUT.png
    python pack_strip.py FRAME_DIR OUT.png --frames 8
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image


def pack(frame_paths, out_path):
    if not frame_paths:
        raise ValueError("no frames given")
    frames = [Image.open(p).convert("RGBA") for p in frame_paths]
    w, h = frames[0].size
    for p, f in zip(frame_paths, frames):
        if f.size != (w, h):
            raise ValueError(
                f"{os.path.basename(p)} is {f.size[0]}x{f.size[1]}, expected {w}x{h} — "
                "a sheet has one stride; mixed sizes cannot be packed")

    sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * w, 0))

    # "Packed, not repainted" — execute it.
    arr = np.array(sheet)
    for i, f in enumerate(frames):
        if not np.array_equal(arr[:, i * w:(i + 1) * w], np.array(f)):
            raise AssertionError(f"frame {i} differs from its source after packing")

    sheet.save(out_path)
    return len(frames), w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="directory of frame PNGs, packed in sorted filename order")
    ap.add_argument("dst", help="output sheet path")
    ap.add_argument("--frames", type=int, default=None,
                    help="assert this many frames; fail if the count differs")
    a = ap.parse_args()

    paths = [os.path.join(a.src, n) for n in sorted(os.listdir(a.src))
             if n.lower().endswith(".png")]
    if a.frames is not None and len(paths) != a.frames:
        sys.exit(f"expected {a.frames} frames, found {len(paths)} in {a.src}")

    n, w, h = pack(paths, a.dst)
    print(f"{a.dst}: {n} frames of {w}x{h} -> {w * n}x{h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
