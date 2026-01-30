# SENTINEL Isometric Animation Rules v1.1

**Resolution:** 48x48 pixels  
**Perspective:** Isometric 2:1  
**Directions:** 4-way (N/E/S/W)  
**Original Spec:** Gemini  
**Integration Patches:** Claude  
**Status:** Production-ready

---

## Core Animation States

### IDLE (Breathing)

**Base Configuration (2-Frame):**
- **Frame 1:** Neutral position
- **Frame 2:** Body raised 1px (chest expansion)
- **Timing:** 0.5s per frame (1.0s loop)
- **Layer behavior:** All layers move together (body+gear+detail)

**Alternative Configuration (3-Frame):**
- **Frame 1:** Neutral position
- **Frame 2:** Body raised 1px (inhale peak)
- **Frame 3:** Return to neutral (exhale)
- **Timing:** 0.4s per frame (1.2s loop)
- **Use when:** 2-frame shift feels too jarring

**Shadow Layer:** Static throughout idle animation - does NOT move with breathing.

---

### WALK CYCLE (4 Frames Per Direction)

#### Frame Breakdown

**Frame 1 - Contact (Leading Foot)**
```
Body: Lowered 1px from neutral
Leading leg: Extended forward 3px
Trailing leg: Extended back 2px
Arms: Natural counter-swing
Foot pixel: MUST align to grid anchor point
```

**Frame 2 - Passing**
```
Body: Neutral height
Legs: Both vertical (passing position)
Arms: Neutral
Weight: Centered
```

**Frame 3 - Contact (Trailing Foot)**
```
Body: Lowered 1px from neutral
Trailing leg: Now leading, extended forward 3px
Previous leading leg: Now trailing, extended back 2px
Arms: Counter-swing reversed
Foot pixel: MUST align to grid anchor point
```

**Frame 4 - Passing (Return)**
```
Body: Neutral height
Legs: Both vertical (passing position)
Arms: Neutral
Weight: Centered
Return to Frame 1 seamlessly
```

#### Timing
- **0.15s per frame** (0.6s full cycle)
- 4 frames × 4 directions = 16 total walk sprites

#### Anti-Slide Math Proof

**Grid Movement:** Character moves 2 tiles/second at walk speed.

**Tile size:** 32px isometric projection  
**Character speed:** 64px/second (2 tiles)  
**Walk cycle duration:** 0.6s  
**Distance per cycle:** 64px × 0.6s = 38.4px

**Frame distribution:**
- Frame 1 (contact): 0px movement (foot planted)
- Frame 2 (passing): 19.2px movement
- Frame 3 (contact): 0px movement (foot planted)
- Frame 4 (passing): 19.2px movement

**Critical alignment:** Contact frames (1 & 3) occur when body position aligns with tile grid intersections. This prevents visual "skating."

**Verification test:**
```
Loop walk animation with grid overlay visible
Contact frames should show foot pixel exactly on grid line
Any deviation = sliding artifact
```

---

### COMBAT STANCE

**Configuration:**
- **Frames:** 1 (static)
- **Weapon ready:** Arms extended forward 2-3px
- **Legs:** Wide stance (feet 6px apart vs 4px neutral)
- **Body:** Lowered 1px (ready crouch)
- **Transition in:** 0.1s from any state

**Direction-specific details:**
- **North:** Back view, weapon silhouette visible over shoulder
- **East/West:** Profile, weapon extends toward screen-right (E) or screen-left (W)
- **South:** Front view, weapon centered between arms

---

### TECH INTERACTION

**Configuration:**
- **Frames:** 3
- **Duration:** 0.9s total (0.3s per frame)
- **Frame 1:** Arms rising to chest height
- **Frame 2:** Device active (2x2px cyan glow)
- **Frame 3:** Arms lowering

**Device glow positions:**
- **North:** Centered on upper back
- **East/West:** Offset 2px toward screen-edge (visible past silhouette)
- **South:** Centered on chest

---

## State Interrupt Hierarchy

**NEW IN v1.1**

### Priority 1 (Immediate): Combat Stance
- **Interrupts:** Walk, Idle, Tech Interaction
- **Transition:** Current frame → hold 0.05s → combat stance
- **Behavior:** Hard cut (no blending) for responsiveness
- **Example:** Player hits combat key during walk frame 2 → hold frame 2 for 0.05s → cut to combat stance

### Priority 2 (Frame Complete): Tech Interaction
- **Interrupts:** Idle
- **Blocks:** Walk (must cancel interaction first)
- **Transition:** Complete current frame → tech interaction frame 1
- **Behavior:** Waits for clean frame boundary
- **Example:** Player activates tech during idle → idle frame completes → tech begins

### Priority 3 (Natural): Idle
- **Never interrupts** other states
- **Triggered by:** No input after walk cycle completes
- **Transition:** Walk frame 4 → idle frame 1 (seamless)
- **Behavior:** Default fallback state

### Priority 4 (Natural): Walk
- **Never interrupts** other states
- **Triggered by:** Movement input during idle/tech
- **Transition:** Blend via first contact frame
- **Behavior:** Starts from frame 1 (contact) regardless of body position

---

## Direction Transitions

**NEW IN v1.1**

### East ↔ West Transitions (Gear Layer Critical)

**E→W Transition:**
```
1. Hold walk_E frame 4 for 0.1s
2. Swap to Layer 3 (Gear) for West direction
   ⚠️ CRITICAL: Use manually-flipped West gear sprites
   ⚠️ NOT runtime mirror of East gear
3. Begin walk_W frame 1
4. Total transition cost: 0.1s + 0.15s = 0.25s
```

**W→E Transition:**
```
1. Hold walk_W frame 4 for 0.1s
2. Swap to Layer 3 (Gear) for East direction
   ✓ East gear is canonical (base sprites)
3. Begin walk_E frame 1
4. Total transition cost: 0.25s
```

**Why manual flip?**
- Mirroring East→West swaps equipment sides
- Laptop case must stay left hip, sidearm must stay right thigh
- Pre-flipped West sprites maintain canonical loadout

### North ↔ South Transitions

**N→S or S→N Transition:**
```
1. Hold current direction frame 4 for 0.1s
2. Swap base body + gear simultaneously
3. No gear flip required (front/back views symmetrical)
4. Begin new direction frame 1
5. Total transition cost: 0.25s
```

---

## Layer Composition During Transitions

**NEW IN v1.1**

### Frame N (Old Direction)
```
Layer 1: Shadow (persistent, no change)
Layer 2: Body (old direction, frame 4)
Layer 3: Gear (old direction, canonical positions)
Layer 4: Detail (old direction)
```

### Hold Period (0.1s)
```
Layer 1: Shadow (persistent)
Layer 2-4: Freeze all layers from frame N
```

### Frame N+1 (New Direction)
```
Layer 1: Shadow (persistent)
Layer 2: Body (new direction, frame 1)
Layer 3: Gear (new direction, MANUALLY FLIPPED if West)
Layer 4: Detail (new direction)
```

**Rendering method:** Hard swap, no cross-fade. Maintains pixel crispness and prevents half-rendered frames.

---

## Rim Light Application

**Condition:** Dark floor tiles (industrial, earth-tone)

**Specification:**
- **Color:** #6B5D52 (lighter than base #4A4238)
- **Width:** 1 pixel
- **Placement:** Top-facing edges only
  - Shoulders (outer edge)
  - Head (top curve)
- **Do NOT apply to:** Bottom-facing surfaces (legs, underside of arms)

**Purpose:** Separates sprite from floor, suggests overhead light source.

---

## Visual Debugging Checklist

### Walk Cycle Validation
- [ ] **Grid Alignment Test:** Overlay tile grid during walk animation
  - Contact frames (1 & 3) show foot pixel on grid line
  - No sliding between tiles
  - Body lowering (1px) visible during contact

- [ ] **Timing Test:** Play full 0.6s cycle at intended game speed
  - Feels natural, not robotic
  - Weight transfer reads clearly
  - No "popping" between frames

- [ ] **Direction Consistency:** Walk all 4 directions
  - Silhouette changes appropriately per direction
  - Gear remains visible and recognizable
  - Shadow stays grounded (no rotation)

### Idle Validation
- [ ] **Breathing Natural:** Watch 3-5 full loops
  - Rhythm feels organic
  - 1px shift is noticeable but not jarring
  - If using 3-frame: middle frame smooths transition

- [ ] **Shadow Persistence:** Idle should NOT move shadow
  - Shadow stays at same ground position
  - Shadow opacity remains 40%

### Gear Layer Tests (NEW IN v1.1)
- [ ] **West Gear Flip Test:**
  - Walk E→W transition
  - Verify laptop case stays left hip
  - Verify sidearm stays right thigh
  - Check for 1-frame "swap flash" (indicates mirror not manually flipped)

- [ ] **Gear Visibility Test:** All 4 directions
  - Sidearm visible in E/S/W views
  - Laptop case visible in E/S/W views
  - Drone controller visible in N/E/S/W
  - No gear "clipping" through body pixels

### Layer Rendering Tests (NEW IN v1.1)
- [ ] **Shadow Persistence Test:**
  - Rotate through all 4 directions rapidly (N→E→S→W→N)
  - Shadow should NOT wobble or rotate
  - Shadow opacity stays 40% throughout
  - Shadow position remains anchored to ground plane

- [ ] **Rim Light Consistency Test:**
  - Test sprite on dark tile (industrial floor)
  - Rim light visible on N/E/S/W top-facing edges
  - Rim light NOT on bottom surfaces (legs, arm undersides)
  - 1px width maintained across all frames

### State Interrupt Tests (NEW IN v1.1)
- [ ] **Combat Interrupt Response:**
  - Walk cycle → press combat key mid-frame (try frame 2)
  - Should hard-cut to combat stance within 0.05s
  - Measured delay: current frame hold + combat frame 1 ≤ 0.2s total
  - No "slide finish" of walk cycle

- [ ] **Tech Interaction Blocking:**
  - Activate tech interaction during idle
  - Attempt walk input mid-interaction
  - Walk should be blocked until interaction completes or cancels
  - Cancel key should drop tech immediately

- [ ] **Idle Fallback:**
  - Complete walk cycle, release input
  - Should transition smoothly to idle frame 1
  - No frame "pop" or visible discontinuity

---

## Performance Optimization

**NEW IN v1.1**

### Sprite Sheet Layout
```
Row 1: Idle_N, Idle_E, Idle_S, Idle_W (2-3 frames each)
Row 2: Walk_N_1, Walk_N_2, Walk_N_3, Walk_N_4
Row 3: Walk_E_1, Walk_E_2, Walk_E_3, Walk_E_4
Row 4: Walk_S_1, Walk_S_2, Walk_S_3, Walk_S_4
Row 5: Walk_W_1, Walk_W_2, Walk_W_3, Walk_W_4 (MANUAL FLIP)
Row 6: Combat_N, Combat_E, Combat_S, Combat_W
Row 7: Tech_N_1-3, Tech_E_1-3, Tech_S_1-3, Tech_W_1-3
```

**Benefits:**
- Single texture atlas prevents texture swaps
- Sequential frames improve cache locality
- Directional grouping simplifies lookup logic

### Pre-calculation Requirements
- **West gear positions:** Calculated at asset build time
- **Stored as:** Separate sprites in atlas (Row 5)
- **NOT:** Runtime mirror + flip operation
- **Reason:** Prevents per-frame CPU cost

### Frame Timing Precision
- **Fixed timestep:** 0.05s or 0.1s for animation updates
- **Independent of:** Game logic tick (may be 0.016s @ 60fps)
- **Prevents:** Animation judder on variable frame timing
- **Implementation:** Accumulate delta time, step when threshold reached

---

## Implementation Priority

### Phase 1: Core (Before coding)
1. Implement **Idle** (2-frame) - simplest validation
2. Implement **Walk North** - test anti-slide math
3. Test grid alignment with visual overlay
4. If anti-slide fails, adjust contact frame foot positions

### Phase 2: Directions
1. Implement **Walk East** (canonical gear)
2. **Manually create Walk West** (flip gear positions)
3. Test E→W transition with gear flip validation
4. Implement Walk South
5. Test all N/E/S/W transitions

### Phase 3: States
1. Implement **Combat Stance** (all 4 directions)
2. Test state interrupt: Walk → Combat
3. Implement **Tech Interaction** (all 4 directions)
4. Test state interrupt: Idle → Tech → Walk (blocked)

### Phase 4: Polish
1. A/B test 2-frame vs 3-frame Idle
2. Test rim light on dark floors
3. Profile animation update cost (target: <1% CPU)
4. Run full visual debugging checklist
5. User playtest: "Does movement feel responsive?"

---

## Common Pitfalls

### 1. "Sliding" Walk Cycle
**Symptom:** Character appears to skate on ice  
**Cause:** Contact frames don't align foot pixels to grid  
**Fix:** Measure exact pixel position during contact frames, adjust body position to grid intersection

### 2. "Jittering" Idle
**Symptom:** Character vibrates instead of breathing  
**Cause:** 1px shift too fast (0.5s too short) or inconsistent frame timing  
**Fix:** Slow to 0.6s or add 3rd middle frame for smoother pulse

### 3. "Equipment Teleporting"
**Symptom:** Gear swaps sides during E→W transitions  
**Cause:** Using runtime mirror instead of pre-flipped West sprites  
**Fix:** Create manual West gear layer with canonical positions

### 4. "Floating Shadow"
**Symptom:** Shadow rotates or moves during animations  
**Cause:** Shadow on Layer 2+ instead of persistent Layer 1  
**Fix:** Render shadow on ground plane (tile layer), not sprite layer

### 5. "Muddy Silhouette"
**Symptom:** Character blends into dark floors  
**Cause:** Insufficient contrast between sprite and background  
**Fix:** Add 1px rim light on top-facing edges, brighten tech accents

---

## Credits & Version History

**v1.0 (Gemini):**
- Walk cycle pixel math
- Anti-slide mathematical proof  
- 3-frame idle specification
- Direction transition frame-hold
- Visual debugging checklist

**v1.1 (Claude integration patches):**
- Gear layer transition behavior
- State interrupt hierarchy
- Layer composition during transitions
- Extended debugging (layer-specific)
- Performance optimization notes
- Implementation phasing

---

**Status:** Production-ready for Cipher base implementation  
**Next Review:** After Phase 2 completion (all 4 walk directions working)