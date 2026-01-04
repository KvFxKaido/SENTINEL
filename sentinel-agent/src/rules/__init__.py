"""
Game rules as pure functions.

Separates logic from data models for easier testing.
"""

from .npc import (
    get_disposition_modifier,
    check_triggers,
    apply_disposition_shift,
)

__all__ = [
    "get_disposition_modifier",
    "check_triggers",
    "apply_disposition_shift",
]
