#!/usr/bin/env python3
"""Mold the walk-off render's sheets from the PixelLab CDN (2026-08-02).

Reads scripts/pixellab_walkoff_render.json — the frozen input record for
the whole-generated body fielded in walkoff.html's BODY B slot — then
downloads the template-walk, breathing-idle, run, dash, fire, and state frames for
the four molded facings and packs them into horizontal strips:

    assets/original/cipher_render/sheets/idle_{facing}.png
    assets/original/cipher_render/sheets/walk_{facing}.png
    assets/original/cipher_render/sheets/run_{facing}.png
    assets/original/cipher_render/sheets/dash_{facing}.png
    assets/original/cipher_render/sheets/kneel_{facing}.png
    assets/original/cipher_render/sheets/aim_{facing}.png
    assets/original/cipher_render/sheets/fire_{facing}.png

DASH molds from the record's `dash` block: animation frames generated on the
Dash STATE's own character/CDN, not the root character. It is a lunge, so its
ground rows are reported like RUN's gait and never enter the standing-row gate.

KNEEL molds from the record's `kneel` block: the Kneel STATE's rotations
(a sibling of the locked appearance in the same character group), the
north facing rebuilt by kneel_frames-style row surgery (the state's
north kept its head at standing height; from behind, dropping the rows
IS the pose), and a 2-frame compression breath authored here rather
than generated — the pack's KNEEL is a 2-frame held pose and this stays
in that dialect.

AIM follows the same held-pose dialect without KNEEL's north surgery: the Aim
STATE's rotations become frame 1, and frame 2 is the record's compression
breath. Like IDLE it is a full-height stand, so both states share the same
cross-facing standing-row gate.

FIRE rides those Aim rotations. Its record cuts five generated source frames
into the shipped order, then the molder executes the seam, decaying bloom,
declared muzzle, and planted-feet contracts before publishing the strips.

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

import numpy as np
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


def bloom_mask(img: Image.Image, blue_min: int) -> np.ndarray:
    rgba = np.asarray(img)
    return (rgba[:, :, 3] > 0) & (rgba[:, :, 2] >= blue_min)


def square_dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """Zero-padded square dilation without adding a scipy dependency."""
    if radius < 0:
        raise ValueError(f"dilation radius must be non-negative, got {radius}")
    if radius == 0:
        return mask.copy()
    h, w = mask.shape
    padded = np.pad(mask, radius, mode="constant", constant_values=False)
    out = np.zeros_like(mask)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            out |= padded[dy:dy + h, dx:dx + w]
    return out


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
    run = record["run"]
    run_n = run["frames_per_facing"]
    if set(run["facing_map"]) != set(record["facing_map"]):
        raise ValueError("run facing bill differs from the standing rotations: "
                         f"{sorted(run['facing_map'])}")
    dash = record["dash"]
    dash_n = dash["frames_per_facing"]
    if dash_n != 7:
        raise ValueError("dash is the room's 500ms one-shot and must mold "
                         f"exactly 7 frames per facing, got {dash_n}")
    if set(dash["facing_map"]) != set(record["facing_map"]):
        raise ValueError("dash facing bill differs from the standing rotations: "
                         f"{sorted(dash['facing_map'])}")

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

    # ---- RUN: its own block, on the root character/CDN ---------------
    for facing in record["facing_map"]:
        pl_facing = run["facing_map"][facing]
        anim_dir = run["run_animation_dirs"][pl_facing]
        strip = Image.new("RGBA", (canvas_w * run_n, canvas_h),
                          (0, 0, 0, 0))
        rows = []
        for i in range(run_n):
            frame = fetch(f"{base}/animations/{anim_dir}/{pl_facing}/{i}.png")
            if frame.size != (canvas_w, canvas_h):
                raise ValueError(f"run {pl_facing}/{i} is {frame.size}, "
                                 f"expected {canvas_w}x{canvas_h}")
            rows.append(last_opaque_row(frame))
            strip.paste(frame, (canvas_w * i, 0))
        built.append((f"run_{facing}.png", strip))
        report.append(f"{facing:5s} run rows {rows}")

    # ---- DASH: animation frames on the Dash state's own CDN ----------
    dash_base = dash["cdn_base"]
    for facing, pl_facing in dash["facing_map"].items():
        anim_dir = dash["dash_animation_dirs"][pl_facing]
        strip = Image.new("RGBA", (canvas_w * dash_n, canvas_h),
                          (0, 0, 0, 0))
        rows = []
        for i in range(dash_n):
            frame = fetch(
                f"{dash_base}/animations/{anim_dir}/{pl_facing}/{i}.png")
            if frame.size != (canvas_w, canvas_h):
                raise ValueError(f"dash {pl_facing}/{i} is {frame.size}, "
                                 f"expected {canvas_w}x{canvas_h}")
            rows.append(last_opaque_row(frame))
            strip.paste(frame, (canvas_w * i, 0))
        built.append((f"dash_{facing}.png", strip))
        report.append(f"{facing:5s} dash rows {rows}")

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

    # ---- AIM: the state's rotations + the held-pose breath -------------
    aim = record["aim"]
    if aim["frames_per_facing"] != 2:
        raise ValueError("aim is a held stance and must mold exactly 2 frames "
                         f"per facing, got {aim['frames_per_facing']}")
    if set(aim["facing_map"]) != set(record["facing_map"]):
        raise ValueError("aim facing bill differs from the standing rotations: "
                         f"{sorted(aim['facing_map'])}")
    aim_base = aim["cdn_base"]
    aim_rows = {}
    aim_stills = {}
    for facing, pl_facing in aim["facing_map"].items():
        still = fetch(f"{aim_base}/rotations/{pl_facing}.png")
        if still.size != (canvas_w, canvas_h):
            raise ValueError(f"aim rotation {pl_facing} is {still.size}, "
                             f"expected {canvas_w}x{canvas_h}")
        aim_stills[facing] = still
        frames = [still, breath_frame(still, aim["breath"])]
        rows = [last_opaque_row(frame) for frame in frames]
        aim_rows[facing] = rows[0]
        strip = Image.new("RGBA",
                          (canvas_w * len(frames), canvas_h), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            strip.paste(frame, (canvas_w * i, 0))
        built.append((f"aim_{facing}.png", strip))
        report.append(f"{facing:5s} aim rows {rows}")

    # ---- FIRE: Aim's launch frame + the record's temporal cut ----------
    fire = record["fire"]
    fire_n = fire["frames_per_facing"]
    if fire_n != 5:
        raise ValueError("fire is the room's 500ms one-shot and must mold "
                         f"exactly 5 frames per facing, got {fire_n}")
    if set(fire["facing_map"]) != set(record["facing_map"]):
        raise ValueError("fire facing bill differs from the standing rotations: "
                         f"{sorted(fire['facing_map'])}")
    for facing in fire["facing_map"]:
        stages = fire["stage_frames"].get(facing)
        if not isinstance(stages, list) or len(stages) != fire_n \
                or any(type(i) is not int or i < 0 or i >= fire_n
                       for i in stages) or stages[0] != 0:
            raise ValueError(
                f"fire stage_frames[{facing!r}] must be 5 source indices "
                f"in 0..4 and begin with 0, got {stages!r}")

    fire_base = fire["cdn_base"]
    bloom = fire["bloom"]
    for facing, pl_facing in fire["facing_map"].items():
        anim_dir = fire["fire_animation_dirs"][pl_facing]
        source = []
        for i in range(fire_n):
            frame = fetch(
                f"{fire_base}/animations/{anim_dir}/{pl_facing}/{i}.png")
            if frame.size != (canvas_w, canvas_h):
                raise ValueError(f"fire {pl_facing}/{i} is {frame.size}, "
                                 f"expected {canvas_w}x{canvas_h}")
            source.append(frame)

        frames = [source[i] for i in fire["stage_frames"][facing]]
        if not np.array_equal(np.asarray(frames[0]),
                              np.asarray(aim_stills[facing])):
            raise ValueError(f"fire {facing} frame 0 differs from its Aim "
                             "rotation — the held-stance seam is broken")
        # both ends: the lock releases into a held aim on the very next
        # update, so a last frame that only NEARLY matches the stance pops
        # visibly at 10fps (caught in review — up shipped its source settle,
        # 71px off the still, and the resume snapped)
        if not np.array_equal(np.asarray(frames[-1]),
                              np.asarray(aim_stills[facing])):
            raise ValueError(f"fire {facing} frame 4 differs from its Aim "
                             "rotation — the shot must end in the stance "
                             "that resumes")

        rows = [last_opaque_row(frame) for frame in frames]
        aim_row = aim_rows[facing]
        if any(abs(row - aim_row) > 1 for row in rows):
            raise ValueError(f"fire {facing} feet moved off Aim row "
                             f"{aim_row}±1: {rows}")

        baseline = square_dilate(
            bloom_mask(frames[0], bloom["blue_min"]),
            bloom["base_dilate_px"])
        new_masks = [bloom_mask(frame, bloom["blue_min"]) & ~baseline
                     for frame in frames]
        new_bright = [int(mask.sum()) for mask in new_masks]
        if not new_bright[1] > new_bright[2] > new_bright[3]:
            raise ValueError(f"fire {facing} bloom must strictly decay on "
                             f"frames 1-3, got {new_bright}")
        if new_bright[1] < bloom["min_burst"]:
            raise ValueError(f"fire {facing} burst is too dim: "
                             f"{new_bright[1]} < {bloom['min_burst']}")
        if new_bright[4] > bloom["max_settle"]:
            raise ValueError(f"fire {facing} settle is too bright: "
                             f"{new_bright[4]} > {bloom['max_settle']}")

        muzzle = fire["muzzle"][facing]
        hand_x, hand_y = muzzle["hand"]
        for i in range(1, 4):
            ys, xs = np.nonzero(new_masks[i])
            if muzzle["mode"] == "side":
                # the FULL forearm vector, not just its sign: bloom must sit
                # forward of the hand along the declared muzzle line (margin
                # behind, reach ahead) and within perp of the line itself —
                # a streak outward on the permitted side dies on reach, a
                # flash off the line dies on perp (caught in review; the
                # first cut compared x alone and consumed neither bound)
                dir_x, dir_y = muzzle["dir"]
                if dir_x == 0 and dir_y == 0:
                    raise ValueError(f"fire {facing} side muzzle has a zero "
                                     "direction vector")
                along = (xs - hand_x) * dir_x + (ys - hand_y) * dir_y
                perp = np.abs((xs - hand_x) * dir_y - (ys - hand_y) * dir_x)
                bad = ((along < -muzzle["margin"])
                       | (along > muzzle["reach"])
                       | (perp > muzzle["perp"]))
            elif muzzle["mode"] == "radius":
                bad = ((xs - hand_x) ** 2 + (ys - hand_y) ** 2
                       > muzzle["r"] ** 2)
            else:
                raise ValueError(f"fire {facing} has unknown muzzle mode "
                                 f"{muzzle['mode']!r}")
            if np.any(bad):
                offender = (int(xs[bad][0]), int(ys[bad][0]))
                raise ValueError(f"fire {facing} frame {i} bloom escapes "
                                 f"the declared muzzle at {offender}")

        strip = Image.new("RGBA", (canvas_w * fire_n, canvas_h),
                          (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            strip.paste(frame, (canvas_w * i, 0))
        built.append((f"fire_{facing}.png", strip))
        report.append(f"{facing:5s} fire rows {rows}  "
                      f"new_bright {new_bright}")

    all_standing_rows = {f"idle/{facing}": row
                         for facing, row in standing_rows.items()}
    all_standing_rows.update({f"aim/{facing}": row
                              for facing, row in aim_rows.items()})
    spread = sorted(set(all_standing_rows.values()))
    if spread[-1] - spread[0] > 1:
        raise ValueError(f"standing ground rows disagree by more than one: "
                         f"{all_standing_rows} — framing fault at the source")

    os.makedirs(OUT, exist_ok=True)
    for name, strip in built:
        strip.save(os.path.join(OUT, name))
    for line in report:
        print(line)

    anchor = spread[-1]
    floaters = [name for name, row in all_standing_rows.items()
                if row != anchor]
    print(f"ground row {anchor} (standing last-opaque row, pack_canvas "
          f"semantics) — walkoff.html hard-codes this as REN_GROUND_ROW")
    if floaters:
        print(f"note: {', '.join(floaters)} stands 1px above the anchor — "
              f"shipped as generated, visible in the audition, not groomed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
