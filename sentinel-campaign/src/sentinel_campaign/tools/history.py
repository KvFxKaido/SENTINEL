"""Campaign history tool handlers."""

import json
import re
from datetime import datetime
from pathlib import Path


def _load_campaign(campaigns_dir: Path, campaign_id: str) -> dict | None:
    """Load campaign JSON file."""
    campaign_file = campaigns_dir / f"{campaign_id}.json"
    if campaign_file.exists():
        return json.loads(campaign_file.read_text())

    # Try partial match
    for f in campaigns_dir.glob("*.json"):
        if f.stem.startswith(campaign_id):
            return json.loads(f.read_text())

    return None


def _extract_keywords(text: str) -> set[str]:
    """Extract keywords from text for matching."""
    # Remove punctuation, lowercase, split
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    # Filter common words
    stopwords = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'was', 'were', 'has', 'have', 'been'}
    return set(w for w in words if w not in stopwords)


def _format_timestamp(ts: str | None) -> str:
    """Format timestamp for display."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(ts)


def search_history(
    campaigns_dir: Path,
    campaign_id: str,
    query: str,
    npc: str | None = None,
    faction: str | None = None,
    entry_type: str | None = None,
    session_min: int | None = None,
    session_max: int | None = None,
    limit: int = 20,
) -> dict:
    """
    Search campaign history with keyword matching and filters.

    Args:
        campaigns_dir: Directory containing campaign files
        campaign_id: Campaign to search
        query: Search query (keywords)
        npc: Filter by NPC name
        faction: Filter by faction name
        entry_type: Filter by history type (hinge, faction_shift, mission, etc.)
        session_min: Minimum session number
        session_max: Maximum session number
        limit: Max results to return
    """
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    query_keywords = _extract_keywords(query)
    results = []

    # Search history entries
    for entry in campaign.get("history", []):
        score = 0
        session = entry.get("session", 0)

        # Apply filters
        if session_min is not None and session < session_min:
            continue
        if session_max is not None and session > session_max:
            continue
        if entry_type and entry.get("type") != entry_type:
            continue

        summary = entry.get("summary", "")
        summary_lower = summary.lower()

        # Filter by faction
        if faction:
            faction_name = faction.replace("_", " ").lower()
            if faction_name not in summary_lower and faction.lower() not in summary_lower:
                continue

        # Filter by NPC
        if npc and npc.lower() not in summary_lower:
            continue

        # Score by keyword matches
        entry_keywords = _extract_keywords(summary)
        matches = query_keywords & entry_keywords
        if matches:
            score = len(matches)

            # Boost for exact phrase match
            if query.lower() in summary_lower:
                score += 5

            # Boost for hinge moments (more significant)
            if entry.get("type") == "hinge":
                score += 2

            results.append({
                "id": entry.get("id"),
                "session": session,
                "type": entry.get("type"),
                "summary": summary,
                "timestamp": _format_timestamp(entry.get("timestamp")),
                "score": score,
                "is_permanent": entry.get("is_permanent", False),
            })

    # Also search character hinge histories
    for char in campaign.get("characters", []):
        for hinge in char.get("hinge_history", []):
            session = hinge.get("session", 0)

            if session_min is not None and session < session_min:
                continue
            if session_max is not None and session > session_max:
                continue
            if entry_type and entry_type != "hinge":
                continue

            text = f"{hinge.get('situation', '')} {hinge.get('choice', '')} {hinge.get('reasoning', '')}"
            text_lower = text.lower()

            if faction:
                faction_name = faction.replace("_", " ").lower()
                if faction_name not in text_lower and faction.lower() not in text_lower:
                    continue

            if npc and npc.lower() not in text_lower:
                continue

            hinge_keywords = _extract_keywords(text)
            matches = query_keywords & hinge_keywords
            if matches:
                score = len(matches) + 2  # Boost hinges

                results.append({
                    "id": hinge.get("id"),
                    "session": session,
                    "type": "hinge",
                    "character": char.get("name"),
                    "summary": f"HINGE: {hinge.get('situation', '')[:100]}",
                    "choice": hinge.get("choice"),
                    "timestamp": _format_timestamp(hinge.get("timestamp")),
                    "score": score,
                })

    # Sort by score (descending), then by session (descending)
    results.sort(key=lambda x: (-x.get("score", 0), -x.get("session", 0)))
    results = results[:limit]

    return {
        "campaign_id": campaign_id,
        "query": query,
        "filters": {
            "npc": npc,
            "faction": faction,
            "entry_type": entry_type,
            "session_range": [session_min, session_max] if session_min or session_max else None,
        },
        "total_results": len(results),
        "results": results,
    }


def get_npc_timeline(
    campaigns_dir: Path,
    campaign_id: str,
    npc_name: str,
) -> dict:
    """
    Get chronological timeline of events involving an NPC.

    Returns all history entries mentioning the NPC, plus NPC's current state.
    """
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    npc_name_lower = npc_name.lower()
    timeline = []
    npc_data = None

    # Find NPC in registry
    npcs = campaign.get("npcs", {})
    for npc in npcs.get("active", []) + npcs.get("dormant", []):
        if npc.get("name", "").lower() == npc_name_lower:
            npc_data = {
                "id": npc.get("id"),
                "name": npc.get("name"),
                "faction": npc.get("faction"),
                "disposition": npc.get("disposition", "neutral"),
                "agenda": npc.get("agenda", {}),
                "remembers": npc.get("remembers", []),
                "last_interaction": npc.get("last_interaction", ""),
                "is_active": npc in npcs.get("active", []),
            }
            break

    # Search history for mentions
    for entry in campaign.get("history", []):
        summary = entry.get("summary", "")
        if npc_name_lower in summary.lower():
            timeline.append({
                "session": entry.get("session", 0),
                "type": entry.get("type"),
                "summary": summary,
                "timestamp": _format_timestamp(entry.get("timestamp")),
                "is_permanent": entry.get("is_permanent", False),
            })

    # Search character hinges for mentions
    for char in campaign.get("characters", []):
        for hinge in char.get("hinge_history", []):
            text = f"{hinge.get('situation', '')} {hinge.get('choice', '')} {hinge.get('reasoning', '')}"
            if npc_name_lower in text.lower():
                timeline.append({
                    "session": hinge.get("session", 0),
                    "type": "hinge",
                    "character": char.get("name"),
                    "summary": f"HINGE involving {npc_name}: {hinge.get('situation', '')[:80]}",
                    "choice": hinge.get("choice"),
                    "timestamp": _format_timestamp(hinge.get("timestamp")),
                })

    # Sort chronologically
    timeline.sort(key=lambda x: (x.get("session", 0), x.get("timestamp", "")))

    return {
        "campaign_id": campaign_id,
        "npc_name": npc_name,
        "npc_found": npc_data is not None,
        "npc_data": npc_data,
        "total_events": len(timeline),
        "timeline": timeline,
    }


def get_session_summary(
    campaigns_dir: Path,
    campaign_id: str,
    session: int,
) -> dict:
    """
    Get a condensed summary of a specific session.

    Aggregates all history entries for the session.
    """
    campaign = _load_campaign(campaigns_dir, campaign_id)
    if not campaign:
        return {"error": f"Campaign not found: {campaign_id}"}

    meta = campaign.get("meta", {})
    total_sessions = meta.get("session_count", 0)

    if session > total_sessions:
        return {"error": f"Session {session} doesn't exist. Campaign has {total_sessions} sessions."}

    entries = []
    hinges = []
    faction_shifts = []
    missions = []

    for entry in campaign.get("history", []):
        if entry.get("session") != session:
            continue

        entry_type = entry.get("type", "")
        entry_data = {
            "id": entry.get("id"),
            "type": entry_type,
            "summary": entry.get("summary", ""),
            "timestamp": _format_timestamp(entry.get("timestamp")),
            "is_permanent": entry.get("is_permanent", False),
        }

        entries.append(entry_data)

        if entry_type == "hinge":
            hinge = entry.get("hinge", {})
            hinges.append({
                "situation": hinge.get("situation", entry.get("summary", "")),
                "choice": hinge.get("choice", ""),
                "what_shifted": hinge.get("what_shifted", ""),
            })
        elif entry_type == "faction_shift":
            faction_shifts.append(entry.get("summary", ""))
        elif entry_type == "mission":
            mission = entry.get("mission", {})
            missions.append({
                "title": mission.get("title", ""),
                "result": mission.get("result", ""),
            })

    # Get character hinges from this session
    for char in campaign.get("characters", []):
        for hinge in char.get("hinge_history", []):
            if hinge.get("session") == session:
                # Avoid duplicates
                if not any(h.get("situation") == hinge.get("situation") for h in hinges):
                    hinges.append({
                        "character": char.get("name"),
                        "situation": hinge.get("situation", ""),
                        "choice": hinge.get("choice", ""),
                        "what_shifted": hinge.get("what_shifted", ""),
                    })

    return {
        "campaign_id": campaign_id,
        "campaign_name": meta.get("name", "Unnamed"),
        "session": session,
        "total_entries": len(entries),
        "entries": entries,
        "summary": {
            "hinges": hinges,
            "faction_shifts": faction_shifts,
            "missions": missions,
        },
    }
