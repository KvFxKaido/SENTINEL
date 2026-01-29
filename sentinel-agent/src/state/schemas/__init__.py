"""
Schema contracts for SENTINEL's turn-based engine.

These schemas define the four artifacts of the Commitment Gate pipeline:

    Proposal → ProposalResult → Action → TurnResult

Each artifact has a clear role:
- Proposal: Player intent (read-only query, no mutation, no action_id)
- ProposalResult: Engine preview (costs, risks, alternatives — no mutation)
- Action: Committed intent (action_id, state_version, payload — mutation begins)
- TurnResult: Resolution outcome (events, state_snapshot — mutation complete)

All schemas are Pydantic BaseModel for validation and JSON serialization.
"""

from .action import (
    ActionType,
    Proposal,
    ProposalResult,
    Requirement,
    RequirementStatus,
    Risk,
    Alternative,
    CostPreview,
    Action,
)
from .turn_result import TurnResult
from .event import TurnEvent

__all__ = [
    # Action pipeline
    "ActionType",
    "Proposal",
    "ProposalResult",
    "Requirement",
    "RequirementStatus",
    "Risk",
    "Alternative",
    "CostPreview",
    "Action",
    # Turn result
    "TurnResult",
    # Events
    "TurnEvent",
]
