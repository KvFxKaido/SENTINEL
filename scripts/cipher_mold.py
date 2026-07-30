"""Cipher walk-sprite mold — deterministic pipeline (2026-07-30).

Molds the licensed "FREE_Adventurer 2D Pixel Art" pack (4-direction
idle/run/attack sheets, 8 frames of 96x80 each) into Cipher, the
walkable-world protagonist. Three passes, all deterministic — same
inputs, same bytes:

  1. Palette LUT: 24 source colors hand-mapped onto Cipher's materials
     (cipher_sprites.js palette; spatially verified, not hue-guessed).
     The leather strap stays warm on purpose — one warm material
     against the cool steels.
  2. Head pass: columnar dread strands (System A's DDE cadence), chunky
     tips, crown rim light, and the signature visor band — SOLID
     (decided 2026-07-30: no glint pixels, nothing may read as an eye
     from any facing).
  3. Blade pass: light-family components classified by SHAPE (PCA
     elongation / size — blades are long-thin or huge, scarves are
     blobs, cuffs are specks). The energy blade is DORMANT dark steel
     in idle/run sheets and IGNITES to the visor's cyan family with a
     halo in attack sheets (decided 2026-07-30: ignition stays — the
     only lights on this body are his own tech, and the blade joins
     the visor only when violence starts).

License note: the source pack allows use in projects but not
redistribution as an asset, so the pack directory is gitignored and
must stay out of the public repo. Outputs are regenerable artifacts
(same rule as graded portraits) and are gitignored too.

Usage:
  python scripts/cipher_mold.py
    reads  prototypes/FREE_Adventurer 2D Pixel Art/Sprites/**.png
    writes assets/sprites/cipher/<ACTION>/<sheet>.png  (+ preview.png)
    then re-runs one sheet in memory and byte-compares — the
    determinism claim is executed, not narrated.
"""
from PIL import Image
import numpy as np
import os, sys, glob, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, 'prototypes', 'FREE_Adventurer 2D Pixel Art', 'Sprites')
OUT = os.path.join(ROOT, 'assets', 'sprites', 'cipher')

FRAME_W, FRAME_H, FRAMES = 96, 80, 8

hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

# ---- pass 1: the LUT (the decision record — 24 colors, hand-assigned) ----
LUT_HEX = {
    # hair -> dreadlock warm darks
    '391f21': '1d1813', '5d2c28': '332a1f',
    # coat reds -> jacket steels
    '800020': '131c26', '571c27': '1d2a37', '891e2b': '2b3a4a', 'c42430': '41586e',
    # skin -> Cipher skin, face kept lit
    'bf6f4a': '6b4a32', 'e69c69': '82603f', 'f6ca9f': '9a7850',
    # leather strap/boots: the one warm material
    '8a4836': '3a2d20',
    # scarf + blade lights -> tech-wrap / steel (split later by shape)
    'ffffff': 'e8f1f7', 'c7cfdd': 'c2d3e0', 'b4b4b4': '93aabf',
    '92a1b9': '6b8199', '858585': '68809a',
    # trousers -> fatigues
    '424c6e': '28374a', '2a2f4e': '1d2733',
    # neutral darks -> cool blacks
    '3d3d3d': '161e28', '272727': '141920', '1b1b1b': '10151c',
    '131313': '0d1117', '000000': '0a0d11', '1c121c': '10131a',
    # eyes -> the data visor
    '0069aa': '5ccfff',
}
LUT = {hx(k): hx(v) for k, v in LUT_HEX.items()}

HAIR_D, HAIR_E, HAIR_R = hx('1d1813'), hx('332a1f'), hx('4a3d2c')
SKINS = {hx('6b4a32'), hx('82603f'), hx('9a7850')}
VISOR_A = hx('5ccfff')
LIGHT_FAMILY = {hx('e8f1f7'), hx('c2d3e0'), hx('93aabf'), hx('6b8199'), hx('68809a')}
ENERGY = {
    hx('e8f1f7'): hx('eaffff'), hx('c2d3e0'): hx('a5ecff'), hx('93aabf'): hx('5ccfff'),
    hx('6b8199'): hx('2196d8'), hx('68809a'): hx('1d7fc0'),
}
DORMANT = {
    hx('e8f1f7'): hx('44586c'), hx('c2d3e0'): hx('384756'), hx('93aabf'): hx('2b3947'),
    hx('6b8199'): hx('223040'), hx('68809a'): hx('1d2a37'),
}
HALO = (26, 111, 168, 130)

def eq(a, c):
    return (a[:, :, 0] == c[0]) & (a[:, :, 1] == c[1]) & (a[:, :, 2] == c[2]) & (a[:, :, 3] > 0)

def mold(a):
    out = a.copy()
    for src, dst in LUT.items():
        m = eq(a, src)
        out[m, 0], out[m, 1], out[m, 2] = dst
    return out

def components(mask):
    lab = np.zeros(mask.shape, dtype=int)
    cur = 0
    for sy, sx in zip(*np.where(mask)):
        if lab[sy, sx]:
            continue
        cur += 1
        stack = [(sy, sx)]
        lab[sy, sx] = cur
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] \
                       and mask[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = cur
                        stack.append((ny, nx))
    return lab, cur

def head_and_blade(a, ignite):
    out = a.copy()
    alpha = out[:, :, 3] > 0
    if not alpha.any():
        return out
    ys, xs = np.where(alpha)
    y0, y1 = ys.min(), ys.max()
    head_limit = y0 + int((y1 - y0 + 1) * 0.45)

    hair = (eq(out, HAIR_D) | eq(out, HAIR_E))
    hair[head_limit + 1:, :] = False
    if hair.any():
        hys, hxs = np.where(hair)
        hx0 = hxs.min()
        for y, x in zip(hys, hxs):
            out[y, x, :3] = HAIR_E if (x - hx0) % 3 == 1 else HAIR_D
        for x in np.unique(hxs):
            col = hys[hxs == x]
            if (x - hx0) % 3 == 1:
                yb = col.max()
                if yb + 1 <= head_limit and out[yb + 1, x, 3] == 0:
                    out[yb + 1, x] = (*HAIR_D, 255)
            if (x - hx0) % 2 == 0:
                yt = col.min()
                if yt - 1 >= 0 and out[yt - 1, x, 3] == 0:
                    out[yt, x, :3] = HAIR_R

    eyes = eq(out, VISOR_A)
    for y in np.unique(np.where(eyes)[0]):
        row = np.where(eyes[y])[0]
        for x in range(row.min() - 1, row.max() + 2):
            if 0 <= x < out.shape[1] and out[y, x, 3] > 0 \
               and tuple(out[y, x, :3]) in (SKINS | {VISOR_A}):
                out[y, x, :3] = VISOR_A

    light = np.zeros(alpha.shape, dtype=bool)
    for c in LIGHT_FAMILY:
        light |= eq(out, c)
    lab, n = components(light)
    blade = np.zeros_like(light)
    for i in range(1, n + 1):
        cy, cx = np.where(lab == i)
        size = len(cy)
        if size < 6:
            continue
        pts = np.stack([cy, cx]).astype(float)
        pts -= pts.mean(axis=1, keepdims=True)
        cov = pts @ pts.T / size
        ev = np.linalg.eigvalsh(cov)
        if (ev[1] + 0.01) / (ev[0] + 0.01) > 5.0 or size > 90:
            blade[lab == i] = True
    table = ENERGY if ignite else DORMANT
    for src, dst in table.items():
        m = eq(out, src) & blade
        out[m, 0], out[m, 1], out[m, 2] = dst
    if ignite and blade.any():
        for y, x in zip(*np.where(blade)):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < out.shape[0] and 0 <= nx < out.shape[1] \
                       and out[ny, nx, 3] == 0:
                        out[ny, nx] = HALO
    return out

def process_sheet(path):
    ignite = 'ATTACK' in path.upper()
    sheet = np.array(Image.open(path).convert('RGBA'))
    out = sheet.copy()
    for i in range(FRAMES):
        x0 = i * FRAME_W
        out[:, x0:x0 + FRAME_W] = head_and_blade(mold(sheet[:, x0:x0 + FRAME_W]), ignite)
    return out

def main():
    sheets = sorted(glob.glob(os.path.join(PACK, '**', '*.png'), recursive=True))
    if not sheets:
        sys.exit(f'source pack not found at {PACK} — it is untracked by license; '
                 'restore it locally before regenerating')
    written = []
    for p in sheets:
        rel = os.path.relpath(p, PACK)
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        Image.fromarray(process_sheet(p)).save(dst)
        written.append(dst)
        print('molded', rel)

    # preview contact sheet: one frame per action, down + right facings
    cells = []
    for rel in ['IDLE/idle_down.png', 'RUN/run_right.png', 'ATTACK 1/attack1_right.png', 'ATTACK 2/attack2_down.png']:
        a = np.array(Image.open(os.path.join(OUT, rel.replace('/', os.sep))))
        f = a[:, 4 * FRAME_W:5 * FRAME_W]
        ys, xs = np.where(f[:, :, 3] > 0)
        cells.append(f[ys.min() - 3:ys.max() + 4, xs.min() - 3:xs.max() + 4])
    Z = 6
    cw = max(c.shape[1] for c in cells) + 4
    ch = max(c.shape[0] for c in cells) + 6
    prev = Image.new('RGBA', ((cw * len(cells) + 4) * Z, ch * Z), (14, 16, 20, 255))
    x = 4
    for c in cells:
        img = Image.fromarray(c)
        cz = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        prev.paste(cz, (x * Z, 3 * Z), cz)   # mask: keep the dark backdrop
        x += cw
    prev.save(os.path.join(OUT, 'preview.png'))

    # execute the determinism claim: reprocess one sheet, byte-compare
    check_src = sheets[0]
    again = process_sheet(check_src)
    ondisk = np.array(Image.open(written[0]))
    same = np.array_equal(again, ondisk)
    digest = hashlib.sha256(b''.join(
        hashlib.sha256(open(w, 'rb').read()).digest() for w in sorted(written)
    )).hexdigest()[:16]
    print(f'determinism re-run: {"IDENTICAL" if same else "MISMATCH"}')
    print(f'{len(written)} sheets -> {OUT}')
    print(f'manifest sha256[:16] = {digest}')
    if not same:
        sys.exit(1)

if __name__ == '__main__':
    main()
