"""
Shared command logic for CLI and TUI.

This module contains pure data-fetching functions that return structured data.
UI layers (CLI/TUI) call these functions and render the results in their own style.

Design principles:
- Functions return dicts/lists/dataclasses, never formatted strings
- No Rich, no Textual, no UI dependencies
- Validation and error handling return structured results
- Business logic lives here, presentation lives in CLI/TUI
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state import CampaignManager
    from ..agent import SentinelAgent
    from ..llm.base import LLMClient


# =============================================================================
# Result Types
# =============================================================================

@dataclass
class CommandResult:
    """Base result for command operations."""
    success: bool
    message: str
    data: dict | None = None


@dataclass
class SimulateResult:
    """Result from simulation analysis."""
    success: bool
    analysis: str = ""
    error: str = ""


# =============================================================================
# Campaign Operations
# =============================================================================

def list_campaigns(manager: "CampaignManager") -> list[dict]:
    """Get list of all campaigns."""
    return manager.list_campaigns()


def load_campaign(manager: "CampaignManager", identifier: str) -> CommandResult:
    """Load a campaign by number or ID."""
    campaign = manager.load_campaign(identifier)
    if campaign:
        return CommandResult(
            success=True,
            message=f"Loaded: {campaign.meta.name}",
            data={"name": campaign.meta.name, "id": campaign.meta.id}
        )
    return CommandResult(success=False, message="Campaign not found")


def save_campaign(manager: "CampaignManager") -> CommandResult:
    """Save current campaign."""
    if not manager.current:
        return CommandResult(success=False, message="No campaign to save")
    manager.save()
    return CommandResult(success=True, message="Campaign saved")


def delete_campaign(manager: "CampaignManager", identifier: str) -> CommandResult:
    """Delete a campaign."""
    if manager.delete_campaign(identifier):
        return CommandResult(success=True, message="Campaign deleted")
    return CommandResult(success=False, message="Campaign not found")


def create_campaign(manager: "CampaignManager", name: str) -> CommandResult:
    """Create a new campaign."""
    campaign = manager.create_campaign(name)
    return CommandResult(
        success=True,
        message=f"Created: {campaign.meta.name}",
        data={"name": campaign.meta.name, "id": campaign.meta.id}
    )


# =============================================================================
# Faction Operations
# =============================================================================

def get_faction_standings(manager: "CampaignManager") -> dict | None:
    """Get all faction standings as structured data."""
    if not manager.current:
        return None

    standings = []
    # Iterate over FactionRegistry fields
    for field_name in manager.current.factions.model_fields:
        faction_standing = getattr(manager.current.factions, field_name)
        standings.append({
            "id": field_name,
            "name": faction_standing.faction.value,
            "standing": faction_standing.standing.value,
            "reputation": getattr(faction_standing, 'reputation', 0),
        })

    return {"standings": standings}


def format_faction_summary(manager: "CampaignManager") -> str:
    """Format faction standings for prompts (used by simulate)."""
    if not manager.current:
        return "No campaign loaded"

    lines = []
    for field_name in manager.current.factions.model_fields:
        faction_standing = getattr(manager.current.factions, field_name)
        lines.append(f"- {faction_standing.faction.value}: {faction_standing.standing.value}")

    return "\n".join(lines) if lines else "All Neutral"


# =============================================================================
# NPC Operations
# =============================================================================

def get_npc_list(manager: "CampaignManager") -> dict | None:
    """Get NPC list as structured data."""
    if not manager.current:
        return None

    npcs = manager.current.npcs
    active = []
    dormant = []

    for npc in (npcs.active if npcs else []):
        active.append({
            "id": npc.id,
            "name": npc.name,
            "faction": npc.faction.value if npc.faction else None,
            "disposition": npc.base_disposition.value if npc.base_disposition else "neutral",
            "role": npc.role,
        })

    for npc in (npcs.dormant if npcs else []):
        dormant.append({
            "id": npc.id,
            "name": npc.name,
            "faction": npc.faction.value if npc.faction else None,
        })

    return {"active": active, "dormant": dormant}


def get_npc_details(manager: "CampaignManager", name_query: str) -> dict | None:
    """Get detailed NPC info by name search."""
    if not manager.current:
        return None

    npcs = manager.current.npcs
    all_npcs = (npcs.active if npcs else []) + (npcs.dormant if npcs else [])

    for npc in all_npcs:
        if name_query.lower() in npc.name.lower():
            status = manager.get_npc_status(npc.id)
            return {
                "id": npc.id,
                "name": npc.name,
                "faction": npc.faction.value if npc.faction else None,
                "role": npc.role,
                "disposition": status.get("effective_disposition", "neutral"),
                "personal_standing": status.get("personal_standing", 0),
                "wants": npc.wants,
                "fears": npc.fears,
                "leverage": npc.leverage,
                "owes": npc.owes,
                "lie_to_self": npc.lie_to_self,
                "remembers": status.get("remembers", []),
                "agenda": status.get("agenda", {}),
            }

    return None


# =============================================================================
# Arc Operations
# =============================================================================

def get_character_arcs(manager: "CampaignManager") -> dict | None:
    """Get character arcs as structured data."""
    if not manager.current or not manager.current.characters:
        return None

    from ..state.schema import ArcStatus

    char = manager.current.characters[0]
    accepted = []
    suggested = []

    for arc in char.arcs:
        arc_data = {
            "arc_type": arc.arc_type.value,
            "title": arc.title,
            "description": arc.description,
            "strength": arc.strength,
            "status": arc.status.value,
        }
        if arc.status == ArcStatus.ACCEPTED:
            accepted.append(arc_data)
        elif arc.status == ArcStatus.SUGGESTED:
            suggested.append(arc_data)

    return {
        "character_name": char.name,
        "accepted": accepted,
        "suggested": suggested,
    }


def detect_arcs(manager: "CampaignManager") -> list[dict]:
    """Detect potential arcs from play patterns."""
    return manager.detect_arcs()


def accept_arc(manager: "CampaignManager", arc_type: str) -> CommandResult:
    """Accept a suggested arc."""
    if manager.accept_arc(arc_type):
        return CommandResult(success=True, message=f"Arc accepted: {arc_type}")
    return CommandResult(success=False, message=f"Could not accept arc: {arc_type}")


def reject_arc(manager: "CampaignManager", arc_type: str) -> CommandResult:
    """Reject a suggested arc."""
    if manager.reject_arc(arc_type):
        return CommandResult(success=True, message=f"Arc rejected: {arc_type}")
    return CommandResult(success=False, message=f"Could not reject arc: {arc_type}")


# =============================================================================
# Consequence/Thread Operations
# =============================================================================

def get_dormant_threads(manager: "CampaignManager") -> list[dict] | None:
    """Get dormant threads as structured data."""
    if not manager.current:
        return None

    threads = []
    for t in manager.current.dormant_threads:
        threads.append({
            "id": t.id,
            "origin": t.origin,
            "trigger_condition": t.trigger_condition,
            "severity": t.severity.value,
            "created_session": t.created_session,
        })

    return threads


# =============================================================================
# History Operations
# =============================================================================

def get_hinge_history(manager: "CampaignManager", limit: int = 10) -> list[dict] | None:
    """Get hinge moments from history."""
    if not manager.current:
        return None

    hinges = []
    for entry in manager.current.history:
        # Check for full hinge object or just hinge type
        if entry.hinge:
            hinges.append({
                "session": entry.session,
                "summary": entry.summary,
                "choice": entry.hinge.choice,
                "what_shifted": entry.hinge.what_shifted,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            })
        elif entry.type.value == "hinge":
            # Simplified hinge entry without full object
            hinges.append({
                "session": entry.session,
                "summary": entry.summary,
                "choice": entry.summary,  # Use summary as choice
                "what_shifted": "",
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            })

    return hinges[-limit:]


def get_faction_shift_history(manager: "CampaignManager", limit: int = 15) -> list[dict]:
    """Get faction shift events from history."""
    if not manager.current:
        return []

    from ..state.schema import HistoryType

    shifts = []
    for entry in manager.current.history:
        if entry.type == HistoryType.FACTION_SHIFT:
            shifts.append({
                "type": "faction_shift",
                "session": entry.session,
                "summary": entry.summary,
            })
        elif entry.hinge:
            shifts.append({
                "type": "hinge",
                "session": entry.session,
                "summary": entry.summary,
                "choice": entry.hinge.choice,
                "shifted": entry.hinge.what_shifted,
            })

    return shifts[-limit:]


# =============================================================================
# Simulate Operations
# =============================================================================

def simulate_preview(
    manager: "CampaignManager",
    client: "LLMClient",
    action: str,
) -> SimulateResult:
    """Preview consequences of a proposed action."""
    if not manager.current:
        return SimulateResult(success=False, error="No campaign loaded")

    from ..llm.base import Message

    # Build context
    char_name = manager.current.characters[0].name if manager.current.characters else "Unknown"
    active_npcs = ", ".join(n.name for n in manager.current.npcs.active[:5]) or "None"

    analysis_prompt = f"""Analyze the potential consequences of this player action WITHOUT narrating a scene.

PROPOSED ACTION: "{action}"

CURRENT STATE:
- Character: {char_name}
- Faction standings: {format_faction_summary(manager)}
- Active NPCs: {active_npcs}
- Dormant threads: {len(manager.current.dormant_threads)}

Provide a structured analysis:

1. LIKELY IMMEDIATE EFFECTS (what happens right away)
2. FACTION IMPLICATIONS (which factions care, standing changes)
3. NPC REACTIONS (who would react, how)
4. POTENTIAL THREADS (consequences that might queue)
5. RISK ASSESSMENT (low/medium/high, why)

Be concise. Use bullet points. This is speculative analysis, not narration."""

    try:
        response = client.chat(
            messages=[Message(role="user", content=analysis_prompt)],
            system="You are a game consequence analyzer. Provide structured, concise analysis of potential action outcomes. Do not narrate scenes.",
            max_tokens=800,
        )
        analysis = response.content if hasattr(response, 'content') else str(response)
        return SimulateResult(success=True, analysis=analysis)
    except Exception as e:
        return SimulateResult(success=False, error=str(e))


def simulate_npc(
    manager: "CampaignManager",
    client: "LLMClient",
    npc_query: str,
    approach: str,
) -> SimulateResult:
    """Predict how an NPC will react to a proposed approach."""
    if not manager.current:
        return SimulateResult(success=False, error="No campaign loaded")

    # Find NPC
    npc = None
    for n in manager.current.npcs.active + manager.current.npcs.dormant:
        if npc_query.lower() in n.name.lower():
            npc = n
            break

    if not npc:
        available = [n.name for n in manager.current.npcs.active[:5]]
        error = f"No NPC found matching '{npc_query}'"
        if available:
            error += f". Active NPCs: {', '.join(available)}"
        return SimulateResult(success=False, error=error)

    from ..llm.base import Message

    # Get NPC status
    status = manager.get_npc_status(npc.id)

    npc_context = f"""NPC: {npc.name}
Faction: {npc.faction.value if npc.faction else 'Independent'}
Disposition toward player: {status['effective_disposition']}
Personal standing: {status['personal_standing']:+d}
Wants: {status['agenda']['wants']}
Fears: {status['agenda']['fears']}
Leverage over player: {status['agenda'].get('leverage', 'None')}
Owes player: {status['agenda'].get('owes', 'Nothing')}
Remembers: {', '.join(status['remembers']) if status['remembers'] else 'Nothing specific'}"""

    analysis_prompt = f"""Predict how this NPC will react to the player's approach.

{npc_context}

PLAYER'S APPROACH: "{approach}"

Provide a structured prediction:

1. LIKELY REACTIONS (3 possibilities with rough probability)
   - Most likely (X%): ...
   - Possible (Y%): ...
   - Unlikely but possible (Z%): ...

2. KEY FACTORS
   - What's working in player's favor
   - What's working against them

3. SUGGESTED TACTICS
   - How to improve chances
   - What to avoid saying/doing

4. RED FLAGS
   - Topics that would backfire
   - Past events that might come up

Be specific to this NPC's personality and history. Keep it concise."""

    try:
        response = client.chat(
            messages=[Message(role="user", content=analysis_prompt)],
            system="You are predicting NPC behavior based on their established personality, standing, and history. Be specific and grounded in the provided context.",
            max_tokens=600,
        )
        prediction = response.content if hasattr(response, 'content') else str(response)

        # Include NPC context in result for UI to display
        return SimulateResult(
            success=True,
            analysis=prediction,
        )
    except Exception as e:
        return SimulateResult(success=False, error=str(e))


def simulate_whatif(
    manager: "CampaignManager",
    client: "LLMClient",
    query: str,
) -> SimulateResult:
    """Explore how past choices might have gone differently."""
    if not manager.current:
        return SimulateResult(success=False, error="No campaign loaded")

    from ..llm.base import Message

    # Get relevant history
    history_events = get_faction_shift_history(manager, limit=15)

    history_context = "\n".join([
        f"S{h['session']} [{h['type']}]: {h['summary']}"
        for h in history_events
    ]) if history_events else "No significant history recorded yet."

    current_state = f"""Current faction standings:
{format_faction_summary(manager)}

Active threads: {len(manager.current.dormant_threads)}
Session count: {manager.current.meta.session_count}"""

    analysis_prompt = f"""The player wants to explore an alternate timeline.

WHAT-IF QUERY: "{query}"

CAMPAIGN HISTORY (key events):
{history_context}

CURRENT STATE:
{current_state}

Analyze this alternate path:

1. DIVERGENCE POINT
   - Identify which past event this relates to
   - What was the original choice vs the hypothetical

2. PROJECTED DIFFERENCES
   - How faction standings would differ
   - NPCs who would have reacted differently
   - Threads that wouldn't exist / would exist instead

3. BUTTERFLY EFFECTS
   - Subsequent events that would have changed
   - Opportunities gained or lost
   - Relationships that would be different

4. CURRENT SITUATION
   - Where would the player be now?
   - What problems would be different?
   - What new problems might exist?

This is speculative alternate history analysis. Be specific but acknowledge uncertainty."""

    try:
        response = client.chat(
            messages=[Message(role="user", content=analysis_prompt)],
            system="You are analyzing alternate timelines in a TTRPG campaign. Ground your analysis in the provided history while exploring plausible divergent paths.",
            max_tokens=800,
        )
        analysis = response.content if hasattr(response, 'content') else str(response)
        return SimulateResult(success=True, analysis=analysis)
    except Exception as e:
        return SimulateResult(success=False, error=str(e))


# =============================================================================
# Lore Operations
# =============================================================================

def search_lore(retriever, query: str, limit: int = 3) -> list[dict]:
    """Search lore documents."""
    if not retriever:
        return []

    results = retriever.retrieve(query=query, limit=limit)
    return [
        {
            "source": r.get("source", "unknown"),
            "text": r.get("text", ""),
            "score": r.get("score", 0),
        }
        for r in results
    ]


# =============================================================================
# Status Operations
# =============================================================================

def get_campaign_status(manager: "CampaignManager") -> dict | None:
    """Get current campaign status."""
    if not manager.current:
        return None

    c = manager.current
    return {
        "name": c.meta.name,
        "id": c.meta.id,
        "phase": c.meta.phase,
        "session_count": c.meta.session_count,
        "character": c.characters[0].name if c.characters else None,
    }


# =============================================================================
# Wiki Operations
# =============================================================================

def get_wiki_timeline(manager: "CampaignManager", wiki_dir: str = "wiki") -> dict | None:
    """Get campaign wiki timeline events."""
    from pathlib import Path
    import re

    if not manager.current:
        return None

    campaign_id = manager.current.meta.id
    events_file = Path(wiki_dir) / "campaigns" / campaign_id / "_events.md"

    if not events_file.exists():
        return {
            "campaign_id": campaign_id,
            "campaign_name": manager.current.meta.name,
            "events": [],
            "raw_content": None,
            "message": "No wiki events recorded yet for this campaign.",
        }

    content = events_file.read_text(encoding="utf-8")

    # Parse events from markdown (supports both formats)
    events = []
    current_session = None

    for line in content.split("\n"):
        line = line.strip()

        # Session header: ## Session N
        session_match = re.match(r"^## Session (\d+)", line)
        if session_match:
            current_session = int(session_match.group(1))
            continue

        # Event line: - (date) [TYPE]: description
        if line.startswith("- (") and current_session is not None:
            # Format as "S{n}: {event}" for display
            event_text = line[2:]  # Remove "- " prefix
            events.append(f"S{current_session}: {event_text}")
            continue

        # Legacy format: - **Session N** (date) [TYPE]: description
        if line.startswith("- **Session"):
            events.append(line[2:])  # Remove "- " prefix

    return {
        "campaign_id": campaign_id,
        "campaign_name": manager.current.meta.name,
        "events": events,
        "raw_content": content,
        "event_count": len(events),
    }


def get_wiki_page_overlay(
    manager: "CampaignManager",
    page: str,
    wiki_dir: str = "wiki",
) -> dict | None:
    """Get a wiki page's campaign overlay if it exists."""
    from pathlib import Path

    if not manager.current:
        return None

    campaign_id = manager.current.meta.id
    overlay_file = Path(wiki_dir) / "campaigns" / campaign_id / f"{page}.md"

    if not overlay_file.exists():
        return {
            "page": page,
            "exists": False,
            "content": None,
        }

    return {
        "page": page,
        "exists": True,
        "content": overlay_file.read_text(encoding="utf-8"),
    }
