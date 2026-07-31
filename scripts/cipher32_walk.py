#!/usr/bin/env python3
"""The walk-off body: System A Cipher (32x32) learns to walk.

Authors 4-direction idle + walk cycles for the 32x32 System A Cipher as
string grids -- the same authoring form as tactical3d/sprites.js and
architecture/mocks/cipher_sprites.js, which this body extends. Emits PNG
frame strips into assets/sprites/cipher32/ for the walk-off audition page
(prototypes/walkable/walkoff.html).

Gait convention is pokered (the product-vision reference): stand / step /
stand / step, feet on the ground line (row 29), no tween frames. Left
faces are mirrored right faces, baked here so the renderer never flips.

Regenerable output; only this script is the decision record.
    python scripts/cipher32_walk.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sprites", "cipher32")

PAL = {
    "B": "10151c",  # outline
    "D": "171310",  # dreadlocks dark
    "E": "332a1f",  # dreadlocks texture
    "S": "6b4a32",  # skin
    "A": "5ccfff",  # data visor
    "L": "bdefff",  # visor glow
    "N": "2196d8",  # nexus accent
    "J": "2b3a4a",  # jacket mid
    "H": "41586e",  # jacket lit (light from upper-left)
    "P": "1d2733",  # fatigues
    "G": "141920",  # boots / belt
}
hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

EMPTY = "................................"

# ---- shared pieces -------------------------------------------------
# The down-facing head + torso are CIPHER_A rows 5-22 verbatim
# (architecture/mocks/cipher_sprites.js) -- this body EXTENDS the audited
# specimen, it does not redraw it.
HEAD_DOWN = [
    ".............DDDDDD.............",
    "...........DEDDEDDEDD...........",
    "..........DDEDDEDDEDDD..........",
    "..........DDSSSSSSSSDD..........",
    "..........DSSSSSSSSSSD..........",
    "..........BALAAAAAAAAB..........",
    "..........BALAAAAAAAAB..........",
    "..........DSSSSSSSSSSD..........",
    "..........DSSSSBBSSSSD..........",
    "...........BSSSSSSSSB...........",
    "............BSSSSSSB............",
    "..............BSSB..............",
]
TORSO_DOWN = [
    "...........BJNNNNNNJB...........",
    "..........BHJJNNNNJJJB..........",
    "..........BHBJJJJJJBJB..........",
    "..........BHBJJJJJJBJB..........",
    "..........BHBJJJJJJBJB..........",
    "..........BGGGGGGGGGGB..........",
]

# Back of the head: no face, no band — and the strand texture is COLUMNAR
# (constant E columns), because alternating it per row stacks into a
# basket-weave checker (caught on the first contact sheet; the walkable
# head pass learned the same lesson as DDE columns).
HEAD_UP = [
    ".............DDDDDD.............",
    "...........DEDDEDDEDD...........",
    "..........DDEDDEDDEDDD..........",
    "..........DDEDDEDDEDDD..........",
    "..........DDEDDEDDEDDD..........",
    "..........DDEDDEDDEDDD..........",
    "..........DDEDDEDDEDDD..........",
    "..........DDEDDEDDEDDD..........",
    "..........DDEDDEDDEDDD..........",
    "...........BDDDDDDDDB...........",
    "............BDDDDDDB............",
    "..............BDDB..............",
]
TORSO_UP = [   # plain jacket back -- the N band is a chest, not a halo
    "...........BJJJJJJJJB...........",
    "..........BHJJJJJJJJJB..........",
    "..........BHBJJJJJJBJB..........",
    "..........BHBJJJJJJBJB..........",
    "..........BHBJJJJJJBJB..........",
    "..........BGGGGGGGGGGB..........",
]

LEGS_STAND = [
    "...........BPPPPPPPPB...........",
    "...........BPPB..BPPB...........",
    "...........BPPB..BPPB...........",
    "...........BPPB..BPPB...........",
    "...........BGGB..BGGB...........",
    "..........BGGGB..BGGGB..........",
    "..........BBBBB..BBBBB..........",
]
# One foot lifts a single pixel; the planted sole stays on row 29.
LEGS_STEP_L = [
    "...........BPPPPPPPPB...........",
    "...........BPPB..BPPB...........",
    "...........BPPB..BPPB...........",
    "...........BGGB..BPPB...........",
    "..........BGGGB..BGGB...........",
    "..........BBBBB..BGGGB..........",
    ".................BBBBB..........",
]
LEGS_STEP_R = [row[::-1] for row in LEGS_STEP_L]

# ---- profile (right; left is baked as a mirror) --------------------
HEAD_RIGHT = [
    ".............DDDDD..............",
    "............DDEDDDD.............",
    "............DDEDDDDD............",
    "............DDEDSSSSB...........",
    "............DDEDSSSSB...........",
    "............DDEAALLB............",
    "............DDEAALLB............",
    "............DDEDSSSB............",
    "............DDEDSSSB............",
    ".............BDSSSB.............",
    "..............BSSB..............",
    "..............BSSB..............",
]
TORSO_RIGHT = [
    ".............BJJNNJB............",
    "............BHJJNNJJB...........",
    "............BHJBJJJJB...........",
    "............BHJBJJJJB...........",
    "............BHJBJJJJB...........",
    "............BGGGGGGGB...........",
]
LEGS_R_STAND = [
    ".............BPPPPPB............",
    ".............BPPPPB.............",
    ".............BPPPPB.............",
    ".............BPPPPB.............",
    ".............BGGGGB.............",
    ".............BGGGGGB............",
    ".............BBBBBB.............",
]
LEGS_R_STRIDE = [
    ".............BPPPPPB............",
    "............BPPPBPPB............",
    "............BPPB.BPPB...........",
    "...........BPPB...BPPB..........",
    "...........BGGB...BGGB..........",
    "..........BGGGB...BGGGB.........",
    "..........BBBBB...BBBBB.........",
]
# The other phase: rear foot in toe-off, one pixel up, front foot planted
# on the ground line. Profile legs share one tone, so leg IDENTITY is
# ambiguous by design — the gait alternates PHASE (contact / toe-off),
# which is what reads as walking at this scale (caught in review: both
# stride slots pointed at the same grid, so nothing alternated at all).
LEGS_R_TOEOFF = [
    ".............BPPPPPB............",
    "............BPPPBPPB............",
    "............BPPB.BPPB...........",
    "............BGGB..BPPB..........",
    "...........BGGGB..BGGB..........",
    "...........BBBBB.BGGGB..........",
    "..................BBBBB.........",
]

def figure(head, torso, legs):
    grid = [EMPTY] * 5 + head + torso + legs + [EMPTY] * 2
    assert len(grid) == 32, f"{len(grid)} rows"
    return grid

FRAMES = {
    "down": {
        "stand": figure(HEAD_DOWN, TORSO_DOWN, LEGS_STAND),
        "stepA": figure(HEAD_DOWN, TORSO_DOWN, LEGS_STEP_L),
        "stepB": figure(HEAD_DOWN, TORSO_DOWN, LEGS_STEP_R),
    },
    "up": {
        "stand": figure(HEAD_UP, TORSO_UP, LEGS_STAND),
        "stepA": figure(HEAD_UP, TORSO_UP, LEGS_STEP_L),
        "stepB": figure(HEAD_UP, TORSO_UP, LEGS_STEP_R),
    },
    "right": {
        "stand": figure(HEAD_RIGHT, TORSO_RIGHT, LEGS_R_STAND),
        "stepA": figure(HEAD_RIGHT, TORSO_RIGHT, LEGS_R_STRIDE),
        "stepB": figure(HEAD_RIGHT, TORSO_RIGHT, LEGS_R_TOEOFF),
    },
}
FRAMES["left"] = {
    key: [row[::-1] for row in grid] for key, grid in FRAMES["right"].items()
}

# pokered gait: stand / step / stand / other-step
CYCLES = {
    "idle": ["stand"],
    "walk": ["stand", "stepA", "stand", "stepB"],
}

def validate():
    bad = []
    for facing, frames in FRAMES.items():
        for key, grid in frames.items():
            tag = f"{facing}.{key}"
            if len(grid) != 32:
                bad.append(f"{tag}: {len(grid)} rows")
            for i, row in enumerate(grid):
                if len(row) != 32:
                    bad.append(f"{tag} r{i}: {len(row)} cols")
                for ch in row:
                    if ch != "." and ch not in PAL:
                        bad.append(f"{tag} r{i}: unknown '{ch}'")
            if not any(ch != "." for ch in grid[29]):
                bad.append(f"{tag}: nothing stands on row 29")
            if any(ch != "." for ch in grid[30] + grid[31]):
                bad.append(f"{tag}: art below the ground line")
    return bad

def paint(grid):
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != ".":
                px[x, y] = (*hx(PAL[ch]), 255)
    return im

def build():
    bad = validate()
    if bad:
        raise SystemExit("grid errors:\n  " + "\n  ".join(bad))
    os.makedirs(OUT, exist_ok=True)
    for facing, frames in FRAMES.items():
        for anim, cycle in CYCLES.items():
            strip = Image.new("RGBA", (32 * len(cycle), 32), (0, 0, 0, 0))
            for i, key in enumerate(cycle):
                strip.paste(paint(frames[key]), (i * 32, 0))
            strip.save(os.path.join(OUT, f"{anim}_{facing}.png"))
    print(f"built {len(FRAMES) * len(CYCLES)} strips -> {OUT}")

def contact(path, zoom=8):
    """audition sheet: every unique frame, all facings, zoomed"""
    order = ["down", "right", "left", "up"]
    keys = ["stand", "stepA", "stepB"]
    W, H = 34 * len(keys) + 2, 34 * len(order) + 2
    sheet = Image.new("RGBA", (W * zoom, H * zoom), (14, 16, 20, 255))
    for r, facing in enumerate(order):
        for c, key in enumerate(keys):
            im = paint(FRAMES[facing][key]).resize((32 * zoom, 32 * zoom), Image.NEAREST)
            sheet.paste(im, ((2 + c * 34) * zoom, (2 + r * 34) * zoom), im)
    sheet.save(path)
    print("contact ->", path)

if __name__ == "__main__":
    import sys
    build()
    if len(sys.argv) > 1:
        contact(sys.argv[1])
