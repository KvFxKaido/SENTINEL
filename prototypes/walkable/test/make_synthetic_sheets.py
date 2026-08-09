"""Synthetic fighter sheets for exercising the world pages' loaders.

NOT sprites — flat-colored frames at the pack's real geometry (96x80
rows, variable frame counts) so the roster/boot/animation code paths can
be executed headless without the licensed pack. Written into the
gitignored assets dir; each harness backs up any real sheets first and
restores them after.

Shared by the headless harnesses on purpose — the walkable room and yard
load the SAME molded bodies, while the walk-off adds its two alternate
body grammars at their own real geometry.

Modes: full (ten verbs) / badgeom (sheets present but wrong height —
must fault on the page, loudly, rather than degrade) / walkoff (the
three-body audition's two authored grammars plus the hybrid stand/walk)
/ slice96 (the render body's six-verb 96x80 sheets for ?body=render96
— flat frames at the exact geometry render_canvas96.py emits, written
into the TRACKED sheets96 dir, which the harness backs up like
everything else).

Usage:  make_synthetic_sheets.py [mode] [fighter,fighter,...]
        fighters default to cipher (the walkable body); the yard passes
        all five because its roster is the whole squad.
"""
from PIL import Image, ImageDraw
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SPRITES = os.path.join(ROOT, "assets", "sprites", "composed")
WALKOFF_PACK = os.path.join(ROOT, "assets", "sprites", "cipher")
WALKOFF_HYBRID = os.path.join(
    ROOT, "assets", "sprites", "hybrid", "cipher", "sheets")
WALKOFF_RENDER = os.path.join(
    ROOT, "assets", "original", "cipher_render", "sheets")

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

# Every destination this script populates gets this marker, and a
# destination that exists WITHOUT it is refused: it holds real art the
# harnesses move aside before generating. Running this script directly
# against a live checkout used to overwrite the tracked render sheets
# and the gitignored pack mold with flat rectangles, no backup taken
# (caught in review, P1). The marker travels with the fixtures, so
# cleanup that removes the dir removes the claim with it.
MARKER = "SYNTHETIC-FIXTURES"


def claim(root):
    if os.path.isdir(root) and os.listdir(root) \
            and not os.path.exists(os.path.join(root, MARKER)):
        sys.exit(f"REFUSING to write fixtures into {root}: it holds real "
                 f"art (no {MARKER} marker). The harnesses back real "
                 "sheets aside before generating — run them, not this "
                 "script, against a live checkout.")
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, MARKER), "w") as fh:
        fh.write("flat harness fixtures - safe to delete\n")


def write_sheet(path, frames, frame_w, height, color, ground_row):
    img = Image.new("RGBA", (frame_w * frames, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    half_body = max(8, frame_w // 8)
    centre = frame_w // 2
    for i in range(frames):
        x0 = i * frame_w
        d.rectangle([
            x0 + centre - half_body,
            max(8, ground_row - 37 + (i % 3)),
            x0 + centre + half_body,
            ground_row,
        ], fill=(*color, 255))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def write_walkoff():
    for root in (WALKOFF_PACK, WALKOFF_HYBRID, WALKOFF_RENDER):
        claim(root)
    pack = {
        "idle": ("IDLE", "idle", 8),
        "run": ("RUN", "run", 8),
        "attack1": ("ATTACK 1", "attack1", 8),
        "attack2": ("ATTACK 2", "attack2", 8),
        "kneel": ("KNEEL", "kneel", 2),
    }
    colors = {
        **COLORS,
        "attack1": (255, 145, 70),
        "attack2": (245, 95, 70),
    }
    for verb, (folder, stem, frames) in pack.items():
        for facing in FACINGS:
            write_sheet(
                os.path.join(WALKOFF_PACK, folder, f"{stem}_{facing}.png"),
                frames, 96, 80, colors[verb], 57)

    for verb, frames in {"idle": 8, "walk": 8}.items():
        for facing in FACINGS:
            write_sheet(
                os.path.join(WALKOFF_HYBRID, f"{verb}_{facing}.png"),
                frames, 96, 80, COLORS[verb], 57)

    for verb, frames in {
            "idle": 4, "walk": 8, "run": 8, "kneel": 2, "aim": 2}.items():
        for facing in FACINGS:
            write_sheet(
                os.path.join(WALKOFF_RENDER, f"{verb}_{facing}.png"),
                frames, 64, 64, COLORS[verb], 47)

    print("synthetic walkoff sheets: pack 5 verbs, hybrid idle/walk "
          "(no kneel), render idle/walk/run/kneel/aim x 4 facings")
# The room composes ONE roster now — the free-pack "core four" state went
# away with the blade (2026-08-02), so there is no reduced set to fake.
# What still needs faking is the two ways a roster can be broken, which is
# what the room's two fault paths are for.
ALWAYS = ["idle", "run"]

mode = sys.argv[1] if len(sys.argv) > 1 else "full"
fighters = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["cipher"])
wanted = list(VERBS)

if mode == "walkoff":
    write_walkoff()
    sys.exit(0)

# The slice declares idle/walk/run/dash/kneel/aim with the render's own frame
# counts (4/8/8/7/2/2 — the re-frame preserves them). Flat sheet names, no verb
# folders: sheets96 is strip-per-verb, the shape render_canvas96.py
# emits — and TRACKED, which is exactly why it rides claim(): a direct
# run against the real re-frame output must refuse, not flatten it.
if mode == "slice96":
    RENDER96 = os.path.join(ROOT, "assets", "original",
                            "cipher_render", "sheets96")
    claim(RENDER96)
    for verb, frames in {
            "idle": 4, "walk": 8, "run": 8, "dash": 7,
            "kneel": 2, "aim": 2}.items():
        for facing in FACINGS:
            write_sheet(
                os.path.join(RENDER96, f"{verb}_{facing}.png"),
                frames, W, H, COLORS[verb], 57)
    print("synthetic sheets: slice96 roster, 6 verbs x 4 facings")
    sys.exit(0)

for fighter in fighters:
    out = os.path.join(SPRITES, fighter)
    claim(out)
    for verb in wanted:
        folder, stem, frames = VERBS[verb]
        height = 64 if (mode == "badgeom" and verb not in ALWAYS) else H
        for facing in FACINGS:
            write_sheet(
                os.path.join(out, folder, f"{stem}_{facing}.png"),
                frames, W, height, COLORS[verb], min(57, height - 3))

print(f"synthetic sheets: {mode} roster, {len(wanted)} verbs x 4 facings "
      f"x {len(fighters)} fighter(s): {','.join(fighters)}")
