#!/usr/bin/env python3
"""Compose a character body from the pack's frames + a generated head (2026-08-02).

The generated pipeline can make a face; it cannot make a walk. Five attempts
proved that — same-side arms, facing drift, a 1px bob, a visible loop seam,
and south-facing only (see scripts/pixellab_cipher.json "dead_ends"). The
pack's own frames already walk correctly, in four facings across eleven
verbs, hand-authored and golden-tested.

So nothing here generates motion. Three deterministic passes run over the
MOLDED pack frames, and identity is the only thing that comes from elsewhere:

  strip()  lift the back-slung stave, the chest strap and the blade-from-
           behind, filling from coat colours only
  swap()   drop the generated head in, anchored to the SHOULDER band
  grey()   neutralise the outfit at constant luminance, sparing skin

Everything animation-shaped — arm phase, bob, gait, loop closure, every
facing — is inherited untouched, because it is never touched. Measured on
Cipher's walk: bob 2px (identical to source), foot swing 3.27 vs 3.35, and
arm/leg correlation -0.55 against the pack's own -0.37.

FACING MAP. The pack's left/right frames are THREE-QUARTER views, not
profiles, so they pair with the 45-degree generated rotations. Pairing them
with the 90-degree ones puts a full-profile head on an angled body, which
reads as the head facing somewhere the shoulders are not.

Usage:
    python compose_body.py --gen assets/sprites/generated/cipher \\
                           --src assets/sprites/cipher \\
                           --out <dir> [--verbs IDLE WALK]
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

# Must track roster_mold.py's SKINS. Note #4a3020 is shared with the pack's
# leather: one source colour serves both, so skin and strap cannot be told
# apart by palette alone — the strap is found by SHAPE below for that reason.
SKINS = [hx(c) for c in ("4a3020", "66452e", "7d5840")]
LEATHER = [hx("3a2d20"), hx("4a3020")]
COAT = [hx(c) for c in ("2b3a4a", "41586e", "28374a", "1d2733", "161e28",
                        "141920", "1d2a37", "2b3947", "44586c", "223040")]
DORM = [hx(c) for c in ("44586c", "384756", "2b3947", "223040", "1d2a37")]
LIGHTS = [hx(c) for c in ("e8f1f7", "c2d3e0", "93aabf", "6b8199", "68809a")]
# roster_mold's per-fighter ignition ramp. The outfit greys; the MARK never
# does. Without this the attack sheets' cyan arc desaturates into a white
# smear — the pass runs clean and destroys the one thing the frame is for.
# Cipher's ramp; a different fighter needs their own ENERGY row here.
MARK = [hx(c) for c in ("eaffff", "a5ecff", "5ccfff", "2196d8", "1d7fc0")]

FACE_MAP = {"down": "south", "up": "north",
            "left": "south-west", "right": "south-east"}
# The numbered attack directories contain a space; their sheet filenames do
# not. Every other pack verb uses its lowercase directory name as the stem.
SHEET_STEMS = {"ATTACK 1": "attack1", "ATTACK 2": "attack2"}
FRAME_W, FRAME_H = 96, 80


def eq(x, c):
    return (x[:, :, 0] == c[0]) & (x[:, :, 1] == c[1]) & (x[:, :, 2] == c[2]) & (x[:, :, 3] > 0)


def _elong(mask, thr, minsz, broad=False):
    """Components selected by shape. `broad` adds roster_mold's clause for a
    blade seen DIAGONALLY, which spreads across both axes and so never
    reaches a thin-line elongation bar — the same blind spot blade_pass had.
    Needed on the dormant family since 2026-08-02: the mold now sheathes the
    back-slung sword, so it arrives here as dark steel rather than light, and
    a check that only looks for thin lines walks straight past it."""
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    out = np.zeros_like(mask)
    for i in range(1, n + 1):
        cy, cx = np.where(lab == i)
        s = len(cy)
        if s < minsz:
            continue
        p = np.stack([cy, cx]).astype(float)
        p -= p.mean(axis=1, keepdims=True)
        ev = np.linalg.eigvalsh(p @ p.T / s)
        el = (ev[1] + .01) / (ev[0] + .01)
        if el > thr or s > 90 or (broad and s >= 40 and el > 2.0):
            out[lab == i] = True
    return out


def back_blade(a):
    """The blade seen from BEHIND — a broad diagonal, not a thin line.

    roster_mold's blade_pass misses this and always has: it classifies by
    elongation > 5.0 or size > 90, and a diagonal blob spreads across both
    axes, so the back-slung sword measures 66px at elongation 3.22 and fails
    both bars. It therefore renders bright silver instead of sheathed steel
    on the _up sheets of EVERY fighter, not just Cipher.

    Bounded above on purpose: the largest light-family components in the
    roster are the 338-400px HURT frames, where the whole figure renders
    light under the flash law. An unbounded rule deletes the character at
    the exact moment they take a hit.
    """
    al = a[:, :, 3] > 0
    light = np.zeros(a.shape[:2], bool)
    for c in LIGHTS:
        light |= eq(a, c)
    if light.sum() > 0.5 * al.sum():          # damage flash — hands off
        return np.zeros_like(light)
    lab, n = ndimage.label(light, structure=np.ones((3, 3)))
    out = np.zeros_like(light)
    for i in range(1, n + 1):
        cy, cx = np.where(lab == i)
        s = len(cy)
        if not (40 <= s <= 120):              # gloves ~8px, flashes 300+
            continue
        p = np.stack([cy, cx]).astype(float)
        p -= p.mean(axis=1, keepdims=True)
        ev = np.linalg.eigvalsh(p @ p.T / s)
        if 2.0 < (ev[1] + .01) / (ev[0] + .01) < 5.0:
            out[lab == i] = True
    return out


def _back_sheathed(mask):
    """The sheathed sword seen from STRAIGHT BEHIND — a blob, not a line.

    Third blade blind spot, same family as the first two: blade_pass missed
    the thin line, _elong's broad clause was added for the diagonal band,
    and both walk past the rear view, where the scabbard mass measures
    80-91px at elongation 1.15-1.72 on idle/walk — under the broad clause's
    2.0 bar, over nothing. The old gate fired only on the two frames that
    happened to hit 91px (s > 90): idle f0 and walk f6, which is why the
    sword vanished from exactly one idle frame and survived seven.

    Shape cannot see this one, so the gate is size alone — safe ONLY
    because it is facing-scoped by the caller: measured across every verb's
    _up sheet (2026-08-02), the sole dormant component >= 40px is this mass
    (41-109px, verb by verb). Bounded at 120 like back_blade, for the same
    reason. CAVEAT for verbs beyond IDLE/WALK: the attack sheets' swung
    blade passes through this window on _up frames — when compose grows
    attack verbs, whether a bladeless body may swing a blade is a design
    decision, not a default.
    """
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    out = np.zeros_like(mask)
    for i in range(1, n + 1):
        s = int((lab == i).sum())
        if 40 <= s <= 120:
            out[lab == i] = True
    return out


def strip(img, facing):
    """Lift the stave, the chest strap and the blade-from-behind.

    Holes are filled from COAT colours only. Filling from the nearest
    surviving pixel of any kind smears skin across the chest, because the
    hands sit adjacent to the strap's lower end (observed, not theorised).
    """
    a = np.array(img.convert("RGBA")).copy()
    lea = np.zeros(a.shape[:2], bool)
    for c in LEATHER:
        lea |= eq(a, c)
    dorm = np.zeros(a.shape[:2], bool)
    for c in DORM:
        dorm |= eq(a, c)
    kill = _elong(lea, 4.0, 8) | _elong(dorm, 5.0, 6, broad=True) | back_blade(a)
    if facing == "up":
        kill |= _back_sheathed(dorm)
    coat = np.zeros(a.shape[:2], bool)
    for c in COAT:
        coat |= eq(a, c)
    coat &= ~kill
    idx = ndimage.distance_transform_edt(~coat, return_distances=False, return_indices=True)
    out = a.copy()
    for y, x in zip(*np.where(kill)):
        sy, sx = idx[0][y, x], idx[1][y, x]
        out[y, x] = a[sy, sx] if coat[sy, sx] else (0, 0, 0, 0)
    return Image.fromarray(out)


def _geom(a):
    al = a[:, :, 3] > 0
    ys, _ = np.where(al)
    return ys.min(), ys.max(), ys.min() + int((ys.max() - ys.min() + 1) * 0.45)


def swap(pack_img, gen_img):
    """Swap the head, anchored to the SHOULDER band.

    Anchoring to the pack head's own centre inherits a bias the body does
    not have: the dreads hang past the skull and drag that centre a pixel
    left of the torso. The shoulders are where a neck actually attaches, and
    they also sway a full pixel across a walk cycle, so the anchor is
    recomputed per frame and the head rides the sway instead of sliding
    against it.
    """
    p = np.array(pack_img.convert("RGBA")).copy()
    g = np.array(gen_img.convert("RGBA"))
    _, _, pl = _geom(p)
    _, _, gl = _geom(g)
    pal = p[:, :, 3] > 0
    ph = pal[:pl]
    _, sx = np.where(pal[pl:pl + 6])
    pcx = (sx.min() + sx.max()) / 2
    gy, gx = np.where(g[:gl, :, 3] > 0)
    gcx = (gx.min() + gx.max()) / 2
    dx, dy = math.floor(pcx - gcx + 0.5), int(pl - gl)
    out = p.copy()
    out[:pl][ph] = 0
    for y, x in zip(gy, gx):
        ny, nx = y + dy, x + dx
        if 0 <= ny < out.shape[0] and 0 <= nx < out.shape[1]:
            out[ny, nx] = g[y, x]
    return Image.fromarray(out)


def grey(img):
    """Neutralise the outfit at constant luminance — desaturated, not
    flattened, so the pack's shading survives. The head is left alone and so
    is skin wherever it appears, which is what keeps the hands from greying,
    and so is the MARK ramp, which is what keeps an attack's ignition arc from
    desaturating into a white smear. Boots and wrist leather stay brown as a
    side effect of the shared #4a3020: the palette cannot separate them from
    skin."""
    a = np.array(img.convert("RGBA")).copy()
    al = a[:, :, 3] > 0
    ys, _ = np.where(al)
    top, bot = ys.min(), ys.max()
    hl = top + int((bot - top + 1) * 0.45)
    spare = np.zeros(a.shape[:2], bool)
    for c in SKINS + MARK:
        spare |= eq(a, c)
    tgt = al.copy()
    tgt[:hl] = False
    tgt &= ~spare
    rgb = a[:, :, :3].astype(float)
    lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    for ch in range(3):
        a[:, :, ch] = np.where(tgt, np.clip(lum, 0, 255).astype(np.uint8), a[:, :, ch])
    return Image.fromarray(a)


def compose(pack_frame, gen_head, facing):
    return grey(swap(strip(pack_frame, facing), gen_head))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="molded pack sheets, e.g. assets/sprites/cipher")
    ap.add_argument("--gen", required=True, help="generated rotations dir")
    ap.add_argument("--out", required=True, help="output dir for frame folders")
    ap.add_argument("--verbs", nargs="+", default=["IDLE", "WALK"])
    a = ap.parse_args()

    # A partial set is worse than no set. walkoff.html loads every idle/walk
    # facing through one Promise.all, so a single missing facing stops BODY C
    # loading at all — and a skipped facing leaves STALE frames from a prior
    # run in place, which pack_strip then ships as current. Collect every
    # fault and fail once, loudly, before writing anything.
    faults, jobs = [], []
    for verb in a.verbs:
        stem = SHEET_STEMS.get(verb, verb.lower())
        for facing, rot in FACE_MAP.items():
            sheet_p = os.path.join(a.src, verb, f"{stem}_{facing}.png")
            head_p = os.path.join(a.gen, f"{rot}.png")
            for p, what in ((sheet_p, "source sheet"), (head_p, "generated rotation")):
                if not os.path.exists(p):
                    faults.append(f"{stem}_{facing}: missing {what} {p}")
            if faults and (not os.path.exists(sheet_p) or not os.path.exists(head_p)):
                continue
            sheet = Image.open(sheet_p).convert("RGBA")
            # Validate here so a malformed sheet fails LOCALLY. Otherwise the
            # crop silently truncates, writes plausible-looking frames, and
            # the wrong count/height only surfaces in loadSheetGen's throw,
            # a renderer away from the cause.
            if sheet.width % FRAME_W or sheet.height != FRAME_H:
                faults.append(
                    f"{stem}_{facing}: sheet is {sheet.width}x{sheet.height}; "
                    f"expected a multiple of {FRAME_W} wide and exactly {FRAME_H} tall")
                continue
            jobs.append((stem, facing, rot, sheet_p, head_p, sheet.width // FRAME_W))

    if faults:
        print("compose aborted — inputs are not usable:", file=sys.stderr)
        for f in faults:
            print(f"  {f}", file=sys.stderr)
        return 1

    for stem, facing, rot, sheet_p, head_p, n in jobs:
        sheet = Image.open(sheet_p).convert("RGBA")
        head = Image.open(head_p).convert("RGBA")
        d = os.path.join(a.out, f"{stem}_{facing}")
        os.makedirs(d, exist_ok=True)
        for stale in os.listdir(d):          # never let a prior run survive
            if stale.lower().endswith(".png"):
                os.remove(os.path.join(d, stale))
        for i in range(n):
            frame = sheet.crop((i * FRAME_W, 0, i * FRAME_W + FRAME_W, FRAME_H))
            compose(frame, head, facing).save(os.path.join(d, f"f{i + 1:02d}.png"))
        print(f"  {stem}_{facing}: {n} frames  (head = {rot})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
