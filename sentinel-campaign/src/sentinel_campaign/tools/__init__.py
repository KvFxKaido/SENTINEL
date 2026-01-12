"""Tool handlers for factions and wiki search."""

import json
import re
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
    """
    Get history of player interactions with a faction.

    DEPRECATED: Prefer /timeline (memvid semantic search) for richer queries.
    This tool provides deterministic keyword fallback when memvid unavailable.
    """
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
        "_deprecated": True,
        "_note": "Prefer /timeline for semantic search. This is keyword fallback.",
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


# -----------------------------------------------------------------------------
# Wiki Tools
# -----------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        # Simple YAML parsing for our use case
        frontmatter = {}
        for line in parts[1].strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip().strip('"').strip("'")
        return frontmatter, parts[2].strip()
    except Exception:
        return {}, content


def _merge_wiki_content(canon_content: str, overlay_content: str, frontmatter: dict) -> str:
    """Merge overlay content into canon content based on frontmatter directives."""
    if not frontmatter.get("extends"):
        # No extends directive = full replacement
        return overlay_content

    append_to = frontmatter.get("append_to", "").strip()

    if append_to:
        # Find the section and append after it
        lines = canon_content.split("\n")
        result = []
        found_section = False
        inserted = False
        section_level = 0

        for i, line in enumerate(lines):
            result.append(line)

            # Check if this line is the target section header
            if line.strip().startswith("#") and append_to.lstrip("#").strip() in line:
                found_section = True
                section_level = len(line) - len(line.lstrip("#"))
                continue

            # If we found the section, look for the next same-or-higher level header
            if found_section and line.strip().startswith("#"):
                current_level = len(line) - len(line.lstrip("#"))
                if current_level <= section_level:
                    # Insert overlay content before this header
                    result.insert(-1, "\n" + overlay_content + "\n")
                    found_section = False
                    inserted = True

        # If section was last in document or section was found
        if found_section:
            result.append("\n" + overlay_content)
            inserted = True

        # If target section wasn't found, append as new section at end
        if not inserted:
            section_header = append_to if append_to.startswith("#") else f"## {append_to}"
            result.append(f"\n\n{section_header}\n\n{overlay_content}")

        return "\n".join(result)
    else:
        # Default: append to end
        return canon_content + "\n\n---\n\n## Campaign Notes\n\n" + overlay_content


def get_wiki_page(
    wiki_dir: Path,
    page: str,
    campaign_id: str | None = None,
) -> dict:
    """
    Get a wiki page with campaign overlay support.

    Checks for campaign-specific overlay first, falls back to canon.
    Supports 'extends' frontmatter for section-level merging.
    """
    canon_dir = wiki_dir / "canon"
    page_filename = f"{page}.md"

    # Normalize page name (handle spaces vs underscores)
    page_variants = [page, page.replace("_", " "), page.replace(" ", "_")]

    # Find canon page
    canon_path = None
    canon_content = None
    for variant in page_variants:
        test_path = canon_dir / f"{variant}.md"
        if test_path.exists():
            canon_path = test_path
            canon_content = test_path.read_text(encoding="utf-8")
            break

    # Check for campaign overlay
    if campaign_id:
        overlay_dir = wiki_dir / "campaigns" / campaign_id
        overlay_path = None
        overlay_content = None

        for variant in page_variants:
            test_path = overlay_dir / f"{variant}.md"
            if test_path.exists():
                overlay_path = test_path
                overlay_content = test_path.read_text(encoding="utf-8")
                break

        if overlay_content:
            frontmatter, body = _parse_frontmatter(overlay_content)

            if canon_content and frontmatter.get("extends"):
                # Merge overlay into canon
                merged = _merge_wiki_content(canon_content, body, frontmatter)
                return {
                    "page": page,
                    "content": merged,
                    "source": "merged",
                    "canon_path": str(canon_path),
                    "overlay_path": str(overlay_path),
                }
            else:
                # Full replacement
                return {
                    "page": page,
                    "content": body if frontmatter else overlay_content,
                    "source": "overlay",
                    "overlay_path": str(overlay_path),
                }

    # Return canon only
    if canon_content:
        return {
            "page": page,
            "content": canon_content,
            "source": "canon",
            "canon_path": str(canon_path),
        }

    return {"error": f"Page not found: {page}"}


def search_wiki(
    wiki_dir: Path,
    query: str,
    campaign_id: str | None = None,
    limit: int = 5,
) -> dict:
    """
    Search wiki pages for a query string.

    Searches both canon and campaign overlay, with overlay results prioritized.
    Returns matching snippets with context.
    """
    canon_dir = wiki_dir / "canon"

    if not canon_dir.exists():
        # Fallback for old structure
        canon_dir = wiki_dir

    # Normalize query for case-insensitive search
    query_lower = query.lower()
    query_words = query_lower.split()

    matches = []
    seen_pages = set()

    # Search campaign overlay first (if provided)
    search_dirs = []
    if campaign_id:
        overlay_dir = wiki_dir / "campaigns" / campaign_id
        if overlay_dir.exists():
            search_dirs.append(("overlay", overlay_dir))
    search_dirs.append(("canon", canon_dir))

    for source, search_dir in search_dirs:
        for wiki_file in search_dir.glob("*.md"):
            if wiki_file.name == "README.md":
                continue

            page_name = wiki_file.stem

            # Skip if we already have this page from overlay
            if page_name in seen_pages:
                continue

            try:
                content = wiki_file.read_text(encoding="utf-8")
            except Exception:
                continue

            content_lower = content.lower()

            # Skip if no query words match
            if not any(word in content_lower for word in query_words):
                continue

            # Find matching sections
            lines = content.split("\n")
            snippets = []

            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(word in line_lower for word in query_words):
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    snippet = "\n".join(lines[start:end]).strip()

                    if snippet not in snippets:
                        snippets.append(snippet)

            if snippets:
                score = sum(1 for word in query_words if word in content_lower)
                # Boost overlay results
                if source == "overlay":
                    score += 10

                matches.append({
                    "page": page_name,
                    "source": source,
                    "score": score,
                    "snippets": snippets[:3],
                })
                seen_pages.add(page_name)

    # Sort by score (most relevant first)
    matches.sort(key=lambda x: x["score"], reverse=True)
    matches = matches[:limit]

    return {
        "query": query,
        "campaign_id": campaign_id,
        "matches": matches,
        "total_found": len(matches),
    }


def update_wiki(
    wiki_dir: Path,
    campaign_id: str,
    page: str,
    content: str,
    mode: str = "append",
    section: str | None = None,
) -> dict:
    """
    Update a campaign wiki overlay page.

    Modes:
    - 'append': Add content to existing page (or create new)
    - 'replace': Replace entire page content
    - 'extend': Create an extends overlay for a canon page
    """
    overlay_dir = wiki_dir / "campaigns" / campaign_id
    overlay_dir.mkdir(parents=True, exist_ok=True)

    page_file = overlay_dir / f"{page}.md"

    if mode == "extend":
        # Create an extends overlay
        frontmatter = f"---\nextends: {page}\n"
        if section:
            frontmatter += f'append_to: "{section}"\n'
        frontmatter += "---\n\n"

        if page_file.exists():
            existing = page_file.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(existing)
            # Append to existing body
            new_content = frontmatter + body + "\n\n" + content
        else:
            new_content = frontmatter + content

        page_file.write_text(new_content, encoding="utf-8")
        return {
            "success": True,
            "page": page,
            "mode": "extend",
            "path": str(page_file),
        }

    elif mode == "replace":
        page_file.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "page": page,
            "mode": "replace",
            "path": str(page_file),
        }

    else:  # append
        if page_file.exists():
            existing = page_file.read_text(encoding="utf-8")
            new_content = existing + "\n\n" + content
        else:
            # Create new campaign page
            new_content = f"# {page}\n\n{content}"

        page_file.write_text(new_content, encoding="utf-8")
        return {
            "success": True,
            "page": page,
            "mode": "append",
            "path": str(page_file),
        }


def log_wiki_event(
    wiki_dir: Path,
    campaign_id: str,
    session: int,
    event: str,
    related_pages: list[str] | None = None,
) -> dict:
    """
    Log a campaign event to the wiki timeline.

    Creates/updates _events.md in the campaign overlay.
    Optionally links to related pages for cross-referencing.
    """
    overlay_dir = wiki_dir / "campaigns" / campaign_id
    overlay_dir.mkdir(parents=True, exist_ok=True)

    events_file = overlay_dir / "_events.md"

    # Format the event entry
    timestamp = datetime.now().strftime("%Y-%m-%d")
    entry = f"- **Session {session}** ({timestamp}): {event}"

    if related_pages:
        links = ", ".join(f"[[{p}]]" for p in related_pages)
        entry += f" — {links}"

    if events_file.exists():
        existing = events_file.read_text(encoding="utf-8")
        new_content = existing + "\n" + entry
    else:
        new_content = f"# Campaign Timeline\n\nEvents from this campaign's playthrough.\n\n{entry}"

    events_file.write_text(new_content, encoding="utf-8")

    return {
        "success": True,
        "event": event,
        "session": session,
        "path": str(events_file),
    }
