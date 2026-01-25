"""
Tool subsets for context-constrained scenarios.

Local models (8B-12B) can't handle 19 tools at once.
Phase-based subsets expose only relevant tools.
"""

from .registry import get_all_schemas


# Core tools always available
CORE_TOOLS = {
    "roll_check",
    "set_phase",
}

# Tools by mission phase
PHASE_TOOLS = {
    "briefing": CORE_TOOLS | {
        "update_npc",
        "describe_npc_appearance",  # For character YAML on first /start
    },
    "planning": CORE_TOOLS | {
        "update_character",
    },
    "execution": CORE_TOOLS | {
        "update_character",
        "update_npc",
        "update_faction",
        "log_hinge_moment",
        "queue_dormant_thread",
        "invoke_restorer",
    },
    "resolution": CORE_TOOLS | {
        "update_character",
        "update_npc",
        "update_faction",
        "log_hinge_moment",
        "queue_dormant_thread",
        "surface_dormant_thread",
        "grant_enhancement",
        "call_leverage",
        "resolve_leverage",
    },
    "debrief": CORE_TOOLS | {
        "update_faction",
        "log_hinge_moment",
        "surface_dormant_thread",
    },
    "between": CORE_TOOLS | {
        "update_character",
        "update_npc",
        "grant_enhancement",
        "refuse_enhancement",
    },
}

# Minimal subset for very constrained contexts
MINIMAL_TOOLS = {
    "roll_check",
    "update_character",
    "update_faction",
    "log_hinge_moment",
    "set_phase",
}


def get_tools_for_phase(phase: str) -> list[dict]:
    """Get tool schemas for a specific phase."""
    allowed = PHASE_TOOLS.get(phase, CORE_TOOLS)
    all_schemas = get_all_schemas()
    return [s for s in all_schemas if s["name"] in allowed]


def get_minimal_tools() -> list[dict]:
    """Get minimal tool set for very constrained contexts."""
    all_schemas = get_all_schemas()
    return [s for s in all_schemas if s["name"] in MINIMAL_TOOLS]


def count_tools_tokens(tools: list[dict]) -> int:
    """Estimate token count for tool schemas."""
    import json
    return len(json.dumps(tools)) // 4  # Rough estimate
