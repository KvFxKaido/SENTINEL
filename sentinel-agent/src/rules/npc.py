"""
NPC behavior rules as pure functions.

These functions operate on NPC data without being methods on the model.
This separation makes testing easier and keeps models as pure data.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state.schema import NPC, DispositionModifier, MemoryTrigger

from ..state.schema import Disposition


def get_disposition_modifier(npc: "NPC") -> "DispositionModifier | None":
    """
    Get the behavior modifier for an NPC's current disposition.

    Args:
        npc: The NPC to check

    Returns:
        DispositionModifier if one exists for current disposition, else None
    """
    return npc.disposition_modifiers.get(npc.disposition.value)


def apply_disposition_shift(npc: "NPC", delta: int) -> Disposition:
    """
    Shift an NPC's disposition by delta steps.

    Mutates the NPC in place and returns the new disposition.

    Args:
        npc: The NPC to modify
        delta: Steps to shift (+1 toward loyal, -1 toward hostile)

    Returns:
        The new disposition after shifting
    """
    dispositions = list(Disposition)
    current_idx = dispositions.index(npc.disposition)
    new_idx = max(0, min(len(dispositions) - 1, current_idx + delta))
    npc.disposition = dispositions[new_idx]
    return npc.disposition


def check_triggers(npc: "NPC", tags: list[str]) -> list["MemoryTrigger"]:
    """
    Check which memory triggers fire for given event tags.

    Mutates the NPC in place (marks triggers as fired, shifts disposition).

    Args:
        npc: The NPC whose triggers to check
        tags: Event tags like ["helped_ember_colonies", "completed_mission"]

    Returns:
        List of triggers that fired
    """
    fired = []
    for trigger in npc.memory_triggers:
        # Skip already-fired one-shot triggers
        if trigger.triggered and trigger.one_shot:
            continue

        if trigger.condition in tags:
            trigger.triggered = True
            fired.append(trigger)

            # Apply disposition shift if specified
            if trigger.disposition_shift != 0:
                apply_disposition_shift(npc, trigger.disposition_shift)

    return fired
