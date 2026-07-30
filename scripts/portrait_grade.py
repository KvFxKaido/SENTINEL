"""Portrait register grading — the art-style audit's decision, as a tool.

The register pair (architecture/art_style_audit.md, decided 2026-07-29):
photoreal generator output is SOURCE ONLY and never ships untreated. This
script produces the registers that do ship:

    {name}.feed.png    broadcast surfaces — "the feed they watch"
    {name}.term.png    owned surfaces, phosphor — "the rig you own"
    {name}.amber.png   owned surfaces, warm mood — opposition/archive

The treatments mirror architecture/mocks/portrait_audition.html exactly —
the audition is the spec, this is the implementation. Grain is seeded from
the filename and register, so grading is deterministic: same source in,
same bytes out, rerun forever. No model in the loop.

Usage:
    python scripts/portrait_grade.py <portrait.png> [more.png ...]
"""

import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

# the six-stop ramps from the audition (hex -> rgb rows)
PHOSPHOR = ["#06120b", "#17231a", "#33463a", "#6d8a72", "#9fc7ab", "#cfe8d6"]
AMBER    = ["#120b06", "#221709", "#4a3012", "#8a5c22", "#d19540", "#ffe2b0"]

TERM_RES = 128          # terminal registers render at this res, upscaled nearest
SCAN_REF = 128          # scanline period = size / SCAN_REF (mock: 2px at 256)


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _luma(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def _grain(a, amt, rng):
    n = rng.uniform(-amt / 2, amt / 2, a.shape[:2])
    return a + n[..., None]


def _scanlines(a, alpha):
    period = max(2, a.shape[0] // SCAN_REF)
    thick = period // 2
    mask = (np.arange(a.shape[0]) % period) < thick
    a[mask] *= (1 - alpha)
    return a


def grade_feed(src, rng):
    a = np.asarray(src, dtype=np.float64)
    l = _luma(a)[..., None]
    a = l + (a - l) * 0.5                                   # desaturate toward luma
    a = 255 / (1 + np.exp(-((a / 255) - 0.5) * 6))          # gentle S-curve
    t = (_luma(a) / 255)[..., None]
    a += (1 - t) * [-6, 8, -2] + t * [14, 6, -12]           # split-tone: green shadows, amber highlights
    a = _grain(a, 26, rng)
    a = _scanlines(a, 0.10)
    return Image.fromarray(np.uint8(a.clip(0, 255)))


def grade_terminal(src, ramp, rng, out_size):
    small = src.resize((TERM_RES, TERM_RES), Image.BILINEAR)
    a = np.asarray(small, dtype=np.float64)
    idx = np.minimum(len(ramp) - 1, (_luma(a) / 255 * len(ramp)).astype(int))
    a = np.array([_rgb(h) for h in ramp], dtype=np.float64)[idx]   # posterized ramp
    a = _grain(a, 14, rng)
    img = Image.fromarray(np.uint8(a.clip(0, 255)))
    img = img.resize((out_size, out_size), Image.NEAREST)          # texel discipline
    a = np.asarray(img, dtype=np.float64)
    a = _scanlines(a, 0.08)
    return Image.fromarray(np.uint8(a.clip(0, 255)))


def grade(path):
    src = Image.open(path).convert("RGB")
    if src.width != src.height:                             # portraits are square; center-crop if not
        s = min(src.size)
        src = src.crop(((src.width - s) // 2, (src.height - s) // 2,
                        (src.width + s) // 2, (src.height + s) // 2))
    out = []
    for register, fn in [
        ("feed",  lambda rng: grade_feed(src, rng)),
        ("term",  lambda rng: grade_terminal(src, PHOSPHOR, rng, src.width)),
        ("amber", lambda rng: grade_terminal(src, AMBER, rng, src.width)),
    ]:
        # crc32, not hash(): Python salts str hashes per process, and the
        # whole point is byte-identical output on every rerun
        rng = np.random.default_rng(zlib.crc32(f"{path.stem}:{register}".encode()))
        dest = path.with_suffix(f".{register}.png")
        fn(rng).save(dest)
        out.append(dest)
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    for arg in argv[1:]:
        p = Path(arg)
        if not p.is_file():
            print(f"SKIP {p} — not found")
            continue
        if any(p.name.endswith(f".{r}.png") for r in ("feed", "term", "amber")):
            print(f"SKIP {p} — already a graded register")
            continue
        for dest in grade(p):
            print(f"WROTE {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
