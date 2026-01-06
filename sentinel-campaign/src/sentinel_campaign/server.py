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
)
from .tools import (
    get_faction_standing,
    get_faction_interactions,
    log_faction_event,
    get_faction_intel,
    query_faction_npcs,
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

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
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
