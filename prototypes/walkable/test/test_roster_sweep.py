"""Executes the roster mold's sweep claims against the ACTUAL script.

Runs scripts/roster_mold.py twice — fake FULL pack, then fake FREE
pack — and judges the sweep on disk state: a remold with a smaller pack
must clear every fighter's stale extended sheets, and must never touch
a sibling artifact (the cipher32 walk-off strips) that another script
owns.

Fully sandboxed via the mold's test hooks (ROSTER_MOLD_PACKS /
ROSTER_MOLD_OUT): everything happens in a temp dir, so the real
licensed packs and real molded sheets are never read, written, or
deleted — safe to run on a working checkout.

With synthetic input the pinned cipher golden MUST fire (exit 1,
"DRIFTED") — that is the guard working, and this test asserts it fires
rather than treating it as noise.

Run:  python test_roster_sweep.py   (needs pillow + numpy)
"""
from PIL import Image, ImageDraw
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MOLD = os.path.join(ROOT, "scripts", "roster_mold.py")
FIGHTERS = ["cipher", "vesper", "koa", "sable", "syn"]

CORE = {"IDLE": "idle", "RUN": "run", "ATTACK 1": "attack1", "ATTACK 2": "attack2"}
EXT = {"WALK": "walk", "DASH": "dash", "HURT": "hurt", "DEATH": "death", "HEAL": "heal"}
# synthesized, not molded: no pack folder feeds these, so the sweep is the
# ONLY thing that removes them on a downgrade — worth its own claim
SYNTH = {"AIM": "aim", "FIRE": "fire", "KNEEL": "kneel"}
FACINGS = ["down", "up", "left", "right"]

def fake_pack(base, verbs):
    for folder, stem in verbs.items():
        d = os.path.join(base, folder)
        os.makedirs(d, exist_ok=True)
        for facing in FACINGS:
            img = Image.new("RGBA", (96 * 8, 80), (0, 0, 0, 0))
            dr = ImageDraw.Draw(img)
            for i in range(8):
                dr.rectangle([i * 96 + 36, 22, i * 96 + 60, 57], fill=(60, 80, 100, 255))
            img.save(os.path.join(d, f"{stem}_{facing}.png"))

fails = 0
def check(name, ok, detail=""):
    global fails
    print(f'{"PASS" if ok else "FAIL"}  {name}{"  — " + detail if detail else ""}')
    if not ok:
        fails += 1

with tempfile.TemporaryDirectory(prefix="roster-sweep-") as tmp:
    packs = os.path.join(tmp, "packs")
    out = os.path.join(tmp, "out")
    env = {**os.environ, "ROSTER_MOLD_PACKS": packs, "ROSTER_MOLD_OUT": out}
    full = os.path.join(packs, "FULL_Adventurer 2D Pixel Art", "Sprites")
    free = os.path.join(packs, "FREE_Adventurer 2D Pixel Art", "Sprites")

    def mold():
        return subprocess.run([sys.executable, MOLD], env=env,
                              capture_output=True, text=True)

    # a sibling artifact that is NOT the mold's to manage
    sentinel = os.path.join(out, "cipher32", "keepme.txt")
    os.makedirs(os.path.dirname(sentinel), exist_ok=True)
    open(sentinel, "w").write("walk-off strip stand-in")

    fake_pack(full, {**CORE, **EXT})
    r = mold()
    check("full mold writes 180 molded sheets", "180 molded" in r.stdout,
          (r.stdout.strip().splitlines() or ["<no output>"])[-1])
    check("full mold synthesizes 60 more", "60 synthesized" in r.stdout)
    check("determinism IDENTICAL per fighter", "determinism re-run: IDENTICAL" in r.stdout)
    check("cipher golden guard FIRES on synthetic input",
          r.returncode == 1 and "DRIFTED" in r.stdout)
    check("all five fighter dirs written",
          all(os.path.isdir(os.path.join(out, f, "HEAL")) for f in FIGHTERS))
    check("synthesized verbs written for every fighter",
          all(os.path.isdir(os.path.join(out, f, d)) for f in FIGHTERS for d in SYNTH))

    # the FULL pack goes away; only FREE remains — the review scenario:
    # stale extended outputs must not survive the remold
    shutil.rmtree(os.path.dirname(full))
    fake_pack(free, CORE)
    r = mold()
    check("free mold writes 80 molded sheets", "80 molded" in r.stdout)
    check("free mold synthesizes nothing", "0 synthesized" in r.stdout)
    stale = [f"{f}/{d}" for f in FIGHTERS for d in EXT
             if os.path.isdir(os.path.join(out, f, d))]
    check("stale extended outputs swept in every fighter dir", not stale,
          f"left behind: {stale[:5]}")
    # aim/fire/kneel have no pack folder to go missing, so nothing but the
    # sweep can retire them — a downgrade that left them behind would show
    # the page a FULL roster built from two different runs
    orphan = [f"{f}/{d}" for f in FIGHTERS for d in SYNTH
              if os.path.isdir(os.path.join(out, f, d))]
    check("synthesized verbs swept on a pack downgrade", not orphan,
          f"left behind: {orphan[:5]}")
    check("core outputs present per fighter",
          all(os.path.isdir(os.path.join(out, f, "IDLE")) for f in FIGHTERS))
    check("sibling cipher32 artifact untouched", os.path.exists(sentinel))

print(f"\n{fails} FAILURES" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
