"""
Dice rolling tools for SENTINEL.

Handles d20 checks with advantage/disadvantage and expertise modifiers.
"""

import random
from dataclasses import dataclass
from typing import Literal


@dataclass
class RollResult:
    """Result of a dice roll."""
    rolls: list[int]  # All dice rolled
    used: int  # The roll that counted
    modifier: int
    total: int
    dc: int
    success: bool
    margin: int  # Positive = over DC, negative = under

    @property
    def narrative(self) -> str:
        """Narrative description of the result."""
        if self.success:
            if self.margin >= 8:
                return "crushing success"
            elif self.margin >= 4:
                return "solid success"
            else:
                return "narrow success"
        else:
            if self.margin <= -8:
                return "complete failure"
            elif self.margin <= -4:
                return "clear failure"
            else:
                return "near miss"


def roll_d20() -> int:
    """Roll a single d20."""
    return random.randint(1, 20)


def roll_check(
    skill: str,
    dc: int,
    trained: bool = True,
    advantage: bool = False,
    disadvantage: bool = False,
) -> RollResult:
    """
    Roll a d20 skill check.

    Args:
        skill: The skill being used (for logging)
        dc: Difficulty class (10, 14, 18, or 22)
        trained: Whether character has expertise (+5 modifier)
        advantage: Roll 2d20, take higher
        disadvantage: Roll 2d20, take lower

    Returns:
        RollResult with all roll information
    """
    modifier = 5 if trained else 0

    # Advantage and disadvantage cancel out
    if advantage and disadvantage:
        advantage = False
        disadvantage = False

    # Roll dice
    if advantage or disadvantage:
        rolls = [roll_d20(), roll_d20()]
        if advantage:
            used = max(rolls)
        else:
            used = min(rolls)
    else:
        rolls = [roll_d20()]
        used = rolls[0]

    total = used + modifier
    success = total >= dc
    margin = total - dc

    return RollResult(
        rolls=rolls,
        used=used,
        modifier=modifier,
        total=total,
        dc=dc,
        success=success,
        margin=margin,
    )


@dataclass
class TacticalResetResult:
    """Result of a tactical reset."""
    old_energy: int
    new_energy: int
    advantage_granted: bool
    narrative_hint: str
    restorer_matched: str | None = None  # Which restorer was invoked


def tactical_reset(current_energy: int, ritual_description: str) -> TacticalResetResult:
    """
    Perform a tactical reset: spend 10% social energy for advantage on next social roll.

    DEPRECATED: Use invoke_restorer in manager.py instead, which connects to character state.

    Args:
        current_energy: Current social energy (0-100)
        ritual_description: How the character resets (for narrative)

    Returns:
        TacticalResetResult with energy change and status
    """
    cost = 10

    if current_energy < cost:
        return TacticalResetResult(
            old_energy=current_energy,
            new_energy=current_energy,
            advantage_granted=False,
            narrative_hint="Not enough reserves to center yourself right now.",
        )

    new_energy = current_energy - cost

    # Generate narrative hint based on new energy level
    if new_energy >= 51:
        hint = f"You take a moment—{ritual_description}. You're ready."
    elif new_energy >= 26:
        hint = f"You pause for {ritual_description}. It helps, but you're still frayed."
    else:
        hint = f"You force yourself through {ritual_description}. Running on fumes now."

    return TacticalResetResult(
        old_energy=current_energy,
        new_energy=new_energy,
        advantage_granted=True,
        narrative_hint=hint,
    )


# Tool schemas for the agent
TOOL_SCHEMAS = [
    {
        "name": "roll_check",
        "description": "Roll a d20 skill check with optional advantage/disadvantage",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": "The skill being tested (e.g., 'Persuasion', 'Stealth')",
                },
                "dc": {
                    "type": "integer",
                    "enum": [10, 14, 18, 22],
                    "description": "Difficulty class: 10=Standard, 14=Challenging, 18=Difficult, 22=Near-Impossible",
                },
                "trained": {
                    "type": "boolean",
                    "description": "Whether the character has expertise in this skill (+5 modifier)",
                    "default": True,
                },
                "advantage": {
                    "type": "boolean",
                    "description": "Roll 2d20, take higher",
                    "default": False,
                },
                "disadvantage": {
                    "type": "boolean",
                    "description": "Roll 2d20, take lower",
                    "default": False,
                },
            },
            "required": ["skill", "dc"],
        },
    },
    {
        "name": "tactical_reset",
        "description": "Spend 10% social energy to gain advantage on next social roll",
        "input_schema": {
            "type": "object",
            "properties": {
                "current_energy": {
                    "type": "integer",
                    "description": "Current social energy percentage (0-100)",
                },
                "ritual_description": {
                    "type": "string",
                    "description": "Brief description of how the character resets (e.g., 'a deep breath', 'stepping outside')",
                },
            },
            "required": ["current_energy", "ritual_description"],
        },
    },
]
