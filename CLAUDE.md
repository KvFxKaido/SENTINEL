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
│   │   └── state/
│   │       ├── wiki_adapter.py   # Wiki page generation
│   │       ├── wiki_watcher.py   # Bi-directional sync
│   │       └── templates.py      # Jinja2 template engine
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
├── lore/                    # World-building documents (novellas)
└── wiki/                    # Reference encyclopedia (Obsidian vault)
```

## What This Is

SENTINEL is a tactical tabletop RPG about navigating political tension, ethical tradeoffs, and survival under fractured systems. The `sentinel-agent` subdirectory contains an AI Game Master that runs the game.

## Key Documents

| Document | Purpose |
|----------|---------|
| `core/SENTINEL Playbook — Core Rules.md` | The complete game rules |
| `architecture/AGENT_ARCHITECTURE.md` | Agent design, state schema, tools |
| `architecture/sentinel_warp_vision.md` | Terminal UI/UX roadmap (Warp + MGS inspired) |
| `sentinel-agent/CLAUDE.md` | Dev guide for the agent codebase |
| `sentinel-campaign/README.md` | Campaign MCP server (factions, history, tools) |

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

**Philosophy:** These aren't just tools for the user to invoke — they're force multipliers. If consulting would improve a decision or deploying would speed up work, do it.

---

## Design Principles

1. **Narrative over mechanics** — The agent is a storyteller, not a rules engine
2. **Consequences bloom over time** — Plant seeds, let them grow
3. **NPCs are people** — Every NPC has wants, fears, and memory
4. **Honor player choices** — No "right answers," no punishment for creativity
5. **Validate limits** — Social energy depletion should feel humane, not punitive

## License

CC BY-NC 4.0
