#!/usr/bin/env python3
"""Mold the room squad's IDLE and KNEEL sheets from its PixelLab record.

Reads scripts/pixellab_squad_render.json, the frozen provenance and check
record for VESPER, KOA, and SABLE, then downloads each identity rotation,
breathing-idle animation, and kneel state. The raw generated canvases ship
unchanged here: no centring, scaling, or re-framing belongs in the molder.

KNEEL is the state still plus the record's 2-frame compression breath. Koa's
right kneel is the one declared exception: PixelLab rolled the wrong facing,
so the accepted south-west still is mirrored into the south-east slot.

The identity rotation is measurement truth for both the recorded standing
row and the fighter's palette mark. Every shipped frame must remain within
the record's mark-count slack of that facing's identity still; the guard is
deliberately narrow identity-loss evidence, not an art-direction verdict.

Writes, in the record's facing order:

    assets/original/squad_render/sheets/{fighter}/idle_{facing}.png
    assets/original/squad_render/sheets/{fighter}/kneel_{facing}.png

Validated, then published: all 24 strips and every fetch, size, standing-row,
and mark guard check complete in memory before a single file is written. A
failed remold therefore cannot leave the room loading a fresh/stale mixture.
"""
import io
import json
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = os.path.join(HERE, "pixellab_squad_render.json")
OUT = os.path.join(HERE, "..", "assets", "original",
                   "squad_render", "sheets")

FIGHTERS = ("vesper", "koa", "sable")
FACINGS = ("down", "up", "left", "right")


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


def checked_size(img: Image.Image, canvas: int, label: str) -> None:
    if img.size != (canvas, canvas):
        raise ValueError(f"{label} is {img.size}, expected {canvas}x{canvas}")


def mark_count(img: Image.Image, rgb: list[int], tol: int) -> int:
    rgba = np.asarray(img)
    delta = rgba[:, :, :3].astype(np.int32) - np.asarray(rgb, dtype=np.int32)
    near = np.sum(delta * delta, axis=2) <= tol * tol
    return int(np.count_nonzero((rgba[:, :, 3] > 0) & near))


# Copied rather than imported from walkoff_render_sheets.py: this molder's
# reproducible inputs remain the one squad record plus the CDN, and importing
# the much larger Cipher molder would couple two otherwise independent bills.
def breath_frame(img: Image.Image, spec: dict) -> Image.Image:
    """Frame 2 of a held pose: the upper body settles one pixel."""
    box = img.getbbox()
    if box is None:
        raise ValueError("cannot breathe a fully transparent frame")
    top, bottom = box[1], box[3] - 1
    split = top + int((bottom - top + 1) * spec["upper_frac"])
    w, _ = img.size
    out = img.copy()
    upper = img.crop((0, top, w, split))
    # Clear the vacated rows, then drop the upper block onto the seam:
    # compression, not translation, in the pack's held-pose dialect.
    out.paste(Image.new("RGBA", (w, split - top), (0, 0, 0, 0)), (0, top))
    out.paste(upper, (0, top + spec["shift_px"]), upper)
    return out


def checked_mark_count(frame: Image.Image, fighter: str, verb: str,
                       facing: str, index: int, baseline: int,
                       rgb: list[int], tol: int, slack: int) -> int:
    count = mark_count(frame, rgb, tol)
    delta = abs(count - baseline)
    if delta > slack:
        raise ValueError(
            f"{fighter} {verb} {facing} frame {index} mark count {count} "
            f"differs from identity {baseline} by {delta}, above slack "
            f"{slack} (mark {rgb}, tol {tol})")
    return count


def validate_record(record: dict) -> None:
    if tuple(record.get("fighters", ())) != FIGHTERS:
        raise ValueError("fighter bill must be exactly "
                         f"{list(FIGHTERS)}, got "
                         f"{list(record.get('fighters', {}))}")
    if tuple(record.get("facing_map", ())) != FACINGS:
        raise ValueError("facing_map order must be exactly "
                         f"{list(FACINGS)}, got "
                         f"{list(record.get('facing_map', {}))}")
    if record.get("idle_frames_per_facing") != 4:
        raise ValueError("the room pins IDLE to exactly 4 frames, got "
                         f"{record.get('idle_frames_per_facing')!r}")
    if record.get("kneel_frames_per_facing") != 2:
        raise ValueError("the held KNEEL must be exactly 2 frames, got "
                         f"{record.get('kneel_frames_per_facing')!r}")

    guard = record.get("mark_guard", {})
    for name in ("tol", "slack"):
        value = guard.get(name)
        if type(value) is not int or value < 0:
            raise ValueError(f"mark_guard.{name} must be a non-negative int, "
                             f"got {value!r}")

    pl_facings = set(record["facing_map"].values())
    for fighter, spec in record["fighters"].items():
        canvas = spec.get("canvas")
        if type(canvas) is not int or canvas <= 0:
            raise ValueError(f"{fighter} canvas must be a positive int, "
                             f"got {canvas!r}")
        if set(spec.get("standing_rows", {})) != set(FACINGS):
            raise ValueError(f"{fighter} standing_rows bill differs from "
                             f"{list(FACINGS)}: "
                             f"{sorted(spec.get('standing_rows', {}))}")
        if set(spec.get("idle_animation_dirs", {})) != pl_facings:
            raise ValueError(f"{fighter} idle animation facings differ from "
                             f"facing_map: "
                             f"{sorted(spec.get('idle_animation_dirs', {}))}")
        rgb = spec.get("mark_rgb")
        if not isinstance(rgb, list) or len(rgb) != 3 \
                or any(type(channel) is not int or not 0 <= channel <= 255
                       for channel in rgb):
            raise ValueError(f"{fighter} mark_rgb must be three bytes, "
                             f"got {rgb!r}")
    if record["fighters"]["koa"].get("kneel_right_mirror") is not True:
        raise ValueError("koa kneel_right_mirror must be true — the record's "
                         "accepted right-facing source is mirrored south-west")


def main() -> int:
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    validate_record(record)

    cdn_root = record["cdn_root"].rstrip("/")
    idle_n = record["idle_frames_per_facing"]
    breath = record["breath"]
    tol = record["mark_guard"]["tol"]
    slack = record["mark_guard"]["slack"]

    # Build and check EVERYTHING before writing ANYTHING — see the
    # validated-then-published clause in the docstring.
    built = []
    report = []
    for fighter, spec in record["fighters"].items():
        canvas = spec["canvas"]
        identity_id = spec["identity_character_id"]
        kneel_id = spec["kneel_state_id"]
        mark_rgb = spec["mark_rgb"]
        for facing, pl_facing in record["facing_map"].items():
            identity_url = (f"{cdn_root}/{identity_id}/rotations/"
                            f"{pl_facing}.png")
            identity = fetch(identity_url)
            checked_size(identity, canvas,
                         f"{fighter} identity rotation {pl_facing}")
            identity_row = last_opaque_row(identity)
            recorded_row = spec["standing_rows"][facing]
            if identity_row != recorded_row:
                raise ValueError(
                    f"{fighter} identity {facing} standing row "
                    f"{identity_row} != recorded {recorded_row} — the "
                    "upstream identity was re-rolled or the record drifted")
            identity_mark = mark_count(identity, mark_rgb, tol)

            idle_frames = []
            idle_rows = []
            idle_marks = []
            anim_dir = spec["idle_animation_dirs"][pl_facing]
            for index in range(idle_n):
                url = (f"{cdn_root}/{identity_id}/animations/{anim_dir}/"
                       f"{pl_facing}/{index}.png")
                frame = fetch(url)
                checked_size(frame, canvas,
                             f"{fighter} idle {pl_facing}/{index}")
                idle_frames.append(frame)
                idle_rows.append(last_opaque_row(frame))
                idle_marks.append(checked_mark_count(
                    frame, fighter, "idle", facing, index, identity_mark,
                    mark_rgb, tol, slack))

            kneel_source = pl_facing
            mirrored = (fighter == "koa" and facing == "right"
                        and spec["kneel_right_mirror"])
            if mirrored:
                kneel_source = record["facing_map"]["left"]
            kneel_url = (f"{cdn_root}/{kneel_id}/rotations/"
                          f"{kneel_source}.png")
            kneel_still = fetch(kneel_url)
            checked_size(kneel_still, canvas,
                         f"{fighter} kneel rotation {kneel_source}")
            if mirrored:
                kneel_still = kneel_still.transpose(
                    Image.Transpose.FLIP_LEFT_RIGHT)
            kneel_frames = [kneel_still, breath_frame(kneel_still, breath)]
            kneel_rows = [last_opaque_row(frame) for frame in kneel_frames]
            kneel_marks = [checked_mark_count(
                frame, fighter, "kneel", facing, index, identity_mark,
                mark_rgb, tol, slack)
                for index, frame in enumerate(kneel_frames)]

            for verb, frames in (("idle", idle_frames),
                                 ("kneel", kneel_frames)):
                strip = Image.new("RGBA", (canvas * len(frames), canvas),
                                  (0, 0, 0, 0))
                for index, frame in enumerate(frames):
                    strip.paste(frame, (canvas * index, 0))
                relative = os.path.join(fighter, f"{verb}_{facing}.png")
                built.append((relative, strip))

            report.append(
                f"{fighter}/idle_{facing}.png  {idle_n} frames  "
                f"rows {idle_rows}  marks {idle_marks} "
                f"(identity {identity_mark})")
            mirror_note = "  source south-west mirrored" if mirrored else ""
            report.append(
                f"{fighter}/kneel_{facing}.png  2 frames  "
                f"rows {kneel_rows}  marks {kneel_marks} "
                f"(identity {identity_mark}){mirror_note}")

    expected = {os.path.join(fighter, f"{verb}_{facing}.png")
                for fighter in FIGHTERS
                for verb in ("idle", "kneel")
                for facing in FACINGS}
    built_names = {name for name, _ in built}
    if len(built) != len(expected) or built_names != expected:
        raise AssertionError(
            f"built sheet bill differs — missing "
            f"{sorted(expected - built_names) or 'none'}, unexpected "
            f"{sorted(built_names - expected) or 'none'}")

    for relative, strip in built:
        path = os.path.join(OUT, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        strip.save(path)
    for line in report:
        print(line)
    print(f"published {len(built)} squad sheets to {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
