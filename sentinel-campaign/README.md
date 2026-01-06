# SENTINEL Campaign MCP Server

MCP server exposing faction data for the SENTINEL TTRPG: faction lore, NPC archetypes, and faction state tracking.

> **Note:** Campaign history search is handled by memvid (semantic search). Use `/timeline` in the agent CLI.

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

---

## Faction Resources

Static faction information exposed as MCP resources.

| URI | Description |
|-----|-------------|
| `faction://{id}/lore` | History, ideology, structure |
| `faction://{id}/npcs` | NPC archetypes and templates |
| `faction://{id}/operations` | Goals, methods, tensions |
| `faction://relationships` | Inter-faction dynamics |

**Available factions:** nexus, ember_colonies, lattice, convergence, covenant, wanderers, cultivators, steel_syndicate, witnesses, architects, ghost_networks

### Example: Faction Lore

```json
{
  "id": "nexus",
  "name": "Nexus",
  "tagline": "The network that watches",
  "ideology": "Coordination through information. Efficiency through prediction.",
  "history": "Emerged from pre-collapse AI research networks...",
  "structure": "Decentralized nodes, no single leader, consensus-based",
  "symbols": ["◈", "interconnected circles"],
  "aesthetic": "Clean, clinical, data-forward"
}
```

### Example: NPC Archetypes

```json
{
  "faction": "nexus",
  "archetypes": [
    {
      "role": "Analyst",
      "description": "Data interpreter, sees patterns others miss",
      "typical_wants": ["accurate information", "system stability"],
      "typical_fears": ["data corruption", "being wrong"],
      "speech_pattern": "Precise, qualified statements, probability language"
    }
  ]
}
```

---

## Faction Tools

Dynamic operations for campaign-specific faction state.

| Tool | Description |
|------|-------------|
| `get_faction_standing` | Current standing + history |
| `get_faction_interactions` | Past encounters this campaign |
| `log_faction_event` | Record faction-related event |
| `get_faction_intel` | What faction knows about topic |
| `query_faction_npcs` | NPCs by faction in campaign |

### Example: get_faction_standing

**Input:**
```json
{
  "campaign_id": "a1b2c3d4",
  "faction": "nexus"
}
```

**Output:**
```json
{
  "faction": "Nexus",
  "standing": "Friendly",
  "standing_history": [
    {"session": 1, "change": "Initial - Neutral"},
    {"session": 3, "change": "Helped secure data cache - now Friendly"}
  ],
  "leverage": null
}
```

### Example: get_faction_intel

**Input:**
```json
{
  "faction": "witnesses",
  "topic": "Sector 7 incident"
}
```

**Output:**
```json
{
  "faction": "Witnesses",
  "topic": "Sector 7 incident",
  "knowledge_level": "detailed",
  "note": "Witnesses have historical archives. They trade information for information.",
  "intel_domains": ["history", "records", "contradictions"]
}
```

---

## Intel Domains

Each faction knows different things:

| Faction | Knows About |
|---------|-------------|
| **Nexus** | Infrastructure, population, predictions |
| **Ember Colonies** | Survival, safe routes, trust networks |
| **Lattice** | Infrastructure, supply chains, logistics |
| **Witnesses** | History, records, contradictions |
| **Steel Syndicate** | Resources, leverage, smuggling |
| **Ghost Networks** | Escape routes, identities, hiding |
| **Architects** | Pre-collapse records, credentials |
| **Convergence** | Enhancement tech, integration research |

---

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

---

## Integration

### With Campaign State

The MCP server reads campaign JSON files from the `campaigns/` directory to:
- Read current faction standings
- Query interaction history
- Log new events

### With GM Agent

The agent can call MCP tools during response generation:
- Before describing faction NPC: `query_faction_npcs`
- When player asks about faction: `get_faction_intel`
- After faction-relevant action: `log_faction_event`

> **Campaign history search** is handled by memvid semantic search via the `/timeline` command, not MCP tools.

---

## Future: Living World (Layer 2)

Once core features are solid, add world simulation:

```python
# Potential new tools
advance_world_clock(campaign_id, days)  # Simulate faction actions
get_pending_events(campaign_id)         # What happened off-screen
check_leverage_calls(campaign_id)       # Any faction calling in debts

# Potential new state
faction_operations_in_progress: [
  {
    "faction": "nexus",
    "operation": "Mapping eastern tunnels",
    "started_session": 3,
    "eta_days": 14,
    "can_disrupt": true
  }
]
```

This would let factions "do things" between sessions, creating a living world.
