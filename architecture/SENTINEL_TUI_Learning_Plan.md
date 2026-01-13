# SENTINEL TUI Learning Plan
*Understanding OpenCode patterns to improve SENTINEL's terminal interface*

---

## Current State Assessment

### What SENTINEL Does Well
- ✅ **Three-column layout** - Character/narrative/factions cleanly separated
- ✅ **Themed aesthetic** - "If it looks calm, it's lying" is working
- ✅ **Information density** - Tactical HUD vibe is correct
- ✅ **Block system** - NARRATIVE/CHOICE/INTEL/SYSTEM separation
- ✅ **Rich integration** - Panels, markdown, tables all working
- ✅ **Glitch banner** - Hexagon reveal sets the mood perfectly
- ✅ **Command registry** - Unified CLI/TUI command handling *(NEW)*
- ✅ **Responsive layout** - Docks adapt to terminal width *(NEW)*

### Where Learning Would Help
- 🔄 **Reactive updates** - Status bar changes don't animate
- 🔄 **Command palette** - Works but could be snappier
- 🔄 **State management** - Manual tracking vs reactive patterns
- ~~🔄 **Layout engine** - Manual calculations vs flexible system~~ ✅ DONE
- 🔄 **Event handling** - Direct polling vs event-driven

---

## Learning Objectives

### 1. Reactive State Management
**Pattern to Learn:** How OpenCode uses SolidJS signals in terminal context

**Why It Matters:**
- Faction standing changes could animate smoothly
- Status bar could update without full redraws
- Context meter could pulse when strain increases
- Social energy bar could drain visually

**SENTINEL Application:**
```python
# Current: Manual status bar rebuild
status_bar(campaign, show_bar=True)

# With reactive patterns:
# Status components subscribe to state changes
# Only affected sections redraw
```

**Learning Path:**
1. Read OpenCode's `sync.tsx` - how they manage reactive stores
2. Understand SolidJS `createSignal` pattern (not to use SolidJS, but to understand the concept)
3. Map to Python equivalents (observers, property watchers, event emitters)
4. Direct Code to implement reactive status components

**Outcome:** You can say "Make the faction bar reactive" and Code knows you mean: "Subscribe to faction standing changes, redraw only that component"

---

### 2. Layout Engine Architecture
**Pattern to Learn:** Yoga layout system vs manual panel sizing

**Why It Matters:**
- Automatic responsive sizing when terminal resizes
- Cleaner separation of content from layout
- Easier to add/remove panels without breaking layout

**SENTINEL Application:**
```python
# Current: Fixed-width panels
Panel(content, width=40)

# With layout engine:
# Panels define constraints, engine calculates sizes
# Character panel: 25% width, min 30 chars
# Narrative: flex-grow, center
# Factions: 25% width, max 50 chars
```

**Learning Path:**
1. Understand Yoga's flexbox model
2. See how OpenCode wraps it for terminal use
3. Research Python alternatives (not necessarily Yoga itself)
4. Direct Code: "Implement flexible layout system for SENTINEL panels"

**Outcome:** Terminal resizing doesn't break your UI, panels reflow naturally

---

### 3. Command System Architecture
**Pattern to Learn:** OpenCode's CommandProvider registry pattern

**Why It Matters:**
- Context-aware commands (hide `/debrief` when no session)
- Command palette with fuzzy search
- Slash commands that autocomplete
- Keybinds that don't conflict with terminal

**SENTINEL Current State:**
```python
# Hardcoded command dict
COMMAND_META = {"/new": "Create campaign", ...}
# Simple completer
# No context filtering
```

**OpenCode Pattern:**
```typescript
// Commands register themselves with context
register(() => [
  {
    id: "session.new",
    category: "Campaign",
    label: "New Campaign",
    when: () => !hasActiveCampaign(),
    onSelect: () => createCampaign(),
  }
])
```

**SENTINEL Application:**
- Commands self-register with categories
- Context predicates hide irrelevant commands
- Fuzzy search works across categories
- Keybinds integrate cleanly

**Learning Path:**
1. Read OpenCode's `dialog-command.tsx` and `keybind.tsx`
2. Understand registry pattern vs dict lookup
3. Map to Python command pattern
4. Direct Code: "Refactor command system to use registry pattern with context predicates"

**Outcome:** You can add commands that automatically show/hide based on game state

---

### 4. Event-Driven Architecture
**Pattern to Learn:** OpenCode's message passing vs direct function calls

**Why It Matters:**
- Decoupled components (renderer doesn't know about state)
- Easier testing (mock events, not whole systems)
- Async operations don't block UI
- Multiple components can react to same event

**SENTINEL Current State:**
```python
# Direct calls
show_status(campaign)
render_narrative_block(text)
# Everything synchronous, tightly coupled
```

**Event-Driven Pattern:**
```python
# Components subscribe to events
event_bus.on("faction_changed", update_faction_panel)
event_bus.on("faction_changed", log_to_wiki)
event_bus.on("faction_changed", trigger_cascade)

# Actions emit events
event_bus.emit("faction_changed", {
    faction: "nexus",
    from: "neutral",
    to: "friendly",
})
```

**Learning Path:**
1. Read OpenCode's Update() method message routing
2. Understand Bubble Tea's message passing
3. Research Python event bus patterns (pypubsub, asyncio events)
4. Direct Code: "Add event bus for state changes in SENTINEL"

**Outcome:** You can say "When faction changes, update three things" and Code wires it through events

---

### 5. Theme System Architecture
**Pattern to Learn:** OpenCode's terminal color detection + theme generation

**Why It Matters:**
- Respects user's terminal theme (dark/light auto-detect)
- Generates complementary colors programmatically
- Consistent syntax highlighting
- Easy theme switching

**SENTINEL Current State:**
```python
# Hardcoded colors
THEME = {
    "primary": "steel_blue",
    "secondary": "grey70",
    ...
}
```

**OpenCode Pattern:**
- OSC queries to detect terminal background
- Generate theme palette from base colors
- Syntax highlighting derived from theme
- User can override with JSON themes

**SENTINEL Application:**
- Detect if user has dark/light terminal
- Adjust SENTINEL's theme accordingly
- Faction colors still distinct, but contrast-adjusted
- User can provide custom theme JSON

**Learning Path:**
1. Read OpenCode's theme.tsx OSC query logic
2. Understand color generation algorithms
3. Research terminal color detection in Python
4. Direct Code: "Add terminal theme detection to SENTINEL"

**Outcome:** SENTINEL looks good in any terminal, respects user preferences

---

## Implementation Priorities

### Phase 1: Quick Wins (1-2 weeks)
**Focus:** Understand patterns without major refactors

1. ✅ **Command Registry Pattern** — *COMPLETED*
   - ~~Refactor COMMAND_META to registry~~
   - ~~Add context predicates~~
   - ~~Improve fuzzy search~~
   - *Learned: registry pattern, context predicates*
   - *Result: Removed ~1400 lines of legacy code, unified CLI/TUI commands*

2. **Terminal Color Detection**
   - Detect dark/light mode
   - Adjust theme contrast
   - *Learn: OSC queries, color math*

### Phase 2: Core Improvements (2-4 weeks)
**Focus:** Architecture changes that enable better UX

3. ✅ **Event Bus** — *COMPLETED*
   - ~~Add pypubsub or custom event system~~
   - ~~Migrate faction changes to events~~
   - ~~Decouple renderer from state~~
   - *Learned: Custom event bus (80 lines) beats external deps for our needs*
   - *Result: Manager emits events → TUI handlers update panels reactively*
   - *See: src/state/event_bus.py*

4. **Reactive Status Components**
   - Make status bar event-driven
   - Animate faction standing changes
   - Update context meter reactively
   - *Learn: observer pattern, partial redraws*

### Phase 3: Polish (4-6 weeks)
**Focus:** Nice-to-haves that improve feel

5. ✅ **Layout Engine** — *COMPLETED*
   - ~~Research Python flexbox alternatives~~
   - ~~Implement responsive panel sizing~~
   - ~~Handle terminal resize gracefully~~
   - *Learned: Textual already has Yoga-equivalent (vw units, min/max constraints)*
   - *Result: Docks use 20vw with 24-32 char bounds, auto-hide < 80 chars*
   - *See: Layout_Engine_Architecture.md*

6. **Advanced Theming**
   - User-customizable themes
   - Per-faction color schemes
   - Syntax highlighting for lore
   - *Learn: theme systems, color theory*

---

## How to Use This Plan

### For Each Pattern:

1. **Read OpenCode Source**
   - Use DeepWiki or GitHub to find relevant files
   - Focus on *why* they did it that way, not *how* in TypeScript

2. **Ask Code to Explain**
   - "Show me OpenCode's command registry pattern"
   - "Explain how their theme detection works"
   - Code can translate TypeScript concepts to Python equivalents

3. **Map to SENTINEL**
   - Where would this pattern help?
   - What would change in current architecture?
   - What's the migration path?

4. **Direct Code to Implement**
   - "Add event bus using pypubsub"
   - "Refactor status bar to be reactive"
   - "Implement terminal color detection"

### Learning Mode Settings:

In Claude Code:
```
/config
→ Learning Mode: ON
→ Explanation Detail: Medium
→ Show Alternatives: Yes
```

When Code makes changes, it'll explain:
- Why this pattern over alternatives
- What trade-offs exist
- How it connects to other systems

---

## Success Metrics

**You'll know learning mode is working when:**

✅ You can direct Code using pattern names
- "Use observer pattern for faction changes"
- "Make this component reactive"
- "Add this to the event bus"

✅ You understand architecture decisions
- Why event bus vs direct calls
- When to use reactive vs static
- Layout engine trade-offs

✅ You can debug at pattern level
- "The event isn't propagating" vs "it's broken"
- "Status bar isn't subscribing" vs "it doesn't update"
- "Layout constraints conflict" vs "panels overlap"

✅ You maintain SENTINEL's aesthetic
- Patterns improve UX without losing tactical vibe
- Additions feel intentional, not bolted on
- Code quality improves without feature creep

---

## Anti-Patterns to Avoid

### ❌ Don't Reimplement @opentui
OpenCode built a whole framework. You don't need that.
You need specific patterns that solve SENTINEL problems.

### ❌ Don't Abandon Rich
Rich works great for your aesthetic.
Learn patterns, apply them to Rich components.

### ❌ Don't Over-Engineer
"Reactive" doesn't mean SolidJS in Python.
It means "update only what changed."
Simple event bus > complex reactive framework.

### ❌ Don't Lose Your Voice
OpenCode is polished productivity tool.
SENTINEL is gritty tactical terminal.
Learn their patterns, keep your aesthetic.

---

## Resources

### OpenCode Source
- **TUI System:** `packages/opencode/src/cli/cmd/tui/`
- **Commands:** `component/dialog-command.tsx`, `context/keybind.tsx`
- **Theme:** `context/theme.tsx`
- **State:** `context/sync.tsx`

### Python Equivalents
- **Event Bus:** `pypubsub`, `asyncio.Event`
- **Reactive:** Property watchers, descriptors
- **Layout:** Textual's layout system (for reference)
- **Terminal:** Rich, prompt_toolkit (already using)

### Learning Tools
- **DeepWiki:** Search OpenCode codebase with semantic queries
- **Code Explain Mode:** Ask Code to break down OpenCode patterns
- **SENTINEL Debug:** Add logging to see where patterns help

---

## Next Steps

1. **Turn on Learning Mode in Claude Code**
2. **Pick Phase 1 objective** (command registry or theme detection)
3. **Read relevant OpenCode source**
4. **Ask Code to explain the pattern**
5. **Direct Code to implement in SENTINEL**
6. **Test and iterate**

Remember: You're not learning to code. You're learning to direct better by understanding the patterns Code will use to implement your vision.

---

*Generated: January 12, 2026*
*Updated: January 12, 2026*
*SENTINEL Version: Post-event-bus*
*Progress: 3/6 objectives complete (Command Registry, Layout Engine, Event Bus)*
