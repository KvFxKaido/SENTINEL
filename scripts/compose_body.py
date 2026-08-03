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
  selout() reconcile the generated head's hard keyline with the pack's
           selective one — measured off the pack, not chosen
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The mold is the palette's single source of truth. This file used to carry
# its own copies with a "must track roster_mold.py" comment on top — a drift
# waiting to happen, and the ENERGY row was hard-coded to Cipher besides.
from roster_mold import (BALA, CREW_RED, DORMANT, ENERGY,  # noqa: E402
                         FIGHTERS, KOA_SKIN, LIGHTS, OUTLINE, RUST, SKINS)

hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

# Note #4a3020 is shared between SKINS and the pack's leather: one source
# colour serves both, so skin and strap cannot be told apart by palette
# alone — the strap is found by SHAPE below for that reason.
LEATHER = [hx("3a2d20"), hx("4a3020")]
COAT = [hx(c) for c in ("2b3a4a", "41586e", "28374a", "1d2733", "161e28",
                        "141920", "1d2a37", "2b3947", "44586c", "223040")]
DORM = list(DORMANT.values())

# Two head passes recolour OUTSIDE the head, and both say so in the mold:
# head_koa remaps skin "everywhere on the body" and head_syn paints every
# skin pixel — gloves included — the balaclava tone, because a crew body
# shows no skin anywhere. Their hands and their wrist leather therefore
# never carry the base tones, which is why these have to be replayed here
# and not assumed. Measured on the molded idle_down sheets: KOA and SYN
# report 0 base-skin pixels where the other three report 22-42, and their
# LEATHER drops 42/34 -> 28 because #4a3020 is shared between skin and
# leather and the remap takes it with the skin (caught in review — Koa's
# composed hands were greying to nothing).
SKIN_REMAP = {
    "koa": dict(KOA_SKIN),
    "syn": {tone: BALA for tone in SKINS},
}
# Fighters whose build_frame runs RUST and CREW_RED over the WHOLE frame
# after the blade pass. Named here rather than string-compared inline: the
# invariant lives in roster_mold.build_frame, and if a second crew fighter
# ever joins, this set is the one place that has to learn about it.
CREW_RECOLOR = {"syn"}


def palette(fighter):
    """The colour families as they exist ON THIS FIGHTER'S molded sheets.

    Four of the five share one wardrobe: the mold's head passes only touch
    the head, so cipher/vesper/koa/sable measure an identical 189 coat and
    91 dormant-steel pixels on idle_up. SYN does not. His build_frame runs
    RUST and CREW_RED swaps over the WHOLE frame after the blade pass, which
    moves 136 of those coat pixels and 26 steel pixels out of the base
    families — measured, not assumed (2026-08-02).

    That matters because strip() fills the holes it cuts from COAT pixels
    only. Run with the base families, SYN has 53 coat pixels to fill from
    instead of 189, so the nearest-coat lookup reaches across the body and
    smears; the sword's own steel half-escapes the kill gate as well. The
    families are therefore DERIVED here by replaying the mold's swaps rather
    than duplicated, so a palette change in the mold cannot silently desync
    this pass. His skin row collapses to the balaclava for the same reason:
    head_syn paints every SKINS pixel — gloves included — BALA, so a crew
    body has no skin anywhere to spare.
    """
    if fighter not in FIGHTERS:
        raise ValueError(f"unknown fighter {fighter!r}; expected one of {FIGHTERS}")
    remap = SKIN_REMAP.get(fighter, {})
    swaps = dict(RUST) | dict(CREW_RED) if fighter in CREW_RECOLOR else {}

    def fam(colours):
        # Replayed in the mold's own order: the head pass runs first, then
        # the crew recolour over the whole frame. Deduped because a remap
        # can collapse three skin tones onto one balaclava.
        out = []
        for colour in colours:
            landed = swaps.get(remap.get(colour, colour), remap.get(colour, colour))
            if landed not in out:
                out.append(landed)
        return out

    return {
        "coat": fam(COAT),
        "dorm": fam(DORM),
        "leather": fam(LEATHER),
        "lights": fam(LIGHTS),
        # The outfit greys; the MARK never does. Without this the attack
        # sheets' ignition arc desaturates into a white smear — the pass runs
        # clean and destroys the one thing the frame is for.
        "mark": ENERGY[fighter],
        "skins": fam(SKINS),
        # The mold's own keyline tone. Not swapped for SYN: RUST and
        # CREW_RED do not touch it, so the squad shares one outline value.
        "outline": OUTLINE,
    }

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


def back_blade(a, pal):
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
    for c in pal["lights"]:
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


def strip(img, facing, pal):
    """Lift the stave, the chest strap and the blade-from-behind.

    Holes are filled from COAT colours only. Filling from the nearest
    surviving pixel of any kind smears skin across the chest, because the
    hands sit adjacent to the strap's lower end (observed, not theorised).
    """
    a = np.array(img.convert("RGBA")).copy()
    lea = np.zeros(a.shape[:2], bool)
    for c in pal["leather"]:
        lea |= eq(a, c)
    dorm = np.zeros(a.shape[:2], bool)
    for c in pal["dorm"]:
        dorm |= eq(a, c)
    kill = _elong(lea, 4.0, 8) | _elong(dorm, 5.0, 6, broad=True) | back_blade(a, pal)
    if facing == "up":
        kill |= _back_sheathed(dorm)
    coat = np.zeros(a.shape[:2], bool)
    for c in pal["coat"]:
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


# Separates a keyline pixel from a material pixel sitting on the silhouette.
# Measured on a composed frame: the pack's keyline runs #101010-#181818
# (luma 16-24) and the generated head's runs #000000-#040007, while the
# lightest thing the pack lets touch its own open edges is #7b7b7b (luma
# 123). 40 sits in the gap with room on both sides.
KEY_LUM = 40
# How far the "full" mode may reach inward for the material that replaces an
# opened keyline pixel. Enough for a doubled outline, not enough to tunnel
# through a feature. Three rows, not two: the KOA headband pixels that leaked
# across her crown under an unbounded probe sit at distance FOUR, measured, so
# three clears them with a row to spare while reaching material that two left
# stranded. See the KOA note in selout().
PROBE_MAX = 3


def _luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def selout(head_img, mode, pal):
    """Reconcile the generated head's HARD outline with the pack's SELECTIVE one.

    PixelLab draws a keyline all the way around — measured on Cipher's
    composed idle_down, 100% of the generated head's silhouette edge is
    near-black on every side. The pack does not. Measured on the SAME
    frame's pack-drawn body, the keyline covers:

        up 10%   left 47%   right 53%   down 46%

    i.e. the top of the silhouette is left OPEN, material colour running
    straight to the boundary, because the light is overhead; the sides and
    bottom carry a keyline about half the time. Asking the generator for
    this does not work — `outline: "selective outline"` is soft guidance and
    all five heads came back hard-keylined anyway — so it is reconciled here,
    deterministically, by a rule read off the pack rather than invented:

      "tone"  re-tone the keyline from the generator's #000000 to the mold's
              own OUTLINE. Value only; coverage untouched. The safe half.
      "full"  additionally OPEN the up-facing edges: each up-facing keyline
              pixel takes the colour of the material directly beneath it, so
              the silhouette keeps its exact shape and the boundary becomes
              colour-derived — which is what the pack's own open edges are.
              Deleting those pixels instead would erode the head a pixel and
              change its outline, which the body law does not permit.

    How close that lands depends on the fighter's own art, and the spread is
    the point. Measured on the shipped sheets against the pack body's
    up 10% / left 47% / right 53%:

        SABLE   up 11%  left 53%  right 47%   — canon, to the pixel
        VESPER  up 25%  left 69%  right 50%
        SYN     up 29%  left 87%  right 73%
        KOA     up 44%  left 75%  right 75%
        CIPHER  up 65%  left 79%  right 71%

    Cipher converges least and that is not a failure: the pack can open its
    top edge because its hair is lighter than the void behind it, and his
    dreads are near-black, so 6 of his 20 up-facing edge pixels have no
    non-keyline material within reach at ANY distance. Opening those would
    swap a keyline for a colour indistinguishable from one. A dark feature
    keeps its outline; the convergence is partial ON PURPOSE.

    (The first version of this docstring claimed "up 0%, left/right 50/50,
    almost exactly the pack's numbers". That was measured before PROBE_MAX
    existed, when the probe tunnelled and opened everything — the same run
    that scattered KOA's headband across her crown. The numbers above are
    from the shipped sheets.)

    Runs on the head image ONCE per facing, before swap: every pixel here is
    generated, so the pass cannot reach the pack's own drawing by accident.
    """
    if mode == "off":
        return head_img
    a = np.array(head_img.convert("RGBA")).copy()
    al = a[:, :, 3] > 0
    dark = al & (_luma(a[:, :, :3].astype(float)) < KEY_LUM)

    h, w = al.shape
    pad = np.zeros((h + 2, w + 2), bool)
    pad[1:-1, 1:-1] = al
    empty_up = ~pad[:-2, 1:-1]
    boundary = al & (empty_up | ~pad[2:, 1:-1] | ~pad[1:-1, :-2] | ~pad[1:-1, 2:])
    key = boundary & dark

    if mode == "full":
        # The borrow reaches at most PROBE_MAX rows down, because on the
        # pack's own open edges the material is IMMEDIATELY inside the
        # boundary. Unbounded, the probe tunnels through a dark feature and
        # takes its colour from whatever it eventually hits: on KOA it drove
        # through the cap and came back with the mint headband, scattering
        # band pixels along her crown (caught by looking, after the coverage
        # numbers said the pass was working). A crown too dark to have
        # material within reach is a crown whose keyline should simply stay.
        for y, x in zip(*np.where(key & empty_up)):
            for probe in range(y + 1, min(y + 1 + PROBE_MAX, h)):
                if al[probe, x] and not dark[probe, x]:
                    a[y, x, :3] = a[probe, x, :3]
                    key[y, x] = False          # no longer a keyline pixel
                    break
    a[key, :3] = pal["outline"]
    return Image.fromarray(a)


def swap(pack_img, gen_img):
    """Swap the head, anchored to the SHOULDER band.

    Anchoring to the pack head's own centre inherits a bias the body does
    not have: the dreads hang past the skull and drag that centre a pixel
    left of the torso. The shoulders are where a neck actually attaches, and
    they also sway a full pixel across a walk cycle, so the anchor is
    recomputed per frame and the head rides the sway instead of sliding
    against it.

    Returns the composed frame AND the mask of pixels this pass wrote, so
    the passes after it can tell generated art from pack art exactly rather
    than guessing with a horizontal line. grey() used to guess, and it was
    wrong at the shoulders — see its docstring.
    """
    p = np.array(pack_img.convert("RGBA")).copy()
    g = np.array(gen_img.convert("RGBA"))
    _, _, pl = _geom(p)
    _, _, gl = _geom(g)
    alpha = p[:, :, 3] > 0
    ph = alpha[:pl]
    _, sx = np.where(alpha[pl:pl + 6])
    pcx = (sx.min() + sx.max()) / 2
    gy, gx = np.where(g[:gl, :, 3] > 0)
    gcx = (gx.min() + gx.max()) / 2
    dx, dy = math.floor(pcx - gcx + 0.5), int(pl - gl)
    out = p.copy()
    out[:pl][ph] = 0
    generated = np.zeros(p.shape[:2], bool)
    for y, x in zip(gy, gx):
        ny, nx = y + dy, x + dx
        if 0 <= ny < out.shape[0] and 0 <= nx < out.shape[1]:
            out[ny, nx] = g[y, x]
            generated[ny, nx] = True
    return Image.fromarray(out), generated


def grey(img, pal, generated):
    """Neutralise the outfit at constant luminance — desaturated, not
    flattened, so the pack's shading survives. The generated head is left
    alone and so is skin wherever it appears, which is what keeps the hands
    from greying, and so is the MARK ramp, which is what keeps an attack's
    ignition arc from desaturating into a white smear. Boots and wrist
    leather stay brown as a side effect of the shared #4a3020: the palette
    cannot separate them from skin.

    The wardrobe neutralises for every fighter, SYN's rust and crew-red
    included: under the composed treatment identity is carried by the head
    and the mark, not the coat, so sparing one fighter's wardrobe colour
    would make him the exception to the thing the treatment is FOR.

    WHAT COUNTS AS THE HEAD is swap()'s own mask, not a horizontal line.
    This pass used to spare everything above 45% of body height, which is a
    proxy for "generated" and is wrong exactly where the two meet.

    The mechanism, measured rather than assumed: swap() clears pack pixels
    above the PACK's 45% line (pl) and pastes the head there, but this pass
    recomputed 45% on the COMPOSED silhouette (hl). When the generated head
    block is SHORTER than the pack's, the composed body is shorter overall
    and hl lands BELOW pl — so the pack rows in the gap [pl, hl) survive
    swap's clear and then get spared here, staying raw pack blue-grey while
    the torso beneath them neutralises. On idle_up: Cipher's generated head
    block is 13 against the pack's 15 and spares row 39; Sable's is 14 and
    spares row 38; SYN's is 15, hl lands on pl, and he spares nothing. That
    is why the defect looked like it belonged to two fighters rather than to
    the rule. Across the shipped set before the fix: 1767 pixels on 124 of
    1300 frames.

    (An earlier version of this note had the cause backwards — it blamed
    heads that were TALLER than the pack's. The direction is the opposite,
    and the numbers above are from the frames themselves.)"""
    a = np.array(img.convert("RGBA")).copy()
    al = a[:, :, 3] > 0
    spare = np.zeros(a.shape[:2], bool)
    for c in pal["skins"] + pal["mark"]:
        spare |= eq(a, c)
    tgt = al & ~generated & ~spare
    rgb = a[:, :, :3].astype(float)
    lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    for ch in range(3):
        a[:, :, ch] = np.where(tgt, np.clip(lum, 0, 255).astype(np.uint8), a[:, :, ch])
    return Image.fromarray(a)


def compose(pack_frame, gen_head, facing, pal):
    swapped, generated = swap(strip(pack_frame, facing, pal), gen_head)
    return grey(swapped, pal, generated)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="molded pack sheets, e.g. assets/sprites/cipher")
    ap.add_argument("--gen", required=True, help="generated rotations dir")
    ap.add_argument("--out", required=True, help="output dir for frame folders")
    ap.add_argument("--verbs", nargs="+", default=["IDLE", "WALK"])
    ap.add_argument("--fighter", default=None,
                    help=f"palette row to compose against, one of {FIGHTERS}; "
                         "defaults to the basename of --src")
    ap.add_argument("--selout", choices=["off", "tone", "full"], default="full",
                    help="reconcile the generated head's hard keyline with the "
                         "pack's selective one: off keeps the generator's black, "
                         "tone re-values it to the mold's outline, full also "
                         "opens the up-facing edges (see selout). Default full, "
                         "decided 2026-08-02 by walking all three")
    a = ap.parse_args()

    # Defaulting off --src keeps the old cipher invocation working verbatim
    # and makes the roster call read as the same command with a new path.
    fighter = a.fighter or os.path.basename(os.path.normpath(a.src))
    try:
        pal = palette(fighter)
    except ValueError as exc:
        print(f"compose aborted — {exc}", file=sys.stderr)
        return 1

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
        # Once per facing, not once per frame: the head image is the same
        # for every frame of a sheet, so the outline pass runs here.
        head = selout(Image.open(head_p).convert("RGBA"), a.selout, pal)
        d = os.path.join(a.out, f"{stem}_{facing}")
        os.makedirs(d, exist_ok=True)
        for stale in os.listdir(d):          # never let a prior run survive
            if stale.lower().endswith(".png"):
                os.remove(os.path.join(d, stale))
        for i in range(n):
            frame = sheet.crop((i * FRAME_W, 0, i * FRAME_W + FRAME_W, FRAME_H))
            compose(frame, head, facing, pal).save(os.path.join(d, f"f{i + 1:02d}.png"))
        print(f"  {stem}_{facing}: {n} frames  (head = {rot}, palette = {fighter}, "
              f"selout = {a.selout})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
