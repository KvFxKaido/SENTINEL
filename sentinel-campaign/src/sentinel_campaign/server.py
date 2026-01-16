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
    search_wiki,
    get_wiki_page,
    update_wiki,
    log_wiki_event,
    get_unique_npc,
    list_unique_npcs,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel-campaign")

# Initialize server
server = Server("sentinel-campaign")

# Configuration
DATA_DIR = Path(__file__).parent / "data"
# Project root is 4 levels up from this file: server.py → sentinel_campaign → src → sentinel-campaign → SENTINEL
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CAMPAIGNS_DIR = PROJECT_ROOT / "sentinel-agent" / "campaigns"
WIKI_DIR = PROJECT_ROOT / "wiki"
PERSONAL_CONTEXT = PROJECT_ROOT / ".claude" / "personal.md"  # Gitignored personal context

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

# Wiki pages (auto-discovered from wiki/ directory if it exists)
WIKI_PAGES = [
    # Hubs
    "Home", "Factions", "Geography", "Timeline",
    # Events
    "The Awakening", "Zero Hour", "The Collapse",
    # Concepts
    "Sentries", "Project BRIDGE",
    # Factions
    "Nexus", "Ember Colonies", "Lattice", "Convergence", "Covenant",
    "Wanderers", "Cultivators", "Steel Syndicate", "Witnesses",
    "Architects", "Ghost Networks",
    # Regions
    "Rust Corridor", "Appalachian Hollows", "Gulf Passage", "The Breadbasket",
    "Northern Reaches", "Pacific Corridor", "Desert Sprawl", "Northeast Scar",
    "Sovereign South", "Texas Spine", "Frozen Edge",
]


# -----------------------------------------------------------------------------
# Resources
# -----------------------------------------------------------------------------

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all available faction and wiki resources."""
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

    # GM resources (personal context, design philosophy)
    resources.append(
        Resource(
            uri="gm://designer",
            name="Designer Context",
            description="Personal design philosophy, preferences, and context for the GM/designer",
            mimeType="text/markdown",
        )
    )

    # Wiki resources (canon pages)
    canon_dir = WIKI_DIR / "canon"
    if canon_dir.exists():
        for page in WIKI_PAGES:
            page_file = canon_dir / f"{page}.md"
            if page_file.exists():
                # Determine page type for description
                page_lower = page.lower()
                if page in ["Home", "Factions", "Geography", "Timeline"]:
                    desc = f"Wiki hub page: {page}"
                elif any(f in page_lower for f in ["nexus", "ember", "lattice", "convergence", "covenant", "wanderers", "cultivators", "syndicate", "witnesses", "architects", "ghost"]):
                    desc = f"Faction reference: {page}"
                elif any(r in page_lower for r in ["corridor", "hollows", "passage", "breadbasket", "reaches", "sprawl", "scar", "south", "spine", "edge"]):
                    desc = f"Region reference: {page}"
                else:
                    desc = f"Lore reference: {page}"

                resources.append(
                    Resource(
                        uri=f"wiki://{page.replace(' ', '_')}",
                        name=page,
                        description=desc,
                        mimeType="text/markdown",
                    )
                )

    return resources


@server.read_resource()
async def read_resource(uri) -> str:
    """Read a resource by URI."""
    # Convert AnyUrl to string if needed
    uri = str(uri)

    # Wiki resources: wiki://{page_name}
    if uri.startswith("wiki://"):
        page_name = uri[len("wiki://"):].replace("_", " ")

        # Find the wiki file in canon directory
        canon_dir = WIKI_DIR / "canon"
        page_file = canon_dir / f"{page_name}.md"
        if not page_file.exists():
            # Fallback to old location for compatibility
            page_file = WIKI_DIR / f"{page_name}.md"
            if not page_file.exists():
                raise ValueError(f"Wiki page not found: {page_name}")

        # Return raw markdown content
        return page_file.read_text(encoding="utf-8")

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

    # GM resources: gm://{resource_type}
    if uri.startswith("gm://"):
        resource_type = uri[len("gm://"):]

        if resource_type == "designer":
            # Read personal context from gitignored file
            if PERSONAL_CONTEXT.exists():
                return PERSONAL_CONTEXT.read_text(encoding="utf-8")
            else:
                return "# Designer Context\n\nNo personal context configured.\n\nCreate `.claude/personal.md` (gitignored) to provide design preferences and context."

        raise ValueError(f"Unknown GM resource: {resource_type}")

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
            description="[DEPRECATED] Get history of player interactions with a faction. Prefer /timeline (memvid) for semantic search.",
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
        Tool(
            name="search_wiki",
            description="Search wiki pages for lore, faction info, geography, or timeline events. Searches both canon and campaign overlay.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (keywords or phrases)",
                    },
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to include overlay pages (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of pages to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_wiki_page",
            description="Get a wiki page with campaign overlay support. Returns merged content if campaign has extensions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "description": "Page name (e.g., 'Nexus', 'The Collapse')",
                    },
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to check for overlay (optional)",
                    },
                },
                "required": ["page"],
            },
        ),
        Tool(
            name="update_wiki",
            description="Update a campaign wiki overlay page. Use to add campaign-specific lore changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID",
                    },
                    "page": {
                        "type": "string",
                        "description": "Page name to update",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to add/replace",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Update mode",
                        "enum": ["append", "replace", "extend"],
                        "default": "append",
                    },
                    "section": {
                        "type": "string",
                        "description": "Section to append to (for extend mode)",
                    },
                },
                "required": ["campaign_id", "page", "content"],
            },
        ),
        Tool(
            name="log_wiki_event",
            description="Log a campaign event to the wiki timeline. Creates chronological record of significant happenings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID",
                    },
                    "session": {
                        "type": "integer",
                        "description": "Session number",
                    },
                    "event": {
                        "type": "string",
                        "description": "Event description",
                    },
                    "related_pages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related wiki pages to link (optional)",
                    },
                },
                "required": ["campaign_id", "session", "event"],
            },
        ),
        Tool(
            name="get_unique_npc",
            description="Get a unique/persistent NPC that transcends factions (e.g., Eli Cross). These NPCs appear across campaigns with special rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "npc_id": {
                        "type": "string",
                        "description": "Unique NPC ID (e.g., 'eli_cross')",
                    },
                },
                "required": ["npc_id"],
            },
        ),
        Tool(
            name="list_unique_npcs",
            description="List all available unique/persistent NPCs. Returns summary info without full details.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
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

    elif name == "search_wiki":
        result = search_wiki(
            wiki_dir=WIKI_DIR,
            query=arguments["query"],
            campaign_id=arguments.get("campaign_id"),
            limit=arguments.get("limit", 5),
        )

    elif name == "get_wiki_page":
        result = get_wiki_page(
            wiki_dir=WIKI_DIR,
            page=arguments["page"],
            campaign_id=arguments.get("campaign_id"),
        )

    elif name == "update_wiki":
        result = update_wiki(
            wiki_dir=WIKI_DIR,
            campaign_id=arguments["campaign_id"],
            page=arguments["page"],
            content=arguments["content"],
            mode=arguments.get("mode", "append"),
            section=arguments.get("section"),
        )

    elif name == "log_wiki_event":
        result = log_wiki_event(
            wiki_dir=WIKI_DIR,
            campaign_id=arguments["campaign_id"],
            session=arguments["session"],
            event=arguments["event"],
            related_pages=arguments.get("related_pages"),
        )

    elif name == "get_unique_npc":
        result = get_unique_npc(
            data_dir=DATA_DIR,
            npc_id=arguments["npc_id"],
        )

    elif name == "list_unique_npcs":
        result = list_unique_npcs(
            data_dir=DATA_DIR,
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
