# SENTINEL Campaign MCP Server

MCP server exposing campaign data for the SENTINEL TTRPG: faction lore, NPC archetypes, campaign history, and state tracking.

## Installation

```bash
cd sentinel-campaign
pip install -e .
```

## Usage

### With Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "sentinel-campaign": {
      "command": "python",
      "args": ["-m", "sentinel_campaign.server"],
      "cwd": "/path/to/sentinel-campaign/src"
    }
  }
}
```

### Standalone

```bash
sentinel-campaign
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

Faction data lives in `src/sentinel_campaign/data/`:

```
data/
├── factions/
│   ├── nexus.json
│   ├── ember_colonies.json
│   ├── witnesses.json
│   └── ... (all 11 factions)
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
  "symbols": ["visual motifs"],
  "aesthetic": "Look and feel...",
  "key_events": [...],
  "archetypes": [...],
  "goals": [...],
  "methods": [...],
  "current_tensions": [...],
  "intel_domains": [...]
}
```

## Future: Campaign History

The design supports adding:

- `search_history(query, filters)` - Search campaign history
- `get_npc_timeline(npc_name)` - Chronological NPC events
- `get_session_summary(session)` - Condensed session recap

See `architecture/MCP_FACTIONS.md` for the full design.
