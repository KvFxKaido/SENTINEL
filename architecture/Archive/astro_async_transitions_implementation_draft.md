# Goal
Give async game processing visible, intentional *temporal weight* using Astro-native page transitions and light ambient motion — without lying about progress or turning the UI into a spinner factory.

This plan assumes:
- Astro is the routing spine
- Pages represent *states* (not continuous runtime)
- Async resolution happens between navigations
- Motion communicates continuity, not speed

---

# Design Principles (Non‑Negotiable)

1. **Animate continuity, not progress**  
   Never show percentages, spinners, or fake timers.

2. **The world is thinking, not loading**  
   Motion should feel like attention, tension, or memory shifting.

3. **Files remain the source of truth**  
   Animations decorate navigation; they never rewrite logic.

4. **Transitions are expressive but finite**  
   Motion duration roughly matches typical backend latency, but does not wait on it.

---

# Phase 1 – Baseline Page Transitions (Low Risk)

### Objective
Introduce page-to-page continuity so navigation no longer feels like a hard cut.

### Steps
1. Enable Astro View Transitions
   - Turn on the View Transitions integration
   - Verify basic fade works between routes

2. Identify persistent layout elements
   - Header
   - Side panels (SELF / WORLD)
   - Background frame

3. Mark shared elements
   - Use view-transition-name on elements that should persist
   - Keep this conservative at first

### Outcome
Navigation feels *intentional* instead of abrupt. No gameplay semantics yet.

---

# Phase 2 – Async Action → Transition Ritual

### Objective
Bind player actions to immediate visual response while async work happens off-screen.

### Pattern
**Action → Transition → Resolve → Land**

### Steps
1. On choice submit:
   - Immediately trigger navigation
   - Do not wait for backend resolution in the UI

2. During transition:
   - Preserve key UI anchors (panels, frame)
   - Let content area clear or dissolve

3. On landing page:
   - Page already reflects resolved state
   - No post-load animation except subtle settle

### Notes
- Backend latency is absorbed *inside* the transition window
- Worst case: player lands slightly before resolution and sees a static holding state

---

# Phase 3 – Ambient Motion During Async Windows

### Objective
Fill perceived dead time without implying progress.

### Allowed Motions
- Slow background drift
- UI "breathing" (opacity, glow, scanlines)
- Subtle panel parallax
- Idle animations tied to faction / mood

### Implementation
- CSS-only where possible
- Client islands only for motion, not logic
- Animations loop calmly and endlessly

### Explicitly Avoid
- Spinners
- Loading bars
- Text like "Processing…" or "Thinking…"

---

# Phase 4 – Transition Styles by Action Type

### Objective
Let *meaning* determine motion character.

### Mapping Examples
- Strategic choice → slow slide / crossfade
- Combat resolution → snap + recoil
- Narrative reveal → dissolve / mask
- Uncertain outcome → delayed settle, micro-jitter

### Implementation
- Pass action type via route params or state
- Conditionally apply transition CSS
- Keep palette and easing consistent

---

# Phase 5 – Optional Dev Tooling (Later)

### Visual Debug Overlay (Dev Only)
- Toggle to label:
  - transition start
  - backend resolve
  - page land

Purpose: tune timing without guessing.

---

# Non‑Goals (Explicitly Out of Scope)

- Real-time streaming UI
- Progress indicators
- SPA-style global runtime
- Automatic animation generation
- CMS-style visual editors

---

# Success Criteria

You know this worked if:
- Async moments feel *deliberate*, not stalled
- Players stop asking "is it loading?"
- Motion reinforces tone instead of distracting
- You can remove all animations and the game still functions

---

# Final Note

This system should feel like a *breath between thoughts*.  
If it ever feels like a performance, it’s doing too much.

