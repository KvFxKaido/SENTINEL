# Faction MCP Server Design

Layer 1: Faction Reference + Campaign Tracking

---

## Overview

An MCP server that exposes faction lore, NPC rosters, and campaign-specific faction state. Provides the GM agent (and potentially Claude Code during dev) structured access to faction data.

---

## Resources

Static/semi-static content exposed as MCP resources.

### Faction Lore
```
URI: faction://{faction_id}/lore
```
Returns faction history, ideology, structure, key events.

**Example:**
```json
{
  "id": "nexus",
  "name": "Nexus",
  "tagline": "The network that watches",
  "ideology": "Coordination through information. Efficiency through prediction.",
  "history": "Emerged from pre-collapse AI research networks...",
  "structure": "Decentralized nodes, no single leader, consensus-based",
  "symbols": ["◈", "interconnected circles"],
  "aesthetic": "Clean, clinical, data-forward",
  "key_events": [
    {"era": "pre-collapse", "event": "Founded as research coordination network"},
    {"era": "collapse", "event": "Predicted infrastructure failures, saved key nodes"},
    {"era": "post-collapse", "event": "Expanded into governance coordination"}
  ]
}
```

### Faction NPCs
```
URI: faction://{faction_id}/npcs
```
Template NPCs associated with faction (not campaign-specific).

**Example:**
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
    },
    {
      "role": "Coordinator",
      "description": "Manages inter-faction logistics",
      "typical_wants": ["smooth operations", "mutual benefit"],
      "typical_fears": ["chaos", "zero-sum conflicts"],
      "speech_pattern": "Diplomatic, solution-oriented"
    }
  ]
}
```

### Faction Operations
```
URI: faction://{faction_id}/operations
```
General goals and methods (not campaign-specific).

**Example:**
```json
{
  "faction": "ember_colonies",
  "goals": [
    "Secure reliable food and water sources",
    "Protect community autonomy from larger factions",
    "Build mutual aid networks between settlements"
  ],
  "methods": [
    "Trade agreements with Lattice for infrastructure",
    "Information sharing with Witnesses for early warnings",
    "Resistance to Convergence 'optimization' offers"
  ],
  "current_tensions": [
    {"with": "Nexus", "about": "Data collection on settlements"},
    {"with": "Convergence", "about": "Enhancement pressure"}
  ]
}
```

### Faction Relationships
```
URI: faction://relationships
```
Inter-faction dynamics (baseline, not campaign-specific).

**Example:**
```json
{
  "relationships": [
    {
      "factions": ["nexus", "lattice"],
      "status": "cooperative",
      "basis": "Mutual dependency - Nexus needs infrastructure, Lattice needs coordination"
    },
    {
      "factions": ["ember_colonies", "convergence"],
      "status": "hostile",
      "basis": "Ideological - Ember values autonomy, Convergence values integration"
    }
  ]
}
```

---

## Tools

Dynamic operations for campaign-specific faction state.

### get_faction_standing
Query player's current standing with a faction.

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
    {"session": 1, "standing": "Neutral", "reason": "Initial"},
    {"session": 3, "standing": "Friendly", "reason": "Helped secure data cache"}
  ],
  "leverage": null,
  "owes_player": "Access to eastern network nodes"
}
```

### get_faction_interactions
Get history of player interactions with a faction this campaign.

**Input:**
```json
{
  "campaign_id": "a1b2c3d4",
  "faction": "ember_colonies",
  "limit": 10
}
```

**Output:**
```json
{
  "faction": "Ember Colonies",
  "interactions": [
    {
      "session": 2,
      "type": "mission",
      "summary": "Escorted medical supplies to Settlement 7",
      "outcome": "Success - standing improved",
      "npcs_involved": ["Marta", "Old Chen"]
    },
    {
      "session": 4,
      "type": "negotiation",
      "summary": "Brokered water rights dispute",
      "outcome": "Partial - Ember got access but owes Lattice",
      "npcs_involved": ["Marta"]
    }
  ]
}
```

### log_faction_event
Record a faction-related event in the campaign.

**Input:**
```json
{
  "campaign_id": "a1b2c3d4",
  "faction": "lattice",
  "event_type": "betrayal",
  "summary": "Player revealed Lattice supply route to Ember",
  "consequences": ["Standing dropped to Unfriendly", "Lattice coordinator now hostile"],
  "session": 5
}
```

**Output:**
```json
{
  "logged": true,
  "event_id": "evt_x7y8z9",
  "warning": "This may trigger dormant threads related to Lattice"
}
```

### get_faction_intel
Ask what a faction knows about a topic (based on their information access).

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
  "intel": "Witnesses have archived footage and survivor testimonies. They know the official Architect story is incomplete. They won't share freely but might trade.",
  "conditions": "Player would need to offer something of archival value"
}
```

### query_faction_npcs
Get NPCs affiliated with a faction in this campaign.

**Input:**
```json
{
  "campaign_id": "a1b2c3d4",
  "faction": "nexus",
  "disposition_filter": "friendly"
}
```

**Output:**
```json
{
  "faction": "Nexus",
  "npcs": [
    {
      "id": "npc_1234",
      "name": "Seven",
      "role": "Analyst",
      "disposition": "warm",
      "last_interaction": "Session 4 - provided intel on Convergence movements",
      "remembers": ["player saved their data cache", "player asked about pre-collapse networks"]
    }
  ]
}
```

---

## File Structure

```
sentinel-mcp/
├── pyproject.toml
├── src/
│   └── sentinel_factions/
│       ├── __init__.py
│       ├── server.py          # MCP server entry point
│       ├── resources/
│       │   ├── __init__.py
│       │   ├── lore.py        # Faction lore resources
│       │   ├── npcs.py        # NPC archetype resources
│       │   └── operations.py  # Faction operations resources
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── standing.py    # Standing queries
│       │   ├── interactions.py # Interaction history
│       │   ├── events.py      # Event logging
│       │   └── intel.py       # Faction intel queries
│       └── data/
│           ├── factions/
│           │   ├── nexus.json
│           │   ├── ember_colonies.json
│           │   ├── lattice.json
│           │   └── ...
│           └── relationships.json
```

---

## Integration Points

### With Campaign State
The MCP server needs access to campaign JSON files to:
- Read current faction standings
- Query interaction history
- Log new events

Options:
1. **Direct file access** - MCP server reads from `campaigns/` directory
2. **HTTP API** - Sentinel agent exposes endpoints, MCP calls them
3. **Shared state** - Both read/write to same JSON files with locking

Recommend **Option 1** for simplicity. MCP server gets `campaigns_dir` as config.

### With Lore Files
Static lore can live in:
- `sentinel-mcp/src/sentinel_factions/data/factions/*.json`
- Or reference existing `lore/` directory

### With GM Agent
Agent can call MCP tools during response generation:
- Before describing faction NPC: `query_faction_npcs`
- When player asks about faction: `get_faction_intel`
- After faction-relevant action: `log_faction_event`

---

## Layer 2 Preview (Living World)

Once Layer 1 is solid, add:

```python
# New tools
advance_world_clock(campaign_id, days) → Simulate faction actions
get_pending_events(campaign_id) → What happened off-screen
check_leverage_calls(campaign_id) → Any faction calling in debts

# New state
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

This lets factions "do things" between sessions, creating a living world.

---

## Next Steps

1. Create `sentinel-mcp/` package structure
2. Implement resource handlers for faction lore
3. Implement tool handlers for campaign queries
4. Write faction data files (or generate from existing lore)
5. Test with Claude Code as client
6. Integrate with GM agent
