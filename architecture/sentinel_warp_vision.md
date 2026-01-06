# SENTINEL Terminal Polish Roadmap
**Warp-Inspired Evolution: Confident, Beautiful, Unapologetically Terminal**

---

## Core Philosophy

> "SENTINEL is a terminal game. That's not a compromise, that's the medium."

**Warp's lesson:** Terminals can be powerful AND delightful. Text-first doesn't mean bare-bones.

**SENTINEL's application:** A tactical TTRPG deserves terminal UI that matches its thematic weight - cold twilight blue, clinical precision, information as atmosphere.

---

## Current State (v1.0) ✓

**What's Working:**
- Rich terminal UI with theming
- Animated hexagon banner with glitch reveal
- Command autocomplete with descriptions
- Colored panels for different content types
- Choice system with visual blocks
- Context meter for conversation depth
- Faction-specific linguistic corruption

**What Could Be Better:**
- Output is linear scroll (hard to reference earlier context)
- Commands are functional but not discoverable
- State changes aren't always visually clear
- History/search is terminal-default (limited)
- No visual distinction between routine and high-stakes moments

---

## Phase 1: Polish Pass (Terminal-Native Improvements)

**Goal:** Warp-level UX without leaving the terminal

### 1.1 Block-Based Output
**Inspiration:** Warp's command blocks make output scannable

**For SENTINEL:**
- GM responses become discrete blocks
- Each block has: timestamp, type indicator (narrative/choice/intel), quick actions
- Blocks are collapsible for long sessions
- Visual separators between conversation "beats"

**Example:**
```
╭──────────────────────── [14:32] NARRATIVE ─────────────────────────╮
│ The guard shifts uncomfortably. You notice his hand drifting        │
│ toward his sidearm - not threatening, just... uncertain.            │
│                                                                      │
│ "Look," he says quietly. "I don't care what Nexus says. My daughter │
│ needs those medical supplies. If you can get them through..."       │
╰──────────────────────────────────────────────────────────────── [▼]─╯

╭──────────────────────── [14:32] CHOICE ────────────────────────────╮
│ 1. Offer to help - no strings attached                              │
│ 2. Negotiate terms first                                            │
│ 3. Report him to Nexus                                              │
│ 4. Something else...                                                │
╰──────────────────────────────────────────────────────────────── [▼]─╯
```

**Technical:** 
- Rich already supports this with `Panel` and `Group`
- Add metadata to each GM response
- Implement block collapse/expand with keybinds

---

### 1.2 Command Palette Enhancement
**Inspiration:** Warp's command palette is discoverable AND fast

**For SENTINEL:**
- `/` opens enhanced command palette with:
  - Category grouping (Character, Mission, Meta, Social)
  - Context-aware suggestions (only show `/debrief` when mission active)
  - Recent commands at top
  - Keybind hints
- Fuzzy search built-in
- Visual preview of what command will do

**Example:**
```
┌─────────────── Command Palette ───────────────┐
│ > /con                                         │
├────────────────────────────────────────────────┤
│ SOCIAL                                         │
│ • /consult <question>  - Ask faction advisors  │
│                          [Ctrl+K]              │
├────────────────────────────────────────────────┤
│ META                                           │
│ • /config              - Update settings       │
│                          [Ctrl+,]              │
└────────────────────────────────────────────────┘
```

**Technical:**
- Extend current autocomplete with rich display
- Add command categorization metadata
- Implement preview pane

---

### 1.3 State Visualization
**Inspiration:** Clear, always-available context without cluttering

**For SENTINEL:**
- Persistent mini-status bar (optional, toggle-able)
- State changes get visual feedback (faction standing shift, social energy drain)
- Inline indicators for important context

**Example:**
```
┌─────────────────────────────────────────────────────────────────┐
│ CIPHER | Mission: Ghost Protocol | Pistachios: 68% | Session: 2h │
└─────────────────────────────────────────────────────────────────┘

[GM describes something that drains social energy]

┌──────────────────────────────────────────────────────────────────┐
│ CIPHER | Mission: Ghost Protocol | Pistachios: 68% → 53% ↓ | ... │
└──────────────────────────────────────────────────────────────────┘
```

**Technical:**
- Live updating header with `rich.live`
- Animate transitions for state changes
- Color coding for thresholds

---

### 1.4 Session History & Search
**Inspiration:** Warp's searchable history is a game-changer

**For SENTINEL:**
- `/history` - full session timeline with filtering
- `/search <term>` - find moments across current campaign
- Jump to specific blocks
- Tag important moments

**Example:**
```
╭────────── Session History ──────────╮
│ [Session 1: First Deployment]       │
│ • Hinges (2)                         │
│ • Faction Events (5)                 │
│ • NPCs Met (3)                       │
│                                      │
│ [Session 2: Ghost Protocol]          │
│ • Current                            │
├──────────────────────────────────────┤
│ Search: "Ghost"                      │
│ → "Ghost Networks contacted..."      │
│ → "Ghost Protocol mission briefing" │
│ → Current mission                    │
╰──────────────────────────────────────╯
```

**Technical:**
- Campaign JSON already tracks everything
- Build search indexing over session data
- Implement jump-to-block navigation

---

### 1.5 NPC Visual Identity (MGS Codec Style)
**Inspiration:** Metal Gear Solid codec calls - character portraits during dialogue

**Goal:** Visual distinction for NPCs without breaking terminal flow

**Phase 1 Approach (Terminal-Native):**
Enhanced faction glyphs + styled frames as placeholders

**Example:**
```
╔═══════════════════════════════════════╗
║  ◈  DR. HELENA VOSS                   ║
║  [NEXUS - ANALYST]                    ║
║  [Disposition: Neutral]               ║
║                                       ║
║  "The probability matrix favors       ║
║   acceptance. Resources gained        ║
║   outweigh projected obligation       ║
║   costs by 2.3x."                     ║
╚═══════════════════════════════════════╝
```

**Phase 2 Approach (Terminal with Image Support):**
Kitty Graphics Protocol or Sixel for actual portraits

**Example:**
```
╔═══════════════════════════════════════╗
║  ┌────────┐                           ║
║  │ [IMG]  │  DR. HELENA VOSS          ║
║  │ PORT   │  [NEXUS - ANALYST]        ║
║  │RAIT   │  [Disposition: Neutral]   ║
║  └────────┘                           ║
║                                       ║
║  "The probability matrix favors       ║
║   acceptance. Resources gained..."    ║
╚═══════════════════════════════════════╝
```

**Phase 3 Approach (Desktop App):**
Full image support with player customization

**Portrait System Architecture:**
```
portraits/
├── player/              # Player's character
├── faction_npcs/        # Generic NPC portraits by faction
│   ├── nexus/          # Clinical, data-driven aesthetic
│   ├── ember/          # Warm, community-focused
│   ├── covenant/       # Formal, traditional
│   └── ghost/          # Glitchy, ephemeral
└── named_npcs/         # Specific important NPCs
```

**Player Customization Options:**
1. Generate with local Stable Diffusion (ComfyUI integration)
2. Choose from curated library (20-30 base portraits)
3. Upload custom PNG/JPG
4. Use enhanced faction glyphs (always available fallback)

**Faction-Specific Styling:**
- **Nexus:** Clean lines, blue-tinted, data overlays
- **Ember:** Warm colors, softer edges, human-focused
- **Covenant:** Formal framing, traditional composition
- **Ghost Networks:** Scan lines, glitch effects, partial transparency
- **Lattice:** Technical augmentation visible, enhanced features
- **Steel Syndicate:** Industrial, utilitarian, worn textures

**Portrait as State Machine:**

Treat portraits as emotional state, not decoration. The AI already tracks disposition, leverage, `lie_to_self`, and social energy — pipe those directly into the portrait renderer.

```typescript
type NPCVisualState =
  | "neutral"
  | "guarded"
  | "hostile"
  | "fractured"    // under pressure, conflicted
  | "lying"        // triggered by lie_to_self
  | "disconnecting"; // ending conversation, withdrawing
```

**Rule of thumb:** If the AI knows something emotionally, the UI should *leak* it visually.

**Portrait Data Schema:**

```python
{
  "npc_id": "cipher",
  "portrait": "data/portraits/cipher_base.png",
  "emotions": {
    "neutral": "cipher_neutral.png",
    "tense": "cipher_tense.png",
    "surprised": "cipher_surprise.png"
  },
  "faction_overlay": "nexus_frame.png",  # Faction-colored border
  "disposition_indicator": "green",       # Color based on relationship
  "speaking": true,
  "active_effects": ["static", "low_battery"]  # For Ghost Network NPCs
}
```

**Practical Portrait Tips:**

- **Aspect-ratio lock:** Keep portraits 4:3 or 3:4 so you can hot-swap art without re-layout
- **Two-state system:** Store `neutral` + `shift` (micro-expression) per NPC. Toggle shift layer for 200ms when text contains trigger words from their agenda (`lie_to_self`, `fears`, etc.). Instant personality without new art.
- **Cheap cohesion:** Generate base face, then grayscale + color-overlay for faction tint. Minimal art, maximum consistency.
- **"Lie to Self" indicator:** Barely visible double-exposure effect — two slightly offset copies of the portrait at 50% opacity

**CSS Filter Approach (MVP):**

You don't need live animation. 3-5 portrait variants + CSS filters = high impact, low effort.

```css
/* Base portrait */
.npc-portrait {
  filter: none;
  transition: filter 200ms ease;
}

/* Lying - subtle wrongness */
[data-state="lying"] .npc-portrait {
  filter: hue-rotate(12deg) contrast(1.1);
  animation: micro-jitter 120ms steps(2) infinite;
}

/* Hostile - desaturated, harsh */
[data-state="hostile"] .npc-portrait {
  filter: saturate(0.6) contrast(1.2);
}

/* Fractured - glitch effect */
[data-state="fractured"] .npc-portrait {
  filter: hue-rotate(-5deg);
  animation: glitch-slice 80ms steps(1) infinite;
}

/* Disconnecting - fading out */
[data-state="disconnecting"] .npc-portrait {
  filter: grayscale(0.8) opacity(0.7);
}

@keyframes micro-jitter {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(1px, -1px); }
}
```

**Technical Implementation:**

**Terminal (Kitty Protocol):**
```python
from kitty.graphics import display_image

def show_npc_dialogue(npc_name, faction, disposition, text, portrait_path=None):
    if portrait_path and kitty_available():
        display_image(portrait_path, position=(2, 2), size=(80, 80))
    # Fall back to glyph if no portrait or not in Kitty
    else:
        display_faction_glyph(faction)
```

**Desktop App (Image Element):**
```javascript
// In Tauri web view
<div class="codec-box">
  <img src={portraitPath} class="npc-portrait" />
  <div class="npc-info">
    <h3>{npcName}</h3>
    <span class="faction">{faction}</span>
    <span class="disposition">{disposition}</span>
  </div>
  <p class="dialogue">{text}</p>
</div>
```

**Portrait Generation Pipeline (Optional):**
1. Install ComfyUI or Automatic1111 locally
2. Fine-tune model on SENTINEL aesthetic (cold twilight blue, clinical precision)
3. Create faction-specific LoRAs
4. In-game `/portrait generate` command
5. Player inputs: faction, role, description
6. System generates + saves to appropriate folder

**Asset Sourcing Strategy:**

**Immediate (Weekend):**
- Artbreeder or This Person Does Not Exist for quick library
- 20-30 generic portraits tagged by faction
- Players can override with their own

**Short-term (Month 1):**
- Kitty protocol implementation for terminal users
- Basic upload system for custom portraits
- Portrait persistence in campaign JSON

**Long-term (Quarter 2-3):**
- Local SD integration for generation
- Faction-specific filters and post-processing
- Expression variants (neutral, suspicious, friendly, hostile)
- Dynamic portrait state based on disposition changes

**Success Metrics:**
- Players recognize NPCs visually, not just by name
- Faction identity is clear from portrait style
- System works gracefully in pure terminal AND desktop app
- Player customization is discoverable and fun
- No performance hit on local LLM users

---

### 1.6 Dynamic Overlays & Indicators

**Goal:** Surface hidden game state without breaking immersion

**NPC Deception Indicators:**
When an NPC's `lie_to_self` agenda triggers, subtle visual cues:
- Slight color shift in portrait frame
- Micro-glitch in text rendering
- Optional: "[unreliable]" tag (toggle-able for players who want explicit info)

**Memory Trigger Feedback:**
When NPC dialogue references stored memory:
```
╔═══════════════════════════════════════╗
║  ◆  MARCUS WEBB                       ║
║  [EMBER - CELL LEADER]                ║
║  [Disposition: Wary]                  ║
║                                       ║
║  "I remember what you did at the      ║
║   depot. Words are cheap."            ║
║                          [⚡ MEMORY]   ║
╚═══════════════════════════════════════╝
```
The `[⚡ MEMORY]` tag indicates NPC is referencing a stored interaction.

**Consequence Preview (Desktop App Only):**
On hover/focus over choice options, show potential ramifications:
```
┌─────────────────────────────────────────────┐
│ 2. Negotiate terms first                    │
├─────────────────────────────────────────────┤
│ ⚠ May affect:                               │
│   • Ember standing (risk)                   │
│   • Guard's disposition                     │
│   • Time pressure                           │
└─────────────────────────────────────────────┘
```
**Important:** Previews are hints, not guarantees. Preserve uncertainty.

**Trust/Disposition Meter:**
Optional inline indicator during NPC dialogue:
```
[Disposition: Wary ▰▰▱▱▱]
```
Updates in real-time as conversation progresses.

---

### 1.7 Social Energy Widget

**Concept:** Reskin the social energy meter as a heartbeat trace on a mini canvas.

**Implementation:**
- Draw 120-point sine wave, clamp amplitude to current %
- **Frayed:** Add `noise()` to the wave
- **Overloaded:** Red overshoot spikes
- One canvas element, 60fps, feels medical/clinical

**Why this works:** Matches SENTINEL's "clinical precision" aesthetic while making an abstract stat feel visceral.

---

### 1.8 Glitch Effects Library

**Banner Glitch Intro (Kimi):**
Corrupt the canvas on load: slice the banner PNG into 8-pixel strips, jitter x-coordinates with `Math.sin(frame * 0.3) * corruption`, then converge to normal over ~90 frames. 30 lines of JS, instant aesthetic.

**Frequency Jitter (Gemini):**
When an NPC is lying or faction is hostile, jitter their portrait position by 1-2 pixels randomly. Subtle wrongness.

**Signal Quality per Faction (Council Mode):**
- **Nexus:** Clean, high-res signal
- **Ember:** Analog fuzz, warm tones
- **Ghost Networks:** Signal drops in and out, visual artifacts

**Warp-Style Block Glow:**
```css
.block {
  background: #111;
  box-shadow: 0 0 0 1px #3a3a3a, 0 0 0 2px #1e1e1e;
}
.block:focus {
  box-shadow: 0 0 0 1px #4a9eff, 0 0 8px #4a9eff40;
}
```

---

## Phase 2: Desktop App (Terminal++, Not Replacement)

**Goal:** Warp's lesson - "better terminal" not "replace terminal"

### 2.1 Tauri Wrapper
**Why Tauri over Electron:**
- Tiny bundle size (~3MB vs 150MB+)
- Uses system webview (no Chromium bloat)
- Rust backend can embed Python runtime
- Native feel, terminal heart
- Better security model
- Plays nicely with local file systems for campaign saves

**What It Adds:**
- Better font rendering (ligatures, custom fonts like JetBrains Mono, Fira Code)
- Theme customization UI
- Window management (split views for notes?)
- File drag-and-drop for character import
- System notifications for important moments
- Subtle key-press sounds or visual flares (very MGS)

**What It Doesn't Change:**
- Still fundamentally terminal interaction
- Same CLI commands
- Same game logic
- Can still run pure CLI version

**Proposed Directory Structure:**
```
sentinel-ui/                    # COMPLETELY OPTIONAL
├── src/
│   ├── terminal/
│   │   ├── cli_wrapper.ts      # Wraps Python CLI
│   │   ├── command_palette.tsx # Warp-style command input
│   │   └── block_renderer.tsx  # Choice blocks, outputs
│   ├── portraits/
│   │   ├── npc_display.tsx     # MGS-style portrait overlay
│   │   ├── faction_overlay.tsx # Faction context display
│   │   └── disposition_meter.tsx
│   ├── visualization/
│   │   ├── timeline_view.tsx   # Consequence chain visualization
│   │   ├── faction_map.tsx     # Relationship graph
│   │   └── memory_inspector.tsx # Browse campaign history
│   └── bridge/
│       ├── ipc.ts              # IPC to Python backend
│       └── memvid_reader.ts    # Read .mv2 file directly
└── assets/
    ├── portraits/              # NPC portrait images
    ├── faction_themes/         # Color schemes per faction
    └── icons/                  # UI iconography
```

**Recommended Tech Stack:**
```
frontend/
├── web/                     # Browser-based UI
│   ├── vite + react         # Fast dev, good component model
│   ├── tailwind             # Theme control, faction colors
│   ├── xterm.js             # Terminal emulation (or custom)
│   ├── pixi.js              # 2D canvas for portraits/effects
│   └── framer-motion        # Animations, glitch reveals
├── desktop/                 # Tauri wrapper
│   └── shared web components
└── mobile/                  # Future: React Native
    └── touch-optimized dialogue
```

---

### 2.2 Backend Connection

**Principle:** Keep Python CLI as single source of truth. Frontend is a view, not a rewrite.

**Options:**
1. **FastAPI + WebSocket** — Best for streaming text ("incoming transmission" feel)
2. **Socket.IO** — Real-time state updates (social energy pushes to UI immediately)
3. **REST polling** — Simplest, but less responsive

**WebSocket Pattern:**
```python
# sentinel-agent/src/interface/websocket_server.py
async def handle_connection(websocket):
    game = load_campaign()

    while True:
        await websocket.send_json({
            "type": "scene_update",
            "npc_portraits": get_active_npcs(game),
            "dialogue": current_dialogue,
            "choices": formatted_choices,
            "player_status": get_player_state(game)
        })

        # Wait for input from ANY interface (CLI, web, mobile)
        choice = await get_next_choice()
        game = process_choice(choice)
```

**Warp-Style Input Hinting:**
Hidden `<span>` that mirrors text; measure width and absolutely-position the ghost hint. Easier than canvas math.

---

### 2.3 Visual Enhancements (App-Only)

**Optional Sidebar:**
- Faction standing visualization
- Quick reference for active NPCs
- Session notes
- Collapsible, keyboard-driven

**Smooth Scrolling:**
- Better paging through long GM responses
- Scroll position memory
- Jump to recent hinge

**Richer Typography:**
- Custom monospace font with character
- Better Unicode support
- Subtle animations for state changes

---

## Phase 3: Polish & Personality

**Goal:** SENTINEL's unique visual identity

### 3.1 Faction-Specific Visual Language

When interacting with factions, subtle UI changes:
- **Nexus:** Clean lines, data-driven layouts
- **Ember:** Warmer colors, community-focused
- **Covenant:** Formal structure, traditional typography
- **Ghost Networks:** Glitch effects, ephemeral text

### 3.2 Moment-Driven UX

**Core principle:** The UI should be *interruptible*, not polite.

**Visual Modes (distinct behaviors, not just components):**

| Mode | Visual Behavior |
|------|-----------------|
| Normal dialogue | Calm cadence, stable layout |
| Choice block | Hard borders, no animation |
| Hinge moment | Color inversion + subtle jitter |
| Council | Split-pane, conflicting alignment |
| Dormant thread surfacing | Brief UI interruption |

**Routine moments:** Clean, minimal
**High-stakes choices:** Visual weight increases
**Hinge moments:** Special framing, maybe even time to think

### 3.3 Micro-Animations

**Subtle, purposeful:**
- Faction standing shifts get brief color pulse
- Social energy drain has gentle fade
- New intel appears with soft reveal
- Council convening gets ceremonial transition

**Never:**
- Distracting bounces
- Unnecessary delays
- Animations for animation's sake

---

### 3.4 Phase-Based UI Layers

Different mission phases should feel visually distinct:

| Phase | UI Theme | Interaction Pattern |
|-------|----------|---------------------|
| Briefing | Command center (blue tones, grids) | Scrollable intel, map view |
| Planning | Whiteboard mode (yellow/orange) | Drag-n-drop assets, timeline |
| Execution | First-person HUD (green/red) | Real-time choices, tension meter |
| Debrief | After-action report (sepia) | Reflection prompts, consequence map |

---

### 3.5 Council as "Codec Mode"

When `/consult` is invoked, trigger a distinct visual mode:
- Screen dims
- Two or three portrait boxes slide in
- Each advisor has distinct signal quality (see §1.8)
- Player's own portrait shows social energy state (glitch shader if Frayed/Overloaded)

---

## Development Tooling

### Hot-Reload for Assets

During dev, watch the `portraits/` folder with `chokidar`; when a file changes, send a `reload_sprite` event down the socket. Artists see updates instantly, no restart.

### GPU Fallback Detection

Detect terminal emulator via `$TERM_PROGRAM` or `process.env.WARP_IS_LOCAL`. If missing GPU support, fall back to Rich-themed ASCII frames (you already have glyphs). Same data layer, two renderers.

### Platform Considerations

**Steam Deck / Handheld:**
- Build with Tauri + responsive web UI → deploys to Steam Deck easily
- Controller mapping: D-pad scrolls through Choice Blocks, 'A' selects, 'Start' opens Codec/Council

---

## Development Pitfalls (Guardrails)

**Avoid:**
- ❌ Rebuilding AI logic in JS — keep it in Python
- ❌ Making UI required — CLI must stay pristine
- ❌ Visual complexity that breaks "calm surface, tension underneath"
- ❌ UI creep — portrait + dialogue box first, ship that, *then* Warp blocks

**Do:**
- ✅ Make UI optional and modular
- ✅ Use existing theme colors (twilight blue, radioactive yellow)
- ✅ Maintain "if it looks calm, it's lying" design principle
- ✅ Build as progressive enhancement (terminal → effects → advanced)

---

## Implementation Priority

**Quarter 1:** ✓ Complete
- [x] Block-based output system (timestamped blocks, auto-detect INTEL/NARRATIVE)
- [x] Enhanced command palette (categories, fuzzy search, context-aware, recent cmds)
- [x] State visualization improvements (persistent status bar with delta tracking)
- [x] Session history enhancement (filter by type/session, keyword search, /search cmd)
- [x] Enhanced faction glyphs for NPC dialogue (MGS codec style, Phase 1)

**Quarter 2:**
- [x] Search functionality (integrated with /history search, /search alias)
- [ ] Faction visual language refinements
- [ ] Desktop app prototype (Tauri POC)
- [ ] Kitty protocol image support for terminals
- [ ] Portrait library (20-30 base portraits via Artbreeder)
- [ ] Custom portrait upload system

**Quarter 3:**
- [ ] Desktop app beta with full image support
- [ ] Theme customization
- [ ] Optional sidebar features
- [ ] Polish pass on animations
- [ ] Faction-specific portrait styling
- [ ] Local SD integration prototype (optional)

**Quarter 4:**
- [ ] Community feedback integration
- [ ] Performance optimization
- [ ] Documentation for contributors
- [ ] Dynamic portrait states (disposition-driven)
- [ ] v2.0 release

---

## Guiding Principles

**Terminal-First Always:**
- CLI version is primary, not legacy
- Desktop app is enhancement, not replacement
- Every feature must work in pure terminal

**Confidence Over Apology:**
- This is a terminal game. Own it.
- Design for keyboard-first users
- Don't try to be what we're not

**Information as Atmosphere:**
- Visual design serves narrative weight
- Factions feel different through typography
- Stakes are communicated through layout

**Performance Matters:**
- No feature that adds noticeable lag
- Smooth scrolling is non-negotiable
- Local LLM users shouldn't suffer

**Stillness Is Power:**
- If *everything* moves, nothing feels important
- Stillness = confidence, Motion = stress
- Reserve animation for moments that earn it
- Let silence and static frames carry weight

---

## Success Metrics

**We'll know it's working when:**
- New players say "oh, THIS is what terminals can do"
- Session history is actually used for reference
- Players customize their experience
- The UI disappears into the experience
- Someone says "this feels like Warp for RPGs"

---

## Feedback Sources

This document incorporates suggestions from:
- ChatGPT (frontend architecture, event-driven UI)
- Claude Chrome Extension (initial consolidation)
- Claude Code (integration, editing)
- Deepseek (phase-based UI, backend patterns, pitfalls)
- Gemini (Tauri, Socket.IO streaming, controller mapping)
- Kimi (portrait tips, glitch algorithms, hot-reload, heartbeat widget)

---

**Version:** 2.0 - Full AI Council Feedback
**Status:** Vision Document - Implementation TBD
**Vibe Check:** Confident, polished, unapologetically terminal
