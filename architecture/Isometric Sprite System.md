
# SENTINEL Isometric Sprite System

## Canvas Size & Grid

**Base sprite:** 48x48 pixels (gives room for detail while staying crisp)
**Isometric angle:** 2:1 ratio (classic isometric)
**Tile footprint:** Character occupies ~24x32 pixel actual space, centered in 48x48 canvas

**Why 48x48?**
- 32x32 too cramped for gear details
- 64x64 too large for tactical overview
- 48x48 = sweet spot for readable detail

---

## Layer Structure (Bottom to Top)

### Layer 1: Shadow
- 16x8 pixel oval
- 30% opacity black
- Anchored to character feet
- Doesn't rotate with facing

### Layer 2: Body Base
- Simple capsule shape
- 12px wide x 20px tall (actual body)
- Neutral gray (#4a4a4a)
- This layer defines posture

### Layer 3: Clothing
- Utilitarian jacket/vest
- Earth tones: #5c5449 (brown-gray)
- Pockets/straps visible as darker lines
- Layered look (collar, hem details)

### Layer 4: Gear
- **Backpack:** 8x10px, sits on shoulders
- **Laptop case:** visible on left hip, 6x4px
- **Belt pouches:** right hip, 4x3px each
- **Sidearm:** holster outline, right thigh

### Layer 5: Head/Face
- 8x8px square centered on body
- Minimal facial features (just eyes + nose suggestion)
- Hair/hood as silhouette
- **Cipher specific:** short cropped hair, neutral expression

### Layer 6: Tech Details
- Subtle temple scars (2px light line each side)
- Drone controller clipped to belt (4x2px device)
- Gear wear (scuffed edges on backpack)

---

## Color Palette (Cipher Base)

**Body/Clothing:**
- Base gray: `#4a4a4a`
- Jacket: `#5c5449` (muted brown-gray)
- Pants: `#3d3d3d` (darker gray)
- Boots: `#2a2a2a` (near-black)

**Gear:**
- Backpack: `#4d5357` (blue-gray, worn)
- Laptop case: `#3a3a3a` (dark, reinforced)
- Belt/straps: `#2d2520` (brown-black leather)

**Tech accents:**
- Drone controller LED: `#4a90a4` (muted cyan, single pixel)
- Temple scars: `#6a6a6a` (lighter gray, subtle)

**Skin:**
- Face/hands: `#d4a574` (neutral warm tone)
- Shadow: `#b8856a` (darker)

---

## Directional Facings

**4-direction system** (start simple, expand to 8 later)

### South (facing camera)
- Full face visible
- Backpack partially hidden
- Feet in wide stance

### East (facing right)
- Profile view
- Backpack visible on left side
- Laptop case on front hip
- Single eye visible

### North (facing away)
- Back of head
- Full backpack visible
- Shoulders squared
- No face visible

### West (facing left)
- Mirrored East
- Backpack on right side
- Laptop case on front hip

---

## Animation Frames

### Idle (2 frames, loops)
1. **Frame 1:** Base stance
2. **Frame 2:** Slight weight shift (1px body move)
- **Timing:** 0.8s per frame (slow, deliberate)

### Walk (4 frames per direction)
1. **Frame 1:** Left foot forward, arms neutral
2. **Frame 2:** Contact pose, both feet down
3. **Frame 3:** Right foot forward, arms neutral  
4. **Frame 4:** Contact pose, both feet down
- **Timing:** 0.15s per frame (purposeful walk, not rushed)

### Interact (1 static frame)
- Body leans slightly forward
- Hand raised to chest height (tablet gesture)
- Used when talking to NPCs or examining objects

---

## Modular Customization (For Other Characters)

**Faction variants use SAME body base, swap:**

### Syndicate Enforcer
- Heavier armor plates (shoulders, chest)
- Weapon more prominent (rifle instead of sidearm)
- Helmet/visor instead of bare head
- Colors: `#5a4a3a` (industrial brown) + `#8b4513` (rust accents)

### Ember Scout  
- Lighter gear, more pockets
- Hood instead of bare head
- Visible improvised repairs (patches, tape)
- Colors: `#6b5d4f` (earth brown) + `#8a6f47` (sun-faded fabric)

### Lattice Engineer
- Clean lines, less wear
- Tech panel on chest (tablet mount)
- Tool belt instead of weapon
- Colors: `#4a5a6a` (blue-gray) + `#7a8a9a` (light tech blue)

**You change ~20% of pixels to create distinct characters, keep 80% base**

---

## Pixel-Level Construction Guide

### Starting Template (South-facing idle)

```
Row 01-08: [empty - headroom]
Row 09-16: Head (8x8 square, centered)
Row 17-18: Neck/shoulders
Row 19-30: Torso + arms
Row 31-38: Legs  
Row 39-40: Feet
Row 41-48: [shadow layer]
```

**Example ASCII map (S = skin, C = clothing, G = gear, . = transparent):**

```
........................................
........................................
................SSSSSSSS................  [Head]
................SSSSSSSS................
................SSSSSSSS................
..............CCGGGGGGCC................  [Shoulders + backpack top]
..............CCGGGGGGCC................
............CCCCGGGGGGCCCC..............  [Torso + backpack]
............CCCCGGGGGGCCCC..............
............CCCCGGGGGGCCCC..............
..............CCCCCCCCCC................  [Waist]
..............CCGGGGGGCC................  [Hips + gear]
................CCCCCC..................  [Legs start]
................CCCCCC..................
................CCCCCC..................
................CCCCCC..................
..................CC....................  [Feet]
........................................
......ssssssssssssssssss................  [Shadow]
........................................
```

---

## Production Workflow

### Phase 1: Base Character (Cipher)
1. Open Aseprite, create 48x48 canvas
2. Draw south-facing idle (single frame)
3. Add layers: shadow → body → clothing → gear → head
4. Test in-game (static sprite)

**Time estimate:** 1-2 hours

### Phase 2: Idle Animation
1. Duplicate frame
2. Shift body 1px
3. Export as 2-frame animation
4. Test looping

**Time estimate:** 30 minutes

### Phase 3: Cardinal Directions
1. Draw east-facing (can mirror for west)
2. Draw north-facing (back view)
3. Test movement between facings

**Time estimate:** 1 hour

### Phase 4: Walk Cycle
1. Animate walk for south (4 frames)
2. Adapt for east/north
3. Export sprite sheet

**Time estimate:** 2-3 hours

**Total for playable Cipher:** ~5-6 hours

---

## Export Format

**Sprite sheet layout:**
```
[Idle S] [Idle E] [Idle N] [Idle W]
[Walk S frame 1-4] [Walk E frame 1-4] ...
[Interact S] [Interact E] ...
```

**Export settings:**
- Format: PNG (transparent background)
- No filter/smoothing (keep pixel-perfect)
- Include JSON metadata for frame positions

---

## Testing Checklist

- [ ] Character visible at 1080p resolution from tactical camera
- [ ] Silhouette readable when zoomed out
- [ ] Facing direction clear from any angle
- [ ] Gear identifiable (can you see the laptop case?)
- [ ] Animation doesn't "float" or "slide"
- [ ] Colors distinct from background tiles
- [ ] Matches faction neutral aesthetic

---

## Next Character Workflow

Once Cipher works:
1. Duplicate base body
2. Swap head (8x8 swap)
3. Modify gear (change backpack to helmet, etc)
4. Adjust color palette
5. Export variant

**Time per variant:** 30-60 minutes

---
## Readability Lock (Design-Binding)

If a sprite cannot be correctly identified at a glance:
- Facing direction
- Equipped role (armed, tech, civilian)
- Faction affiliation (via silhouette + color)

Then the sprite is invalid, regardless of detail quality.

No outlines, glows, or UI markers may be added to compensate.
Readability must come from shape, contrast, and motion alone.