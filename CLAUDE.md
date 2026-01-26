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

See `core/SENTINEL Playbook — Core Rules.md` for complete rules. Summary:

| Mechanic | Purpose |
|----------|---------|
| **Social Energy** | Emotional bandwidth; depletes on interaction, at zero complex social auto-fails |
| **Hinge Moments** | Irreversible choices with narrative gravity; always log and reference later |
| **Enhancements** | Faction-granted power; accepting creates leverage they can call in |
| **Dormant Threads** | Delayed consequences; queue with trigger, surface when conditions met |
| **NPC Disposition** | hostile→wary→neutral→warm→loyal; each level has tone/reveals/withholds |
| **Geography** | 11 regions with faction control; `/region` to travel |
| **Vehicles** | Transport that unlocks certain jobs; buy via `/shop` |
| **Favors** | Call in favors from allied NPCs; disposition-gated |
| **Job Board** | Faction-specific jobs by location/standing; `/jobs` to browse |
| **Endgame** | Player-initiated conclusion; readiness tracks hinges/arcs/threads/factions |
| **Memvid** | Optional semantic search over campaign history; `/timeline` |
| **Wiki** | Auto-generated Obsidian wiki; bi-directional sync with game state |

Character appearances and portraits are campaign-isolated: `assets/characters/campaigns/{id}/{name}.yaml`

## MCP Server: sentinel-campaign

Provides faction tools, wiki resources, and campaign state. See `sentinel-campaign/README.md` for full details.

**Resources:** `faction://{id}/lore`, `faction://{id}/npcs`, `faction://{id}/operations`, `wiki://{page}`

**Key tools:** `get_faction_standing`, `get_faction_intel`, `query_faction_npcs`, `search_wiki`, `log_wiki_event`

**Setup:** `cd sentinel-campaign && pip install -e .` — configured in `.mcp.json`

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
