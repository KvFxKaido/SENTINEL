"""Campaign history resource handlers."""

import json
from pathlib import Path
from datetime import datetime


def _load_campaign(campaigns_dir: Path, campaign_id: str) -> dict | None:
    """Load campaign JSON file."""
    campaign_file = campaigns_dir / f"{campaign_id}.json"
    if campaign_file.exists():
        return json.loads(campaign_file.read_text())
    return None


def _format_timestamp(ts: str | None) -> str:
    """Format timestamp for display."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(ts)


def get_campaign_sessions(campaigns_dir: Path, campaign_id: str) -> dict:
    """Get session summaries from campaign history."""
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    history = campaign.get("history", [])
    meta = campaign.get("meta", {})

    # Group history by session
    sessions = {}
    for entry in history:
        session_num = entry.get("session", 0)
        if session_num not in sessions:
            sessions[session_num] = {
                "session": session_num,
                "entries": [],
                "hinges": [],
                "faction_shifts": [],
            }

        entry_type = entry.get("type", "")
        summary = {
            "id": entry.get("id", ""),
            "type": entry_type,
            "summary": entry.get("summary", ""),
            "timestamp": _format_timestamp(entry.get("timestamp")),
            "is_permanent": entry.get("is_permanent", False),
        }

        sessions[session_num]["entries"].append(summary)

        # Track significant events separately
        if entry_type == "hinge":
            sessions[session_num]["hinges"].append(summary)
        elif entry_type == "faction_shift":
            sessions[session_num]["faction_shifts"].append(summary)

    # Convert to sorted list
    session_list = sorted(sessions.values(), key=lambda s: s["session"])

    return {
        "campaign_id": campaign_id,
        "campaign_name": meta.get("name", "Unnamed"),
        "total_sessions": meta.get("session_count", 0),
        "sessions": session_list,
    }


def get_campaign_hinges(campaigns_dir: Path, campaign_id: str) -> dict:
    """Get all hinge moments from a campaign."""
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    hinges = []

    # Get hinges from history entries
    for entry in campaign.get("history", []):
        if entry.get("type") == "hinge":
            hinge_data = entry.get("hinge", {})
            hinges.append({
                "id": entry.get("id", ""),
                "session": entry.get("session", 0),
                "situation": hinge_data.get("situation", entry.get("summary", "")),
                "choice": hinge_data.get("choice", ""),
                "reasoning": hinge_data.get("reasoning", ""),
                "what_shifted": hinge_data.get("what_shifted", ""),
                "timestamp": _format_timestamp(entry.get("timestamp")),
            })

    # Also get hinges from character hinge_history
    for char in campaign.get("characters", []):
        for hinge in char.get("hinge_history", []):
            # Avoid duplicates
            if not any(h.get("id") == hinge.get("id") for h in hinges):
                hinges.append({
                    "id": hinge.get("id", ""),
                    "session": hinge.get("session", 0),
                    "character": char.get("name", ""),
                    "situation": hinge.get("situation", ""),
                    "choice": hinge.get("choice", ""),
                    "reasoning": hinge.get("reasoning", ""),
                    "what_shifted": hinge.get("what_shifted", ""),
                    "timestamp": _format_timestamp(hinge.get("timestamp")),
                })

    # Sort by session
    hinges.sort(key=lambda h: (h.get("session", 0), h.get("timestamp", "")))

    return {
        "campaign_id": campaign_id,
        "total_hinges": len(hinges),
        "hinges": hinges,
    }


def get_npc_history(campaigns_dir: Path, campaign_id: str, npc_name: str) -> dict:
    """Get all history related to a specific NPC."""
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    npc_name_lower = npc_name.lower()
    results = {
        "campaign_id": campaign_id,
        "npc_name": npc_name,
        "npc_data": None,
        "mentions": [],
        "interactions": [],
    }

    # Find NPC in registry
    npcs = campaign.get("npcs", {})
    for npc in npcs.get("active", []) + npcs.get("dormant", []):
        if npc.get("name", "").lower() == npc_name_lower:
            results["npc_data"] = {
                "id": npc.get("id"),
                "name": npc.get("name"),
                "faction": npc.get("faction"),
                "disposition": npc.get("disposition"),
                "agenda": npc.get("agenda", {}),
                "remembers": npc.get("remembers", []),
                "last_interaction": npc.get("last_interaction", ""),
            }
            break

    # Search history for mentions
    for entry in campaign.get("history", []):
        summary = entry.get("summary", "")
        if npc_name_lower in summary.lower():
            results["mentions"].append({
                "id": entry.get("id"),
                "session": entry.get("session", 0),
                "type": entry.get("type"),
                "summary": summary,
                "timestamp": _format_timestamp(entry.get("timestamp")),
            })

    # Sort mentions by session
    results["mentions"].sort(key=lambda m: (m.get("session", 0), m.get("timestamp", "")))

    return results
