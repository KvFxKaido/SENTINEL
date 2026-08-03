#!/usr/bin/env python3
"""Unit-test compose_body's palette(), selout() and the head mask (2026-08-03).

These two passes were shipping untested: test_roster_sweep.py only drives
roster_mold, and the .mjs harnesses feed the PAGE synthetic flat sheets
that never reach compose_body at all. Both passes hold contracts that a
future KEY_LUM / PROBE_MAX / palette tweak could quietly break for every
fighter at once, and both have already broken once each in review —
KOA's hands greying to nothing, and KOA's headband scattering across her
crown. Those two are pinned here by name, and so is the third: pack
shoulders left un-neutralised by grey()'s old 45% line.

Runs on synthetic heads built in memory. No licensed pack, no network, no
molded sheets — so this can run anywhere the browser harnesses cannot.

    python prototypes/walkable/test/test_compose_passes.py
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))

from compose_body import (KEY_LUM, PROBE_MAX, grey, palette,  # noqa: E402
                          selout, swap)
from roster_mold import BALA, KOA_SKIN, SKINS  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  — ' + str(detail) if detail else ''}")
    if not ok:
        failures.append(name)


def head(rows):
    """Build a tiny RGBA head from a row-per-string map. '.' is empty."""
    key = {"K": (0, 0, 0), "H": (120, 80, 50), "M": (110, 217, 160)}
    h, w = len(rows), len(rows[0])
    a = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                a[y, x, :3] = key[ch]
                a[y, x, 3] = 255
    return Image.fromarray(a)


# ---- palette() --------------------------------------------------------
# The mold's head passes recolour outside the head for two fighters, and
# the families have to follow or strip() and grey() hunt colours that are
# not on the sheet.
base = palette("cipher")
check("cipher keeps the base skin row", base["skins"] == list(SKINS), base["skins"])

koa = palette("koa")
check("koa's skin row is the remapped one, not the base",
      koa["skins"] == list(KOA_SKIN.values()), koa["skins"])
check("no base skin tone survives in koa's row",
      not (set(koa["skins"]) & set(SKINS)))
# #4a3020 is shared between skin and leather, so the skin remap takes the
# strap tone with it — the half of the review finding that is easy to miss.
check("koa's leather follows the shared #4a3020 into the remap",
      KOA_SKIN[SKINS[0]] in koa["leather"], koa["leather"])

syn = palette("syn")
check("syn's skin row collapses to the balaclava", syn["skins"] == [BALA], syn["skins"])
check("syn's skin row is deduped, not three copies", len(syn["skins"]) == 1)
check("syn's leather follows the same shared tone", BALA in syn["leather"], syn["leather"])
check("syn's coat is rust, not the base blue-grey",
      syn["coat"] != base["coat"])
check("the other three share one wardrobe",
      palette("vesper")["coat"] == base["coat"] == palette("sable")["coat"])
check("every fighter carries their own mark",
      len({tuple(palette(f)["mark"]) for f in
           ("cipher", "vesper", "koa", "sable", "syn")}) == 5)
try:
    palette("nobody")
    check("an unknown fighter is refused", False, "no raise")
except ValueError:
    check("an unknown fighter is refused", True)

# ---- selout() ---------------------------------------------------------
# A crown with material one row under the keyline: 'full' must open it.
shallow = head([
    "..KK..",
    ".KHHK.",
    ".KHHK.",
    "..KK..",
])
pal = palette("cipher")

untouched = np.array(selout(shallow, "off", pal).convert("RGBA"))
check("off is byte-identical", np.array_equal(untouched, np.array(shallow.convert("RGBA"))))

toned = np.array(selout(shallow, "tone", pal).convert("RGBA"))
check("tone re-values the keyline to the mold's outline",
      tuple(toned[0, 2, :3]) == tuple(pal["outline"]), tuple(toned[0, 2, :3]))
check("tone changes no alpha", np.array_equal(toned[:, :, 3], np.array(shallow.convert("RGBA"))[:, :, 3]))
check("tone leaves interior material alone", tuple(toned[1, 2, :3]) == (120, 80, 50))

opened = np.array(selout(shallow, "full", pal).convert("RGBA"))
check("full opens an up-facing edge to the material beneath",
      tuple(opened[0, 2, :3]) == (120, 80, 50), tuple(opened[0, 2, :3]))
check("full keeps the silhouette exactly — no erosion",
      np.array_equal(opened[:, :, 3], np.array(shallow.convert("RGBA"))[:, :, 3]))
check("full still re-tones the side keyline it does not open",
      tuple(opened[1, 1, :3]) == tuple(pal["outline"]), tuple(opened[1, 1, :3]))

# The KOA regression, pinned: a crown too deep for PROBE_MAX must KEEP its
# keyline rather than tunnel through and borrow a distant feature's colour.
# 'M' is the mint headband sitting far below a thick dark cap.
deep = head([
    "..KK..",
    ".KKKK.",
    ".KKKK.",
    ".KKKK.",
    ".KMMK.",
])
deep_out = np.array(selout(deep, "full", pal).convert("RGBA"))
mint = (110, 217, 160)
crown = [tuple(deep_out[0, x, :3]) for x in range(6) if deep_out[0, x, 3] > 0]
check("a too-dark crown keeps its keyline instead of tunnelling",
      mint not in crown, crown)
check("that crown is re-toned, not left the generator's black",
      all(c == tuple(pal["outline"]) for c in crown), crown)
check("PROBE_MAX is short enough to have stopped the headband",
      PROBE_MAX < 4, PROBE_MAX)
check("KEY_LUM separates the keyline from the material it borrows",
      KEY_LUM > 0 and 0.2126 * 120 + 0.7152 * 80 + 0.0722 * 50 > KEY_LUM)

# ---- swap() + grey(): the shoulder boundary ---------------------------
# The regression this pins: grey() used to spare everything above 45% of
# the COMPOSED body's height, while swap() clears the pack only above 45%
# of the PACK's height. A generated head block shorter than the pack's
# makes the composed body shorter, drops the composed line BELOW the pack
# line, and the pack rows in that gap survive both — raw wardrobe sitting
# above a boundary that was never measuring the right thing.
WARDROBE, HEADCOL = (40, 60, 90), (200, 100, 50)


def slab(colour, top, height, w=40, h=40, x0=18, x1=22):
    a = np.zeros((h, w, 4), np.uint8)
    a[top:top + height, x0:x1, :3] = colour
    a[top:top + height, x0:x1, 3] = 255
    return Image.fromarray(a)


# pack body 22 tall from row 10; generated head block deliberately SHORT,
# which is the arrangement that produced the bug on Cipher and Sable.
pack_frame = slab(WARDROBE, 10, 22)
gen_head = slab(HEADCOL, 0, 14)
swapped, generated = swap(pack_frame, gen_head)
composed = np.array(grey(swapped, palette("cipher"), generated).convert("RGBA"))

alive = composed[:, :, 3] > 0
ys, _ = np.where(alive)
old_line = ys.min() + int((ys.max() - ys.min() + 1) * 0.45)
survivors = np.all(composed[:, :, :3] == WARDROBE, axis=2) & alive
above_old_line = survivors[:old_line]

check("swap reports a non-empty generated mask", generated.any())
check("the mask covers only what swap wrote",
      not (generated & ~alive).any())
check("no raw pack wardrobe survives anywhere", not survivors.any(),
      f"{int(survivors.sum())} px")
check("in particular none survives above the old 45% cutoff",
      not above_old_line.any(), f"{int(above_old_line.sum())} px")
# The case must actually exercise the bug — a synthetic that never puts
# pack pixels above the composed line would pass while proving nothing.
pack_rows = sorted({int(y) for y in np.where(alive & ~generated)[0]})
check("the synthetic really does straddle the old cutoff",
      any(r < old_line for r in pack_rows),
      f"pack rows {pack_rows[:4]}, old line {old_line}")
gen_px = composed[generated]
check("the generated head keeps its colour", len(gen_px) and
      all(tuple(p[:3]) == HEADCOL for p in gen_px))
neutral = composed[alive & ~generated][:, :3]
check("every surviving pack pixel is neutralised to greyscale",
      len(neutral) and all(p[0] == p[1] == p[2] for p in neutral))

# The symmetric hazard, and the reason the fix is a mask rather than a
# better line: a TALL generated head puts its own lower pixels BELOW the
# composed 45% line, where the old rule greyed everything. A line can be
# wrong in both directions at once; swap()'s mask cannot.
tall_pack = slab(WARDROBE, 10, 22)
tall_head = slab(HEADCOL, 0, 30)
tall_swapped, tall_mask = swap(tall_pack, tall_head)
tall = np.array(grey(tall_swapped, palette("cipher"), tall_mask).convert("RGBA"))
tal = tall[:, :, 3] > 0
tys, _ = np.where(tal)
tall_line = tys.min() + int((tys.max() - tys.min() + 1) * 0.45)
below = tall_mask.copy()
below[:tall_line] = False
check("the tall synthetic really does cross the composed line",
      below.any(), f"line {tall_line}")
check("generated pixels below the line keep their colour, not luminance",
      all(tuple(p[:3]) == HEADCOL for p in tall[below]),
      f"{int(below.sum())} px checked")

print()
if failures:
    print(f"{len(failures)} FAILURES: {', '.join(failures)}")
    sys.exit(1)
print("ALL PASS")
