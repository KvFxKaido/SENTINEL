# SENTINEL Mechanics Stack

How SENTINEL's systems interconnect to create emergent narrative gameplay.

## The Stack at a Glance

```
                    ┌─────────────────────────────────────┐
                    │         PLAYER INTERFACE            │
                    │    TUI (Textual) / Web UI (Astro)   │
                    └──────────────────┬──────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
   ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
   │  CONSEQUENCE  │◀────────▶│    STATE      │◀────────▶│   CONTEXT     │
   │    ENGINE     │          │   MANAGER     │          │   CONTROL     │
   │               │          │               │          │               │
   │ • Hinges      │          │ • Campaign    │          │ • Packer      │
   │ • Threads     │          │ • Characters  │          │ • Window      │
   │ • Leverage    │          │ • NPCs        │          │ • Strain      │
   │ • Arcs        │          │ • Factions    │          │ • Retrieval   │
   └───────────────┘          └───────────────┘          └───────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │            GM (LLM)                 │
                    │  Narrative + Tool Calls + Choices   │
                    └─────────────────────────────────────┘
```

---

## System Interactions

### 1. Social Energy → Everything

Social energy (0-100%) is the universal constraint that ripples through all systems:

```
Social Energy ──┬──▶ Roll Modifiers (frayed = disadvantage)
                ├──▶ NPC Reactions (NPCs notice fatigue)
                ├──▶ Choice Availability (0% = complex social fails)
                ├──▶ Favor Costs (can't call in favors when depleted)
                └──▶ Tactical Reset (spend 10% for advantage when in element)
```

**Files:** `schema.py` (SocialEnergy), `dice.py` (roll modifiers), `tui.py` (visual feedback)

---

### 2. Faction Standing → Cascading Effects

Faction relationships create ripple effects:

```
Player helps Nexus (+20)
    │
    ├──▶ Direct: Nexus standing +20
    │
    ├──▶ Cascade: Lattice +3 (ally)
    │           Ghost Networks -5 (rival)
    │
    ├──▶ NPC Triggers: fire for all NPCs with "faction:nexus" trigger
    │
    ├──▶ Job Access: new Nexus jobs unlocked
    │
    └──▶ Intel Access: Nexus-domain queries now available
```

**Files:** `schema.py` (FactionStanding), `manager.py` (cascade logic), MCP tools (faction intel)

---

### 3. NPC Disposition → Behavior Stack

NPCs combine faction standing with personal history:

```
Effective Disposition = (Personal × 0.6) + (Faction × 0.4)

                    ┌─────────────────────────────────────┐
                    │           NPC BEHAVIOR              │
                    └─────────────────────────────────────┘
                                       │
    ┌──────────────────────────────────┼──────────────────────────────────┐
    │                                  │                                  │
    ▼                                  ▼                                  ▼
┌─────────────┐                ┌─────────────┐                ┌─────────────┐
│  TONE       │                │  REVEALS    │                │  WITHHOLDS  │
│             │                │             │                │             │
│ hostile:    │                │ hostile:    │                │ hostile:    │
│ "Curt,      │                │ Nothing     │                │ Everything  │
│  defensive" │                │ useful      │                │             │
│             │                │             │                │             │
│ loyal:      │                │ loyal:      │                │ loyal:      │
│ "Warm,      │                │ Full        │                │ Nothing     │
│  confiding" │                │ disclosure  │                │             │
└─────────────┘                └─────────────┘                └─────────────┘
                                       │
                                       ▼
                            ┌─────────────────┐
                            │  MEMORY TAGS    │
                            │                 │
                            │ "helped_ember"  │
                            │ triggers shift  │
                            └─────────────────┘
```

**Files:** `schema.py` (NPC, DispositionModifiers), `npc.py` (behavior rules)

---

### 4. Consequence Flow

Choices create consequences that unfold over time:

```
Player Choice
    │
    ├──▶ IMMEDIATE
    │    └── Faction shift, NPC reaction, resource change
    │
    ├──▶ HINGE MOMENT (irreversible)
    │    └── Logged permanently, referenced by GM, informs arc detection
    │
    └──▶ DORMANT THREAD (delayed)
         │
         ├── trigger: "return to Rust Corridor"
         ├── deadline: 3 sessions
         └── escalation: ROUTINE → PRESSING → URGENT → CRITICAL
                              │
                              ▼
                    ┌─────────────────┐
                    │   SURFACING     │
                    │                 │
                    │ GM weaves into  │
                    │ narrative when  │
                    │ trigger fires   │
                    └─────────────────┘
```

**Files:** `schema.py` (HingeMoment, DormantThread), `leverage.py` (escalation), `hinge_detector.py`

---

### 5. Enhancement Leverage Loop

Accepting faction power creates obligation:

```
Player accepts enhancement from Convergence
    │
    ├──▶ Enhancement active (mechanical benefit)
    │
    └──▶ Leverage Created
         │
         ├── Convergence can make DEMANDS
         │
         └── Demand lifecycle:
             │
             ├── OFFERED (faction proposes)
             ├── ACTIVE (deadline counting)
             ├── ESCALATING (deadline approaching)
             └── CALLED (compliance required or consequence)
                        │
                        ├──▶ Comply: faction satisfied, leverage reset
                        ├──▶ Refuse: consequence + "Unbought" reputation
                        └──▶ Negotiate: partial compliance, thread queued
```

**Files:** `schema.py` (Enhancement, LeverageState), `leverage.py` (demand system)

---

### 6. Context Pressure → GM Behavior

Context window fills → systems adapt:

```
Context Usage
    │
    ├── 0-70%: NORMAL
    │   └── Full prompts, all retrieval, narrative guidance
    │
    ├── 70-85%: STRAIN I
    │   └── Reduced window, minimal retrieval
    │
    ├── 85-95%: STRAIN II
    │   └── Narrative guidance DROPPED (core logic survives)
    │
    └── 95%+: STRAIN III
        └── Minimal context, checkpoint suggested

SafetyNet: Rules have ELSE IF context_incomplete branches
           → "pressure yes, permanence no"
```

**Files:** `packer.py` (budgets), `window.py` (trimming), `prompts/rules/core_logic.md`

---

### 7. Async Presence Stack

Making stillness feel alive:

```
┌────────────────────────────────────────────────────────────────┐
│                     ASYNC PRESENCE                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  THINKING PANEL          PRESSURE PANEL         SESSION BRIDGE │
│  ┌────────────┐          ┌────────────┐         ┌────────────┐ │
│  │ ◇ Context  │          │ 🔴 Demand   │         │ WHILE YOU  │ │
│  │ ◆ Packing  │          │    T-2 days │         │ WERE AWAY  │ │
│  │ ○ Awaiting │          │ 🟡 Thread   │         │            │ │
│  └────────────┘          │ ⚪ NPC (3s) │         │ • Changes  │ │
│                          └────────────┘         │ • Messages │ │
│                                                 └────────────┘ │
│                                                                │
│  AMBIENT CONTEXT: Woven into GM responses naturally           │
│  "Cipher's voice on the comm: 'We need an answer. Today.'"    │
│                                                                │
│  REACTIVE ANIMATIONS: Faction shifts, energy pulses           │
└────────────────────────────────────────────────────────────────┘
```

**Files:** `event_bus.py`, `tui.py` (ThinkingPanel, PressurePanel), `ambient_context.py`

---

### 8. Wiki Bi-Directional Sync

Game state and wiki stay synchronized:

```
                    ┌─────────────────┐
                    │   GAME STATE    │
                    │   (JSON files)  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  wiki_adapter   │           │  wiki_watcher   │
    │                 │           │                 │
    │  State → Wiki   │           │  Wiki → State   │
    │  (on events)    │           │  (on file edit) │
    └─────────────────┘           └─────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │  OBSIDIAN WIKI  │
                    │  (Markdown)     │
                    └─────────────────┘

Edit NPC disposition in Obsidian → game state updates
Log hinge moment in game → wiki timeline appends
```

**Files:** `wiki_adapter.py`, `wiki_watcher.py`, `templates.py`

---

### 9. Character Arc Detection

Emergent arcs from play patterns:

```
Play History (hinges, faction shifts, NPC interactions)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   ARC DETECTOR                          │
│                                                         │
│  Pattern matching against 8 arc types:                  │
│  • Diplomat (negotiation focus)                         │
│  • Partisan (faction loyalty)                           │
│  • Broker (information gathering)                       │
│  • Pacifist (violence avoidance)                        │
│  • Pragmatist (resource focus)                          │
│  • Survivor (self-preservation)                         │
│  • Protector (defending others)                         │
│  • Seeker (truth-finding)                               │
│                                                         │
│  Strength: 0-100% based on evidence count               │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Player accepts/rejects → Accepted arcs inform GM behavior
```

**Files:** `schema.py` (ArcType, CharacterArc, ARC_PATTERNS), `arcs.py`

---

### 10. Endgame Readiness

Multi-factor tracking for campaign conclusion:

```
                    READINESS SCORE
                    ┌───────────────┐
                    │     78%       │
                    │  APPROACHING  │
                    └───────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐          ┌─────────┐          ┌─────────┐
│ HINGES  │          │  ARCS   │          │ THREADS │
│  30%    │          │  25%    │          │  25%    │
│         │          │         │          │         │
│ ≥3 for  │          │ ≥1 arc  │          │ ≥75%    │
│ full    │          │ ≥50%    │          │ resolved│
└─────────┘          └─────────┘          └─────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  FACTIONS   │
                    │    20%      │
                    │             │
                    │ Meaningful  │
                    │ standings   │
                    └─────────────┘
                           │
                           ▼
              ACTIVE → APPROACHING → EPILOGUE → CONCLUDED
```

**Files:** `schema.py` (EndgameReadiness, CampaignStatus), `endgame.py`

---

## The Complete Loop

```
     ┌──────────────────────────────────────────────────────────────┐
     │                                                              │
     │   Player Input ──▶ GM Response ──▶ State Change ──▶ Events  │
     │         │                               │              │     │
     │         │                               │              │     │
     │         │    ┌──────────────────────────┘              │     │
     │         │    │                                         │     │
     │         │    ▼                                         ▼     │
     │         │  ┌─────────┐   ┌─────────┐   ┌─────────┐  ┌─────┐ │
     │         │  │Hinges   │   │Threads  │   │Factions │  │ TUI │ │
     │         │  │Arcs     │   │NPCs     │   │Standing │  │React│ │
     │         │  └─────────┘   └─────────┘   └─────────┘  └─────┘ │
     │         │        │              │             │        │     │
     │         │        └──────────────┴─────────────┴────────┘     │
     │         │                       │                            │
     │         │                       ▼                            │
     │         │              ┌─────────────────┐                   │
     │         └─────────────▶│  Wiki Sync      │                   │
     │                        │  Obsidian pages │                   │
     │                        └─────────────────┘                   │
     │                                                              │
     └──────────────────────────────────────────────────────────────┘
```

Every player action ripples through interconnected systems, creating emergent narrative consequences that surface organically over time.

---

## Implementation Status

| System | Status | Key Files |
|--------|--------|-----------|
| Social Energy | ✅ Complete | `schema.py`, `dice.py` |
| Faction Cascades | ✅ Complete | `manager.py`, MCP tools |
| NPC Dispositions | ✅ Complete | `schema.py`, `npc.py` |
| Hinge Moments | ✅ Complete | `hinge_detector.py` |
| Dormant Threads | ✅ Complete | `schema.py`, `leverage.py` |
| Enhancement Leverage | ✅ Complete | `leverage.py` |
| Context Control | ✅ Complete | `packer.py`, `window.py` |
| Async Presence | ✅ Complete | `event_bus.py`, `tui.py` |
| Wiki Sync | ✅ Complete | `wiki_adapter.py`, `wiki_watcher.py` |
| Arc Detection | ✅ Complete | `arcs.py` |
| Endgame | ✅ Complete | `endgame.py` |

---

## See Also

- `AGENT_ARCHITECTURE.md` — Detailed technical design
- Root `CLAUDE.md` § Design Philosophy (condensed) — Non-negotiable principles
- `sentinel-agent/CLAUDE.md` — Development guide
- `Archive/OBSIDIAN_INTEGRATION.md` — Wiki implementation history
