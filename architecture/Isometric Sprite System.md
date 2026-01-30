# SENTINEL Isometric Sprite System v1.1

**Resolution:** 48x48 pixels  
**Perspective:** Isometric 2:1 (2 horizontal : 1 vertical)  
**Directions:** 4-way (N/E/S/W)  
**Status:** Patched with Gemini technical review

---

## Core Principles

### The 48x48 Sweet Spot
- **32x32:** Too small for character identity details (temple scars, gear placement)
- **48x48:** Goldilocks zone - readable silhouettes, manageable pixel debt
- **64x64:** Beautiful but unsustainable for solo dev walk cycles

### Modular Construction Philosophy
**20% Rule:** Any faction variant shares 80% pixels with base template. Only modify what creates identity.

### Isometric Math
- **2:1 ratio** prevents jagged diagonal lines
- Horizontal movement: 2 pixels = 1 pixel vertical shift
- Keeps tile edges clean, prevents "staircase" artifacts

---

## Layer Architecture

### Layer 1: Shadow (Persistent)
- **Size:** Oval, ~20x10 pixels
- **Position:** Anchored to ground plane
- **Opacity:** 40% black
- **Critical:** Does NOT rotate with sprite - prevents ground "wobbling"
- **Rendering:** Pre-rendered on tile, not sprite layer

### Layer 2: Base Body
- **Torso:** 24x28 pixels (half sprite width, ~60% height)
- **Legs:** Variable based on stance
- **Contact Poses:** See Walk Cycle section for anti-slide logic

### Layer 3: Gear
- **Equipment:** Laptop case, sidearm, drone controller
- **Placement:** 4-6 pixels per item
- **⚠️ MIRRORING TRAP:** West facing requires manual gear flip
  - East sprite mirrored = gear positions flipped
  - Fix: Manually reposition gear pixels to match canonical loadout
  - Example: Laptop case stays left hip, sidearm stays right thigh

### Layer 4: Face/Detail
- **Head:** 12x12 pixels
- **Character markers:** Temple scars (2 pixels), visor, hood
- **Tech accents:** LED indicators, screen glow

---

## Animation States

### Idle (Revised Timing)
- **Frames:** 2
- **Timing:** ~~0.8s~~ → **0.5s per frame** (1.0s total loop)
- **Motion:** Subtle 1px vertical shift (breathing)
- **Reason for change:** 0.8s felt "heavy" - characters appeared to breathe in slow motion
- **Alternative:** If 1px shift feels jarring, add 3rd middle frame for smoother pulse

### Walk
- **Frames:** 4 per direction
- **Timing:** 0.15s per frame (0.6s full cycle)
- **Phases:**
  1. **Contact:** Leading foot planted, body lowered 1px
  2. **Passing:** Weight shifts, body at neutral height
  3. **Contact:** Trailing foot planted, body lowered 1px
  4. **Passing:** Return to neutral
- **Anti-Slide Logic:** 
  - Contact poses MUST align foot pixels to grid anchor points
  - Body lowers 1px during contact = visual weight transfer
  - Prevents "skating" appearance on tile transitions

### Combat Stance
- **Frames:** 1 (static)
- **Weapon ready:** Arms extended forward 2-3 pixels
- **Legs:** Wide stance for stability

### Tech Interaction
- **Frames:** 2-3
- **Action:** Arms raised to chest height
- **Details:** Device glow (2x2 pixels, cyan accent)

---

## Palette System

### Base Tones (Grounded Earth)
- **Body:** #4A4238 (warm brown-gray)
- **Clothing:** #2C2824 (dark earth)
- **Shadows:** #1A1814 (near-black)

### Tech Accents (Focal Points)
- **LED indicators:** #00FFFF (cyan) - **CRITICAL for readability**
- **Screen glow:** #1A9B8E (muted teal)

### ⚠️ Contrast Warning (Gemini Observation)
**Issue:** Grounded palette risks blending with dark industrial/earth-tone floors

**Solutions:**
1. **Tech accents must be bright enough** to act as focal points
2. **Optional rim light:** Subtle 1px highlight on top-facing shoulder edges
3. **Color:** #6B5D52 (lighter than base, separates sprite from floor)
4. **Application:** Top edge of shoulders, head - suggests overhead light source

---

## Direction System (4-Way)

### North (Moving Up-Right)
- **Visible:** Back of head, shoulders
- **Gear:** Backpack silhouette visible
- **Legs:** Right leg forward

### East (Moving Down-Right)
- **Visible:** Right profile
- **Gear:** Sidearm on right thigh, laptop case on left hip
- **Face:** Right temple scar visible

### South (Moving Down-Left)
- **Visible:** Front view
- **Gear:** Both sidearm and laptop case visible
- **Face:** Full face, both temple scars

### West (Moving Up-Left)
- **⚠️ DERIVED FROM EAST VIA MIRROR**
- **Manual Fix Required:** Gear must be repositioned after mirror
  - Laptop case: Move back to left hip (canonical position)
  - Sidearm: Move back to right thigh (canonical position)
- **Reason:** Prevents equipment "swapping sides" in player's mental model

---

## Faction Variants (20% Rule)

| Faction | Silhouette Change | Color Shift | Key Detail | Pixel Budget |
|---------|-------------------|-------------|------------|--------------|
| **Cipher (Base)** | Standard | Muted Brown/Gray | Temple scars, drone controller | — |
| **Syndicate** | +4px shoulders (bulkier) | Industrial rust accents | Visible rifle, visor overlay | ~192px |
| **Ember Scout** | +6px hood, +8px pouches | Sun-faded earth tones | Repair patches (3-4 pixel clusters) | ~216px |
| **Lattice** | Angular, clean edges | Tech blue/gray | Chest-mounted tablet (8x6px) | ~180px |

**Modularity Check:** Each variant shares base body layer, only swaps Layer 3 (Gear) and Layer 4 (Detail).

---

## Technical Notes

### Why 4 Directions (Not 8)
- **Diagonal facings** (NE, SE, SW, NW) require different footprint math
- 2:1 ratio distorts width on diagonals - creates asymmetry
- **Time savings:** 4 directions = half the animation frames
- **Playable build priority:** Polish later if needed

### Rendering Order
1. Shadow (ground layer, pre-rendered on tile)
2. Base body (direction-dependent)
3. Gear (manual flip for West)
4. Face/detail (rim light if dark floor)

### Future 8-Direction Consideration
If you eventually need diagonals:
- Recalculate 2:1 ratio for NE/SE/SW/NW footprints
- Gear layer will need 8 unique states (can't mirror diagonals)
- Animation workload increases ~70%

---

## Implementation Workflow

### Phase 1: Cipher Base
1. Create North walk cycle (4 frames)
2. Test contact poses for grid alignment
3. Add rim light if floor blend occurs
4. Derive East from North (new art)
5. Derive South from North (new art)
6. **Mirror East → West, manually fix gear**

### Phase 2: Idle Refinement
1. Test 0.5s timing
2. If 1px shift feels jarring, add middle frame
3. Verify shadow stays grounded during breathing

### Phase 3: Faction Variants
1. Copy Cipher base layers 1-2
2. Swap gear layer (Layer 3) per faction
3. Add faction detail layer (Layer 4)
4. Test 80/20 rule - if touching >20% pixels, simplify

---

## Gemini Contributions
- Idle timing analysis (0.8s → 0.5s)
- West mirroring gear trap identification
- Color contrast floor blend warning
- Walk cycle contact pose anti-slide logic
- 8-direction footprint math complexity note

---

**Version:** 1.1 (Gemini-patched)  
**Status:** Production-ready for CLI implementation  
**Next Review:** After first faction variant (Syndicate) test
```