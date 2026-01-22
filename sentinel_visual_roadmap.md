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
│   WARM            │  [NEGOTIATOR] "Let's find common ground."       │
│                   │  [STEEL SYNDICATE: Friendly] "Malik sent me."   │
│   FACTION         │  [HISTORY: Saved her courier] "We're even."     │
│   Steel Syndicate │  [LOW ENERGY] "I don't have time for games."    │
│                   │  > Say something else...                        │
│                   │                                                 │
├───────────────────┴─────────────────────────────────────────────────┤
│ ▸ Type response or select option...                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Dialogue Option Tags

Unlike Fallout's numeric skill checks, SENTINEL uses **contextual unlocks** based on who you are and what you've done:

| Tag Type | Format | What It Represents |
|----------|--------|-------------------|
| **Background** | `[NEGOTIATOR]` | Your professional training unlocks this approach |
| **Faction** | `[LATTICE: Allied]` | Your standing with a faction opens doors |
| **Enhancement** | `[NEURAL LINK]` | Faction-granted ability enables this option |
| **Gear** | `[FORGED PAPERS]` | An item in your inventory creates opportunity |
| **History** | `[Saved their sister]` | Past actions with this NPC are remembered |
| **Energy** | `[LOW ENERGY]` | Exhaustion unlocks desperate/aggressive options |
| **Disposition** | `[WARM+]` | Only available if NPC already trusts you |

### Why This Is Better Than Skill Numbers

1. **No grinding** — Your background is your background, not a number to farm
2. **Relationships matter** — Faction standing unlocks options, not abstract charisma
3. **Gear has narrative weight** — That forged ID isn't +5 Speech, it's a specific tool
4. **History echoes** — The game remembers you helped this NPC's courier last session
5. **Energy as choice** — Low social energy doesn't just debuff, it unlocks darker paths

### Features

| Feature | Description |
|---------|-------------|
| **Portrait box** | Character portrait (NanoBanana-generated or placeholder) |
| **Disposition bar** | Visual indicator of current relationship |
| **Faction badge** | Shows affiliation and standing impact |
| **Contextual tags** | Options unlocked by background, faction, gear, history, energy |
| **Typing effect** | NPC dialogue types out character-by-character (skippable) |
| **Voice line hints** | Tone indicators: `(coldly)`, `(laughing)`, `(hesitant)` |

### Implementation Path

1. **Phase 1: Static codec layout** — CSS/HTML for the codec frame
2. **Phase 2: Portrait integration** — Pull from `assets/portraits/` or generate
3. **Phase 3: Dialogue options** — Parse GM response for tag patterns `[TAG]`
4. **Phase 4: Tag rendering** — Color-code by type (background=cyan, faction=purple, etc.)
5. **Phase 5: Typing animation** — Character-by-character with sound
6. **Phase 6: Transition effects** — Codec open/close animations

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
| 🟡 Medium | Contextual dialogue tags | Medium | SENTINEL-native feel |
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

- **Fallout 1/2/New Vegas** — Dialogue trees with contextual options, consequences
- **Metal Gear Solid** — Codec call framing, portrait boxes, dramatic tension
- **Deus Ex** — Information density, dark UI, meaningful choices
- **Disco Elysium** — Skill checks as character expression, not power fantasy
- **Caves of Qud** — ASCII aesthetic with depth, emergent narrative
