# CLAUDE.md

Context for AI assistants working on the SENTINEL project.

## Project Structure

```
SENTINEL/
├── core/                    # Game design documents
│   └── SENTINEL Playbook — Core Rules.md
├── architecture/            # Technical design
│   └── AGENT_ARCHITECTURE.md
├── sentinel-agent/          # The AI GM implementation
│   ├── CLAUDE.md            # Detailed dev context
│   ├── src/                 # Python source
│   ├── prompts/             # Hot-reloadable prompts
│   └── campaigns/           # Save files
├── sentinel-campaign/       # Campaign MCP server
│   ├── src/sentinel_campaign/
│   │   ├── server.py        # MCP entry point
│   │   ├── resources/       # Lore, NPCs, operations
│   │   ├── tools/           # Standing, interactions, intel
│   │   └── data/factions/   # Faction JSON files
│   └── README.md
└── lore/                    # World-building documents
```

## What This Is

SENTINEL is a tactical tabletop RPG about navigating political tension, ethical tradeoffs, and survival under fractured systems. The `sentinel-agent` subdirectory contains an AI Game Master that runs the game.

## Key Documents

| Document | Purpose |
|----------|---------|
| `core/SENTINEL Playbook — Core Rules.md` | The complete game rules |
| `architecture/AGENT_ARCHITECTURE.md` | Agent design, state schema, tools |
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

## MCP Server: sentinel-campaign

When enabled, provides faction tools and resources.

### Resources
- `faction://{id}/lore` — History, ideology, structure
- `faction://{id}/npcs` — NPC archetypes with wants/fears/speech
- `faction://{id}/operations` — Goals, methods, tensions
- `faction://relationships` — Inter-faction dynamics

### Tools
| Tool | Purpose |
|------|---------|
| `get_faction_standing` | Player's standing + history |
| `get_faction_interactions` | Past encounters this campaign |
| `log_faction_event` | Record faction-related event |
| `get_faction_intel` | What does faction know about topic? |
| `query_faction_npcs` | NPCs by faction in campaign |

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
python -m src.interface.cli
```

## Design Principles

1. **Narrative over mechanics** — The agent is a storyteller, not a rules engine
2. **Consequences bloom over time** — Plant seeds, let them grow
3. **NPCs are people** — Every NPC has wants, fears, and memory
4. **Honor player choices** — No "right answers," no punishment for creativity
5. **Validate limits** — Social energy depletion should feel humane, not punitive

## License

CC BY-NC 4.0
