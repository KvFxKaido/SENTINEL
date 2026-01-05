"""
SENTINEL Campaign MCP Server.

Exposes faction lore, NPC archetypes, campaign history, and state
via the Model Context Protocol.
"""

import json
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
)

from .resources import (
    get_faction_lore,
    get_faction_npcs,
    get_faction_operations,
    get_relationships,
    get_campaign_sessions,
    get_campaign_hinges,
    get_npc_history,
)
from .tools import (
    get_faction_standing,
    get_faction_interactions,
    log_faction_event,
    get_faction_intel,
    query_faction_npcs,
    search_history,
    get_npc_timeline,
    get_session_summary,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel-campaign")

# Initialize server
server = Server("sentinel-campaign")

# Configuration
DATA_DIR = Path(__file__).parent / "data"
CAMPAIGNS_DIR = Path.cwd() / "campaigns"  # Can be overridden

# Available factions
FACTIONS = [
    "nexus",
    "ember_colonies",
    "lattice",
    "convergence",
    "covenant",
    "wanderers",
    "cultivators",
    "steel_syndicate",
    "witnesses",
    "architects",
    "ghost_networks",
]


# -----------------------------------------------------------------------------
# Resources
# -----------------------------------------------------------------------------

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all available faction resources."""
    resources = []

    # Faction-specific resources
    for faction in FACTIONS:
        resources.extend([
            Resource(
                uri=f"faction://{faction}/lore",
                name=f"{faction.replace('_', ' ').title()} Lore",
                description=f"History, ideology, and background for {faction.replace('_', ' ').title()}",
                mimeType="application/json",
            ),
            Resource(
                uri=f"faction://{faction}/npcs",
                name=f"{faction.replace('_', ' ').title()} NPC Archetypes",
                description=f"NPC templates and archetypes for {faction.replace('_', ' ').title()}",
                mimeType="application/json",
            ),
            Resource(
                uri=f"faction://{faction}/operations",
                name=f"{faction.replace('_', ' ').title()} Operations",
                description=f"Goals, methods, and current tensions for {faction.replace('_', ' ').title()}",
                mimeType="application/json",
            ),
        ])

    # Global resources
    resources.append(
        Resource(
            uri="faction://relationships",
            name="Inter-Faction Relationships",
            description="Relationships and tensions between all factions",
            mimeType="application/json",
        )
    )

    # Campaign history resources (require campaign_id in URI)
    # These are templates - actual campaign IDs filled in at runtime
    resources.extend([
        Resource(
            uri="campaign://{campaign_id}/sessions",
            name="Campaign Sessions",
            description="Session summaries and history for a campaign. Replace {campaign_id} with actual ID.",
            mimeType="application/json",
        ),
        Resource(
            uri="campaign://{campaign_id}/hinges",
            name="Campaign Hinge Moments",
            description="All irreversible choices made during a campaign. Replace {campaign_id} with actual ID.",
            mimeType="application/json",
        ),
        Resource(
            uri="campaign://{campaign_id}/npc/{npc_name}",
            name="NPC History",
            description="Everything involving a specific NPC. Replace {campaign_id} and {npc_name}.",
            mimeType="application/json",
        ),
    ])

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    # Campaign history resources: campaign://{campaign_id}/{resource_type}
    if uri.startswith("campaign://"):
        path = uri[len("campaign://"):]
        parts = path.split("/")

        if len(parts) < 2:
            raise ValueError(f"Invalid campaign URI: {uri}")

        campaign_id = parts[0]
        resource_type = parts[1]

        if resource_type == "sessions":
            data = get_campaign_sessions(CAMPAIGNS_DIR, campaign_id)
        elif resource_type == "hinges":
            data = get_campaign_hinges(CAMPAIGNS_DIR, campaign_id)
        elif resource_type == "npc" and len(parts) >= 3:
            npc_name = "/".join(parts[2:])  # Handle names with slashes
            data = get_npc_history(CAMPAIGNS_DIR, campaign_id, npc_name)
        else:
            raise ValueError(f"Unknown campaign resource type: {resource_type}")

        return json.dumps(data, indent=2)

    # Faction resources: faction://{faction_id}/{resource_type}
    if uri.startswith("faction://"):
        path = uri[len("faction://"):]

        # Global resources
        if path == "relationships":
            data = get_relationships(DATA_DIR)
            return json.dumps(data, indent=2)

        # Faction-specific resources
        parts = path.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid faction URI: {uri}")

        faction_id, resource_type = parts

        if faction_id not in FACTIONS:
            raise ValueError(f"Unknown faction: {faction_id}")

        if resource_type == "lore":
            data = get_faction_lore(DATA_DIR, faction_id)
        elif resource_type == "npcs":
            data = get_faction_npcs(DATA_DIR, faction_id)
        elif resource_type == "operations":
            data = get_faction_operations(DATA_DIR, faction_id)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

        return json.dumps(data, indent=2)

    raise ValueError(f"Unknown URI scheme: {uri}")


# -----------------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available faction tools."""
    return [
        Tool(
            name="get_faction_standing",
            description="Get player's current standing with a faction, including history of changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to query",
                    },
                    "faction": {
                        "type": "string",
                        "description": "Faction ID (e.g., 'nexus', 'ember_colonies')",
                        "enum": FACTIONS,
                    },
                },
                "required": ["campaign_id", "faction"],
            },
        ),
        Tool(
            name="get_faction_interactions",
            description="Get history of player interactions with a faction this campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to query",
                    },
                    "faction": {
                        "type": "string",
                        "description": "Faction ID",
                        "enum": FACTIONS,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum interactions to return",
                        "default": 10,
                    },
                },
                "required": ["campaign_id", "faction"],
            },
        ),
        Tool(
            name="log_faction_event",
            description="Record a faction-related event in the campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID",
                    },
                    "faction": {
                        "type": "string",
                        "description": "Faction ID",
                        "enum": FACTIONS,
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Type of event",
                        "enum": ["help", "oppose", "betray", "negotiate", "mission", "contact"],
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief description of what happened",
                    },
                    "session": {
                        "type": "integer",
                        "description": "Session number when this occurred",
                    },
                },
                "required": ["campaign_id", "faction", "event_type", "summary", "session"],
            },
        ),
        Tool(
            name="get_faction_intel",
            description="Query what a faction knows about a topic based on their information access",
            inputSchema={
                "type": "object",
                "properties": {
                    "faction": {
                        "type": "string",
                        "description": "Faction to query",
                        "enum": FACTIONS,
                    },
                    "topic": {
                        "type": "string",
                        "description": "Topic to ask about",
                    },
                },
                "required": ["faction", "topic"],
            },
        ),
        Tool(
            name="query_faction_npcs",
            description="Get NPCs affiliated with a faction in this campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID",
                    },
                    "faction": {
                        "type": "string",
                        "description": "Faction ID",
                        "enum": FACTIONS,
                    },
                    "disposition_filter": {
                        "type": "string",
                        "description": "Filter by disposition",
                        "enum": ["hostile", "wary", "neutral", "warm", "loyal"],
                    },
                },
                "required": ["campaign_id", "faction"],
            },
        ),
        # Campaign history tools
        Tool(
            name="search_history",
            description="Search campaign history with keyword matching and filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to search",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (keywords)",
                    },
                    "npc": {
                        "type": "string",
                        "description": "Filter by NPC name",
                    },
                    "faction": {
                        "type": "string",
                        "description": "Filter by faction name",
                        "enum": FACTIONS,
                    },
                    "entry_type": {
                        "type": "string",
                        "description": "Filter by history type",
                        "enum": ["hinge", "faction_shift", "mission", "faction_help", "faction_oppose"],
                    },
                    "session_min": {
                        "type": "integer",
                        "description": "Minimum session number",
                    },
                    "session_max": {
                        "type": "integer",
                        "description": "Maximum session number",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 20,
                    },
                },
                "required": ["campaign_id", "query"],
            },
        ),
        Tool(
            name="get_npc_timeline",
            description="Get chronological timeline of all events involving an NPC",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID",
                    },
                    "npc_name": {
                        "type": "string",
                        "description": "Name of the NPC to look up",
                    },
                },
                "required": ["campaign_id", "npc_name"],
            },
        ),
        Tool(
            name="get_session_summary",
            description="Get a condensed summary of a specific session",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID",
                    },
                    "session": {
                        "type": "integer",
                        "description": "Session number to summarize",
                    },
                },
                "required": ["campaign_id", "session"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a faction tool."""

    if name == "get_faction_standing":
        result = get_faction_standing(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            faction=arguments["faction"],
        )

    elif name == "get_faction_interactions":
        result = get_faction_interactions(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            faction=arguments["faction"],
            limit=arguments.get("limit", 10),
        )

    elif name == "log_faction_event":
        result = log_faction_event(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            faction=arguments["faction"],
            event_type=arguments["event_type"],
            summary=arguments["summary"],
            session=arguments["session"],
        )

    elif name == "get_faction_intel":
        result = get_faction_intel(
            data_dir=DATA_DIR,
            faction=arguments["faction"],
            topic=arguments["topic"],
        )

    elif name == "query_faction_npcs":
        result = query_faction_npcs(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            faction=arguments["faction"],
            disposition_filter=arguments.get("disposition_filter"),
        )

    # Campaign history tools
    elif name == "search_history":
        result = search_history(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            query=arguments["query"],
            npc=arguments.get("npc"),
            faction=arguments.get("faction"),
            entry_type=arguments.get("entry_type"),
            session_min=arguments.get("session_min"),
            session_max=arguments.get("session_max"),
            limit=arguments.get("limit", 20),
        )

    elif name == "get_npc_timeline":
        result = get_npc_timeline(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            npc_name=arguments["npc_name"],
        )

    elif name == "get_session_summary":
        result = get_session_summary(
            campaigns_dir=CAMPAIGNS_DIR,
            campaign_id=arguments["campaign_id"],
            session=arguments["session"],
        )

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point."""
    import asyncio
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
