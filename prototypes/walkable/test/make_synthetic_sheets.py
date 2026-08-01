"""Synthetic fighter sheets for exercising the world pages' loaders.

NOT sprites — flat-colored frames at the pack's real geometry (96x80
rows, variable frame counts) so the roster/boot/animation code paths can
be executed headless without the licensed pack. Written into the
gitignored assets dir; each harness backs up any real sheets first and
restores them after.

Shared by two harnesses on purpose — the walkable room and the yard load
the SAME molded bodies, so faking them two different ways would let the
fixtures drift exactly where the convergence says they must not.

Modes: full (twelve verbs) / core (four) / badfull (extended sheets
present but wrong height — must fault on the page, never read as core).

Usage:  make_synthetic_sheets.py [mode] [fighter,fighter,...]
        fighters default to cipher (the walkable body); the yard passes
        all five because its roster is the whole squad.
"""
from PIL import Image, ImageDraw
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SPRITES = os.path.join(ROOT, "assets", "sprites")

# verb -> (folder, stem, frames): counts deliberately varied to prove the
# width-derived frame logic (heal 12 and hurt 4 match the real full pack)
VERBS = {
    "idle": ("IDLE", "idle", 8),
    "run": ("RUN", "run", 8),
    "attack1": ("ATTACK 1", "attack1", 8),
    "attack2": ("ATTACK 2", "attack2", 8),
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
    "idle": (90, 110, 130), "run": (70, 140, 90), "attack1": (170, 90, 60),
    "attack2": (170, 60, 120), "walk": (60, 100, 170), "dash": (220, 200, 80),
    "hurt": (200, 60, 60), "death": (60, 60, 70), "heal": (92, 207, 255),
    "aim": (150, 150, 165), "fire": (255, 180, 90), "kneel": (110, 90, 140),
}
FACINGS = ["down", "up", "left", "right"]
W, H = 96, 80
CORE = ["idle", "run", "attack1", "attack2"]

mode = sys.argv[1] if len(sys.argv) > 1 else "full"
fighters = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["cipher"])
wanted = CORE if mode == "core" else list(VERBS)

for fighter in fighters:
    out = os.path.join(SPRITES, fighter)
    for verb in wanted:
        folder, stem, frames = VERBS[verb]
        height = 64 if (mode == "badfull" and verb not in CORE) else H
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
