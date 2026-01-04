# SENTINEL Faction MCP Server

MCP server exposing faction lore, NPC archetypes, and campaign-specific faction state for the SENTINEL TTRPG.

## Installation

```bash
cd sentinel-mcp
pip install -e .
```

## Usage

### With Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "sentinel-factions": {
      "command": "python",
      "args": ["-m", "sentinel_factions.server"],
      "cwd": "/path/to/sentinel-mcp/src"
    }
  }
}
```

### Standalone

```bash
sentinel-factions
```

## Resources

Static faction information exposed as MCP resources:

| URI | Description |
|-----|-------------|
| `faction://{id}/lore` | History, ideology, structure |
| `faction://{id}/npcs` | NPC archetypes and templates |
| `faction://{id}/operations` | Goals, methods, tensions |
| `faction://relationships` | Inter-faction dynamics |

**Available factions:** nexus, ember_colonies, lattice, convergence, covenant, wanderers, cultivators, steel_syndicate, witnesses, architects, ghost_networks

## Tools

Campaign-specific operations:

| Tool | Description |
|------|-------------|
| `get_faction_standing` | Current standing + history |
| `get_faction_interactions` | Past encounters this campaign |
| `log_faction_event` | Record faction-related event |
| `get_faction_intel` | What faction knows about topic |
| `query_faction_npcs` | NPCs by faction in campaign |

## Data Files

Faction data lives in `src/sentinel_factions/data/`:

```
data/
├── factions/
│   ├── nexus.json
│   ├── ember_colonies.json
│   ├── witnesses.json
│   └── ... (add more)
└── relationships.json
```

## Adding Factions

Create a JSON file in `data/factions/` with:

```json
{
  "id": "faction_id",
  "name": "Display Name",
  "tagline": "Short motto",
  "ideology": "Core beliefs...",
  "history": "Origin story...",
  "structure": "How they organize...",
  "symbols": ["◈", "visual motifs"],
  "aesthetic": "Look and feel...",
  "key_events": [...],
  "archetypes": [...],
  "goals": [...],
  "methods": [...],
  "current_tensions": [...],
  "intel_domains": [...]
}
```

## Layer 2: Living World (Future)

The design supports adding:

- `advance_world_clock(days)` - Simulate faction actions
- `get_pending_events()` - What happened off-screen
- `check_leverage_calls()` - Faction demands

See `architecture/MCP_FACTIONS.md` for the full design.
