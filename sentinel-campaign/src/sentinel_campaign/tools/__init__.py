"""Tool handlers for factions."""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def _load_campaign(campaigns_dir: Path, campaign_id: str) -> dict | None:
    """Load campaign JSON file."""
    # Try exact match
    campaign_file = campaigns_dir / f"{campaign_id}.json"
    if campaign_file.exists():
        return json.loads(campaign_file.read_text())

    # Try partial match
    for f in campaigns_dir.glob("*.json"):
        if f.stem.startswith(campaign_id):
            return json.loads(f.read_text())

    return None


def _save_campaign(campaigns_dir: Path, campaign_id: str, data: dict) -> bool:
    """Save campaign JSON file."""
    campaign_file = campaigns_dir / f"{campaign_id}.json"

    # Find the actual file if partial ID
    if not campaign_file.exists():
        for f in campaigns_dir.glob("*.json"):
            if f.stem.startswith(campaign_id):
                campaign_file = f
                break

    if campaign_file.exists():
        # Backup
        backup = campaign_file.with_suffix(".json.bak")
        backup.write_text(campaign_file.read_text())

    campaign_file.write_text(json.dumps(data, indent=2, default=str))
    return True


# -----------------------------------------------------------------------------
# Event Queue (for safe MCP → Agent communication)
# -----------------------------------------------------------------------------

QUEUE_FILE = "pending_events.json"


def _append_event(campaigns_dir: Path, event: dict) -> str:
    """
    Append an event to the queue file.

    This is the safe way for MCP to communicate state changes.
    The agent processes these events on startup.

    Returns the event ID.
    """
    queue_file = campaigns_dir / QUEUE_FILE

    # Load existing queue
    if queue_file.exists():
        try:
            queue = json.loads(queue_file.read_text())
        except json.JSONDecodeError:
            queue = {"events": [], "last_processed": None}
    else:
        queue = {"events": [], "last_processed": None}

    # Generate event ID and timestamp
    event_id = str(uuid4())[:8]
    event["id"] = event_id
    event["timestamp"] = datetime.now().isoformat()
    event["processed"] = False

    # Append and save
    queue["events"].append(event)
    queue_file.write_text(json.dumps(queue, indent=2, default=str))

    return event_id


def _faction_id_to_attr(faction_id: str) -> str:
    """Convert faction ID to attribute name (e.g., 'ember_colonies' -> 'ember_colonies')."""
    return faction_id.lower().replace(" ", "_")


def get_faction_standing(
    campaigns_dir: Path,
    campaign_id: str,
    faction: str,
) -> dict:
    """Get player's current standing with a faction."""
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    factions_data = campaign.get("factions", {})
    faction_attr = _faction_id_to_attr(faction)
    faction_standing = factions_data.get(faction_attr, {})

    # Get standing history from campaign history
    history = campaign.get("history", [])
    standing_history = []
    for entry in history:
        if entry.get("type") == "faction_shift":
            summary = entry.get("summary", "")
            if faction.replace("_", " ").title() in summary or faction in summary.lower():
                standing_history.append({
                    "session": entry.get("session", 0),
                    "change": summary,
                    "timestamp": entry.get("timestamp"),
                })

    # Check for leverage from enhancements
    leverage = None
    characters = campaign.get("characters", [])
    for char in characters:
        for enh in char.get("enhancements", []):
            if enh.get("source", "").lower().replace(" ", "_") == faction_attr:
                lev = enh.get("leverage", {})
                if lev.get("pending_obligation"):
                    leverage = lev.get("pending_obligation")

    return {
        "faction": faction.replace("_", " ").title(),
        "standing": faction_standing.get("standing", {}).get("value", "Neutral"),
        "standing_history": standing_history,
        "leverage": leverage,
    }


def get_faction_interactions(
    campaigns_dir: Path,
    campaign_id: str,
    faction: str,
    limit: int = 10,
) -> dict:
    """Get history of player interactions with a faction."""
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    faction_name = faction.replace("_", " ").title()
    history = campaign.get("history", [])

    interactions = []
    for entry in history:
        summary = entry.get("summary", "")
        # Check if this entry mentions the faction
        if faction_name in summary or faction in summary.lower():
            interactions.append({
                "session": entry.get("session", 0),
                "type": entry.get("type", "unknown"),
                "summary": summary,
                "timestamp": entry.get("timestamp"),
            })

    # Most recent first, limited
    interactions = sorted(interactions, key=lambda x: x.get("session", 0), reverse=True)
    interactions = interactions[:limit]

    return {
        "faction": faction_name,
        "interactions": interactions,
    }


def log_faction_event(
    campaigns_dir: Path,
    campaign_id: str,
    faction: str,
    event_type: str,
    summary: str,
    session: int,
) -> dict:
    """
    Queue a faction-related event for the agent to process.

    Instead of directly modifying campaign state, this appends to an event
    queue that the agent processes on startup. This prevents race conditions
    between MCP and agent state modifications.
    """
    # Verify campaign exists (read-only check)
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    # Resolve actual campaign ID (in case partial match was used)
    actual_campaign_id = campaign.get("meta", {}).get("id", campaign_id)

    # Queue the event for agent processing
    event = {
        "source": "mcp",
        "event_type": "faction_event",
        "campaign_id": actual_campaign_id,
        "payload": {
            "faction": faction,
            "event_type": event_type,
            "summary": summary,
            "session": session,
            "is_permanent": event_type == "betray",
        },
    }

    event_id = _append_event(campaigns_dir, event)

    # Check for dormant threads that might trigger (read-only advisory)
    dormant = campaign.get("dormant_threads", [])
    warnings = []
    faction_name = faction.replace("_", " ").title()
    for thread in dormant:
        trigger = thread.get("trigger_condition", "").lower()
        if faction.lower() in trigger or faction_name.lower() in trigger:
            warnings.append(f"Dormant thread may trigger: {thread.get('consequence', '')[:50]}...")

    return {
        "queued": True,
        "event_id": event_id,
        "note": "Event queued for agent processing on next startup",
        "warnings": warnings if warnings else None,
    }


def get_faction_intel(
    data_dir: Path,
    faction: str,
    topic: str,
) -> dict:
    """Query what a faction knows about a topic."""
    # Load faction data for intel capabilities
    faction_file = data_dir / "factions" / f"{faction}.json"
    faction_data = {}
    if faction_file.exists():
        faction_data = json.loads(faction_file.read_text())

    intel_domains = faction_data.get("intel_domains", [])
    intel_level = "minimal"

    # Check if topic matches faction's intel domains
    topic_lower = topic.lower()
    for domain in intel_domains:
        if domain.lower() in topic_lower or topic_lower in domain.lower():
            intel_level = "detailed"
            break

    # Faction-specific intel tendencies
    faction_intel_notes = {
        "nexus": "Nexus has broad surveillance data but may not share freely.",
        "witnesses": "Witnesses have historical archives. They trade information for information.",
        "lattice": "Lattice knows infrastructure and logistics. Practical, not political.",
        "ember_colonies": "Ember knows ground-level survival intel. Suspicious of outsiders.",
        "convergence": "Convergence knows enhancement tech. Has ulterior motives.",
        "architects": "Architects have pre-collapse records. Guard them jealously.",
        "ghost_networks": "Ghost Networks know what others want hidden. Price is steep.",
    }

    return {
        "faction": faction.replace("_", " ").title(),
        "topic": topic,
        "knowledge_level": intel_level,
        "note": faction_intel_notes.get(faction, "Intel access varies by relationship."),
        "intel_domains": intel_domains,
    }


def query_faction_npcs(
    campaigns_dir: Path,
    campaign_id: str,
    faction: str,
    disposition_filter: str | None = None,
) -> dict:
    """Get NPCs affiliated with a faction in this campaign."""
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    faction_name = faction.replace("_", " ").title()
    npcs_data = campaign.get("npcs", {})

    # Combine active and dormant NPCs
    all_npcs = npcs_data.get("active", []) + npcs_data.get("dormant", [])

    # Filter by faction
    faction_npcs = []
    for npc in all_npcs:
        npc_faction = npc.get("faction", "")
        if npc_faction and (
            npc_faction.lower().replace(" ", "_") == faction.lower() or
            npc_faction == faction_name
        ):
            # Apply disposition filter if provided
            if disposition_filter:
                if npc.get("disposition", "neutral") != disposition_filter:
                    continue

            faction_npcs.append({
                "id": npc.get("id"),
                "name": npc.get("name"),
                "disposition": npc.get("disposition", "neutral"),
                "last_interaction": npc.get("last_interaction", ""),
                "remembers": npc.get("remembers", [])[-3:],  # Last 3 memories
                "agenda_summary": npc.get("agenda", {}).get("wants", "Unknown"),
            })

    return {
        "faction": faction_name,
        "npcs": faction_npcs,
        "count": len(faction_npcs),
    }
