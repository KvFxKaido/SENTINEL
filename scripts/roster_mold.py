#!/usr/bin/env python3
"""The roster mold — one deterministic pipeline, five fighters (2026-07-31).

Molds the licensed Adventurer pack (nine verbs x four facings, 96x80
canvas — the canon body per the walk-off verdict) into the whole yard
roster. Identity lives in the head (sprites.js doctrine), so every
fighter is the shared wardrobe mold plus a deterministic head pass
translated from their audited 32x32 kit — and every blade ignites in
its fighter's mark color:

  CIPHER  dreads + solid visor band            cyan ignition
  VESPER  crested helm + visor slit            cobalt ignition
  KOA     topknot + mint headband + bare face  mint ignition
  SABLE   cowl + shadowed face + lit goggles   ice ignition
  SYN     cap + balaclava + red lenses + rust  red ignition

Succeeds scripts/cipher_mold.py (2026-07-30). The succession was
executed at promotion by resurrecting the retired script from git and
byte-diffing both pipelines over the full pack: 25 of Cipher's 36
sheets are byte-identical; the 11 divergent sheets are all deliberate
fixes — the 8 ATTACK sheets (the legacy flash heuristic misread big
swing arcs as damage flashes and skipped their ignition; arcs ignite
again here) and 3 HEAL sheets (source-color eye masks + mark-color
heal; heal_up has no eyes and stayed identical). The pinned
EXPECTED_CIPHER digest below guards that state: the run FAILS if the
cipher subset drifts, and changing the constant is a deliberate act a
diff will show — golden-transcript discipline, applied to pixels.
Roster-sheet review fixes carried in: KOA's eyes are per-cluster points,
not a band (a wide dark stripe read as a blindfold); VESPER's ignition
is cobalt, clearly apart from Cipher's cyan; VESPER's crest is a ridge
sunk into the helm dome, not a floating knob.

Pass 3 (2026-08-01) synthesizes the yard's bill — aim / fire / kneel —
which the pack does not ship. They are built as pack-palette SOURCE
frames and then run through the same build_frame as everything else, so
they inherit the head passes, the mark colors, and the flash law without
a single special case. The emitter's charge cell and its muzzle bloom
are drawn in the pack's heal greens, which already map to each fighter's
mark color; the housing is drawn in the pack's steels, which blade_pass
already sheathes when a sheet is not an ATTACK. Aiming shows cold steel
and only the shot lights — the blade's own law, read onto a barrel.
See the pass-3 comment block for the poses and their references.

Frame law: a frame that is mostly light-family IS the damage flash —
it takes the palette mold and nothing else. The blade classifier would
read it as one huge blade, and SYN's crew-red swap would repaint it;
both skip (caught chasing a review finding).

License note: the source pack allows use in projects but not
redistribution as an asset; pack directories and all outputs are
gitignored, regenerable artifacts. This script is the decision record.

Usage:
  python scripts/roster_mold.py
    reads  prototypes/FULL_Adventurer 2D Pixel Art/Sprites/**.png
           (or the FREE pack's four verbs if the full one is absent)
    writes assets/sprites/<fighter>/<ACTION>/<sheet>.png (+ preview.png)
           — 36 molded sheets per fighter, plus 12 synthesized on the
           full pack (AIM / FIRE / KNEEL)
    then re-runs one sheet per fighter and byte-compares.
"""
from PIL import Image
import numpy as np
import os, sys, glob, hashlib, io, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Test hooks: the harness (prototypes/walkable/test/) redirects both roots
# into temp dirs so it can fake packs and sweep outputs without ever
# touching the real licensed pack or real molded sheets. Unset, behavior
# is exactly the paths named in the docstring.
_PACKS = os.environ.get('ROSTER_MOLD_PACKS', os.path.join(ROOT, 'prototypes'))
_FULL = os.path.join(_PACKS, 'FULL_Adventurer 2D Pixel Art', 'Sprites')
_FREE = os.path.join(_PACKS, 'FREE_Adventurer 2D Pixel Art', 'Sprites')
FULL_PACK = os.path.isdir(_FULL)
PACK = _FULL if FULL_PACK else _FREE
OUT_ROOT = os.environ.get('ROSTER_MOLD_OUT', os.path.join(ROOT, 'assets', 'sprites'))

FRAME_W, FRAME_H = 96, 80   # frame COUNT varies per sheet (heal 12, hurt 4)

hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

# ---- pass 1: the shared wardrobe LUT (hand-assigned, one source of truth
# with cipher_sprites.js / sprites.js — the ops kit) ----------------------
LUT_HEX = {
    '391f21': '171310', '5d2c28': '332a1f',                      # hair -> dread darks
    '800020': '131c26', '571c27': '1d2a37',                      # coat reds ->
    '891e2b': '2b3a4a', 'c42430': '41586e',                      #   jacket steels
    'bf6f4a': '6b4a32', 'e69c69': '82603f', 'f6ca9f': '9a7850',  # skin ramp
    '8a4836': '3a2d20',                                          # leather strap
    'ffffff': 'e8f1f7', 'c7cfdd': 'c2d3e0', 'b4b4b4': '93aabf',  # scarf + blade
    '92a1b9': '6b8199', '858585': '68809a',                      #   lights
    '424c6e': '28374a', '2a2f4e': '1d2733',                      # fatigues
    '3d3d3d': '161e28', '272727': '141920', '1b1b1b': '10151c',  # cool darks
    '131313': '0d1117', '000000': '0a0d11', '1c121c': '10131a',
    '0069aa': '5ccfff',                                          # eyes -> visor
    # heal greens are NOT here: the heal effect takes each fighter's mark
    # color (build_frame), same law as the blade — SYN vents red, not cyan
}
LUT = {hx(k): hx(v) for k, v in LUT_HEX.items()}

HAIR_D, HAIR_E, HAIR_R = hx('171310'), hx('332a1f'), hx('4a3d2c')
SKINS = [hx('6b4a32'), hx('82603f'), hx('9a7850')]   # dark, mid, light
VISOR_A = hx('5ccfff')
OUTLINE = hx('10151c')
LIGHTS = [hx('e8f1f7'), hx('c2d3e0'), hx('93aabf'), hx('6b8199'), hx('68809a')]
DORMANT = dict(zip(LIGHTS, [hx('44586c'), hx('384756'), hx('2b3947'),
                            hx('223040'), hx('1d2a37')]))

# mark-color ignition ramps, hot -> cool, aligned to the five light tones.
# VESPER runs cobalt and SABLE runs pale ice so no two squad flames read
# as the same color at room scale (caught on the roster sheet: blue-vs-
# cyan collapsed at 32px).
ENERGY = {
    'cipher': [hx('eaffff'), hx('a5ecff'), hx('5ccfff'), hx('2196d8'), hx('1d7fc0')],
    'vesper': [hx('c8d8ff'), hx('8fa8f8'), hx('4a68e8'), hx('2a3fc0'), hx('1f2f96')],
    'koa':    [hx('eafff2'), hx('b0f0cc'), hx('6fd9a0'), hx('3aae72'), hx('2b8a58')],
    'sable':  [hx('f8feff'), hx('e0f6ff'), hx('b8e6ff'), hx('7cc0e8'), hx('5898c0')],
    'syn':    [hx('ffe4d6'), hx('ff9f88'), hx('ff5c5c'), hx('d93a30'), hx('a82a22')],
}
HALO = {
    'cipher': (26, 111, 168, 130), 'vesper': (42, 64, 200, 130),
    'koa': (40, 150, 100, 130), 'sable': (110, 170, 215, 120),
    'syn': (180, 60, 45, 130),
}

def eq(a, c):
    return (a[:, :, 0] == c[0]) & (a[:, :, 1] == c[1]) & (a[:, :, 2] == c[2]) & (a[:, :, 3] > 0)

def swap(a, pairs):
    for src, dst in pairs:
        m = eq(a, src)
        a[m, 0], a[m, 1], a[m, 2] = dst

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

# Identity masks come from the SOURCE frame, not the molded one: the
# source's 0069aa is uniquely eyes, its hair and skin ramps uniquely
# themselves. Detecting on molded colors was cipher_mold's latent bug —
# the heal greens mold into the visor family, so on heal sheets the eye
# detector could read the heal effect as eyes (caught in promotion).
SRC_HAIR = [hx('391f21'), hx('5d2c28')]
SRC_SKIN = [hx('bf6f4a'), hx('e69c69'), hx('f6ca9f')]
SRC_EYE = hx('0069aa')

def head_geometry(src):
    """shared per-frame geometry from SOURCE colors: head limit, masks"""
    alpha = src[:, :, 3] > 0
    ys = np.where(alpha)[0]
    head_limit = ys.min() + int((ys.max() - ys.min() + 1) * 0.45)
    hair = np.zeros(alpha.shape, dtype=bool)
    for c in SRC_HAIR:
        hair |= eq(src, c)
    hair[head_limit + 1:, :] = False
    eyes = eq(src, SRC_EYE)
    face = np.zeros(alpha.shape, dtype=bool)
    for c in SRC_SKIN:
        face |= eq(src, c)
    face[head_limit + 1:, :] = False
    return head_limit, hair, eyes, face

def blade_pass(out, name, ignite):
    """light-family components classified by SHAPE (PCA elongation / size);
    dormant steel sheathed, mark-color energy + halo when attacking"""
    light = np.zeros(out.shape[:2], dtype=bool)
    for c in LIGHTS:
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
        ev = np.linalg.eigvalsh(pts @ pts.T / size)
        if (ev[1] + 0.01) / (ev[0] + 0.01) > 5.0 or size > 90:
            blade[lab == i] = True
    table = dict(zip(LIGHTS, ENERGY[name])) if ignite else DORMANT
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
                        out[ny, nx] = HALO[name]

def crown_growth(out, hair, half_w, color, rows=1):
    """grow pixels above the hair crown — the dread-tip trick, skyward"""
    if not hair.any():
        return
    hys, hxs = np.where(hair)
    mid = (hxs.min() + hxs.max()) // 2
    for x in range(mid - half_w, mid + half_w + 1):
        col = hys[hxs == x]
        if not len(col):
            continue
        yt = col.min()
        for r in range(1, rows + 1):
            if yt - r >= 0 and out[yt - r, x, 3] == 0:
                out[yt - r, x] = (*color, 255)

# ---- per-fighter head passes ---------------------------------------

def head_cipher(out, geo):
    head_limit, hair, eyes, face = geo
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
    # the signature: a SOLID band through the eye rows — nothing may read
    # as an eye from any facing (decided 2026-07-30)
    for y in np.unique(np.where(eyes)[0]):
        row = np.where(eyes[y])[0]
        for x in range(row.min() - 1, row.max() + 2):
            if 0 <= x < out.shape[1] and out[y, x, 3] > 0 \
               and tuple(out[y, x, :3]) in (set(SKINS) | {VISOR_A}):
                out[y, x, :3] = VISOR_A

M_HELM, T_HELM, N_BLUE = hx('33465a'), hx('4b647d'), hx('2196d8')

def head_vesper(out, geo):
    head_limit, hair, eyes, face = geo
    dome = hair | face
    if not dome.any():
        return
    dys, dxs = np.where(dome)
    dy0, dx0 = dys.min(), dxs.min()
    for y, x in zip(dys, dxs):
        lit = (x - dx0 < 3) or (y - dy0 < 2)
        out[y, x, :3] = T_HELM if lit else M_HELM
    # the slit: eye rows only, one glint at the light edge
    for y in np.unique(np.where(eyes)[0]):
        row = np.where(eyes[y])[0]
        for x in range(row.min() - 1, row.max() + 2):
            if 0 <= x < out.shape[1] and out[y, x, 3] > 0 \
               and tuple(out[y, x, :3]) in (M_HELM, T_HELM):
                out[y, x, :3] = VISOR_A
        r2 = np.where(eq(out, VISOR_A)[y])[0]
        if len(r2):
            out[y, r2.min(), :3] = hx('bdefff')
    # the crest is a RIDGE: four columns, one row proud of the dome and
    # one row sunk INTO it, so it reads attached (caught on the roster
    # sheet — the two-column knob floated)
    if hair.any():
        hys, hxs = np.where(hair)
        mid = (hxs.min() + hxs.max()) // 2
        for x in range(mid - 2, mid + 2):
            col = hys[hxs == x]
            if not len(col):
                continue
            yt = col.min()
            out[yt, x, :3] = N_BLUE
            if yt - 1 >= 0 and out[yt - 1, x, 3] == 0:
                out[yt - 1, x] = (*N_BLUE, 255)

W_MINT = hx('bfe3cf')
KOA_HAIR = hx('1a1512')
KOA_SKIN = dict(zip(SKINS, [hx('6b4530'), hx('8a5a3a'), hx('a5744c')]))

def head_koa(out, geo):
    head_limit, hair, eyes, face = geo
    # bare face: warmer skin, everywhere on the body
    for src, dst in KOA_SKIN.items():
        m = eq(out, src)
        out[m, 0], out[m, 1], out[m, 2] = dst
    # plain dark hair (no dread stripe), his knot above the crown
    for y, x in zip(*np.where(hair)):
        out[y, x, :3] = KOA_HAIR
    crown_growth(out, hair, 1, KOA_HAIR, rows=2)
    # the mint band rides the brow — the row above the eyes
    eyerows = np.unique(np.where(eyes)[0])
    if len(eyerows):
        brow = eyerows.min() - 1
        koa_faces = set(KOA_SKIN.values()) | {KOA_HAIR}
        if brow >= 0:
            for x in range(out.shape[1]):
                if out[brow, x, 3] > 0 and tuple(out[brow, x, :3]) in koa_faces:
                    out[brow, x, :3] = W_MINT
    # eyes read as EYES, not a blindfold: each eye cluster keeps one dark
    # pixel at its centroid, the rest of the band returns to skin (caught
    # on the roster sheet — the source's wide eye band went all-dark)
    lab, n = components(eyes)
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        for y, x in zip(ys, xs):
            out[y, x, :3] = KOA_SKIN[SKINS[1]]
        out[int(round(ys.mean())), int(round(xs.mean())), :3] = OUTLINE

C_COWL, V_COWL, F_SHADOW = hx('232e26'), hx('33413a'), hx('0d1116')

def head_sable(out, geo):
    head_limit, hair, eyes, face = geo
    if hair.any():
        hys, hxs = np.where(hair)
        hy0, hx0 = hys.min(), hxs.min()
        for y, x in zip(hys, hxs):
            lit = (x - hx0 < 3) or (y - hy0 < 2)
            out[y, x, :3] = V_COWL if lit else C_COWL
        # the hood adds bulk: one pixel of growth into the sky
        for y, x in zip(hys, hxs):
            for dy, dx in ((-1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < out.shape[0] and 0 <= nx < out.shape[1] \
                   and out[ny, nx, 3] == 0 and ny <= head_limit:
                    out[ny, nx] = (*C_COWL, 255)
    # everything under the hood is shadow...
    out[face, 0], out[face, 1], out[face, 2] = F_SHADOW
    # ...except the goggles, lit inside it
    for y in np.unique(np.where(eyes)[0]):
        row = np.where(eyes[y])[0]
        out[y, row, 0], out[y, row, 1], out[y, row, 2] = hx('9fdcff')
        out[y, row.min(), :3] = hx('e8f7ff')

CAP, BALA = hx('2e211d'), hx('241b18')
RUST = [(hx('131c26'), hx('231511')), (hx('1d2a37'), hx('2e1d16')),
        (hx('2b3a4a'), hx('3a2622')), (hx('41586e'), hx('55352c')),
        (hx('1d2733'), hx('231a16')), (hx('28374a'), hx('332420')),
        (hx('141920'), hx('16100d'))]
CREW_RED = list(zip(LIGHTS, [hx('e06a4a'), hx('c2452f'), hx('9c3423'),
                             hx('7a2819'), hx('5f1f14')]))

def head_syn(out, geo):
    head_limit, hair, eyes, face = geo
    for y, x in zip(*np.where(hair)):
        out[y, x, :3] = CAP
    out[face, 0], out[face, 1], out[face, 2] = BALA
    # gloves: no skin anywhere on a crew body
    for s in SKINS:
        m = eq(out, s)
        out[m, 0], out[m, 1], out[m, 2] = BALA
    for y in np.unique(np.where(eyes)[0]):
        row = np.where(eyes[y])[0]
        out[y, row, 0], out[y, row, 1], out[y, row, 2] = hx('ff5c5c')
        out[y, row.min(), :3] = hx('ffd0c0')

HEADS = {'cipher': head_cipher, 'vesper': head_vesper, 'koa': head_koa,
         'sable': head_sable, 'syn': head_syn}
FIGHTERS = ['cipher', 'vesper', 'koa', 'sable', 'syn']

# The succession golden: sha256[:16] over Cipher's 36 sheets, pinned at
# promotion (2026-07-31, full pack). The run FAILS if this drifts —
# changing it is a deliberate act a diff will show (see docstring).
EXPECTED_CIPHER = 'a1b8428d6c84a0b5'
# and the same discipline over the synthesized verbs (aim/fire/kneel),
# pinned separately so each golden guards exactly one claim.
# Re-pinned 2026-08-01 for the explicit housing sheathe: the down and up
# emitters were shipping a LIT barrel because blade_pass skips components
# under six pixels and their housings are 3px and 2px runs. Only the
# synthesized sheets move; the molded digest above is unchanged, which is
# how you can tell the fix stayed inside its own pass.
EXPECTED_SYNTH = '17ae33e9da943204'

HEAL_GREENS = [hx('99e65f'), hx('5ac54f'), hx('33984b')]   # light -> dark

def build_frame(name, a, ignite):
    out = mold(a)
    # the heal effect channels the fighter's OWN tech: greens map into the
    # mark-color energy ramp, same law as the blade
    swap(out, list(zip(HEAL_GREENS, ENERGY[name][1:4])))
    alpha = out[:, :, 3] > 0
    if not alpha.any():
        return out
    # The flash law, stated exactly: a damage flash is a frame where the
    # ENTIRE figure renders light — measured, the pack's true flashes are
    # 1.00 light and its biggest swing arcs 0.82, so equality is the
    # convention, not a tuned threshold. (Caught chasing a review finding:
    # a >50% heuristic read the big swing-arc frames as flashes and
    # skipped their ignition — mid-swing frames shipped unlit.)
    light = np.zeros(out.shape[:2], dtype=bool)
    for c in LIGHTS:
        light |= eq(out, c)
    if light.sum() == alpha.sum():
        return out
    geo = head_geometry(a)             # identity masks from the SOURCE
    HEADS[name](out, geo)              # head before blade: ignition may
    blade_pass(out, name, ignite)      # mint visor-family pixels
    if name == 'syn':                  # crew-red after blade: it must not
        swap(out, RUST)                # eat the light-family blade
        swap(out, CREW_RED)
    return out

def process_sheet(name, path):
    rel = os.path.relpath(path, PACK)
    ignite = rel.replace('\\', '/').split('/')[0].upper().startswith('ATTACK')
    sheet = np.array(Image.open(path).convert('RGBA'))
    if sheet.shape[1] % FRAME_W or sheet.shape[0] != FRAME_H:
        sys.exit(f'{rel}: {sheet.shape[1]}x{sheet.shape[0]} is not a row of {FRAME_W}x{FRAME_H} frames')
    out = sheet.copy()
    for i in range(sheet.shape[1] // FRAME_W):
        x0 = i * FRAME_W
        out[:, x0:x0 + FRAME_W] = build_frame(name, sheet[:, x0:x0 + FRAME_W], ignite)
    return out

def process_frames(name, frames, ignite=False):
    """assemble a sheet from already-built SOURCE frames (the synthesis path).

    Each entry is (frame, housing) — housing being the emitter's own steel
    cells, sheathed here by name rather than left for blade_pass to find
    by shape. See place_emitter for why that distinction had teeth.
    """
    out = np.zeros((FRAME_H, FRAME_W * len(frames), 4), dtype=np.uint8)
    for i, (f, housing) in enumerate(frames):
        built = build_frame(name, f, ignite)
        if housing is not None:
            for src, dst in DORMANT.items():
                m = eq(built, src) & housing
                built[m, 0], built[m, 1], built[m, 2] = dst
        out[:, i * FRAME_W:(i + 1) * FRAME_W] = built
    return out

# ---- pass 3: the yard's bill, synthesized (2026-08-01) ----------------
#
# aim / fire / kneel do not exist in the pack. They are synthesized here
# into pack-palette SOURCE frames and then run through build_frame like
# any molded sheet, so the head passes, the mark colors, and the flash
# law apply with no special cases. Two rules carry the whole design:
#
#   * the emitter's charge cell and the muzzle bloom are drawn in the
#     pack's HEAL GREENS, which build_frame already swaps to each
#     fighter's mark color. Cipher's emitter vents cyan and SYN's vents
#     red for free — the mark-color law, reused rather than reimplemented.
#   * the housing is drawn in the pack's steels, so blade_pass sheathes
#     it to DORMANT here (ignite is False for every folder that is not
#     ATTACK*). Aiming shows cold steel; the shot is the only thing that
#     lights. That is the blade's own law, read onto a barrel.
#
# The poses are not invented from nothing. AIM lifts the HEAL draw — its
# frame 1 is the one where the held object sits at the chest, below the
# scarf, with the hand already closed on it — and replaces the vial with
# the emitter. The pack's artist drew that grip; we do not redraw it.
# The reference for what a fired weapon looks like from four sides is the
# licensed thug pack (`FREE Character 16-bit Thug Outlined`, 8 facings x
# 8 frames of gunplay): it says the arm is the pose, the flash is the
# verb, and — the answer to the hard facing — that a shot fired AWAY from
# the camera shows no weapon at all, only a bloom past the head.
#
# Facing up therefore has no vial to convert (measured: heal_up frames
# 0-4 contain zero green — the body occludes it), so its emitter anchor
# comes from body geometry rather than from the vial, and only the tip
# clears the shoulder.

SYNTH_BASE = 1              # HEAL frame 1: object at chest, clear of the scarf
LEG_TOP, FOOT_TOP = 48, 55  # the pack body's hip->leg and ankle->boot rows

EMIT = {
    'W': hx('ffffff'), 'w': hx('c7cfdd'), 'l': hx('b4b4b4'),
    'm': hx('92a1b9'), 'n': hx('858585'), 'K': hx('131313'),
    'C': hx('5ac54f'), 'H': hx('99e65f'),   # -> ENERGY[2] and ENERGY[1]
}

# authored as string grids, the dialect cipher32_walk.py established.
# side grids are drawn barrel-right and mirrored for left.
EMITTER_SIDE = [
    '..KKKK....',
    '.KwWllKKK.',
    'KKCCCnnmCK',
    '.KKKKKKKK.',
    '..KwK.....',
]
# pointed at the camera a barrel has no length — only the aperture shows,
# so the down emitter is a held block with a lit mouth and no protruding
# stub (the first cut grew one and read as held at the hip).
EMITTER_DOWN = [
    '.KKK.',
    'KwWlK',
    'KCCCK',
    'KKnKK',
]
# turned away, all that clears the body is the tip past the near shoulder —
# and it has to break the silhouette to be seen at all against the pack's
# back-slung sword.
EMITTER_UP = [
    '.KKK',
    'KwlK',
    'KCCK',
    '.KKK',
]
# muzzle bloom, hot -> spent. drawn barrel-right, pinned by the mouth edge.
#
# Sized by measurement, not by eye. Counting mark-colour pixels per frame,
# the shipped verbs run: blade ignition 706 at its peak, heal channel 38.
# The first bloom peaked at 21 — dimmer than a heal, and at room scale
# (a ~34px body drawn ~20px tall) that is a flicker, not a gunshot. These
# read at a peak near the heal channel's own extent and carry spikes as
# wide as the body, because at this scale reach carries further than area.
BLOOM = [
    ['...H.....',
     '..HCH..H.',
     '.HCCCH...',
     'HCCCCCCHH',
     '.HCCCH...',
     '..HCH..H.',
     '...H.....'],
    ['..H..',
     '.HCH.',
     'HCCCH',
     '.HCH.',
     '..H..'],
    ['.H.',
     'H.H',
     '.H.'],
]
# where the grid's core column/row lands relative to the anchor
EMIT_OFFSET = {'right': (-2, -3), 'left': (-2, -3), 'down': (-5, -2), 'up': (-1, 0)}


def pack_frame(rel, i):
    a = np.array(Image.open(os.path.join(PACK, rel.replace('/', os.sep))).convert('RGBA'))
    return a[:, i * FRAME_W:(i + 1) * FRAME_W].copy()


def green_mask(f):
    m = np.zeros(f.shape[:2], dtype=bool)
    for c in HEAL_GREENS:
        m |= eq(f, c)
    return m


def clear_green(f):
    f[green_mask(f)] = (0, 0, 0, 0)


STEEL_CHARS = set('Wwlmn')   # the housing tones, as opposed to core and outline


def stamp(f, grid, ay, ax, flip=False, mask=None):
    rows = [r[::-1] for r in grid] if flip else grid
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            y, x = ay + j, ax + i
            if 0 <= y < f.shape[0] and 0 <= x < f.shape[1]:
                f[y, x] = (*EMIT[ch], 255)
                if mask is not None and ch in STEEL_CHARS:
                    mask[y, x] = True


def emitter_anchor(f, facing):
    """where the emitter's core sits. Vial centroid where a vial is visible;
    from the body's own bbox facing up, where it never is."""
    m = green_mask(f)
    if m.any():
        ys, xs = np.where(m)
        return int(round(ys.mean())), int(round(xs.mean()))
    ys, xs = np.where(f[:, :, 3] > 0)
    # chest height on the near shoulder: the only part of a weapon held
    # away from the camera that clears the body. It overlaps the shoulder
    # deliberately — held a clear pixel off the silhouette it read as
    # floating rather than carried.
    return ys.min() + 12, xs.max() - 2


def place_emitter(f, facing, core='C', housing=None):
    """stamp the emitter over the vial and report the muzzle pixel.

    `housing` collects the steel cells this stamp owns. They are sheathed
    explicitly after the mold rather than left to blade_pass, which finds
    blades in art it did not author by shape — and skips components under
    six pixels. The side emitter's housing happened to clear that gate;
    the down and up emitters (a 3px and a 2px run) did not, so the two
    facings that matter most shipped a lit barrel while the panel said
    the emitter was cold (caught in review, and measured before believed).
    Authored geometry should not be rediscovered by a classifier.
    """
    ay, ax = emitter_anchor(f, facing)
    grid = {'down': EMITTER_DOWN, 'up': EMITTER_UP}.get(facing, EMITTER_SIDE)
    grid = [r.replace('C', core) for r in grid]
    oy, ox = EMIT_OFFSET[facing]
    clear_green(f)
    if facing == 'left':
        w = len(grid[0])
        x0 = ax - ox - w + 1
        stamp(f, grid, ay + oy, x0, flip=True, mask=housing)
        return ay + oy + 2, x0
    x0 = ax + ox
    stamp(f, grid, ay + oy, x0, mask=housing)
    if facing == 'down':
        return ay + oy + 2, x0 + 2      # the aperture, mouth-on to the camera
    if facing == 'up':
        return ay + oy, x0 + 1          # the tip clearing the shoulder
    return ay + oy + 2, x0 + len(grid[0]) - 1


def bloom(f, facing, my, mx, stage):
    """muzzle bloom at the muzzle, thrown along the facing.

    The grids are symmetric, so no rotation is needed — only which edge is
    pinned to the mouth. Firing at the camera is the odd one out: a bloom
    coming at you has no direction on screen, so it is centred on the
    aperture rather than thrown past it.
    """
    g = BLOOM[stage]
    h, w = len(g), max(len(r) for r in g)
    g = [r.ljust(w, '.') for r in g]
    if facing == 'right':
        stamp(f, g, my - h // 2, mx + 1)
    elif facing == 'left':
        stamp(f, g, my - h // 2, mx - w)
    elif facing == 'up':
        stamp(f, g, my - h, mx - w // 2)
    else:
        stamp(f, g, my + 1 - h // 2, mx - w // 2)


def aim_frames(facing):
    """held, charged, breathing — the body is still and the cell pulses"""
    out = []
    for core in ('C', 'C', 'H', 'C'):
        f = pack_frame(f'HEAL/heal_{facing}.png', SYNTH_BASE)
        housing = np.zeros(f.shape[:2], dtype=bool)
        place_emitter(f, facing, core=core, housing=housing)
        out.append((f, housing))
    return out


def fire_frames(facing):
    """one shot: hold, bloom + recoil, settle, hold"""
    out = []
    for core, stage in [('H', None), ('H', 0), ('H', 1), ('C', 2), ('C', None)]:
        f = pack_frame(f'HEAL/heal_{facing}.png', SYNTH_BASE)
        housing = np.zeros(f.shape[:2], dtype=bool)
        my, mx = place_emitter(f, facing, core=core, housing=housing)
        if stage is not None:
            bloom(f, facing, my, mx, stage)
        # recoil is one pixel, and only where it cannot lift the feet:
        # a side shot shoves the whole figure back along its own axis.
        # The housing mask rides the same roll or it stops naming the
        # pixels it owns.
        if stage in (0, 1) and facing in ('left', 'right'):
            d = -1 if facing == 'right' else 1
            out.append((np.roll(f, d, axis=1), np.roll(housing, d, axis=1)))
        else:
            out.append((f, housing))
    return out


KNEEL_DROP = 6      # rows the body loses; 7 is the most the boots leave room for


def kneel_frames(facing):
    """the legs fold and the body drops onto them; the boots never move.

    Row surgery, not a resample: torso rows are copied down, the hip rows
    the coat still shows carry the weight, and the shin rows the pose would
    hide are the ones dropped. The body law forbids scaling a body into
    being — copying rows is not scaling — and the ground contract holds
    because the boots stay on the line they were authored on.

    The first cut dropped four rows and read as a shorter man, not a
    crouching one: this body wears a long coat, so folding the legs edits
    something the coat already hides. What sells it is the hem — a coat on
    a dropped body pools outward, so the bottom rows flare a pixel. That
    flare is the crouch; the height loss alone was not.
    """
    out = []
    for i in (0, 4):
        src = pack_frame(f'IDLE/idle_{facing}.png', i)
        f = np.zeros_like(src)
        d = KNEEL_DROP
        f[24 + d:LEG_TOP + d] = src[24:LEG_TOP]                  # head + torso
        f[LEG_TOP + d:FOOT_TOP] = src[LEG_TOP:FOOT_TOP - d]      # what is left of the legs
        f[FOOT_TOP:] = src[FOOT_TOP:]                            # boots, planted
        # the hem pools: widen the last three coat rows by one pixel a side
        for y in range(FOOT_TOP - 4, FOOT_TOP):
            row = np.where(f[y, :, 3] > 0)[0]
            if not len(row):
                continue
            for x, src_x in ((row.min() - 1, row.min()), (row.max() + 1, row.max())):
                if 0 <= x < f.shape[1] and f[y, x, 3] == 0:
                    f[y, x] = f[y, src_x]
        out.append((f, None))    # kneel carries no emitter
    return out


# folder -> (stem, builder, needs the FULL pack). aim and fire read HEAL,
# which only the full pack ships; kneel reads IDLE, but it rides with them
# so the page keeps exactly two honest roster states, CORE and FULL.
SYNTH = {
    'AIM': ('aim', aim_frames),
    'FIRE': ('fire', fire_frames),
    'KNEEL': ('kneel', kneel_frames),
}
FACINGS = ('down', 'left', 'right', 'up')


def preview(name, out_dir):
    cells = []
    for rel in ['IDLE/idle_down.png', 'RUN/run_right.png', 'ATTACK 1/attack1_right.png',
                'ATTACK 2/attack2_down.png', 'HURT/hurt_right.png', 'DEATH/death_right.png',
                'HEAL/heal_down.png', 'AIM/aim_right.png', 'FIRE/fire_right.png',
                'KNEEL/kneel_down.png']:
        p = os.path.join(out_dir, rel.replace('/', os.sep))
        if not os.path.exists(p):
            continue
        with Image.open(p) as im:
            a = np.array(im)
        # frame 4 is a fair sample of most verbs, but FIRE's bloom is over
        # by then — a muzzle-flash verb previewing without its flash is a
        # picture that lies about the sheet
        fi = 1 if rel.startswith('FIRE/') else min(4, a.shape[1] // FRAME_W - 1)
        f = a[:, fi * FRAME_W:(fi + 1) * FRAME_W]
        ys, xs = np.where(f[:, :, 3] > 0)
        if not len(ys):
            continue
        cells.append(f[max(0, ys.min() - 3):min(f.shape[0], ys.max() + 4),
                       max(0, xs.min() - 3):min(f.shape[1], xs.max() + 4)])
    if not cells:
        print(f'{name}: preview skipped — nothing to draw')
        return
    Z = 6
    cw = max(c.shape[1] for c in cells) + 4
    ch = max(c.shape[0] for c in cells) + 6
    prev = Image.new('RGBA', ((cw * len(cells) + 4) * Z, ch * Z), (14, 16, 20, 255))
    x = 4
    for c in cells:
        img = Image.fromarray(c)
        cz = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        prev.paste(cz, (x * Z, 3 * Z), cz)
        x += cw
    prev.save(os.path.join(out_dir, 'preview.png'))

def main():
    sheets = sorted(glob.glob(os.path.join(PACK, '**', '*.png'), recursive=True))
    if not sheets:
        sys.exit(f'source pack not found at {PACK} — it is untracked by license; '
                 'restore it locally before regenerating')
    # Outputs mirror exactly ONE pack per fighter. Without this sweep,
    # molding FULL once and later remolding with only FREE leaves the 20
    # extended sheets from the old run in every fighter dir — the page
    # then reads a mixed two-run roster as CANON / FULL (fix ported from
    # PR #81's cipher_mold patch; five fighters wide it matters more).
    # Swept per fighter, never OUT_ROOT wholesale: the cipher32 walk-off
    # strips live beside these and belong to another script.
    for name in FIGHTERS:
        stale = os.path.join(OUT_ROOT, name)
        if os.path.isdir(stale):
            shutil.rmtree(stale)
    written, synth_written = [], []
    for name in FIGHTERS:
        out_dir = os.path.join(OUT_ROOT, name)
        for p in sheets:
            rel = os.path.relpath(p, PACK)
            dst = os.path.join(out_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            Image.fromarray(process_sheet(name, p)).save(dst)
            written.append(dst)
        for folder, (stem, builder) in sorted(SYNTH.items()) if FULL_PACK else []:
            for facing in FACINGS:
                dst = os.path.join(out_dir, folder, f'{stem}_{facing}.png')
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                Image.fromarray(process_frames(name, builder(facing))).save(dst)
                synth_written.append(dst)
        preview(name, out_dir)
        # stated directly rather than divided out of the running total:
        # the old form was only correct while every fighter synthesized an
        # identical count in strict order (caught in review)
        extra = f' + {len(SYNTH) * len(FACINGS)} synthesized' if FULL_PACK else ''
        print(f'{name}: {len(sheets)} sheets molded{extra}')

    # determinism, executed per fighter on encoded bytes
    ok = True
    for name in FIGHTERS:
        buf = io.BytesIO()
        Image.fromarray(process_sheet(name, sheets[0])).save(buf, format='PNG')
        first = os.path.join(OUT_ROOT, name, os.path.relpath(sheets[0], PACK))
        with open(first, 'rb') as f:
            if buf.getvalue() != f.read():
                ok = False
                print(f'{name}: determinism MISMATCH')
    def _digest(path):
        with open(path, 'rb') as fh:
            return hashlib.sha256(fh.read()).digest()

    def _sub(paths, who):
        return hashlib.sha256(b''.join(
            _digest(p) for p in sorted(paths) if os.sep + who + os.sep in p
        )).hexdigest()[:16]

    manifest = hashlib.sha256(b''.join(
        _digest(w) for w in sorted(written + synth_written))).hexdigest()[:16]
    # scoped deliberately: EXPECTED_CIPHER guards the succession from
    # cipher_mold.py, a claim about the MOLDED sheets only. Synthesized
    # verbs never entered that comparison, so they get their own golden
    # instead of diluting one that means something else.
    cipher_only = _sub(written, 'cipher')
    print(f'determinism re-run: {"IDENTICAL" if ok else "MISMATCH"}')
    print(f'{len(written)} molded + {len(synth_written)} synthesized '
          f'-> {OUT_ROOT}/<fighter>/')
    print(f'manifest sha256[:16] = {manifest}')
    print(f'cipher molded subset = {cipher_only}  (golden: {EXPECTED_CIPHER})')
    drift = cipher_only != EXPECTED_CIPHER
    if synth_written:
        synth_only = _sub(synth_written, 'cipher')
        print(f'cipher synth subset  = {synth_only}  (golden: {EXPECTED_SYNTH})')
        if synth_only != EXPECTED_SYNTH:
            print('synthesized subset DRIFTED from its pinned golden')
            drift = True
    if drift:
        print('a pinned golden DRIFTED — if the pipeline change is deliberate, '
              'update the constant in the same commit and say why; if not, '
              'this exit just saved the roster')
        sys.exit(1)
    if not ok:
        sys.exit(1)

if __name__ == '__main__':
    main()
