# SENTINEL Visual & Aesthetic Roadmap

## Vision

Transform SENTINEL from functional TUI to an **immersive tactical experience** that evokes:
- **Fallout** — Dialogue skill checks, pip-boy interfaces, retro-futuristic terminals
- **Metal Gear Solid** — Codec calls with character portraits, dramatic framing, tension

The aesthetic should feel like you're operating in a post-collapse world through salvaged tech.

---

## Design Principles

1. **Diegetic UI** — Interface elements should feel like in-world tech, not floating HUD
2. **Information density** — Show what matters without clutter (TUI heritage)
3. **Mood through constraint** — Limited palette, deliberate typography, negative space
4. **Sound as presence** — Audio reinforces the world, not just events

---

## NPC Codec System (MGS-Inspired)

The crown jewel. When talking to NPCs, switch to a **codec-style dialogue view**.

### Visual Design

```
┌─────────────────────────────────────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ INCOMING ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
├───────────────────┬─────────────────────────────────────────────────┤
│                   │                                                 │
│   ┌───────────┐   │  KIRA VANCE                                     │
│   │           │   │  Steel Syndicate • Fixer                        │
│   │  [PORT-   │   │  ─────────────────────────────────────────────  │
│   │   RAIT]   │   │                                                 │
│   │           │   │  "You've got nerve showing up here after        │
│   │           │   │   what happened in the Corridor. But nerve      │
│   └───────────┘   │   is exactly what I need right now."            │
│                   │                                                 │
│   DISPOSITION     │  ─────────────────────────────────────────────  │
│   ████████░░      │                                                 │
│   WARM            │  [SPEECH 45] "I saved your courier. We're even."│
│                   │  [BARTER 30] "Name your price for forgiveness." │
│   FACTION         │  [HONEST] "I made a call. It cost us both."     │
│   Steel Syndicate │  > Ask about the job instead                    │
│                   │                                                 │
├───────────────────┴─────────────────────────────────────────────────┤
│ ▸ Type response or select option...                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| **Portrait box** | Character portrait (NanoBanana-generated or placeholder) |
| **Disposition bar** | Visual indicator of current relationship |
| **Faction badge** | Shows affiliation and standing impact |
| **Skill checks** | Fallout-style `[SKILL ##]` options with success threshold |
| **Typing effect** | NPC dialogue types out character-by-character (skippable) |
| **Voice line hints** | Tone indicators: `(coldly)`, `(laughing)`, `(hesitant)` |

### Implementation Path

1. **Phase 1: Static codec layout** — CSS/HTML for the codec frame
2. **Phase 2: Portrait integration** — Pull from `assets/portraits/` or generate
3. **Phase 3: Dialogue options** — Parse GM response for skill check patterns
4. **Phase 4: Typing animation** — Character-by-character with sound
5. **Phase 5: Transition effects** — Codec open/close animations

---

## Character Portraits

### Sources

| Source | Use Case |
|--------|----------|
| **NanoBanana** | Generate from `assets/characters/*.yaml` specs |
| **Manual upload** | Custom portraits in `assets/portraits/` |
| **Placeholder** | Silhouette with faction color accent |

### Portrait Specs

- **Dimensions:** 256×256 (display at 128×128 for retina)
- **Style:** Consistent art style (see `assets/ART_STYLE.md`)
- **Variants:** Neutral, angry, pleased, suspicious (disposition-driven)
- **Format:** PNG with transparency

### Generation Workflow

```bash
# Generate portrait for NPC
/portrait <npc_name>

# Uses assets/characters/<npc_name>.yaml for appearance spec
# Outputs to assets/portraits/<npc_name>.png
```

---

## Map & Region Visualization

### World Map

ASCII-art style map showing:
- Current region (highlighted)
- Adjacent regions (accessible)
- Faction control (color-coded borders)
- Travel routes (dashed lines)

```
                    ┌─────────────┐
                    │  NORTHERN   │
                    │  REACHES    │
                    │  (Covenant) │
                    └──────┬──────┘
                           │
    ┌──────────┐    ┌──────┴──────┐    ┌───────────┐
    │ PACIFIC  │────│    RUST     │────│ NORTHEAST │
    │ CORRIDOR │    │  CORRIDOR   │    │   SCAR    │
    │(Converg.)│    │ ★ YOU ARE   │    │(Architects│
    └──────────┘    │    HERE     │    └───────────┘
                    │  (Lattice)  │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ BREADBASKET │
                    │(Cultivators)│
                    └─────────────┘
```

### Location Detail

When zoomed into a region:
- Key locations (safe houses, markets, faction HQs)
- Current position marker
- Points of interest from active jobs

---

## Faction Relationship Graph

Visual web showing faction relationships:

```
                    NEXUS
                   /  |  \
                  /   |   \
            LATTICE   |   ARCHITECTS
              |    \  |  /    |
              |     \ | /     |
        CULTIVATORS──COVENANT──WITNESSES
              |       |       |
              |       |       |
         WANDERERS   |    GHOST NETWORKS
              \      |      /
               \     |     /
            EMBER COLONIES
                    |
             STEEL SYNDICATE
                    |
              CONVERGENCE
```

- **Line color:** Alliance (green), tension (orange), hostile (red)
- **Node size:** Based on player standing
- **Pulse effect:** On recent faction changes

---

## Timeline Visualization

Horizontal timeline of campaign events:

```
Session 1        Session 2        Session 3        Session 4
    │                │                │                │
    ├── Started      ├── Met Kira     ├── ⬡ HINGE     ├── NOW
    │   campaign     │                │   Betrayed     │
    │                ├── Job:         │   Lattice      │
    │                │   Smuggling    │                │
    │                │                ├── Standing:    │
    │                │                │   Lattice →    │
    │                │                │   Hostile      │
```

- **Hinges:** Diamond markers (⬡)
- **Faction shifts:** Color-coded arrows
- **Dormant threads:** Dotted lines extending into future

---

## Sound Design

See also: [Sound Roadmap](sentinel_sound_roadmap.md)

### Categories

| Category | Examples |
|----------|----------|
| **Ambient** | Terminal hum, distant machinery, wind |
| **UI feedback** | Key clicks, command confirmation, error buzz |
| **Events** | Faction shift chime, hinge moment tone, thread surfacing |
| **Codec** | Call incoming, call end, static bursts |
| **Music** | Low tension drone, escalation cues (optional, toggleable) |

### Implementation

- Web Audio API for browser
- Howler.js for cross-browser compatibility
- Volume/mute controls in settings
- Sound pack as optional download (keeps base install light)

---

## Terminal Aesthetic Details

### Typography

| Element | Font | Style |
|---------|------|-------|
| **Headers** | JetBrains Mono | Bold, uppercase, letter-spacing |
| **Body** | JetBrains Mono | Regular |
| **NPC dialogue** | JetBrains Mono | Italic for tone hints |
| **System** | JetBrains Mono | Dim, smaller |

### Color Palette (Already Implemented)

| Purpose | Variable | Hex |
|---------|----------|-----|
| Background | `--bg-primary` | `#000000` |
| Panel | `--bg-secondary` | `#0a0a0a` |
| Primary accent | `--accent-steel` | `#79c0ff` |
| Cyan accent | `--accent-cyan` | `#56d4dd` |
| Danger | `--status-danger` | `#f85149` |
| Warning | `--status-warning` | `#d29922` |
| Success | `--status-success` | `#3fb950` |

### Effects

- **CRT scanlines** (optional, toggleable) — subtle horizontal lines
- **Screen flicker** — on error states or dramatic moments
- **Glitch effect** — when connection unstable or during tense scenes

---

## Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 🔴 High | NPC codec dialogue system | Large | Transformative |
| 🔴 High | Character portraits (NanoBanana) | Medium | High immersion |
| 🟡 Medium | Skill check display in options | Small | Fallout feel |
| 🟡 Medium | Typing animation for NPC text | Small | MGS feel |
| 🟡 Medium | Sound effects (UI feedback) | Medium | Polish |
| 🟢 Low | World map visualization | Medium | Nice-to-have |
| 🟢 Low | Faction relationship graph | Medium | Nice-to-have |
| 🟢 Low | Timeline visualization | Medium | Nice-to-have |
| 🟢 Low | CRT effects | Small | Aesthetic |
| 🟢 Low | Ambient audio | Medium | Immersion |

---

## Non-Goals

- Full voice acting (text is the medium)
- 3D graphics or complex animations
- Real-time multiplayer visuals
- Mobile-first design (desktop is primary)

---

## Success Criteria

- [ ] NPC conversations feel like codec calls, not chat logs
- [ ] Skill checks are visible before committing to dialogue
- [ ] Portraits exist for key NPCs (at least 1 per faction)
- [ ] Sound enhances without annoying (mute is always available)
- [ ] The UI feels like salvaged post-collapse tech, not a modern web app

---

## References

- **Fallout 1/2** — Dialogue trees with skill checks
- **Fallout: New Vegas** — [Speech 75] option format
- **Metal Gear Solid** — Codec call framing, portrait boxes
- **Deus Ex** — Information density, dark UI
- **Caves of Qud** — ASCII aesthetic with depth
