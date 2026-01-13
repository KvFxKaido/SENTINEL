# Layout Engine Architecture
*Translating Yoga/flexbox patterns to Textual for SENTINEL TUI*

---

## Executive Summary

**Good news: We don't need Yoga.** Textual already has a constraint-based layout system with:
- `fr` units (like `flex-grow`)
- `min-width` / `max-width` constraints
- `vw` / `vh` viewport-relative units
- Automatic recalculation on terminal resize

**The problem:** SENTINEL isn't using these capabilities. The side docks use fixed `width: 26` instead of responsive constraints.

---

## Current State Analysis

### What SENTINEL Does Now

```css
/* Current: Fixed widths that don't respond to terminal size */
#self-dock {
    width: 26;           /* Fixed 26 chars - PROBLEM */
    height: 100%;
}

#center-column {
    width: 1fr;          /* Flex-grow - GOOD */
    align: center top;
}

#console-wrapper {
    width: 90%;
    max-width: 120;      /* Constraint - GOOD */
}

#world-dock {
    width: 26;           /* Fixed 26 chars - PROBLEM */
    height: 100%;
}
```

### The Layout Structure

```
+---------------------------------------------------------------------+
| HeaderBar (height: 2)                                               |
+---------------------------------------------------------------------+
| ContextBar (height: 1)                                              |
+------------+----------------------------------------+---------------+
| SELF Dock  |         Center Column                 | WORLD Dock    |
| (26 chars) |   +------------------------------+    | (26 chars)    |
|   FIXED    |   |  Console (90%, max 120)      |    |   FIXED       |
|            |   |     - Output Log (1fr)       |    |               |
|            |   |     - Choices (auto)         |    |               |
|            |   |     - Input (3)              |    |               |
|            |   +------------------------------+    |               |
+------------+----------------------------------------+---------------+
| BottomDock (height: 1)                                              |
+---------------------------------------------------------------------+
```

### Problems with Fixed Widths

| Terminal Width | Left Dock | Center | Right Dock | Issue |
|----------------|-----------|--------|------------|-------|
| 120 chars      | 26        | 68     | 26         | OK    |
| 100 chars      | 26        | 48     | 26         | Center cramped |
| 80 chars       | 26        | 28     | 26         | Center too narrow |
| 60 chars       | 26        | 8      | 26         | Unusable |

The center column gets squeezed because docks don't adapt.

---

## What Yoga Does (The Pattern)

OpenCode uses Facebook's Yoga layout engine with this mental model:

```typescript
// Yoga constraint declaration (conceptual)
leftPanel: {
    flex: 0,              // Don't grow
    width: "20%",         // Proportion of parent
    minWidth: 24,         // Floor constraint
    maxWidth: 35,         // Ceiling constraint
}

centerPanel: {
    flex: 1,              // Grow to fill remaining space
    maxWidth: 120,        // But never exceed 120
}

rightPanel: {
    flex: 0,              // Don't grow
    width: "20%",         // Proportion of parent
    minWidth: 24,
    maxWidth: 35,
}
```

**Key insight:** Panels declare *constraints*, not sizes. The engine solves for actual sizes.

### How Yoga Handles Resize

1. Terminal reports new size
2. Yoga recalculates all constraints simultaneously
3. Each panel gets computed size respecting min/max bounds
4. Render with new sizes

```
Terminal 120 chars:
  Left:   20% = 24 (within 24-35 bounds)
  Right:  20% = 24 (within 24-35 bounds)
  Center: remaining 72 (within max 120)

Terminal 80 chars:
  Left:   20% = 16 -> 24 (floor hit)
  Right:  20% = 16 -> 24 (floor hit)
  Center: remaining 32

Terminal 60 chars:
  Left:   24 (can't go lower)
  Right:  24 (can't go lower)
  Center: 12 (cramped, but docks protected)
  -> Consider: hide docks below threshold
```

---

## Textual's Equivalent Capabilities

### Units Available

| Unit | Meaning | Use Case |
|------|---------|----------|
| `26` | Fixed cells | Current dock width (bad) |
| `1fr` | Flex fraction | Center column (good) |
| `25%` | % of parent | Relative sizing |
| `25vw` | % of viewport | Responsive to terminal |
| `25w` | % of available | After docked elements |

### Constraint Properties

```css
/* Textual supports all of these */
min-width: 24;       /* Floor in cells */
max-width: 35;       /* Ceiling in cells */
min-width: 20vw;     /* Floor as viewport % */
max-width: 30vw;     /* Ceiling as viewport % */
```

### Key Insight: `vw` vs `%`

- `%` = percentage of *parent container*
- `vw` = percentage of *viewport* (terminal width minus docked widgets)

For SENTINEL's three-column layout, `vw` is what we want for the docks.

---

## Recommended Layout Constraints

### Panel Specifications

| Panel | Proportion | Min | Max | Behavior |
|-------|------------|-----|-----|----------|
| **Self Dock** | 20vw | 24 chars | 32 chars | Character stats, social energy |
| **Center** | 1fr | 40 chars | 120 chars | Narrative, input, choices |
| **World Dock** | 20vw | 24 chars | 32 chars | Factions, NPCs, threads |

### Behavior at Different Sizes

```
Wide Terminal (140+ chars):
  +--------+---------------------------+--------+
  |  28    |          84               |   28   |
  | (20vw) |       (capped)            | (20vw) |
  +--------+---------------------------+--------+
  Docks at proportional size, center capped at 120

Standard Terminal (100-140 chars):
  +------+-------------------------+------+
  |  24  |          72             |  24  |
  | (min)|        (flex)           | (min)|
  +------+-------------------------+------+
  Docks at minimum, center gets remaining space

Narrow Terminal (80-100 chars):
  +----+-------------------+----+
  | 24 |        32         | 24 |
  +----+-------------------+----+
  Docks protected, center compressed

Very Narrow (<80 chars):
  Hide docks entirely, center fills screen
```

---

## Recommended CSS Changes

### Current (Fixed)

```css
#self-dock {
    width: 26;
    height: 100%;
}

#world-dock {
    width: 26;
    height: 100%;
}
```

### Proposed (Responsive)

```css
#self-dock {
    width: 20vw;         /* 20% of viewport */
    min-width: 24;       /* Never narrower than 24 chars */
    max-width: 32;       /* Never wider than 32 chars */
    height: 100%;
}

#self-dock.hidden {
    display: none;
}

#world-dock {
    width: 20vw;
    min-width: 24;
    max-width: 32;
    height: 100%;
}

#world-dock.hidden {
    display: none;
}

#center-column {
    width: 1fr;          /* Take remaining space */
    min-width: 40;       /* Ensure usable minimum */
    height: 100%;
    align: center top;
}

#console-wrapper {
    width: 100%;         /* Fill center column */
    max-width: 120;      /* Cap narrative width */
    height: 100%;
}
```

### Auto-Hide on Narrow Terminals

Add responsive behavior to hide docks when terminal is too narrow:

```python
# In SentinelTUI class
def on_resize(self, event) -> None:
    """Handle terminal resize - auto-hide docks on narrow terminals."""
    width = event.size.width

    # Below 80 chars: hide both docks automatically
    if width < 80:
        self.query_one("#self-dock").add_class("hidden")
        self.query_one("#world-dock").add_class("hidden")
    else:
        # Restore based on user preference
        if self.show_self_dock:
            self.query_one("#self-dock").remove_class("hidden")
        if self.show_world_dock:
            self.query_one("#world-dock").remove_class("hidden")
```

---

## Implementation Strategy

### Phase 1: CSS-Only Changes (Low Risk)

1. Update dock CSS to use `vw` units with `min-width`/`max-width`
2. Test at various terminal sizes
3. Verify existing hide/show behavior still works

```css
/* Minimal change - just update the constraint */
#self-dock {
    width: 20vw;
    min-width: 24;
    max-width: 32;
}
```

### Phase 2: Auto-Hide Behavior

1. Add `on_resize` handler
2. Track user preference vs auto-hide state
3. Add status indicator when docks are auto-hidden

### Phase 3: Graceful Degradation

For very narrow terminals (<60 chars):
- Single-column mode
- Docks become overlay panels (slide in on `[` / `]`)
- Or tab-based switching between views

---

## Comparison: Yoga vs Textual

| Feature | Yoga (OpenCode) | Textual (SENTINEL) |
|---------|-----------------|-------------------|
| Flex-grow | `setFlexGrow(1)` | `width: 1fr` |
| Fixed size | `setWidth(26)` | `width: 26` |
| Percentage | `setWidth("25%")` | `width: 25%` or `25vw` |
| Min constraint | `setMinWidth(24)` | `min-width: 24` |
| Max constraint | `setMaxWidth(32)` | `max-width: 32` |
| Auto resize | Yoga recalculates | Textual recalculates CSS |
| Hierarchy | Node tree | Widget tree |

**Conclusion:** Textual provides equivalent constraint-solving capabilities. No need to implement Yoga - just use Textual's existing features correctly.

---

## Trade-offs

### Why Not Just Use Fixed Widths?

**Pros of fixed:**
- Simple, predictable
- Works fine on standard terminals (100-120 chars)

**Cons of fixed:**
- Breaks on narrow terminals
- Wastes space on wide terminals
- Poor experience on non-standard setups

### Why Constraints Are Better

**Pros:**
- Adapts to any terminal size
- Maintains usability at extremes
- Future-proof for different displays

**Cons:**
- Slightly more complex CSS
- Need to test at various sizes
- May need resize handler for edge cases

---

## Testing Checklist

After implementing responsive layout:

- [ ] 140+ char terminal: docks at max-width, center capped
- [ ] 120 char terminal: balanced layout
- [ ] 100 char terminal: docks at min, center reasonable
- [ ] 80 char terminal: docks at min, center usable
- [ ] 60 char terminal: docks hidden, center fills
- [ ] Dock toggle (`[` / `]`) still works
- [ ] Content remains readable at all sizes
- [ ] No horizontal scrolling introduced

---

## Summary

| Current | Recommended |
|---------|-------------|
| `width: 26` | `width: 20vw; min-width: 24; max-width: 32` |
| Fixed sizing | Constraint-based |
| Breaks on narrow | Adapts gracefully |
| Manual hide only | Auto-hide on narrow + manual toggle |

**No new dependencies required.** Textual already has everything we need - we just need to use it.

---

*Generated: January 12, 2026*
*Based on: OpenCode Yoga patterns + Textual documentation*
