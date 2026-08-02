"""Executes blade_pass's shape claims against synthetic components.

The roster mold's goldens are computed from the licensed pack, which is
gitignored — so CI can prove the guard FIRES on drift (test_roster_sweep)
but cannot prove WHAT the classifier decides. The broad-diagonal clause
added 2026-08-02 is exactly the kind of rule that needs the second thing:
its floor sits one pixel above the largest component that must not be
caught, and that margin was measured against art no test can read.

So this pins the behaviour instead of the pixels. Every case is a shape
built from scratch, run through the real blade_pass, and judged on
whether it was sheathed. It needs no pack and no assets.

The sizes are not invented. Measured across five fighters, twelve verbs
and every frame:
    back blade seen diagonally   41..67 px, elongation ~3.2
    largest non-blade component  39 px DASH motion streak
    gloves                       ~8 px

Run:  python test_blade_classifier.py   (needs pillow + numpy)
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import roster_mold as rm  # noqa: E402

LIGHT = rm.LIGHTS[0]
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(f'{"PASS" if ok else "FAIL"}  {name}{"  — " + detail if detail else ""}')


def frame():
    """A body big enough that no case trips the flash law, which returns
    before blade_pass and would mask every result here."""
    a = np.zeros((80, 96, 4), dtype=np.uint8)
    a[20:70, 30:66] = (*rm.hx("2b3a4a"), 255)      # coat, not light-family
    return a


def band(a, n, d, y0=26, x0=36):
    """Points within `d` of an n x n box's main diagonal — the shape of a
    blade seen broadside. A thin diagonal LINE has elongation far above 5
    and is caught by the original clause; what the broad clause exists for
    is this thick, compact band. Measured on the real sprite: 66px in a
    13x13 box, eigenvalues [4.82, 15.56], elongation 3.22."""
    n_px = 0
    for y in range(n):
        for x in range(n):
            if abs(y - x) / 2 ** 0.5 <= d:
                a[y0 + y, x0 + x] = (*LIGHT, 255)
                n_px += 1
    return n_px


def horizontal(a, w, h, y0=40, x0=36):
    a[y0:y0 + h, x0:x0 + w] = (*LIGHT, 255)
    return w * h


def sheathed(a):
    """blade_pass maps caught light-family pixels to DORMANT steel."""
    before = int(rm.eq(a, LIGHT).sum())
    out = a.copy()
    rm.blade_pass(out, "cipher", False)
    after = int(rm.eq(out, LIGHT).sum())
    return after < before, before - after


# --- the clause this test exists for -----------------------------------
# n=9 d=3.0 -> 61px elongation 2.99, inside the observed blade envelope
a = frame()
n = band(a, 9, 3.0)
ok, moved = sheathed(a)
check("blade seen broadside is sheathed", ok, f"{n}px, {moved} sheathed")

# --- gloves must survive; they are why a floor exists at all -----------
a = frame()
n = horizontal(a, 4, 2)                      # 8px
ok, moved = sheathed(a)
check("8px glove is NOT sheathed", not ok, f"{n}px, {moved} sheathed")

# --- a compact component below the floor must survive ------------------
# 8x4 rect: 32px, elongation 4.17 — inside the broad ELONGATION range but
# under its size floor. This is the case the 39px DASH streak stands for.
a = frame()
n = horizontal(a, 8, 4)
ok, moved = sheathed(a)
check("32px compact component below the floor is NOT sheathed",
      not ok, f"{n}px, elongation 4.17, {moved} sheathed")

# --- the ceiling: above the observed blade range, broad must not fire ---
# n=11 d=4.0 -> 91px... that clears the bulk bar, so use n=10 d=4.0 = 80px
a = frame()
n = band(a, 10, 4.0)
ok, moved = sheathed(a)
check(f"80px band above BLADE_BROAD_MAX({rm.BLADE_BROAD_MAX}) is NOT sheathed",
      not ok, f"{n}px, elongation 2.44, {moved} sheathed")

# --- the two original clauses must still hold --------------------------
a = frame()
n = horizontal(a, 24, 1)                     # thin line, elongation >> 5
ok, moved = sheathed(a)
check("thin drawn blade still sheathed (elongation clause)", ok, f"{moved} sheathed")

a = frame()
n = horizontal(a, 14, 8)                     # 112px, over the bulk bar
ok, moved = sheathed(a)
check("bulk over 90px still sheathed (bulk clause)", ok, f"{moved} sheathed")

print(f"\n{fails} FAILURES" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
