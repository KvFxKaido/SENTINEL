#!/usr/bin/env python3
"""Re-frame the room squad's sheets onto the canon 96x80 body canvas.

Reads the 24 IDLE/KNEEL sheets molded by squad_render_sheets.py and executes
the squad record's anchor law: translation only, with one constant offset per
strip. This deliberately differs from render_canvas96.py's single recorded
constant. The squad's generated states wobble +/-2 rows on the ground line;
Cipher's never did. Per-frame anchoring would erase that authored movement,
so each strip derives dy from its maximum last-opaque row and applies it to
every frame unchanged.

    dx = CENTER_X - (fighter_canvas - 1) / 2
    dy = FEET_Y - max(frame last-opaque rows in this strip)

Reads  assets/original/squad_render/sheets/
       {fighter}/{idle,kneel}_{down,up,left,right}.png
Writes assets/original/squad_render/sheets96/... same names, frames at 96x80.

Validated, then published: the source bill is exact, all 24 strips are rebuilt
in memory, and every size, fit, byte-equality, and ground-anchor check passes
before any output is written. Publication then sweeps stale PNGs and verifies
the output side is the exact same bill.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

from pack_canvas import CANVAS_H, CANVAS_W, CENTER_X, FEET_Y

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = os.path.join(HERE, "pixellab_squad_render.json")
SRC = os.path.join(HERE, "..", "assets", "original",
                   "squad_render", "sheets")
OUT = os.path.join(HERE, "..", "assets", "original",
                   "squad_render", "sheets96")

FIGHTERS = ("vesper", "koa", "sable")
FACINGS = ("down", "up", "left", "right")
FRAME_COUNTS = {"idle": 4, "kneel": 2}
EXPECTED = {os.path.join(fighter, f"{verb}_{facing}.png")
            for fighter in FIGHTERS
            for verb in FRAME_COUNTS
            for facing in FACINGS}


def last_opaque_row(img: Image.Image) -> int:
    box = img.getbbox()  # exclusive bottom: the row index is bbox[3] - 1
    if box is None:
        raise ValueError("frame is fully transparent")
    return box[3] - 1


def png_set(root: str) -> set[str]:
    if not os.path.isdir(root):
        return set()
    present = set()
    for directory, _, names in os.walk(root):
        for name in names:
            if name.lower().endswith(".png"):
                present.add(os.path.relpath(
                    os.path.join(directory, name), root))
    return present


def checked_bill(present: set[str], expected: set[str], label: str) -> None:
    missing = sorted(expected - present)
    extra = sorted(present - expected)
    if missing or extra:
        raise ValueError(
            f"{label} set is not the squad molder's bill — missing: "
            f"{missing or 'none'}, unexpected: {extra or 'none'}")


def frame_count(name: str) -> int:
    basename = os.path.basename(name)
    verb = basename.split("_", 1)[0]
    try:
        return FRAME_COUNTS[verb]
    except KeyError as exc:
        raise ValueError(f"{name} has unknown verb {verb!r}") from exc


def _translate(strip: Image.Image, name: str, canvas: int, count: int,
               dx: int, dy: int) -> tuple[Image.Image, list[int], list[int]]:
    expected_size = (canvas * count, canvas)
    if strip.size != expected_size:
        raise ValueError(f"{name} is {strip.size[0]}x{strip.size[1]}; "
                         f"expected {count} frames at {canvas}x{canvas} "
                         f"({expected_size[0]}x{expected_size[1]} strip)")

    # The whole source CANVAS must land inside the target. Testing only the
    # opaque bbox would silently permit a crop of the generated frame law.
    if dx < 0 or dy < 0 or dx + canvas > CANVAS_W \
            or dy + canvas > CANVAS_H:
        raise AssertionError(
            f"{name}: {canvas}-canvas at ({dx},{dy}) exceeds "
            f"{CANVAS_W}x{CANVAS_H}")

    out = Image.new("RGBA", (CANVAS_W * count, CANVAS_H), (0, 0, 0, 0))
    src_rows = []
    dst_rows = []
    for index in range(count):
        frame = strip.crop((canvas * index, 0,
                            canvas * (index + 1), canvas))
        src_row = last_opaque_row(frame)
        out_x = CANVAS_W * index + dx
        out.paste(frame, (out_x, dy))

        # The claim is "translated, never resampled" — execute it per frame.
        placed = np.asarray(out)[dy:dy + canvas, out_x:out_x + canvas]
        if not np.array_equal(placed, np.asarray(frame)):
            raise AssertionError(f"{name} frame {index}: placed pixels differ "
                                 "from source — this resampled")
        reframed = out.crop((CANVAS_W * index, 0,
                            CANVAS_W * (index + 1), CANVAS_H))
        dst_row = last_opaque_row(reframed)
        if dst_row != src_row + dy:
            raise AssertionError(f"{name} frame {index}: ground row "
                                 f"{dst_row} did not shift from {src_row} "
                                 f"by exactly dy={dy}")
        src_rows.append(src_row)
        dst_rows.append(dst_row)

    if any(row > FEET_Y for row in dst_rows):
        raise AssertionError(f"{name}: re-framed ground rows {dst_rows} "
                             f"cross below FEET_Y {FEET_Y}")
    if max(dst_rows) != FEET_Y:
        raise AssertionError(f"{name}: re-framed max ground row "
                             f"{max(dst_rows)} != FEET_Y {FEET_Y} — the "
                             f"strip anchor did not execute (dx={dx}, dy={dy})")
    return out, src_rows, dst_rows


def reframe(strip: Image.Image, name: str, canvas: int, count: int
            ) -> tuple[Image.Image, list[int], list[int], int, int]:
    expected_size = (canvas * count, canvas)
    if strip.size != expected_size:
        raise ValueError(f"{name} is {strip.size[0]}x{strip.size[1]}; "
                         f"expected {count} frames at {canvas}x{canvas} "
                         f"({expected_size[0]}x{expected_size[1]} strip)")
    frames = [strip.crop((canvas * index, 0,
                          canvas * (index + 1), canvas))
              for index in range(count)]
    strip_ground = max(last_opaque_row(frame) for frame in frames)

    dx = CENTER_X - (canvas - 1) / 2
    if dx != int(dx):
        raise AssertionError(
            f"{name}: dx {dx} is not integer for canvas {canvas} — "
            "translation-only forbids it")
    dx = int(dx)
    dy = FEET_Y - strip_ground

    out, src_rows, dst_rows = _translate(
        strip, name, canvas, count, dx, dy)
    if max(src_rows) != strip_ground:
        raise AssertionError(f"{name}: measured strip ground {strip_ground} "
                             f"disagrees with frame rows {src_rows}")
    return out, src_rows, dst_rows, dx, dy


def validate_record(record: dict) -> None:
    if (CANVAS_W, CANVAS_H) != (96, 80):
        raise AssertionError("pack_canvas law drifted: expected 96x80, got "
                             f"{CANVAS_W}x{CANVAS_H}")
    if tuple(record.get("fighters", ())) != FIGHTERS:
        raise ValueError("fighter bill must be exactly "
                         f"{list(FIGHTERS)}, got "
                         f"{list(record.get('fighters', {}))}")
    if tuple(record.get("facing_map", ())) != FACINGS:
        raise ValueError("facing_map order must be exactly "
                         f"{list(FACINGS)}, got "
                         f"{list(record.get('facing_map', {}))}")
    if record.get("idle_frames_per_facing") != FRAME_COUNTS["idle"]:
        raise ValueError("record idle frame count differs from the 4-frame "
                         f"bill: {record.get('idle_frames_per_facing')!r}")
    if record.get("kneel_frames_per_facing") != FRAME_COUNTS["kneel"]:
        raise ValueError("record kneel frame count differs from the 2-frame "
                         f"bill: {record.get('kneel_frames_per_facing')!r}")
    for fighter, spec in record["fighters"].items():
        canvas = spec.get("canvas")
        if type(canvas) is not int or canvas <= 0:
            raise ValueError(f"{fighter} canvas must be a positive int, "
                             f"got {canvas!r}")


def main() -> int:
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    validate_record(record)

    checked_bill(png_set(SRC), EXPECTED, "source")

    # Build and check EVERYTHING before writing ANYTHING — see the
    # validated-then-published clause in the docstring.
    built = []
    report = []
    for relative in sorted(EXPECTED):
        fighter = relative.split(os.sep, 1)[0]
        canvas = record["fighters"][fighter]["canvas"]
        count = frame_count(relative)
        source = os.path.join(SRC, relative)
        with Image.open(source) as image:
            strip = image.convert("RGBA")
        reframed, src_rows, dst_rows, dx, dy = reframe(
            strip, relative, canvas, count)
        built.append((relative, reframed))
        report.append(
            f"{relative}  {count} frames  source rows {src_rows}  "
            f"offset ({dx},{dy})  rows96 {dst_rows}")

    built_names = {name for name, _ in built}
    checked_bill(built_names, EXPECTED, "built")

    for relative, strip in built:
        path = os.path.join(OUT, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        strip.save(path)
    # Sweep only after every strip passed, so a failed check leaves the
    # previously published set intact rather than half-current.
    for stale in sorted(png_set(OUT) - EXPECTED):
        os.remove(os.path.join(OUT, stale))
        print(f"swept stale {stale}")
    checked_bill(png_set(OUT), EXPECTED, "output")

    for line in report:
        print(line)
    print(f"published {len(built)} 96x80 squad sheets to "
          f"{os.path.normpath(OUT)}; source and output bills exact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
