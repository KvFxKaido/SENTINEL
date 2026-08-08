#!/usr/bin/env python3
"""Mold the walk-off render's sheets from the PixelLab CDN (2026-08-02).

Reads scripts/pixellab_walkoff_render.json — the frozen input record for
the whole-generated body fielded in walkoff.html's BODY B slot — then
downloads the template-walk and breathing-idle frames for the four molded
facings and packs them into horizontal strips:

    assets/original/cipher_render/sheets/idle_{facing}.png
    assets/original/cipher_render/sheets/walk_{facing}.png
    assets/original/cipher_render/sheets/kneel_{facing}.png

KNEEL molds from the record's `kneel` block: the Kneel STATE's rotations
(a sibling of the locked appearance in the same character group), the
north facing rebuilt by kneel_frames-style row surgery (the state's
north kept its head at standing height; from behind, dropping the rows
IS the pose), and a 2-frame compression breath authored here rather
than generated — the pack's KNEEL is a 2-frame held pose and this stays
in that dialect.

The rotation stills are fetched for MEASUREMENT only: the ground-row
anchor is the standing last-opaque row, and the breathing idle bobs, so
the anchor cannot be read off the frames that ship.

The raw canvas ships as generated: no re-centring, no scaling, no
re-framing. Per-frame re-centring injects sideways shimmy (pack_canvas.py
learned this the hard way), and the walk-off shows this body on its own
own canvas the way BODY B always rode its own 32x32 — the audition is
the render as it came, not the render after grooming.

Ground line measured, not chosen (pack_canvas discipline): every frame's
LAST OPAQUE ROW is printed, and the standing rows must agree across all
four rotations — that number is what walkoff.html hard-codes as the
render's ground row. Locomotion frames may dip below it; that is the
gait, not the anchor. A standing spread wider than one row is a framing
fault in the source and stops the run.

Validated, then published (caught in review): every strip is built in
memory and every check — fetch, per-frame size, the cross-facing
standing-row invariant — runs before a single file is written. A molder
that fails mid-run must leave the previous set intact; publishing as it
goes leaves a mix of fresh and stale facings that walkoff.html would
load as current, which is the exact partial-set lie compose_body.py
already refuses to tell.
"""
import io
import json
import os
import sys
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = os.path.join(HERE, "pixellab_walkoff_render.json")
OUT = os.path.join(HERE, "..", "assets", "original",
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


def north_kneel_surgery(img: Image.Image, spec: dict) -> Image.Image:
    """kneel_frames' row surgery, on the state's north rotation.

    Head and torso rows copy DOWN by `drop`, the legs absorb the loss,
    the boots keep their rows, and the jacket's last rows pool one pixel
    a side. Same algorithm, same reasoning as roster_mold.kneel_frames:
    from behind, the height loss plus the pooled hem IS the kneel — the
    one facing where 'reads as a shorter man' is not a criticism.
    """
    head_top, leg_top = spec["head_top"], spec["leg_top"]
    foot_top, d = spec["foot_top"], spec["drop"]
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img.crop((0, foot_top, w, h)), (0, foot_top))          # boots
    out.paste(img.crop((0, leg_top, w, foot_top - d)), (0, leg_top + d))
    out.paste(img.crop((0, head_top, w, leg_top)), (0, head_top + d))
    # the jacket pools: widen the last `pool_rows` torso rows a pixel a side
    px = out.load()
    for y in range(leg_top + d - spec["pool_rows"], leg_top + d):
        xs = [x for x in range(w) if px[x, y][3] > 0]
        if not xs:
            continue
        for x, sx in ((min(xs) - 1, min(xs)), (max(xs) + 1, max(xs))):
            if 0 <= x < w and px[x, y][3] == 0:
                px[x, y] = px[sx, y]
    return out


def breath_frame(img: Image.Image, spec: dict) -> Image.Image:
    """Frame 2 of a held pose: the upper body settles one pixel.

    The upper `upper_frac` of the body's rows shift down `shift_px`,
    overwriting the seam row — compression, not translation. The pack's
    2-frame KNEEL breathes at exactly this amplitude.
    """
    box = img.getbbox()
    top, bottom = box[1], box[3] - 1
    split = top + int((bottom - top + 1) * spec["upper_frac"])
    w, h = img.size
    out = img.copy()
    upper = img.crop((0, top, w, split))
    # clear the vacated row, then drop the upper block onto the seam
    out.paste(Image.new("RGBA", (w, split - top), (0, 0, 0, 0)), (0, top))
    out.paste(upper, (0, top + spec["shift_px"]), upper)
    return out


def main() -> int:
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)

    base = record["cdn_base"]
    frames_n = record["frames_per_facing"]
    canvas_w, canvas_h = (int(n) for n in record["raw_canvas"].split("x"))

    # Build and check EVERYTHING before writing ANYTHING — see the
    # validated-then-published clause in the docstring.
    idle_n = record["idle_frames_per_facing"]
    standing_rows = {}
    built = []
    report = []
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
            built.append((f"{anim}_{facing}.png", strip))
            rows_by_anim[anim] = rows
        report.append(f"{facing:5s} stand row {standing_rows[facing]}  "
                      f"idle rows {rows_by_anim['idle']}  "
                      f"walk rows {rows_by_anim['walk']}")

    # ---- KNEEL: the state's rotations, molded (see the kneel block) ----
    kneel = record["kneel"]
    kneel_base = kneel["cdn_base"]
    for facing, pl_facing in kneel["facing_map"].items():
        still = fetch(f"{kneel_base}/rotations/{pl_facing}.png")
        if still.size != (canvas_w, canvas_h):
            raise ValueError(f"kneel rotation {pl_facing} is {still.size}, "
                             f"expected {canvas_w}x{canvas_h}")
        if facing == "up":
            still = north_kneel_surgery(still, kneel["north_surgery"])
        frames = [still, breath_frame(still, kneel["breath"])]
        strip = Image.new("RGBA",
                          (canvas_w * len(frames), canvas_h), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            strip.paste(frame, (canvas_w * i, 0))
        built.append((f"kneel_{facing}.png", strip))
        report.append(f"{facing:5s} kneel rows "
                      f"{[last_opaque_row(f) for f in frames]}"
                      f"{'  (north: row surgery)' if facing == 'up' else ''}")

    spread = sorted(set(standing_rows.values()))
    if spread[-1] - spread[0] > 1:
        raise ValueError(f"standing ground rows disagree by more than one: "
                         f"{standing_rows} — framing fault at the source")

    os.makedirs(OUT, exist_ok=True)
    for name, strip in built:
        strip.save(os.path.join(OUT, name))
    for line in report:
        print(line)

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
