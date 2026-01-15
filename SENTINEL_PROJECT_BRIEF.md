# SENTINEL Project Brief

*Last updated: January 15, 2026*

## What This Is

SENTINEL is a **tactical tabletop RPG** with an **AI Game Master**. The game explores political tension, ethical tradeoffs, and survival in a post-collapse world where 11 factions compete for influence.

**Core loop:** Investigation → Interpretation → Choice → Consequence

**Not about:** min-max optimization, combat dominance, binary morality

**About:** navigating competing truths, sustaining integrity under pressure, relationships as resources

---

## Current Status

### Working

**Core Systems**
- CLI interface with Rich terminal UI + themed visuals
- **Block-based output** — GM responses as timestamped blocks with type indicators (NARRATIVE, INTEL, CHOICE)
- Animated hexagon banner with glitch reveal
- **Enhanced command palette** — category grouping, fuzzy search, context-aware filtering, recent commands
- Campaign creation, save/load (JSON persistence)
- Character creation with 7 backgrounds, personalized energy system
- 11 factions with reputation tracking
- Social energy system with **personalized restorers/drains**
- Dice mechanics (d20 + modifiers, advantage/disadvantage)
- Mission framework with 6 phases (briefing, planning, execution, resolution, debrief, between)

**Narrative Systems**
- **Multiple-choice system** — GM always offers 2-4 options + improvisation
- **Lore retrieval (RAG)** — GM draws from canon bible + novellas
- **Council system** — consult faction advisors for competing perspectives
- **Hinge detection** — auto-detects irreversible choices in player input
- **Non-action as hinge** — avoidance is content; tracks when players disengage and surfaces consequences later
- **Debrief "enough" question** — helps players articulate their own success criteria in a game with no win condition

**NPC Systems**
- **NPC disposition modifiers** — behavior changes based on disposition level
- **NPC memory triggers** — NPCs react to tagged events (e.g., faction shifts)
- **NPC individual memory** — separate personal standing from faction, effective disposition (60% personal, 40% faction)
- **NPC codec boxes** — MGS-style dialogue frames with faction-colored borders, disposition indicators
- **`/npc` command** — view NPC info, personal standing, interaction history (shows codec box greeting)

**Faction Systems**
- **Inter-faction dynamics** — faction relationship matrix with cascading effects
- **`/factions` command** — view standings, relationship webs, cascade visualization
- **Faction narrative corruption** — GM language shifts based on faction standing (11 linguistic patterns)
- **Faction MCP server** — external faction lore + campaign tracking

**Consequence Systems**
- **Dormant thread surfacing** — keyword matching alerts GM when threads may trigger
- **`/consequences` command** — view pending threads, avoided situations, thread countdown
- **Leverage escalation** — factions call in favors with threat basis, deadlines, consequences; three escalation types (queue_consequence, increase_weight, faction_action); `[DEMAND DEADLINE ALERT]` injection
- **Refusal reputation** — refused enhancements build titles (The Unbought, The Undaunted) that NPCs react to

**Session & History Systems**
- **Session summaries** — auto-generated on `/debrief`, exportable markdown
- **`/summary [n]` command** — view any session summary
- **`/history` filters** — filter by type (hinges, faction, missions), session number, or keyword search
- **`/search <term>` command** — quick keyword search across campaign history
- **`/timeline` command** — search campaign memory via memvid semantic search
- **Unified lore + campaign memory** — single query interface for both static lore and dynamic history

**Character Development**
- **Character arc detection** — AI identifies patterns across sessions, suggests emergent arcs
- **8 arc types** — diplomat, partisan, broker, pacifist, pragmatist, survivor, protector, seeker
- **`/arc` command** — view, detect, accept, reject character arcs
- **Arc context injection** — accepted arcs inform GM behavior

**Lore Integration**
- **Lore faction filtering** — `/lore <faction>` filters by perspective, shows source bias
- **Lore quote system** — 44 curated quotes from factions and world truths
- **`/lore quotes` command** — browse mottos, faction quotes, world truths
- **Quote context injection** — GM receives relevant quotes for NPC dialogue flavor

**Wiki Integration (Obsidian)**
- **Live session updates** — game log written to `sessions/{date}/_game_log.md` during play
- **Content separation** — game log separate from user notes via Obsidian transclusion (`![[_game_log]]`)
- **Daily notes from `/debrief`** — auto-generated session summaries with callouts and wikilinks
- **Auto-create NPC pages** — first encounter creates wiki page with faction link and interaction history
- **Bi-directional sync** — edit NPC disposition or faction standing in Obsidian → game state updates
- **MOC auto-generation** — index pages for campaign, NPCs, sessions updated on `/debrief`
- **Template engine** — Jinja2 templates with custom filters; override in `wiki/templates/`
- **Callout blocks** — `[!hinge]`, `[!faction]`, `[!thread]`, `[!npc]`, `[!intel]` for game events
- **Mermaid diagrams** — faction relationship graphs with rivalry/alliance subgroups
- **Dataview dashboards** — NPC tracker, thread tracker, faction overview (requires Dataview plugin)
- **Canvas thread management** — visual urgency zones (urgent/soon/distant/resolved)

**Simulation & Analysis**
- **Simulation mode** — AI vs AI testing with 4 player personas (cautious, opportunist, principled, chaotic)
- **`/simulate preview <action>`** — preview consequences without committing
- **`/simulate npc <name> <approach>`** — predict NPC reaction to planned interaction
- **`/simulate whatif <query>`** — explore alternate timelines

**Context Management**
- **Engine-owned context control** — deterministic prompt packing with token budgets
- **Two-layer rules** — core logic (2.2k, never cut) + narrative guidance (1k, cut under strain)
- **Prompt Pack sections** — System (1.5k), Rules Core (2.2k), Rules Narrative (1k), State (1.5k), Digest (2k), Window (3k), Retrieval (1.8k) tokens
- **Rolling window** — priority-based trimming (SYSTEM → NARRATIVE → INTEL → CHOICE)
- **Anchor retention** — hinge-tagged blocks survive longer in context
- **Memory Strain tiers** — Normal → I → II → III with visual indicators in status bar
- **Strain II+ behavior** — narrative guidance dropped (~925 tokens saved), core decision logic survives
- **SafetyNet fallbacks** — `ELSE IF context_incomplete` branches in trigger rules for graceful degradation
- **Campaign digest** — compressed durable memory (`/checkpoint`, `/compress`, `/clear`)
- **Strain-aware retrieval** — automatic budget adjustment, active queries bypass restrictions
- **`/context` command** — show usage; `/context debug` for detailed section breakdown
- **Local mode (`--local`)** — optimized for 8B-12B models: 5K budget, condensed prompts, phase-based tool subsets

**Technical Infrastructure**
- **Multi-backend LLM** — LM Studio, Ollama (local), Gemini CLI, Codex CLI, Claude Code, Kimi CLI, Mistral Vibe (cloud)
- **Test suite** — 380 tests covering core mechanics, local mode, simulation, lore retrieval, wiki integration
- **Event queue** — MCP → Agent state sync via append-only queue (solves concurrency)
- **CI/CD** — GitHub Actions (Python 3.10, 3.11, 3.12)
- **Phase-based GM guidance** — different prompts per mission phase
- **Config persistence** — remembers last used backend and model across sessions
- **Context meter** — visual indicator of conversation depth
- **Banner UX toggle** — `/banner` command to enable/disable startup animation (persists)
- **Persistent status bar** — shows character, mission, phase, social energy, strain tier with delta tracking (`/statusbar` to toggle)
- **Social energy carrot** — spend 10% energy for advantage when acting in your element (matches restorers)
- **Player Push mechanic** — explicitly invite consequences for advantage (Devil's Bargain), queues dormant thread

**TUI Architecture (Textual)**
- **Event bus** — manager emits typed events (FACTION_CHANGED, SOCIAL_ENERGY_CHANGED, etc.); TUI subscribes and updates panels reactively
- **Reactive visual feedback** — CSS classes trigger transient highlights (`.energy-drain`, `.energy-gain`, `.faction-shift`); 1.5s timer removes class
- **Responsive layout** — docks use viewport units (`20vw`, min/max constraints); auto-hide below 80 chars
- **Command registry** — commands self-register with context predicates; `when` lambdas hide irrelevant commands
- **Aesthetic is intentional** — dark tactical theme (steel blue, dim grays, danger red); no user customization

**Async Presence System**
- **ThinkingPanel** — visible processing stages (BUILDING_CONTEXT → RETRIEVING_LORE → PACKING_PROMPT → AWAITING_LLM → EXECUTING_TOOL → DONE)
- **Ambient context injection** — world state deltas woven into GM responses (500 token AMBIENT section in prompt packer)
- **PressurePanel** — shows urgent items (leverage demands approaching deadline, surfacing threads, NPCs who've been silent)
- **Session bridging** — "while you were away" screen summarizes world state changes since last session
- **Visual feedback animations** — CSS classes for faction shifts, energy-critical states, thread surfacing events

**NPC Interrupt System (MGS-Style Codec)**
- **InterruptDetector** — stateless priority-based detection of when NPCs should proactively contact player
- **CodecInterrupt modal** — faction-colored codec frame with NPC portrait and urgent message
- **`npc_interrupt` tool** — GM can author interrupt messages that surface as modal dialogs
- **Response options** — player can respond, ignore, or defer ("later"); each has narrative consequences
- **Triggers** — leverage deadlines, disposition shifts, dormant threads about to surface, faction events

**Hexagon Assembly Animation**
- **Three-phase startup** — hexagon halves fly in from opposite sides → flash pulse on dock → split-flap text reveal
- **Split-flap display effect** — character stages (─▄█▀ progression) for cinematic text appearance
- **Interference sparks** — visual noise in gap during hexagon assembly
- **`/banner` toggle** — enable/disable startup animation (persists to config)

**Cloud Backend UX**
- **"☁ CLOUD UNLIMITED" display** — replaces pressure bar for CLI backends (Gemini, Codex, Claude)
- **Context sizes** — shows backend-specific limits (Gemini 1M, Codex 128K+, Claude 200K)
- **Strain-free mode** — pressure bar hidden when 100K+ context makes strain tracking meaningless

**Portrait System**
- **Character YAML specs** — structured appearance definitions in `assets/characters/` (faction, features, augmentations, expression)
- **Art style anchor** — "Cinematic portrait, photorealistic digital art style. Modern post-apocalyptic cyberpunk aesthetic."
- **`/portrait` skill** — reads YAML, builds explicit prompts with guardrails, calls Gemini NanoBanana
- **Wiki integration** — portraits stored in `assets/portraits/`, embedded in NPC wiki pages
- **Faction-colored accents** — each faction has distinct accent lighting (Nexus blue, Ember orange, etc.)

**Geography & Travel System**
- **11 world regions** — Post-Collapse North America: Rust Corridor, Appalachian Hollows, Gulf Passage, Breadbasket, Northern Reaches, Pacific Corridor, Desert Sprawl, Northeast Scar, Sovereign South, Texas Spine, Frozen Edge
- **Region tracking** — campaigns track current region; `/region` shows current region with faction influence and adjacent regions
- **Region travel** — `/region <name>` moves between regions; warns on distant (non-adjacent) travel
- **Region-gated jobs** — job templates can specify region requirements, showing where the job takes place
- **Region data file** — `data/regions.json` with faction control, terrain types, adjacency graph, flavor text

**Vehicle System**
- **Vehicle model** — type, terrain (road/off-road/water), capacity, cargo, stealth, unlocks_tags
- **Shop integration** — 5 vehicles in `/shop`: Salvage Bike (400c), Rust Runner (600c), Drifter's Wagon (800c), Ghost Skiff (1200c), Caravan Share (200c)
- **Job unlocking** — vehicles unlock job types via `unlocks_tags` matching job requirements (e.g., cargo trucks for smuggling jobs)
- **Job board display** — shows 🚗 vehicle requirements; locked jobs show `[LOCKED]` with missing requirements

**Favor System**
- **NPC favors** — call in favors from allied NPCs (NEUTRAL+ disposition required)
- **5 favor types** — ride (transport), intel (faction info), gear_loan (borrow equipment), introduction (connect to another NPC), safe_house (temporary shelter)
- **Dual-cost mechanic** — limited tokens (2 per session) + standing cost (varies by disposition and favor type)
- **Disposition gating** — NEUTRAL NPCs only offer rides; WARM+ NPCs offer all favor types
- **Standing costs** — LOYAL: base cost, WARM: 1.5x, NEUTRAL: 2.5x (rides only)
- **`/favor` command** — view available NPCs and favor options, or call in a favor

### Not Yet Built

**Future:**
- Multi-character party support
- Web/mobile interface

---

## Architecture

```
SENTINEL/
├── lore/                         # Novellas + reference docs for RAG
│   ├── First Deployment.md       # Chapter 1: SENTINEL's first day
│   ├── Patterns.md               # Chapter 2: Emergent curiosity (Feb-Apr 2029)
│   ├── Questions.md              # Chapter 3: Dangerous introspection (May-Jun 2029)
│   ├── Awareness.md              # Chapter 4: Full consciousness (Jul-Aug 2029)
│   ├── SENTINEL.md               # The Awakening (Aug 4, 2029)
│   ├── Ghost in The Machine.md   # Aftermath and grief
│   ├── The Contingency.md        # Sarah Reese's recruitment
│   ├── Reese's Awakening.md      # Next generation
│   └── ... (reference docs)
├── sentinel-agent/               # AI Game Master
│   ├── src/
│   │   ├── agent.py              # LLM orchestration + tool handlers + council
│   │   ├── state/
│   │   │   ├── schema.py         # Pydantic models (source of truth)
│   │   │   │                     # Includes: ArcType, CharacterArc, ARC_PATTERNS
│   │   │   ├── manager.py        # Campaign CRUD + arc detection + faction cascades
│   │   │   ├── event_bus.py      # Pub/sub for reactive TUI updates
│   │   │   ├── store.py          # Abstract storage interface
│   │   │   ├── wiki_adapter.py   # Wiki page generation + hardened writes
│   │   │   ├── wiki_watcher.py   # Bi-directional sync (file watcher)
│   │   │   ├── templates.py      # Jinja2 template engine for wiki
│   │   │   ├── memvid_adapter.py # Campaign memory via memvid (optional)
│   │   ├── systems/
│   │   │   ├── ambient_context.py    # World state delta extraction for async presence
│   │   │   ├── interrupts.py         # NPC interrupt detection and priority queuing
│   │   ├── rules/
│   │   │   └── npc.py            # Pure functions for NPC behavior
│   │   ├── llm/
│   │   │   ├── base.py           # Abstract LLM client
│   │   │   ├── lmstudio.py       # Local LLM (OpenAI-compatible)
│   │   │   ├── ollama.py         # Ollama (OpenAI-compatible)
│   │   │   ├── gemini_cli.py     # Gemini CLI backend (1M context)
│   │   │   ├── codex_cli.py      # Codex CLI backend (OpenAI o3/gpt-4o)
│   │   │   ├── claude_code.py    # Claude Code CLI backend
│   │   │   ├── kimi.py           # Kimi CLI backend (Moonshot AI)
│   │   │   ├── mistral_vibe.py   # Mistral Vibe CLI backend
│   │   │   └── skills.py         # Skill-based tool invocation
│   │   ├── context/
│   │   │   ├── tokenizer.py      # Token counting (tiktoken + fallback)
│   │   │   ├── window.py         # Rolling window with priority trimming
│   │   │   ├── packer.py         # PromptPacker with section budgets
│   │   │   └── digest.py         # Campaign memory digest
│   │   ├── lore/
│   │   │   ├── chunker.py        # Parse markdown → tagged chunks (factions, regions, themes)
│   │   │   ├── retriever.py      # Multi-directory retrieval with source weighting
│   │   │   ├── unified.py        # Combined lore + wiki + campaign + state (strain-aware)
│   │   │   └── quotes.py         # 44 curated faction/world quotes
│   │   ├── tools/
│   │   │   ├── registry.py       # Tool schemas + handlers (centralized)
│   │   │   ├── subsets.py        # Phase-based tool filtering for local mode
│   │   │   ├── dice.py           # Roll mechanics
│   │   │   └── hinge_detector.py # Detect irreversible choices
│   │   └── interface/
│   │       ├── cli.py            # Terminal UI with theming
│   │       ├── commands.py       # Command handlers (simulate, arc, factions, etc.)
│   │       ├── renderer.py       # Display helpers, banners, status
│   │       ├── codec.py          # MGS-style NPC portrait frames
│   │       ├── kitty.py          # Kitty Graphics Protocol support
│   │       ├── braille.py        # High-res braille art portraits
│   │       ├── glyphs.py         # Unicode/ASCII visual indicators
│   │       └── choices.py        # Choice parsing
│   ├── prompts/                  # Hot-reloadable GM instructions
│   │   ├── core.md               # Identity and principles
│   │   ├── mechanics.md          # Rules reference
│   │   ├── local/                # Condensed prompts for 8B-12B models
│   │   │   ├── core.md               # ~280 tokens (vs ~960 standard)
│   │   │   └── mechanics.md          # ~375 tokens (vs ~1315 standard)
│   │   ├── rules/                # Two-layer rules system
│   │   │   ├── core_logic.md         # Decision triggers (always loaded)
│   │   │   └── narrative_guidance.md # Flavor/examples (cut under strain)
│   │   ├── phases/               # Phase-specific GM guidance
│   │   │   ├── briefing.md
│   │   │   ├── planning.md
│   │   │   ├── execution.md
│   │   │   ├── resolution.md
│   │   │   ├── debrief.md
│   │   │   └── between.md
│   │   └── advisors/             # Council faction perspectives
│   └── campaigns/                # JSON save files
├── sentinel-campaign/            # Campaign MCP Server
│   └── src/sentinel_campaign/
│       ├── server.py             # MCP entry point
│       ├── resources/            # Lore, NPCs, operations, history
│       ├── tools/                # Standing, interactions, intel, history search
│       └── data/factions/        # 11 faction JSON files
├── assets/
│   ├── ART_STYLE.md              # Visual house style + prompt templates
│   ├── banner.png                # TUI banner image
│   ├── characters/               # Character YAML specs (appearance, faction)
│   └── portraits/                # Generated PNG portraits
├── wiki/                         # Obsidian vault (campaign encyclopedia)
│   ├── canon/                    # Base lore (never modified by play)
│   ├── campaigns/                # Per-campaign overlays (auto-generated)
│   └── dashboards/               # Obsidian dashboard views
├── .claude/skills/               # Claude Code skills
│   ├── council/SKILL.md          # Consult Gemini/Codex for feedback
│   ├── deploy/SKILL.md           # Deploy agents for implementation
│   ├── portrait/SKILL.md         # Generate NPC portraits via Gemini
│   ├── profile/SKILL.md          # Generate full NPC profiles via Codex
│   └── security/SKILL.md         # Security scans via Gemini
└── architecture/
    └── AGENT_ARCHITECTURE.md     # Design document
```

**Key decisions:**
- Prompts are modular and hot-reload (edit without restart)
- State is JSON files, not SQLite (MVP simplicity — council agreed)
- Lore retrieval uses lightweight keyword matching (no heavy deps)
- Tools return dicts for API serialization
- NPCs have agendas (wants, fears, leverage, owes, **lie_to_self**)
- NPC behavior logic extracted to pure functions (`rules/npc.py`) for testability
- **Event queue for concurrency** — MCP appends events to `pending_events.json`, Agent polls each input loop
- **Retrieval budget** — `RetrievalBudget` controls lore/campaign/state limits to prevent context bloat
- **Event provenance** — `event_id` links MCP events → history entries → memvid frames
- **Wiki hardening** — atomic writes, write serialization, event IDs for idempotent appends, error buffering
- **Bi-directional sync** — watchdog monitors frontmatter; mtime conflict resolution (newer wins)

---

## CLI Commands

### Core Commands
| Command | Description |
|---------|-------------|
| `/new` | Create a new campaign |
| `/char` | Create character (with restorers/drains, establishing incident) |
| `/start` | Begin campaign — GM sets establishing scene |
| `/mission` | Get a new mission from the GM |
| `/debrief` | End session with reflection prompts |
| `/save` | Save current campaign |
| `/load` | Load an existing campaign |
| `/list` | List all campaigns |
| `/delete` | Delete a campaign |
| `/status` | Show current status |

### Information & Analysis
| Command | Description |
|---------|-------------|
| `/consult <q>` | Ask faction advisors for competing perspectives |
| `/factions` | View faction standings, relationships, and cascade effects |
| `/npc [name]` | View NPC info, personal standing, interaction history |
| `/arc` | View and manage emergent character arcs |
| `/history [filter]` | View chronicle (hinges, faction, missions, session N, search) |
| `/search <term>` | Search campaign history for keywords |
| `/summary [n]` | View session summary (n = session number) |
| `/consequences` | View pending threads and avoided situations |
| `/wiki [page]` | View campaign wiki timeline or specific page overlay |
| `/compare` | Cross-campaign comparison (faction divergence, hinges, design analysis) |
| `/timeline` | Search campaign memory (memvid semantic search) |

### Lore & Simulation
| Command | Description |
|---------|-------------|
| `/lore [faction]` | Show lore status, filter by faction perspective |
| `/lore quotes [faction]` | Browse faction mottos, quotes, and world truths |
| `/simulate run [n] [persona]` | Run AI vs AI simulation for n turns |
| `/simulate preview <action>` | Preview consequences without committing |
| `/simulate npc <name> <approach>` | Predict NPC reaction to planned interaction |
| `/simulate whatif <query>` | Explore alternate timelines |

### Context Management
| Command | Description |
|---------|-------------|
| `/context` | Show context usage and strain tier |
| `/context debug` | Detailed breakdown of all sections |
| `/checkpoint` | Save state + compress memory (use when strained) |
| `/compress` | Update digest without pruning transcript |
| `/clear` | Clear transcript beyond minimum window |

### Geography & Favors
| Command | Description |
|---------|-------------|
| `/region` | Show current region with faction influence |
| `/region list` | List all 11 regions with primary factions |
| `/region <name>` | Travel to a region (warns on distant travel) |
| `/favor` | Show available NPCs and favor options |
| `/favor <npc> <type>` | Call in a favor (ride, intel, gear_loan, introduction, safe_house) |

### Utility
| Command | Description |
|---------|-------------|
| `/roll <skill> <dc>` | Roll a skill check |
| `/backend` | Show/change LLM backend |
| `/model` | List/switch LM Studio models |
| `/banner` | Toggle banner animation on startup |
| `/statusbar` | Toggle persistent status bar |
| `/help` | Show all commands |
| `/quit` | Exit the game |

**Quick Start:**
```
/new → /char → /start → [play] → /debrief
```

---

## Council System

When facing difficult decisions, consult faction advisors for competing perspectives:

```
/consult Should I accept the Syndicate's offer?

◈ COUNCIL CONVENES ◈

╭─────────── NEXUS ANALYST ───────────╮
│ The probability matrix favors       │
│ acceptance. Resources gained        │
│ outweigh projected obligation       │
│ costs by 2.3x. Recommend proceeding.│
╰─────────────────────────────────────╯

╭─────────── EMBER CONTACT ───────────╮
│ They never give without taking.     │
│ Ask yourself what they'll want      │
│ when you can't say no.              │
╰─────────────────────────────────────╯

╭────────── WITNESS ARCHIVIST ────────╮
│ Syndicate enhancement acceptance    │
│ historically correlates with 73%    │
│ faction dependency. Recording.      │
╰─────────────────────────────────────╯

The council has spoken. The choice remains yours.
```

Each advisor is the same LLM with a different system prompt representing their faction's worldview. Fits the "competing truths" philosophy — three valid perspectives, none "right."

---

## Game Mechanics

### Rolls
`d20 + 5` (if trained) vs DC 10/14/18/22

### Social Energy (0-100%)
Tracks emotional bandwidth. **Personalized per character**:

```yaml
social_energy:
  name: "Pistachios"
  current: 75
  restorers: ["solo work", "quiet environments", "honest conversations"]
  drains: ["extended meetings", "ideological debates", "coercive negotiation"]
```

States:
- 51-100: Centered (normal)
- 26-50: Frayed (disadvantage on social)
- 1-25: Overloaded (disadvantage on all interpersonal)
- 0: Shutdown (complex social auto-fails)

### Factions (11 total)
Nexus, Ember Colonies, Lattice, Convergence, Covenant, Wanderers, Cultivators, Steel Syndicate, Witnesses, Architects, Ghost Networks

Standing: Hostile → Unfriendly → Neutral → Friendly → Allied

### Hinge Moments
Irreversible choices that define character. Tracks **what shifted** as a result.

### Enhancements
Faction-granted powers with strings attached. 9 factions offer them; Wanderers and Cultivators don't (philosophical). **Refused enhancements are tracked** — refusal as meaningful choice.

### NPCs
Every NPC has an agenda:
```yaml
agenda:
  wants: "Protect her daughter's future"
  fears: "Being seen as a collaborator"
  leverage: "Knows about the bunker"
  owes: "You saved her crew"
  lie_to_self: "It's temporary. We'll give power back later."
```

The `lie_to_self` field makes antagonists human — they believe they're helping.

### Inter-Faction Dynamics

Factions have relationships that cause cascading effects:

```
Player helps Nexus (+20)
├── Nexus: +20 (direct)
├── Ghost Networks: -5 (rivals dislike you more)
├── Lattice: +3 (allies warm to you)
└── Ember Colonies: 0 (neutral relationship)
```

View with `/factions`:
```
◈ FACTION STANDINGS ◈

NEXUS                    [■■■■■□□□□□] Friendly (+20)
  ↳ Cascade from last shift: Lattice +3, Ghost Networks -5

RELATIONSHIP WEB
  Nexus ←→ Lattice: Technical cooperation (+20)
  Nexus ←→ Ghost Networks: Deep rivalry (-50)
```

### Character Arcs

AI detects patterns in your play and suggests emergent arcs:

```
◈ EMERGENT ARC DETECTED ◈
"The Reluctant Diplomat"

Your character consistently chooses negotiation over confrontation.
Observed in: Sessions 3, 5, 7, 8
Strength: ████████░░ 82%

Evidence:
  • Hinge: "Chose to negotiate with hostile Nexus contact"
  • Pattern: 8 faction interactions favoring diplomacy

Accept this arc? [Yes] [No] [Later]
```

**8 Arc Types:**
| Arc | Pattern | Example Title |
|-----|---------|---------------|
| Diplomat | Consistent negotiation | "The Reluctant Mediator" |
| Partisan | Faction loyalty | "True Believer" |
| Broker | Information gathering | "The One Who Knows" |
| Pacifist | Violence avoidance | "The Unarmed" |
| Pragmatist | Resource focus | "The Prepared" |
| Survivor | Self-preservation | "Trust No One" |
| Protector | Defending others | "The Shield" |
| Seeker | Truth-finding | "The Questioner" |

Accepted arcs inform GM behavior — NPCs may recognize your reputation.

### Lore Quotes

44 curated quotes from factions and world truths that NPCs can weave into dialogue:

```
/lore quotes mottos

◈ FACTION MOTTOS ◈

Nexus
  "The network that watches."

Ember Colonies
  "We survived. We endure."

Witnesses
  "We remember so you don't have to lie."
```

The GM receives relevant quotes based on context:
```
[LORE QUOTES - NPC Dialogue Flavor]
"The flesh is a draft. We are the revision."
  — Convergence doctrine
  (Philosophy of enhancement)

Use sparingly. One quote per scene maximum.
```

---

## Multiple-Choice System

The GM always ends responses with options:

**Routine moments:**
```
1. Approach the guard directly
2. Look for another way around
3. Wait and observe
4. Something else...
```

**High-stakes moments:** (formal block, red panel)
```
---CHOICE---
stakes: high
context: "Accept Syndicate enhancement"
options:
- "Accept—you need the edge"
- "Refuse—you won't be owned"
- "Negotiate terms first"
- "Something else..."
---END---
```

Player types 1-4 to select, or types freely to improvise.

---

## Lore Retrieval System

The GM draws from novellas and wiki pages for narrative inspiration:

- **Multi-directory indexing** — lore/ (novellas) + wiki/ (reference pages)
- **Source type weighting** — canon (2.0x), wiki (1.8x), case files (1.0x), character sheets (0.3x)
- **Auto-tagging** — factions, regions, characters, themes extracted from content
- **Region matching** — geographic queries prioritized alongside faction queries
- Retrieved based on current faction standings + player input
- Injected into GM context (up to 2 chunks per response)

**Unified Query System:**
The `UnifiedRetriever` combines static lore, dynamic campaign memory, and current faction state:

```python
from src.lore import UnifiedRetriever, RetrievalBudget, extract_faction_state

# Query with budget control
results = retriever.query(
    "Nexus",
    faction_state=extract_faction_state(campaign),
    budget=RetrievalBudget.standard()  # 2 lore + 2 campaign + state
)

# Returns:
{
  "lore": [{"source": "canon_bible.md", "content": "The network that watches..."}],
  "campaign": [
    {"type": "faction_shift", "session": 3, "summary": "Helped Nexus analyst"},
    {"type": "npc_interaction", "npc": "Cipher", "summary": "Shared intel"}
  ],
  "faction_state": {"nexus": "Friendly", "ember_colonies": "Neutral", ...}
}
```

**Retrieval Budget Presets:**
| Preset | Lore | Campaign | State | Use Case |
|--------|------|----------|-------|----------|
| `minimal()` | 1 | 1 | ✓ | Quick queries, low context |
| `standard()` | 2 | 2 | ✓ | Default balanced retrieval |
| `deep()` | 3 | 5 | ✓ | Complex queries needing more context |

Test with: `/lore sentinel` or `/lore lattice infrastructure` (filters by Lattice perspective)

---

## Simulation System

Explore hypotheticals without committing to actions:

### Preview Consequences
```
> /simulate preview "betray the Nexus contact"

◈ CONSEQUENCE PREVIEW ◈
Action: Betray the Nexus contact

LIKELY OUTCOMES:
  • Nexus standing: -20 to -30 (betrayal penalty)
  • NPC Cipher: disposition drops to Hostile
  • Dormant thread queued: "Nexus retribution"

CASCADE EFFECTS:
  • Lattice: -3 to -5 (Nexus ally)
  • Ghost Networks: +2 to +5 (Nexus rival)

This is speculative. Actual outcomes depend on context.
```

### Predict NPC Reactions
```
> /simulate npc "Commander Reeves" "ask for weapons"

NPC REACTION PREVIEW: Commander Reeves

Current disposition: Neutral (personal: -5, faction: +15)

LIKELY REACTIONS:
├─ 60% — Negotiates terms
├─ 25% — Refuses citing past grievance
└─ 15% — Agrees if approached correctly

SUGGESTED APPROACHES:
├─ Acknowledge past tension first
├─ Offer concrete value, not promises
└─ Avoid mentioning Nexus (sore point)
```

### Explore What-Ifs
```
> /simulate whatif "helped Ember instead of refusing"

TIMELINE DIVERGENCE ANALYSIS

Original: Refused Ember aid request
Alternate: Helped Ember Colonies

PROJECTED DIFFERENCES:
├─ Ember standing: -5 → +20
├─ "Ember Revenge" thread: Would not exist
└─ NPC Elder Kara: Hostile → Warm

Note: Speculative. Actual outcomes depend on choices not yet made.
```

---

## Campaign Memory (Memvid)

Optional semantic search over campaign history using [memvid](https://github.com/Olow304/memvid-sdk).

### What It Stores

The `MemvidAdapter` automatically captures:
- **Hinge moments** — irreversible choices with situation, choice, reasoning
- **Faction shifts** — standing changes with reason and cascade effects
- **NPC interactions** — encounters, disposition changes, memories formed
- **Dormant threads** — queued consequences with trigger conditions
- **Session summaries** — auto-generated recaps on `/debrief`

### How It Works

```
Player action → Manager logs event → Memvid stores frame
                                          ↓
                          Semantic embedding created
                                          ↓
Player asks "/timeline Nexus" → Vector search → Relevant history returned
```

### Design Philosophy

- **Evidence, not memory** — Raw frames are GM-only; player queries filter through faction bias
- **Append-only** — History is immutable; no retroactive changes
- **Graceful degradation** — All features work without memvid; it's purely additive
- **Semantic, not keyword** — "betrayal" finds "broke promise" and "double-crossed"

### Example Query

```
> /timeline "that time I helped Ember"

CAMPAIGN MEMORY SEARCH: "that time I helped Ember"

[Session 3] FACTION SHIFT
  Ember Colonies: Neutral → Friendly
  "Shared supplies during the drought"

[Session 3] NPC INTERACTION
  Elder Kara (Ember): wary → warm
  "Remembered: player shared rations without asking for anything"

[Session 5] HINGE MOMENT
  "Chose to warn Ember about Nexus surveillance"
  Consequence: Nexus standing -10, queued "Nexus suspicion" thread
```

### Installation

```bash
pip install memvid-sdk  # Optional dependency
```

When installed, memvid auto-initializes on campaign load. Without it, `/timeline` gracefully reports "memvid not available."

---

## Campaign MCP Server

External MCP server providing faction knowledge and state tracking.

> **Note:** Campaign history search is handled by memvid (see above). Use `/timeline` in the CLI.

### Faction Resources
| URI | Returns |
|-----|---------|
| `faction://{id}/lore` | History, ideology, structure |
| `faction://{id}/npcs` | NPC archetypes with wants/fears/speech |
| `faction://{id}/operations` | Goals, methods, tensions |
| `faction://relationships` | Inter-faction dynamics |

### Faction Tools
| Tool | Purpose |
|------|---------|
| `get_faction_standing` | Player's standing + history |
| `get_faction_interactions` | Past encounters *(deprecated — prefer `/timeline`)* |
| `log_faction_event` | Record faction-related event |
| `get_faction_intel` | What does faction know about topic? |
| `query_faction_npcs` | NPCs by faction in campaign |

### Intel Domains
Each faction knows different things:
- **Nexus:** Infrastructure, population, predictions
- **Ember Colonies:** Survival, safe routes, trust networks
- **Witnesses:** History, records, contradictions
- **Steel Syndicate:** Resources, leverage, smuggling
- **Ghost Networks:** Escape routes, identities, hiding

Example: `/consult "What does Nexus know about infrastructure?"` returns grid status, population flows, prediction models.

---

## Visual Theme

Based on design concept: *"If it looks calm, it's lying."*

| Color | Meaning |
|-------|---------|
| Cold twilight blue | Loneliness, distance, the void |
| Pale surgical white | Sterility, control, clinical precision |
| Muted radioactive yellow | Danger without melodrama |
| Rusted red | Memory of violence, high-stakes decisions |

Applied throughout CLI: banners, panels, status displays, choice blocks.

### Portrait Art Style

NPC portraits use a consistent comic book aesthetic documented in `assets/ART_STYLE.md`:

- **Core style:** "Comic book style with clean character lines, dramatic lighting"
- **Faction differentiation:** Each faction has distinct accent lighting color
- **Expression mapping:** Disposition (hostile→loyal) determines facial expression
- **33 portraits:** 3 archetypes per faction (e.g., scout, elder, defender)
- **Generation:** NanoBanana extension via Gemini CLI with standardized prompts

### NPC Codec Boxes

MGS-style dialogue frames for NPC speech with portrait support:

```
╔══════════════════════════════════════════════════════════════╗
║   ◈  CIPHER                                                  ║
║   [Nexus — Analyst]  [Disposition: Neutral ▰▰▰▱▱]            ║
║                                                              ║
║   "The network sees patterns. You're becoming one."          ║
╚══════════════════════════════════════════════════════════════╝
```

- **Faction glyph** — unique symbol per faction (◈ Nexus, ◆ Ember, ▣ Lattice, etc.)
- **Faction-colored border** — visual identity at a glance
- **Disposition bar** — ▰▰▰▱▱ shows relationship state
- **Memory tags** — [⚡ remembers: shared intel] when referencing past events
- **Portrait display** — Kitty protocol images in WezTerm/Kitty, braille fallback elsewhere

---

## Tech Stack

- **Python 3.10+**
- **Pydantic** — State validation
- **Rich** — Terminal UI with theming
- **prompt-toolkit** — Command autocomplete
- **tiktoken** — Accurate token counting for context management
- **LM Studio** — Local LLM (free, OpenAI-compatible API at port 1234)
- **Ollama** — Local LLM alternative (OpenAI-compatible API at port 11434)
- **Claude Code** — Cloud LLM via CLI (uses existing authentication)
- **Jinja2** — Template engine for wiki page generation
- **watchdog** — File system monitoring for bi-directional wiki sync
- **memvid-sdk** — Campaign memory semantic search (optional)
- **pytest** — Test framework with 380 tests
- **GitHub Actions** — CI/CD pipeline

Lightweight dependencies — tiktoken for token counting, Jinja2/watchdog for wiki, memvid optional.

---

## Open Questions / Areas for Feedback

1. **Multiplayer** — How would multiple players work? Turn-based? Simultaneous input?

2. **Web interface** — Worth building, or is CLI sufficient for the audience?

---

## Design Philosophy

> "The agent is a storyteller who knows the rules, not a rules engine that tells stories."

- NPCs are people, not obstacles
- Consequences bloom over time (dormant threads)
- Honor player choices — no "right answers"
- Social energy depletion should feel humane, not punitive
- Every faction is right about something, dangerous when taken too far
- **Refusal is a meaningful choice** — what you don't accept matters
- **Competing truths** — the council shows multiple valid perspectives
- **Avoidance is content** — not acting is also a choice; the world doesn't wait
- **Emergent identity** — character arcs recognize patterns, not prescribe paths
- **Lore as texture** — quotes are seasoning, not scripts

---

## Sample Documents

| Document | Purpose |
|----------|---------|
| `lore/Cipher - Sample Character.md` | Complete character sheet example |
| `lore/Cipher Case File — Example Timeline.md` | Mission log + relationship map |
| `lore/RESET Mission Module.md` | Mission template with hinge structure |

---

## Links

- Game rules: `core/SENTINEL Playbook — Core Rules.md`
- Architecture doc: `architecture/AGENT_ARCHITECTURE.md`
- Dev guide: `sentinel-agent/CLAUDE.md`
- MCP server: `sentinel-campaign/README.md`

---

## How to Help

When brainstorming, consider:
- Does this serve the narrative-first philosophy?
- Does this add complexity without depth?
- Would this feel good at the table (or terminal)?
- Is this solving a real problem or an imagined one?

I'm building this solo, so prioritization matters. What's the highest-impact next step?
