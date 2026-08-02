#!/usr/bin/env python3
"""Mold the walk-off render's sheets from the PixelLab CDN (2026-08-02).

Reads scripts/pixellab_walkoff_render.json — the frozen input record for
the whole-generated body fielded in walkoff.html's BODY B slot — then
downloads the template-walk and breathing-idle frames for the four molded
facings and packs them into horizontal strips:

    assets/sprites/generated/cipher_render/sheets/idle_{facing}.png
    assets/sprites/generated/cipher_render/sheets/walk_{facing}.png

The rotation stills are fetched for MEASUREMENT only: the ground-row
anchor is the standing last-opaque row, and the breathing idle bobs, so
the anchor cannot be read off the frames that ship.

The raw canvas ships as generated: no re-centring, no scaling, no
re-framing. Per-frame re-centring injects sideways shimmy (pack_canvas.py
learned this the hard way), and the walk-off shows this body on its own
68x68 canvas the way BODY B always rode its own 32x32 — the audition is
the render as it came, not the render after grooming.

Ground line measured, not chosen (pack_canvas discipline): every frame's
LAST OPAQUE ROW is printed, and the standing rows must agree across all
four rotations — that number is what walkoff.html hard-codes as the
render's ground row. Locomotion frames may dip below it; that is the
gait, not the anchor. A standing spread wider than one row is a framing
fault in the source and stops the run.
"""
import io
import json
import os
import sys
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = os.path.join(HERE, "pixellab_walkoff_render.json")
OUT = os.path.join(HERE, "..", "assets", "sprites", "generated",
                   "cipher_render", "sheets")


def fetch(url: str) -> Image.Image:
    # The CDN 403s urllib's default Python-urllib agent; curl's sails through.
    request = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return Image.open(io.BytesIO(response.read())).convert("RGBA")


def last_opaque_row(img: Image.Image) -> int:
    box = img.getbbox()  # exclusive bottom: the row index is bbox[3] - 1
    if box is None:
        raise ValueError("frame is fully transparent")
    return box[3] - 1


def main() -> int:
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)

    base = record["cdn_base"]
    frames_n = record["frames_per_facing"]
    canvas_w, canvas_h = (int(n) for n in record["raw_canvas"].split("x"))
    os.makedirs(OUT, exist_ok=True)

    idle_n = record["idle_frames_per_facing"]
    standing_rows = {}
    for facing, pl_facing in record["facing_map"].items():
        rotation = fetch(f"{base}/rotations/{pl_facing}.png")
        if rotation.size != (canvas_w, canvas_h):
            raise ValueError(f"rotation {pl_facing} is {rotation.size}, "
                             f"expected {canvas_w}x{canvas_h}")
        standing_rows[facing] = last_opaque_row(rotation)

        sheets = (("idle", record["idle_animation_dirs"], idle_n),
                  ("walk", record["walk_animation_dirs"], frames_n))
        rows_by_anim = {}
        for anim, dirs, n in sheets:
            anim_dir = dirs[pl_facing]
            strip = Image.new("RGBA", (canvas_w * n, canvas_h), (0, 0, 0, 0))
            rows = []
            for i in range(n):
                frame = fetch(f"{base}/animations/{anim_dir}/{pl_facing}/{i}.png")
                if frame.size != (canvas_w, canvas_h):
                    raise ValueError(f"{anim} {pl_facing}/{i} is {frame.size}, "
                                     f"expected {canvas_w}x{canvas_h}")
                rows.append(last_opaque_row(frame))
                strip.paste(frame, (canvas_w * i, 0))
            strip.save(os.path.join(OUT, f"{anim}_{facing}.png"))
            rows_by_anim[anim] = rows
        print(f"{facing:5s} stand row {standing_rows[facing]}  "
              f"idle rows {rows_by_anim['idle']}  "
              f"walk rows {rows_by_anim['walk']}")

    spread = sorted(set(standing_rows.values()))
    if spread[-1] - spread[0] > 1:
        raise ValueError(f"standing ground rows disagree by more than one: "
                         f"{standing_rows} — framing fault at the source")
    anchor = spread[-1]
    floaters = [f for f, row in standing_rows.items() if row != anchor]
    print(f"ground row {anchor} (standing last-opaque row, pack_canvas "
          f"semantics) — walkoff.html hard-codes this as REN_GROUND_ROW")
    if floaters:
        print(f"note: {', '.join(floaters)} stands 1px above the anchor — "
              f"shipped as generated, visible in the audition, not groomed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
