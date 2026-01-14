"""
Ambient world state extraction for prompt injection.

Builds compact, unseen world-state deltas so the GM can weave them naturally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..state.schema import HistoryType, ThreadSeverity

if TYPE_CHECKING:
    from ..state.schema import Campaign, DormantThread, NPC


_SEEN_ITEMS: dict[str, set[str]] = {}
_LAST_SESSION: dict[str, int] = {}


def _get_seen(campaign_id: str, session_count: int) -> set[str]:
    """Return the seen set for this campaign, resetting each session."""
    last_session = _LAST_SESSION.get(campaign_id)
    if last_session != session_count:
        _SEEN_ITEMS[campaign_id] = set()
        _LAST_SESSION[campaign_id] = session_count
    return _SEEN_ITEMS[campaign_id]


def _trim(text: str, limit: int = 80) -> str:
    """Trim long text for compact ambient lines."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _thread_escalation_label(thread: "DormantThread", age: int) -> str | None:
    """Map thread age/severity to an escalation label."""
    if thread.severity == ThreadSeverity.MAJOR or age >= 4:
        return "URGENT"
    if thread.severity == ThreadSeverity.MODERATE or age >= 2:
        return "PRESSING"
    return None


def _npc_last_session(npc: "NPC") -> int | None:
    """Get the last interaction session for an NPC."""
    if not npc.interactions:
        return None
    return npc.interactions[-1].session


def extract_ambient_context(campaign: "Campaign") -> str:
    """
    Extract unseen ambient world-state deltas from campaign state.

    Returns a bullet list (no header). Empty string if nothing new.
    """
    if not campaign:
        return ""

    seen = _get_seen(campaign.meta.id, campaign.meta.session_count)
    lines: list[str] = []
    max_items = 6
    current_session = campaign.meta.session_count

    def add_item(key: str, line: str) -> None:
        if key in seen or len(lines) >= max_items:
            return
        seen.add(key)
        lines.append(line)

    # Thread escalations (age/severity driven)
    for thread in campaign.dormant_threads:
        age = max(0, current_session - thread.created_session)
        label = _thread_escalation_label(thread, age)
        if not label:
            continue
        key = f"thread:{thread.id}:{label}"
        origin = _trim(thread.origin, 70)
        add_item(
            key,
            f"- [Thread] {origin} escalated to {label} (age {age} sessions)"
        )
        if len(lines) >= max_items:
            break

    # Recent faction shifts (use history entries as deltas)
    if len(lines) < max_items:
        shifts = [
            entry for entry in campaign.history
            if entry.type == HistoryType.FACTION_SHIFT and entry.faction_shift
        ]
        shifts.sort(key=lambda e: e.timestamp, reverse=True)
        for entry in shifts[:5]:
            if entry.session < max(0, current_session - 1):
                continue
            shift = entry.faction_shift
            if not shift:
                continue
            key = f"faction:{entry.id}"
            cause = _trim(shift.cause, 60) if shift.cause else ""
            detail = f" ({cause})" if cause else ""
            add_item(
                key,
                f"- [Faction] {shift.faction.value} standing "
                f"{shift.from_standing.value} -> {shift.to_standing.value}{detail}"
            )
            if len(lines) >= max_items:
                break

    # NPC silence (active NPCs with long gaps)
    if len(lines) < max_items:
        for npc in campaign.npcs.active:
            last_session = _npc_last_session(npc)
            if last_session is None:
                continue
            silence = current_session - last_session
            if silence < 2:
                continue
            bucket = "4+" if silence >= 4 else "2+"
            key = f"npc:{npc.id}:silence:{bucket}"
            add_item(
                key,
                f"- [NPC] {npc.name} has been quiet for {silence} sessions"
            )
            if len(lines) >= max_items:
                break

    # Supply changes (credits/consumables/vehicles)
    if len(lines) < max_items:
        for char in campaign.characters:
            if char.credits <= 100:
                key = f"supply:{char.id}:credits_low"
                add_item(
                    key,
                    f"- [World] {char.name} credits running low ({char.credits}cr)"
                )
            used_items = [g for g in char.gear if g.single_use and g.used]
            if used_items:
                count = len(used_items)
                bucket = "3+" if count >= 3 else str(count)
                names = ", ".join(_trim(g.name, 18) for g in used_items[:2])
                detail = f"{count} single-use items spent"
                if names:
                    detail += f" ({names})"
                key = f"supply:{char.id}:consumables:{bucket}"
                add_item(
                    key,
                    f"- [World] {char.name} is down {detail}"
                )
            for vehicle in char.vehicles:
                if vehicle.fuel <= 20:
                    key = f"supply:{vehicle.id}:fuel_low"
                    add_item(
                        key,
                        f"- [World] {vehicle.name} fuel low ({vehicle.fuel}%)"
                    )
                if vehicle.condition <= 40:
                    key = f"supply:{vehicle.id}:condition_low"
                    add_item(
                        key,
                        f"- [World] {vehicle.name} needs repair ({vehicle.condition}%)"
                    )
            if len(lines) >= max_items:
                break

    return "\n".join(lines)
