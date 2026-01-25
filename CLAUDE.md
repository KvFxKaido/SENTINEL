# CLAUDE.md

Context for AI assistants working on the SENTINEL project.

## Project Structure

```
SENTINEL/
├── core/                    # Game design documents
│   └── SENTINEL Playbook — Core Rules.md
├── architecture/            # Technical design
│   ├── AGENT_ARCHITECTURE.md
│   ├── sentinel_warp_vision.md
│   └── npc_codec_prototype.py
├── sentinel-agent/          # The AI GM implementation
│   ├── CLAUDE.md            # Detailed dev context
│   ├── src/                 # Python source
│   │   ├── state/
│   │   │   ├── schema.py         # Pydantic models (source of truth)
│   │   │   ├── manager.py        # Campaign CRUD + delegation
│   │   │   ├── event_bus.py      # Pub/sub for reactive TUI updates
│   │   │   ├── wiki_adapter.py   # Wiki page generation
│   │   │   ├── wiki_watcher.py   # Bi-directional sync
│   │   │   └── templates.py      # Jinja2 template engine
│   │   ├── systems/              # Domain logic modules
│   │   │   ├── jobs.py           # Job board, templates, lifecycle
│   │   │   ├── favors.py         # NPC favor system
│   │   │   ├── endgame.py        # Readiness tracking, epilogue
│   │   │   ├── leverage.py       # Enhancement demands
│   │   │   └── arcs.py           # Character arc detection
│   │   └── interface/
│   │       ├── tui.py            # Primary Textual-based UI
│   │       ├── tui_commands.py   # TUI command handlers
│   │       └── commands.py       # CLI command handlers
│   ├── data/                # Game data files
│   │   ├── regions.json     # 11 regions with factions, adjacency
│   │   └── jobs/            # Job templates by faction
│   ├── prompts/             # Hot-reloadable prompts
│   │   └── local/           # Condensed prompts for 8B-12B models
│   └── campaigns/           # Save files
├── sentinel-campaign/       # Campaign MCP server
│   ├── src/sentinel_campaign/
│   │   ├── server.py        # MCP entry point
│   │   ├── resources/       # Lore, NPCs, operations
│   │   ├── tools/           # Standing, interactions, intel
│   │   └── data/factions/   # Faction JSON files
│   └── README.md
├── sentinel-bridge/         # Deno orchestration layer (Phase 2)
│   ├── src/
│   │   ├── process.ts       # Sentinel process manager
│   │   ├── api.ts           # Local HTTP API
│   │   ├── types.ts         # Shared TypeScript types
│   │   └── main.ts          # Entry point
│   └── README.md
├── sentinel-ui/             # Astro web interface (Phase 4)
│   ├── src/
│   │   ├── layouts/         # Dark tactical theme
│   │   ├── pages/           # Main game view
│   │   ├── components/      # UI components
│   │   └── lib/bridge.ts    # Bridge API client
│   └── README.md
├── lore/                    # World-building documents (novellas)
└── wiki/                    # Reference encyclopedia (Obsidian vault)
```

## What This Is

SENTINEL is a tactical tabletop RPG about navigating political tension, ethical tradeoffs, and survival under fractured systems. The `sentinel-agent` subdirectory contains an AI Game Master that runs the game.

## Designer Context

Before diving into code, understand who you're working with:

| Resource | Location | Purpose |
|----------|----------|---------|
| Design philosophy | `architecture/design-philosophy.md` | Non-negotiable design principles |
| Personal context | `.claude/personal.md` | Shawn's preferences, communication style (gitignored) |
| MCP resource | `gm://designer` | Query personal context programmatically |

The design philosophy is real — these aren't aspirational guidelines, they're postmortem-driven rules. Read it before proposing architectural changes.

## Key Documents

| Document | Purpose |
|----------|---------|
| `core/SENTINEL Playbook — Core Rules.md` | The complete game rules |
| `architecture/AGENT_ARCHITECTURE.md` | Agent design, state schema, tools |
| `architecture/sentinel_warp_vision.md` | Terminal UI/UX roadmap (Warp + MGS inspired) |
| `architecture/sentinel_cross_platform_implementation_plan.md` | Cross-platform roadmap (Phases 0-6) |
| `sentinel-agent/CLAUDE.md` | Dev guide for Claude assistants |
| `sentinel-agent/GEMINI.md` | Dev guide for Gemini CLI |
| `sentinel-campaign/README.md` | Campaign MCP server (factions, history, tools) |
| `sentinel-bridge/README.md` | Deno bridge for UI integration |
| `sentinel-ui/README.md` | Astro web interface |

## Game Philosophy

**Not about:** min-max optimization, combat dominance, binary morality

**About:** navigating competing truths, sustaining integrity under pressure, relationships as resources, choosing consequences you can live with

**Core loop:** Investigation → Interpretation → Choice → Consequence

## The Eleven Factions

| Faction | Tagline | Intel Domains |
|---------|---------|---------------|
| Nexus | The network that watches | Infrastructure, population, predictions |
| Ember Colonies | We survived. We endure. | Survival, safe routes, trust networks |
| Lattice | We keep the lights on | Infrastructure, supply chains, logistics |
| Convergence | Become what you were meant to be | Enhancement tech, integration research |
| Covenant | We hold the line | Oaths, sanctuary, ethics |
| Wanderers | The road remembers | Trade routes, news, safe passages |
| Cultivators | From the soil, we rise | Food production, seed stocks, land |
| Steel Syndicate | Everything has a price | Resources, leverage, smuggling |
| Witnesses | We remember so you don't have to lie | History, records, contradictions |
| Architects | We built this world | Pre-collapse records, credentials |
| Ghost Networks | We were never here | Escape routes, identities, hiding |

Full faction data available via MCP: `faction://{id}/lore`, `faction://{id}/npcs`, `faction://{id}/operations`

## Unique Mechanics

### Social Energy (Pistachios)
Tracks emotional bandwidth. Depletes on social interaction, restores on solitude. At low levels, social rolls get disadvantage. At zero, complex social auto-fails.

### Hinge Moments
Irreversible choices that define character identity. No mechanical rewards — pure narrative gravity. Must be logged and referenced in future sessions.

### Enhancements
Faction-granted power with strings attached. When you accept an enhancement, the faction gains leverage they can call in later.

### Dormant Threads
Delayed consequences. When a choice has future implications, queue a thread with trigger condition. Surface it when the condition is met.

### NPC Disposition System
NPCs have disposition modifiers that change their behavior:
- **Disposition levels:** hostile → wary → neutral → warm → loyal
- **Modifiers per level:** tone, reveals, withholds, tells
- **Memory triggers:** NPCs react to tagged events (e.g., `helped_ember` shifts Lattice NPCs wary)

### Character Appearance System (Campaign-Isolated)
Each campaign has its own character appearances and portraits for emergent playthroughs:

**Directory Structure:**
```
assets/characters/campaigns/{campaign_id}/{name}.yaml  # Appearance YAML
sentinel-ui/public/assets/portraits/campaigns/{campaign_id}/{name}.png  # Portraits
```

**Auto-generation:** On first `/start`, the GM calls `describe_npc_appearance` to create the player character's YAML automatically.

**Portrait generation:** Use `/portrait <name>` to generate portraits. Portraits are campaign-specific — the same NPC name can look different across campaigns.

**Fallback:** For backward compatibility, the UI checks campaign folder first, then falls back to global `portraits/npcs/` folder.

### Geography System
11 post-Collapse North American regions with faction control:
- **Regions:** Rust Corridor, Appalachian Hollows, Gulf Passage, Breadbasket, Northern Reaches, Pacific Corridor, Desert Sprawl, Northeast Scar, Sovereign South, Texas Spine, Frozen Edge
- **Tracking:** Campaign tracks current region; default is Rust Corridor
- **Commands:** `/region` shows current region; `/region list` shows all; `/region <name>` travels
- **Adjacency:** Regions have adjacent neighbors; distant travel warns about vehicle/favor requirements
- **Data file:** `data/regions.json` with faction control, terrain, adjacency, flavor text

### Vehicle System
Transport that unlocks certain jobs:
- **Vehicle model:** type, terrain (road/off-road/water), capacity, cargo, stealth, unlocks_tags
- **Shop:** 5 vehicles — Salvage Bike (400c), Rust Runner (600c), Drifter's Wagon (800c), Ghost Skiff (1200c), Caravan Share (200c)
- **Job unlocking:** Vehicle `unlocks_tags` match job `requires_vehicle_tags` (e.g., cargo trucks for smuggling)
- **Job board:** Shows 🚗 requirements; locked jobs display `[LOCKED]`

### Favor System
Call in favors from allied NPCs:
- **Favor types:** ride, intel, gear_loan, introduction, safe_house
- **Disposition gating:** NEUTRAL offers rides only; WARM+ offers all types
- **Dual-cost mechanic:** 2 tokens per session + standing cost
- **Standing costs:** LOYAL=base, WARM=1.5x, NEUTRAL=2.5x
- **Command:** `/favor` shows available NPCs; `/favor <npc> <type>` calls favor

### Job Board System
Faction-specific jobs available based on location and standing:
- **Templates:** JSON files in `data/jobs/` with objectives, rewards, requirements
- **Location-aware:** At Faction HQ, see that faction's jobs; at Market, see Wanderer jobs
- **Requirements:** Jobs can require region, vehicle type, or vehicle tags
- **Commands:** `/jobs` lists available; `/jobs accept <n>` accepts; `/jobs status` shows active

### Endgame System
Player-initiated campaign conclusion with multi-factor readiness tracking:
- **Campaign status:** ACTIVE → APPROACHING_END → EPILOGUE → CONCLUDED
- **Readiness factors:** Hinges (30%), arcs (25%), threads (25%), factions (20%)
- **Readiness levels:** early (<40%), developing (40-60%), approaching (60-80%), ready (≥80%)
- **Player goals:** Tracked from debrief fourth question ("What would 'enough' look like?")
- **Epilogue:** Final session surfaces ALL dormant threads; presents culmination hinges
- **Philosophy:** No failure state — "hostile to all factions" is a valid ending
- **Commands:** `/endgame` views readiness; `/endgame begin` starts epilogue; `/retire` is narrative alias

### Memvid Campaign Memory (Optional)
Semantic search over campaign history using [memvid](https://github.com/memvid/memvid). Stores hinges, NPC interactions, faction shifts as queryable frames.
- **Install:** `pip install -e ".[memvid]"` in sentinel-agent
- **Query:** `/timeline` command or `manager.query_campaign_history()`
- **Philosophy:** Evidence, not memory — raw frames are GM-only; player queries filter through faction bias
- **Graceful degradation:** All ops are no-ops if SDK not installed

### Wiki Integration (Obsidian)
SENTINEL auto-generates a campaign wiki as you play, designed for Obsidian.

**Live Updates:**
- Game log written to `sessions/{date}/_game_log.md` during play
- Session summary generated on `/debrief`
- NPC pages created on first encounter
- Timeline (`_events.md`) tracks hinges, faction shifts, threads

**Commands:**
- `/wiki` — Campaign timeline with color-coded events
- `/wiki <page>` — Page overlay (campaign additions to canon)
- `/compare` — Cross-campaign analysis for faction divergence

**Features:**
- **Content separation** — Game log separate from user notes via transclusion (`![[_game_log]]`)
- **Bi-directional sync** — Edit NPC disposition or faction standing in Obsidian → game state updates
- **MOC auto-generation** — Index pages for campaign, NPCs, sessions updated on `/debrief`
- **Custom templates** — Override page layouts in `wiki/templates/` (Jinja2)
- **Obsidian callouts** — Styled blocks for hinges, faction shifts, threads
- **Dataview ready** — YAML frontmatter on all pages for queries

**Directory Structure:**
```
wiki/campaigns/{id}/
├── _index.md           # Campaign MOC
├── _events.md          # Timeline
├── NPCs/
│   ├── _index.md       # NPC index by faction
│   └── {name}.md       # NPC overlay pages
└── sessions/
    ├── _index.md       # Session index
    └── {date}/
        ├── {date}.md       # Session summary
        └── _game_log.md    # Live updates
```

### Local Mode (8B-12B Models)
Optimized context for smaller local models. Run with `--local` flag.
- **Context budget:** 5K tokens (vs 13K standard)
- **Prompts:** Condensed versions in `prompts/local/` (70% smaller)
- **Tools:** Phase-specific subsets (3-12 tools vs 19)
- **Skipped:** Narrative guidance, digest, retrieval sections

Core mechanics and narrative quality remain intact — you lose flavor text, not functionality.

### TUI Architecture (Textual)
The primary interface uses reactive patterns:
- **Event bus** (`state/event_bus.py`) — Manager emits typed events; TUI subscribes and updates panels
- **Reactive feedback** — CSS classes trigger transient highlights (energy drain/gain, faction shifts)
- **Responsive layout** — Viewport units with min/max constraints; auto-hide docks below 80 chars
- **Command registry** — Commands self-register with context predicates

**Aesthetic is intentional:** Dark tactical theme (steel blue, dim grays, danger red). No user customization — the constraints are the identity.

### Web UI Architecture (Astro)
Browser-based alternative to the TUI, connecting via Deno bridge:

```
Astro UI (4321) → HTTP → Deno Bridge (3333) → stdin/stdout → Sentinel (Python)
```

**3-Column Layout:**
- **SELF** (left) — Character stats, loadout, enhancements
- **NARRATIVE** (center) — Conversation log with `> YOU` and `◆ GM` prefixes
- **WORLD** (right) — Faction standings with progress bars, threads, events

**State Flow:**
- `getCampaignState()` returns detailed UI state (character, factions, gear)
- Commands that trigger GM (`/start`, `/mission`) return `response` field
- SSE stream (`/events`) provides real-time event updates
- Backend preference persists to `campaigns/.sentinel_config.json`

**To run:** Start bridge (`deno task dev` in sentinel-bridge), then UI (`npm run dev` in sentinel-ui).

## MCP Server: sentinel-campaign

When enabled, provides faction tools, wiki resources, and campaign state.

### Resources
- `faction://{id}/lore` — History, ideology, structure
- `faction://{id}/npcs` — NPC archetypes with wants/fears/speech
- `faction://{id}/operations` — Goals, methods, tensions
- `faction://relationships` — Inter-faction dynamics
- `wiki://{page}` — Wiki page from canon

### Tools
| Tool | Purpose |
|------|---------|
| `get_faction_standing` | Player's standing + history |
| `get_faction_interactions` | Past encounters this campaign |
| `log_faction_event` | Record faction-related event |
| `get_faction_intel` | What does faction know about topic? |
| `query_faction_npcs` | NPCs by faction in campaign |
| `search_wiki` | Search wiki (canon + campaign overlay) |
| `get_wiki_page` | Get page with overlay merging |
| `update_wiki` | Update campaign wiki overlay |
| `log_wiki_event` | Log event to campaign timeline |

### Wiki Overlay System
Wiki supports per-campaign overlays with bi-directional sync:
```
wiki/
├── canon/           # Base lore (never modified)
├── campaigns/{id}/  # Per-campaign additions (auto-generated)
└── templates/       # User-overridable page templates
```

- **Canon pages:** Source of truth, shared across campaigns
- **Overlay pages:** Campaign-specific additions, auto-generated during play
- **Bi-directional sync:** Edit frontmatter in Obsidian (disposition, standing) → game state updates
- **Template engine:** Jinja2 templates with custom filters (`wikilink`, `npc_link`)
- **Event logging:** `log_wiki_event` creates chronological campaign timeline

### Setup
```bash
cd sentinel-campaign && pip install -e .
```
Configured in `.mcp.json` and enabled in `.claude/settings.local.json`.

---

## Working on This Project

### To modify game rules
Edit `core/SENTINEL Playbook — Core Rules.md`. Then update `sentinel-agent/prompts/mechanics.md` with the condensed reference.

### To modify agent behavior
See `sentinel-agent/CLAUDE.md` for detailed guidance. Key files:
- `prompts/*.md` — GM personality and guidance (hot-reloadable)
- `src/agent.py` — Tool definitions and API orchestration
- `src/state/schema.py` — Data models

### To modify faction data
Edit JSON files in `sentinel-campaign/src/sentinel_campaign/data/factions/`.

### To modify regions or jobs
- **Regions:** Edit `sentinel-agent/data/regions.json` (faction control, adjacency, terrain)
- **Job templates:** Edit JSON files in `sentinel-agent/data/jobs/` (one file per faction)
- **Job requirements:** Add `region`, `requires_vehicle`, `requires_vehicle_type`, or `requires_vehicle_tags` to templates

### To modify vehicles or shop
Edit `SHOP_INVENTORY` and `VEHICLE_DATA` in `sentinel-agent/src/interface/tui_commands.py`.

### To modify favor system
Edit `sentinel-agent/src/systems/favors.py` for costs, disposition rules, or favor types.

### To run the agent
```bash
cd sentinel-agent
pip install -e .
sentinel                  # Textual TUI (recommended)
sentinel-cli              # Dev CLI with simulation
sentinel --local          # For 8B-12B models (reduced context)
```

## AI Collaboration

This project has access to multiple AI agents. **Use them proactively** — don't wait to be asked.

### `/council` — Get External Perspectives
Consults Gemini and Codex for design feedback. Use when:
- Facing architectural decisions with multiple valid approaches
- Uncertain about implementation strategy
- Making changes that affect multiple subsystems
- Design tradeoffs need external perspective

### `/deploy` — Delegate Implementation
Deploys Codex or Gemini as working agents. Use when:
- Task has independent subtasks that can be parallelized
- Well-scoped implementation work can be delegated
- Bulk file operations or repetitive changes needed
- You want a different implementation approach to compare

### `/playtest` — Automated Bug Hunting
Deploys Claude as a player to interact with SENTINEL through the bridge API. Use when:
- After implementing new features or fixing bugs
- Before releases to catch regressions
- Testing edge cases systematically
- Verifying state consistency across game actions

**Requires:** Bridge running at `localhost:3333` with Claude backend.

### `/playtest-web` — Visual UI Testing
Uses Chrome automation to test the web UI visually. Catches bugs that API testing misses:
- Layout issues, CSS bugs, responsive breakpoints
- State display sync (UI not updating after commands)
- Codec frame styling and NPC rendering
- Form interaction and accessibility

**Requires:** Bridge at `localhost:3333` + Web UI at `localhost:4321` + Claude in Chrome extension.

**Philosophy:** These aren't just tools for the user to invoke — they're force multipliers. If consulting would improve a decision or deploying would speed up work, do it.

---

## Design Principles

1. **Narrative over mechanics** — The agent is a storyteller, not a rules engine
2. **Consequences bloom over time** — Plant seeds, let them grow
3. **NPCs are people** — Every NPC has wants, fears, and memory
4. **Honor player choices** — No "right answers," no punishment for creativity
5. **Validate limits** — Social energy depletion should feel humane, not punitive

## Test Campaigns

| Campaign | Owner | Purpose |
|----------|-------|---------|
| `cipher` | Shawn | Primary playtest campaign |
| `axiom` | Claude | AI assistant testing save (do not delete) |

The `axiom` campaign is used by Claude for testing new features, command flows, and UI changes. It has a Ghost background character named "Axiom" and serves as a safe sandbox for development testing.

## License

CC BY-NC 4.0
