#!/usr/bin/env python3
"""Mold the squad's FULL render roster from its PixelLab record.

Reads scripts/pixellab_squad_render.json, the frozen provenance and check
record for VESPER, KOA, SABLE, and SYN, then downloads and validates every
verb the yard stages: idle, kneel, run, aim, fire, hurt, death. The raw
generated canvases ship unchanged here: no centring, scaling, or re-framing
belongs in the molder (squad_canvas96.py owns the re-frame).

Verb sources and their contracts:

  idle   identity animations, 4f - mark guard
  kneel  state stills + breath, 2f - koa's right is the declared mirror of
         south-west; SYN's north is kneel_frames row surgery on the IDENTITY
         north rotation (the pack's own north-kneel construction - his state
         ladder stood tall and painted lenses on the back of the head)
  aim    aim-state stills + breath, 2f - standing rows held EXACTLY
  run    identity animations, 8f - gait dips are authored; mark guard only
  hurt   identity animations, 4f - planted rows, recovery floor, mark guard
  death  identity animations, 9f - the yard HOLDS the last frame: flat
         contract + final row band + mark guard
  fire   AIM-state animations, 5f STAGE-MAPPED per the record (the scalpel
         cuts time): both ends must equal the aim still byte-for-byte (the
         resume seam), the shipped strip must decay in bright-CHANGED pixels
         (the squad's head-on flashes sit INSIDE the silhouette, where
         cipher's outside-baseline mask is blind), and bloom that does leave
         the silhouette must sit within the declared muzzle radius (the
         declaration is the accepted art, per heal's precedent - no rig
         socket exists for the squad bodies)

Writes, in the record's facing order:

    assets/original/squad_render/sheets/{fighter}/{verb}_{facing}.png

Validated, then published: all 112 strips and every fetch, size, seam, row,
decay, containment, and mark check complete in memory before a single file
is written. A failed remold therefore cannot leave the yard loading a
fresh/stale mixture.
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

FIGHTERS = ("vesper", "koa", "sable", "syn")
FACINGS = ("down", "up", "left", "right")
VERBS = ("idle", "kneel", "run", "aim", "fire", "hurt", "death")


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


def bbox_height(img: Image.Image) -> int:
    box = img.getbbox()
    if box is None:
        raise ValueError("frame is fully transparent")
    return box[3] - box[1]


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


def kneel_surgery(img: Image.Image, spec: dict) -> Image.Image:
    """kneel_frames' row surgery, on SYN's identity north rotation.

    Head and torso rows copy DOWN by `drop`, the legs absorb the loss, the
    boots keep their rows, and the jacket's last rows pool one pixel a side.
    Same algorithm as walkoff_render_sheets.north_kneel_surgery and
    roster_mold.kneel_frames: from behind, the height loss plus the pooled
    hem IS the kneel.
    """
    head_top, leg_top = spec["head_top"], spec["leg_top"]
    foot_top, d = spec["foot_top"], spec["drop"]
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img.crop((0, foot_top, w, h)), (0, foot_top))          # boots
    out.paste(img.crop((0, leg_top, w, foot_top - d)), (0, leg_top + d))
    out.paste(img.crop((0, head_top, w, leg_top)), (0, head_top + d))
    px = out.load()
    for y in range(leg_top + d - spec["pool_rows"], leg_top + d):
        xs = [x for x in range(w) if px[x, y][3] > 0]
        if not xs:
            continue
        for x, sx in ((min(xs) - 1, min(xs)), (max(xs) + 1, max(xs))):
            if 0 <= x < w and px[x, y][3] == 0:
                px[x, y] = px[sx, y]
    return out


def square_dilate(mask: np.ndarray, px: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(px):
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        out = grown
    return out


def bright_mask(img: Image.Image, floor: int) -> np.ndarray:
    rgba = np.asarray(img)
    return (rgba[:, :, :3].max(axis=2) >= floor) & (rgba[:, :, 3] > 0)


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
    counts = record.get("frames_per_facing", {})
    expected_counts = {"idle": 4, "kneel": 2, "run": 8, "aim": 2,
                       "fire": 5, "hurt": 4, "death": 9}
    if counts != expected_counts:
        raise ValueError("frames_per_facing must be exactly "
                         f"{expected_counts}, got {counts!r}")

    guard = record.get("mark_guard", {})
    for name in ("tol", "slack"):
        value = guard.get(name)
        if type(value) is not int or value < 0:
            raise ValueError(f"mark_guard.{name} must be a non-negative int, "
                             f"got {value!r}")
    for name in ("row_tol",):
        value = record.get("hurt_checks", {}).get("planted", {}).get(name)
        if type(value) is not int or value < 0:
            raise ValueError(f"hurt_checks.planted.{name} must be a "
                             f"non-negative int, got {value!r}")
    death = record.get("death_checks", {})
    if death.get("flat_frames") != 2 or not (0 < death.get("flat_frac", 0) < 1):
        raise ValueError(f"death_checks are malformed: {death!r}")

    pl_facings = set(record["facing_map"].values())
    dir_keys = ("idle_animation_dirs", "run_animation_dirs",
                "hurt_animation_dirs", "death_animation_dirs",
                "fire_animation_dirs")
    for fighter, spec in record["fighters"].items():
        canvas = spec.get("canvas")
        if type(canvas) is not int or canvas <= 0:
            raise ValueError(f"{fighter} canvas must be a positive int, "
                             f"got {canvas!r}")
        if set(spec.get("standing_rows", {})) != set(FACINGS):
            raise ValueError(f"{fighter} standing_rows bill differs from "
                             f"{list(FACINGS)}")
        rgb = spec.get("mark_rgb")
        if not isinstance(rgb, list) or len(rgb) != 3 \
                or any(type(c) is not int or not 0 <= c <= 255 for c in rgb):
            raise ValueError(f"{fighter} mark_rgb must be three bytes, "
                             f"got {rgb!r}")
        for key in dir_keys:
            dirs = spec.get(key, {})
            if set(dirs) != pl_facings:
                raise ValueError(f"{fighter} {key} facings differ from "
                                 f"facing_map: {sorted(dirs)}")
            for facing, value in dirs.items():
                if not isinstance(value, str) or len(value) != 36:
                    raise ValueError(
                        f"{fighter} {key}[{facing!r}] is not an animation "
                        f"id: {value!r} — the record is fail-closed and the "
                        "molder refuses placeholders")
        for facing in FACINGS:
            muzzle = spec.get("fire_muzzle", {}).get(facing)
            if not muzzle or "point" not in muzzle or "r" not in muzzle:
                raise ValueError(f"{fighter} fire_muzzle[{facing!r}] is "
                                 "missing point/r")
            stages = spec.get("fire_stage_frames", {}).get(facing)
            if not isinstance(stages, list) or len(stages) != 5 \
                    or any(type(i) is not int or not 0 <= i <= 4
                           for i in stages) \
                    or stages[0] != 0 or stages[-1] != 0:
                raise ValueError(
                    f"{fighter} fire_stage_frames[{facing!r}] must be 5 "
                    f"source indices beginning AND ending with 0 (the resume "
                    f"seam), got {stages!r}")
    if record["fighters"]["koa"].get("kneel_right_mirror") is not True:
        raise ValueError("koa kneel_right_mirror must be true — the record's "
                         "accepted right-facing source is mirrored south-west")
    syn = record["fighters"]["syn"]
    if syn.get("kneel_facings_from_state") != ["south", "south-west",
                                               "south-east"]:
        raise ValueError("syn kneel_facings_from_state must be exactly "
                         "south/south-west/south-east — north is surgery")
    surgery = syn.get("kneel_north_surgery", {})
    for name in ("head_top", "leg_top", "foot_top", "drop", "pool_rows"):
        if type(surgery.get(name)) is not int:
            raise ValueError(f"syn kneel_north_surgery.{name} must be an int")


def main() -> int:
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    validate_record(record)

    cdn_root = record["cdn_root"].rstrip("/")
    counts = record["frames_per_facing"]
    breath = record["breath"]
    tol = record["mark_guard"]["tol"]
    slack = record["mark_guard"]["slack"]
    row_tol = record["hurt_checks"]["planted"]["row_tol"]
    recovery_floor = record["hurt_checks"]["recovery"]["min_final_height_delta"]
    death_checks = record["death_checks"]
    bright_min = record["fire_checks"]["bright_min"]
    base_dilate = record["fire_checks"]["base_dilate_px"]

    def anim_frames(source_id: str, anim: str, pl_facing: str, n: int,
                    canvas: int, label: str) -> list[Image.Image]:
        frames = []
        for index in range(n):
            frame = fetch(f"{cdn_root}/{source_id}/animations/{anim}/"
                          f"{pl_facing}/{index}.png")
            checked_size(frame, canvas, f"{label}/{index}")
            frames.append(frame)
        return frames

    # Build and check EVERYTHING before writing ANYTHING — see the
    # validated-then-published clause in the docstring.
    built = []
    report = []
    for fighter, spec in record["fighters"].items():
        canvas = spec["canvas"]
        identity_id = spec["identity_character_id"]
        mark_rgb = spec["mark_rgb"]

        identities = {}
        identity_marks = {}
        for facing, pl_facing in record["facing_map"].items():
            identity = fetch(f"{cdn_root}/{identity_id}/rotations/"
                             f"{pl_facing}.png")
            checked_size(identity, canvas,
                         f"{fighter} identity rotation {pl_facing}")
            identity_row = last_opaque_row(identity)
            recorded_row = spec["standing_rows"][facing]
            if identity_row != recorded_row:
                raise ValueError(
                    f"{fighter} identity {facing} standing row "
                    f"{identity_row} != recorded {recorded_row} — the "
                    "upstream identity was re-rolled or the record drifted")
            identities[facing] = identity
            identity_marks[facing] = mark_count(identity, mark_rgb, tol)

        aim_stills = {}
        for facing, pl_facing in record["facing_map"].items():
            still = fetch(f"{cdn_root}/{spec['aim_state_id']}/rotations/"
                          f"{pl_facing}.png")
            checked_size(still, canvas, f"{fighter} aim rotation {pl_facing}")
            aim_row = last_opaque_row(still)
            recorded_row = spec["standing_rows"][facing]
            if aim_row != recorded_row:
                raise ValueError(
                    f"{fighter} aim {facing} row {aim_row} != standing "
                    f"{recorded_row} — the held stance must share the "
                    "standing envelope")
            aim_stills[facing] = still

        for facing, pl_facing in record["facing_map"].items():
            identity = identities[facing]
            identity_row = spec["standing_rows"][facing]
            identity_h = bbox_height(identity)
            identity_mark = identity_marks[facing]

            def guard(frames, verb):
                return [checked_mark_count(
                    frame, fighter, verb, facing, index, identity_mark,
                    mark_rgb, tol, slack)
                    for index, frame in enumerate(frames)]

            # ---- idle: the breathing template ---------------------------
            idle_frames = anim_frames(
                identity_id, spec["idle_animation_dirs"][pl_facing],
                pl_facing, counts["idle"], canvas,
                f"{fighter} idle {pl_facing}")
            idle_marks = guard(idle_frames, "idle")

            # ---- kneel: state still + breath (with the two exceptions) --
            mirrored = (fighter == "koa" and facing == "right")
            surgered = (fighter == "syn" and facing == "up")
            if surgered:
                kneel_still = kneel_surgery(
                    identity, spec["kneel_north_surgery"])
            else:
                source_facing = (record["facing_map"]["left"] if mirrored
                                 else pl_facing)
                kneel_still = fetch(
                    f"{cdn_root}/{spec['kneel_state_id']}/rotations/"
                    f"{source_facing}.png")
                checked_size(kneel_still, canvas,
                             f"{fighter} kneel rotation {source_facing}")
                if mirrored:
                    kneel_still = kneel_still.transpose(
                        Image.Transpose.FLIP_LEFT_RIGHT)
            if surgered:
                folded = bbox_height(kneel_still)
                if folded >= identity_h:
                    raise ValueError(
                        f"syn kneel north surgery did not fold: height "
                        f"{folded} >= standing {identity_h}")
            kneel_frames = [kneel_still, breath_frame(kneel_still, breath)]
            kneel_marks = guard(kneel_frames, "kneel")

            # ---- aim: the held stance + breath --------------------------
            # The aim guard baselines on the AIM STILL, not the identity:
            # the pistol's glow strip is AUTHORED mark addition (koa's left
            # measures +17 over his unarmed identity), so the guard's job
            # here is only that the breath frame keeps the still's marks.
            aim_frames = [aim_stills[facing],
                          breath_frame(aim_stills[facing], breath)]
            aim_baseline = mark_count(aim_frames[0], mark_rgb, tol)
            aim_marks = [checked_mark_count(
                frame, fighter, "aim", facing, index, aim_baseline,
                mark_rgb, tol, slack)
                for index, frame in enumerate(aim_frames)]

            # ---- run: the template cycle (gait dips are authored) -------
            run_frames = anim_frames(
                identity_id, spec["run_animation_dirs"][pl_facing],
                pl_facing, counts["run"], canvas,
                f"{fighter} run {pl_facing}")
            run_marks = guard(run_frames, "run")

            # ---- hurt: planted flinch that stands back up ---------------
            hurt_frames = anim_frames(
                identity_id, spec["hurt_animation_dirs"][pl_facing],
                pl_facing, counts["hurt"], canvas,
                f"{fighter} hurt {pl_facing}")
            hurt_rows = [last_opaque_row(f) for f in hurt_frames]
            if any(abs(row - identity_row) > row_tol for row in hurt_rows):
                raise ValueError(f"{fighter} hurt {facing} left the standing "
                                 f"line {identity_row}±{row_tol}: {hurt_rows}")
            final_h = bbox_height(hurt_frames[-1])
            if final_h < identity_h + recovery_floor:
                raise ValueError(
                    f"{fighter} hurt {facing} never stood back up: final "
                    f"height {final_h} < {identity_h}{recovery_floor:+d}")
            hurt_marks = guard(hurt_frames, "hurt")

            # ---- death: the held flat one-shot --------------------------
            death_frames = anim_frames(
                identity_id, spec["death_animation_dirs"][pl_facing],
                pl_facing, counts["death"], canvas,
                f"{fighter} death {pl_facing}")
            death_rows = [last_opaque_row(f) for f in death_frames]
            death_heights = [bbox_height(f) for f in death_frames]
            flat_limit = death_checks["flat_frac"] * identity_h
            if any(h > flat_limit
                   for h in death_heights[-death_checks["flat_frames"]:]):
                raise ValueError(
                    f"{fighter} death {facing} held frame is not flat: "
                    f"heights {death_heights} vs limit {flat_limit:.1f}")
            low, high = death_checks["final_row_band"]
            if not low <= death_rows[-1] - identity_row <= high:
                raise ValueError(
                    f"{fighter} death {facing} final row {death_rows[-1]} "
                    f"outside {identity_row}{low:+d}..{identity_row}{high:+d}")
            death_marks = guard(death_frames, "death")

            # ---- fire: the stage-mapped shot ----------------------------
            source = anim_frames(
                spec["aim_state_id"], spec["fire_animation_dirs"][pl_facing],
                pl_facing, counts["fire"], canvas,
                f"{fighter} fire {pl_facing}")
            stages = spec["fire_stage_frames"][facing]
            fire_frames = [source[i] for i in stages]
            for end in (0, -1):
                if not np.array_equal(np.asarray(fire_frames[end]),
                                      np.asarray(aim_stills[facing])):
                    raise ValueError(
                        f"{fighter} fire {facing} frame {end % 5} differs "
                        "from its Aim rotation — the resume seam is broken")
            fire_rows = [last_opaque_row(f) for f in fire_frames]
            if any(abs(row - identity_row) > 1 for row in fire_rows):
                raise ValueError(f"{fighter} fire {facing} feet moved off "
                                 f"the aim row {identity_row}±1: {fire_rows}")

            still_rgba = np.asarray(fire_frames[0])
            baseline = square_dilate(
                bright_mask(fire_frames[0], bright_min), base_dilate)
            changed_counts = []
            outside_counts = []
            outside_masks = []
            for frame in fire_frames:
                rgba = np.asarray(frame)
                changed = np.any(rgba != still_rgba, axis=2)
                bright = bright_mask(frame, bright_min)
                changed_counts.append(int(np.count_nonzero(bright & changed)))
                outside = bright & ~baseline
                outside_masks.append(outside)
                outside_counts.append(int(np.count_nonzero(outside)))
            # Two-tier decay: cipher's spatial mask wherever the flash leaves
            # the silhouette; the change-based count only where it does not
            # (the head-on chest flashes) — bright-changed alone conflates
            # flash with recoil and would misorder flash-free frames.
            series = (outside_counts if sum(outside_counts[1:4]) > 0
                      else changed_counts)
            s1, s2, s3 = series[1:4]
            if not (s1 >= s2 >= s3 and s1 > 0 and s3 < s1):
                raise ValueError(
                    f"{fighter} fire {facing} does not decay burst-first: "
                    f"outside {outside_counts} changed {changed_counts}")
            if changed_counts[4] != 0:
                raise ValueError(
                    f"{fighter} fire {facing} last frame is not the still: "
                    f"{changed_counts[4]} bright-changed pixels")
            muzzle = spec["fire_muzzle"][facing]
            mx, my = muzzle["point"]
            mark = np.asarray(mark_rgb, dtype=np.int32)
            for i in range(1, 4):
                frame_rgba = np.asarray(fire_frames[i]).astype(np.int32)
                rgb = frame_rgba[:, :, :3]
                # Containment gates FLASH-COLORED pixels only (see the
                # record's containment clause): white-hot cores are
                # low-chroma, tinted fringes sit near the mark. Bright kit
                # riding authored recoil is neither, and is not an invention.
                chroma = rgb.max(axis=2) - rgb.min(axis=2)
                near_mark = np.sum((rgb - mark) ** 2, axis=2) \
                    <= record["mark_guard"]["tol"] ** 2
                flash = outside_masks[i] & ((chroma <= 16) | near_mark)
                ys, xs = np.nonzero(flash)
                if len(xs) == 0:
                    continue
                bad = (xs - mx) ** 2 + (ys - my) ** 2 > muzzle["r"] ** 2
                if np.any(bad):
                    offender = (int(xs[bad][0]), int(ys[bad][0]))
                    raise ValueError(
                        f"{fighter} fire {facing} frame {i} flash escapes "
                        f"the declared muzzle at {offender}")
            fire_marks = None  # the flash IS invented light; no mark guard

            for verb, frames in (("idle", idle_frames),
                                 ("kneel", kneel_frames),
                                 ("run", run_frames),
                                 ("aim", aim_frames),
                                 ("fire", fire_frames),
                                 ("hurt", hurt_frames),
                                 ("death", death_frames)):
                strip = Image.new("RGBA", (canvas * len(frames), canvas),
                                  (0, 0, 0, 0))
                for index, frame in enumerate(frames):
                    strip.paste(frame, (canvas * index, 0))
                built.append((os.path.join(fighter, f"{verb}_{facing}.png"),
                              strip))

            notes = []
            if mirrored:
                notes.append("kneel right: mirrored south-west")
            if surgered:
                notes.append("kneel north: row surgery on the identity")
            report.append(
                f"{fighter}/{facing}: idle marks {idle_marks} kneel "
                f"{kneel_marks} aim {aim_marks} run {run_marks} hurt "
                f"{hurt_marks} death {death_marks} | fire bright-changed "
                f"{changed_counts}{('  [' + '; '.join(notes) + ']') if notes else ''}")

    expected = {os.path.join(fighter, f"{verb}_{facing}.png")
                for fighter in FIGHTERS
                for verb in VERBS
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
