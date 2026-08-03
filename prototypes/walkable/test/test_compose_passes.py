#!/usr/bin/env python3
"""Unit-test compose_body's palette() and selout() (2026-08-03).

These two passes were shipping untested: test_roster_sweep.py only drives
roster_mold, and the .mjs harnesses feed the PAGE synthetic flat sheets
that never reach compose_body at all. Both passes hold contracts that a
future KEY_LUM / PROBE_MAX / palette tweak could quietly break for every
fighter at once, and both have already broken once each in review —
KOA's hands greying to nothing, and KOA's headband scattering across her
crown. Those two are pinned here by name.

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

from compose_body import KEY_LUM, PROBE_MAX, palette, selout  # noqa: E402
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

print()
if failures:
    print(f"{len(failures)} FAILURES: {', '.join(failures)}")
    sys.exit(1)
print("ALL PASS")
