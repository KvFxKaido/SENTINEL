"""Synthetic fighter sheets for exercising the world pages' loaders.

NOT sprites — flat-colored frames at the pack's real geometry (96x80
rows, variable frame counts) so the roster/boot/animation code paths can
be executed headless without the licensed pack. Written into the
gitignored assets dir; each harness backs up any real sheets first and
restores them after.

Shared by two harnesses on purpose — the walkable room and the yard load
the SAME molded bodies, so faking them two different ways would let the
fixtures drift exactly where the convergence says they must not.

Modes: full (ten verbs) / badgeom (sheets present but wrong height —
must fault on the page, loudly, rather than degrade) / slice96 (the
render body's three-verb 96x80 sheets for ?body=render96 — flat frames
at the exact geometry render_canvas96.py emits, written into the
TRACKED sheets96 dir, which the harness backs up like everything else).

Usage:  make_synthetic_sheets.py [mode] [fighter,fighter,...]
        fighters default to cipher (the walkable body); the yard passes
        all five because its roster is the whole squad.
"""
from PIL import Image, ImageDraw
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SPRITES = os.path.join(ROOT, "assets", "sprites", "composed")

# verb -> (folder, stem, frames): counts deliberately varied to prove the
# width-derived frame logic (heal 12 and hurt 4 match the real full pack)
VERBS = {
    "idle": ("IDLE", "idle", 8),
    "run": ("RUN", "run", 8),
    "walk": ("WALK", "walk", 8),
    "dash": ("DASH", "dash", 6),
    "hurt": ("HURT", "hurt", 4),
    "death": ("DEATH", "death", 6),
    "heal": ("HEAL", "heal", 12),
    # the synthesized verbs load through exactly the same path as molded
    # ones, so the harness fakes them the same way — kneel's 2 frames are
    # the new shortest sheet, which keeps the width-derived frame logic
    # honest at the bottom of the range as heal does at the top
    "aim": ("AIM", "aim", 4),
    "fire": ("FIRE", "fire", 5),
    "kneel": ("KNEEL", "kneel", 2),
}
COLORS = {
    "idle": (90, 110, 130), "run": (70, 140, 90),
    "walk": (60, 100, 170), "dash": (220, 200, 80),
    "hurt": (200, 60, 60), "death": (60, 60, 70), "heal": (92, 207, 255),
    "aim": (150, 150, 165), "fire": (255, 180, 90), "kneel": (110, 90, 140),
}
FACINGS = ["down", "up", "left", "right"]
W, H = 96, 80
# The room composes ONE roster now — the free-pack "core four" state went
# away with the blade (2026-08-02), so there is no reduced set to fake.
# What still needs faking is the two ways a roster can be broken, which is
# what the room's two fault paths are for.
ALWAYS = ["idle", "run"]

mode = sys.argv[1] if len(sys.argv) > 1 else "full"
fighters = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["cipher"])
wanted = list(VERBS)

# The slice declares idle/walk/kneel with the render's own frame counts
# (4/8/2 — the re-frame preserves them). Flat sheet names, no verb
# folders: sheets96 is strip-per-verb, the shape render_canvas96.py emits.
if mode == "slice96":
    RENDER96 = os.path.join(ROOT, "assets", "original",
                            "cipher_render", "sheets96")
    SLICE = {"idle": 4, "walk": 8, "kneel": 2}
    os.makedirs(RENDER96, exist_ok=True)
    for verb, frames in SLICE.items():
        for facing in FACINGS:
            img = Image.new("RGBA", (W * frames, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            for i in range(frames):
                x0 = i * W
                d.rectangle([x0 + 36, 20 + (i % 3), x0 + 60, 57],
                            fill=(*COLORS[verb], 255))
            img.save(os.path.join(RENDER96, f"{verb}_{facing}.png"))
    print(f"synthetic sheets: slice96 roster, {len(SLICE)} verbs x 4 facings")
    sys.exit(0)

for fighter in fighters:
    out = os.path.join(SPRITES, fighter)
    for verb in wanted:
        folder, stem, frames = VERBS[verb]
        height = 64 if (mode == "badgeom" and verb not in ALWAYS) else H
        for facing in FACINGS:
            img = Image.new("RGBA", (W * frames, height), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            for i in range(frames):
                x0 = i * W
                # a body-ish rectangle standing on ground row 57, wobbling per frame
                d.rectangle([x0 + 36, 20 + (i % 3), x0 + 60, min(57, height - 3)],
                            fill=(*COLORS[verb], 255))
            os.makedirs(os.path.join(out, folder), exist_ok=True)
            img.save(os.path.join(out, folder, f"{stem}_{facing}.png"))

print(f"synthetic sheets: {mode} roster, {len(wanted)} verbs x 4 facings "
      f"x {len(fighters)} fighter(s): {','.join(fighters)}")
