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

## Phase 2: Desktop App (Terminal++, Not Replacement)

**Goal:** Warp's lesson - "better terminal" not "replace terminal"

### 2.1 Tauri Wrapper
**Why Tauri:**
- Tiny bundle size (~3MB)
- Uses system webview (no Electron bloat)
- Rust backend can embed Python runtime
- Native feel, terminal heart

**What It Adds:**
- Better font rendering (ligatures, custom fonts)
- Theme customization UI
- Window management (split views for notes?)
- File drag-and-drop for character import
- System notifications for important moments

**What It Doesn't Change:**
- Still fundamentally terminal interaction
- Same CLI commands
- Same game logic
- Can still run pure CLI version

---

### 2.2 Visual Enhancements (App-Only)

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

## Implementation Priority

**Quarter 1:**
- [ ] Block-based output system
- [ ] Enhanced command palette
- [ ] State visualization improvements
- [ ] Basic session history
- [ ] Enhanced faction glyphs for NPC dialogue (MGS codec style, Phase 1)

**Quarter 2:**
- [ ] Search functionality
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

---

## Success Metrics

**We'll know it's working when:**
- New players say "oh, THIS is what terminals can do"
- Session history is actually used for reference
- Players customize their experience
- The UI disappears into the experience
- Someone says "this feels like Warp for RPGs"

---

**Version:** 1.0 - Planning Phase
**Status:** Vision Document - Implementation TBD
**Vibe Check:** Confident, polished, unapologetically terminal
