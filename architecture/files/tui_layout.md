# SENTINEL TUI Layout Specification

## Screen Layout (ASCII Mockup)

**Default Mode: Focused Play (Centered Console + Dock)**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ┌─ HEADER ─────────────────────────────────────────────────────────────┐ │
│ │ SENTINEL v0.1  ·  Campaign  ·  Seed 7F3A                              │ │
│ ├─ STATUS ─────────────────────────────────────────────────────────────┤ │
│ │ CIPHER │ Phase: INFILTRATE                                            │ │
│ ├─ CONTEXT ────────────────────────────────────────────────────────────┤ │
│ │ Active Factions                                                      │ │
│ │   Nexus ▰▰▱▱▱ Wary        │ Ember ▰▰▰▱▱ Friendly                     │ │
│ │   Others ▰▱▱ Neutral (background)                                   │ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │                                                                      │ │
│ │  [ CURRENT SCENE ]                                                   │ │
│ │                                                                      │ │
│ │  The rain hasn’t stopped in three days. The signal you intercepted  │ │
│ │  is old, fragmented, and deliberately misrouted. Someone wanted     │ │
│ │  you to find it — just not yet.                                      │ │
│ │                                                                      │ │
│ │  A door blinks amber at the end of the corridor.                     │ │
│ │                                                                      │ │
│ ├─ INPUT ──────────────────────────────────────────────────────────────┤ │
│ │ > What do you do?                                                   │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ──────────────────────────────────────────────────────────────────────  │
│  Pistachios ▰▰▰▱▱ 67% ↓   |   Strain ▰▱▱ LOW   |   Session 04            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

**Invoked Mode: Tactical View (Panels Expanded)**

> This view is *never default*. It is entered deliberately via keybind or command.

```
┌── SELF [L] ────────────┐┌── ◈ SENTINEL STREAM ───────────────────────────┐┌── WORLD [R] ───────────┐
│ CIPHER                 ││ 🔋 Pistachios ▰▰▰▱▱ 67% │ Strain ▰▱▱ LOW        ││ ◈ ACTIVE STANDING      │
│ [Intel Operative]      │├────────────────────────────────────────────────┤│                        │
│                        ││ ╭── NARRATIVE ───────────────────────────────╮ ││ NEXUS [Friendly]      │
│ ── STATUS ──────────── ││ │ The rain hasn’t stopped in three days.       │ ││ ▰▰▰▱▱ (+20)           │
│ Pistachios 67%         ││ │ Someone wanted you to find the signal —     │ ││ ↳ Lattice +3          │
│ Strain: Low            ││ │ just not yet.                                │ ││                        │
│                        ││ ╰────────────────────────────────────────────╯ ││ EMBER [Neutral]       │
│ ── LOADOUT ─────────── ││                                                ││ ▰▱▱▱▱ (-5)            │
│ [x] Encrypted Laptop   ││ ╭── CHOICE ──────────────────────────────────╮ ││                        │
│ [x] Tactical Drone     ││ │ 1. Hack the door panel                        │ ││ ── THREADS (Pending) ─ │
│ [ ] Sidearm            ││ │ 2. Force the lock                             │ ││ ⚠ Syndicate (2)       │
│                        ││ │ 3. Scan with drone                            │ ││ ⚠ Lattice (latent)   │
│ ── ENHANCEMENTS ────── ││ ╰────────────────────────────────────────────╯ ││                        │
│ [Refused Corp Suite]   ││                                                ││                        │
└────────────────────────┘└────────────────────────────────────────────────┘└────────────────────────┘
```

---

## Panel Definitions

### Panel: Header

* **Position:** top (center panel)
* **Size:** fixed (1–2 lines)
* **Content:** game identity, campaign seed
* **Updates when:** campaign/session changes
* **Border:** yes

---

### Panel: Status

* **Position:** top (main console)
* **Size:** fixed (1 line)
* **Content:** character name, current phase
* **Updates when:** phase changes
* **Border:** yes

---

### Panel: Context

* **Position:** below status
* **Size:** fixed (3–4 lines)
* **Content:** top 1–2 active factions, background others
* **Updates when:** faction standing changes
* **Border:** yes

---

### Panel: Narrative / Choice Stream

* **Position:** center
* **Size:** flexible
* **Content:** narrative blocks, dialogue, choices
* **Updates when:** every GM response
* **Border:** framed blocks

---

### Panel: Bottom Dock

* **Position:** bottom
* **Size:** fixed (1 line)
* **Content:** social energy (bar + delta), strain tier, session
* **Updates when:** values change
* **Border:** minimal divider only

**Rules:**

* Display-only
* Toggleable
* No duplication of detailed info

---

### Panel: Self (Tactical View Only)

* **Position:** left
* **Size:** fixed width
* **Content:** detailed social energy, loadout, refused enhancements
* **Updates when:** on action
* **Border:** yes

---

### Panel: World (Tactical View Only)

* **Position:** right
* **Size:** fixed width
* **Content:** faction standings (delta-aware), pending threads (abstracted)
* **Updates when:** faction shift, thread creation
* **Border:** yes

---

## Color Theme

| Element       | Color                  | Notes                                       |
| ------------- | ---------------------- | ------------------------------------------- |
| Background    | AMOLED black (#000000) | True black for OLED; reduces visual fatigue |
| Panel borders | Pale surgical white    | Clinical framing                            |
| Primary text  | Soft white             | Long-read safe                              |
| Accent        | Muted cyan             | Faction-neutral highlight                   |
| Warning       | Muted amber            | Pressure, not alarm                         |
| Danger        | Rusted red             | High-stakes only                            |
| Dim/secondary | Grey-blue              | Background info                             |

---

## Keybindings

| Key    | Action                                   |
| ------ | ---------------------------------------- |
| TAB    | Cycle UI mode (Focus → Split → Tactical) |
| [      | Toggle Self panel                        |
| ]      | Toggle World panel                       |
| /dock  | Toggle bottom dock                       |
| /focus | Force Focus mode                         |
| Ctrl+Q | Quit                                     |

---

## Behavior Notes

* Focus mode is the default and canonical play state
* Tactical view is deliberate and phase-appropriate
* UI never answers questions the player hasn’t chosen to ask
* Pressure is shown continuously; detail is revealed intentionally
* Threads are abstracted unless explicitly inspected

---

## Reference: Current Implementation

The current TUI (`src/interface/tui.py`) has:

* STATUS panel (top, fixed)
* FACTIONS panel (below status)
* OUTPUT RichLog (scrollable)
* INPUT field (bottom)

This specification replaces stacked panels with **hierarchy + mode switching**.

---

## Ideas / Wishlist

* Strain-tier-based UI intrusion (visual weight increases under pressure)
* Brief flash on faction or strain change
* Optional fade-in for Tactical View during Planning/Resolution
* Accessibility pass for reduced visual density modes
