"""
Action schemas for the Commitment Gate pipeline.

Defines the first two artifacts:
- Proposal: Read-only intent (player wants to do something)
- ProposalResult: Engine preview (what it would cost, what might go wrong)
- Action: Committed intent (mutation authorized)

Design invariants (from Sentinel 2D §4):
- Proposals are non-mutating (4e)
- ProposalResults are non-mutating (4e)
- Actions include state_version for idempotency (4d)
- Cancellation before Action has zero side effects
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of committed actions that cost one turn."""
    TRAVEL = "travel"
    ACCEPT_JOB = "accept_job"
    COMPLETE_JOB = "complete_job"
    CALL_FAVOR = "call_favor"
    COMMIT_ATTENTION = "commit_attention"
    RECON = "recon"
    INITIATE_COMBAT = "initiate_combat"
    LOCAL = "local"  # Generic local action


class RequirementStatus(str, Enum):
    """Whether a requirement is met, unmet, or can be bypassed."""
    MET = "met"
    UNMET = "unmet"
    BYPASSABLE = "bypassable"  # Can be met via alternative


class Requirement(BaseModel):
    """
    A single requirement for an action to succeed.

    Each requirement has a status and optional bypass description.
    This is returned in ProposalResult so the player sees exactly
    what's needed before committing.
    """
    label: str  # "Friendly standing with Architects"
    status: RequirementStatus
    detail: str = ""  # "Current: Neutral (need Friendly)"
    bypass: str | None = None  # "Use Ghost Networks contact instead"


class Risk(BaseModel):
    """
    A risk associated with taking an action.

    Risks are informational — they don't prevent the action,
    but they let the player make informed choices.
    """
    label: str  # "Ember Colonies will notice"
    severity: Literal["low", "medium", "high"]
    detail: str = ""  # "Standing may decrease by 1"


class CostPreview(BaseModel):
    """
    Preview of what an action will cost.

    All costs are shown before commitment. No hidden costs.
    """
    turns: int = 1  # Always 1 for commitments
    social_energy: int = 0
    credits: int = 0
    fuel: int = 0
    condition: int = 0  # Vehicle wear
    standing_changes: dict[str, int] = Field(default_factory=dict)
    # e.g., {"Ember Colonies": -1, "Lattice": +1}


class Alternative(BaseModel):
    """
    An alternative way to accomplish an action when requirements aren't met.

    Alternatives have their own costs — the question is never "can I?"
    but "what does it cost?" (Sentinel 2D §12).
    """
    label: str  # "Smuggler route through ruins"
    type: str  # "contact", "bribe", "risky"
    description: str
    additional_costs: CostPreview = Field(default_factory=CostPreview)
    consequence: str | None = None  # "architects_noticed"


class Proposal(BaseModel):
    """
    Player intent — a read-only query that triggers no mutation.

    The player is asking: "What would happen if I did this?"
    The engine answers with a ProposalResult.

    No action_id — this is not a commitment yet.
    """
    action_type: ActionType
    payload: dict = Field(default_factory=dict)
    # Payload varies by action_type:
    # travel: {"to": "appalachian_hollows"}
    # accept_job: {"template_id": "lattice_supply_run"}
    # call_favor: {"npc_id": "abc123", "favor_type": "ride"}
    # commit_attention: {"target": "npc_id or region or thread_id"}
    # recon: {"region": "gulf_passage"}
    # initiate_combat: {"target_npc_id": "xyz789"}


class ProposalResult(BaseModel):
    """
    Engine preview — what the action would cost and risk.

    This is the engine's answer to "What would happen if I did this?"
    It includes requirements, costs, risks, and alternatives.

    NO MUTATION occurs. The player can cancel with zero side effects.

    The UI renders this as a confirmation dialog:
    "Travel to Appalachian Hollows? Cost: 1 turn, 10 fuel.
     Risk: Ember Colonies will notice. [Commit] [Cancel]"
    """
    feasible: bool  # Can this action proceed (all requirements met or bypassable)?
    requirements: list[Requirement] = Field(default_factory=list)
    costs: CostPreview = Field(default_factory=CostPreview)
    risks: list[Risk] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    summary: str = ""  # Human-readable summary for UI
    # Which alternative the player chose (if any), set before committing
    chosen_alternative: str | None = None


class Action(BaseModel):
    """
    Committed intent — mutation authorized.

    Once a player reviews the ProposalResult and clicks "Commit",
    a Proposal becomes an Action with:
    - action_id: UUID for idempotency (invariant 4d)
    - state_version: Must match current campaign state_version
    - timestamp: When the commitment was made

    The engine will reject Actions with stale state_version.
    """
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: ActionType
    state_version: int  # Must match Campaign.state_version
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    # If an alternative was chosen during proposal review
    chosen_alternative: str | None = None

    @classmethod
    def from_proposal(
        cls,
        proposal: Proposal,
        state_version: int,
        chosen_alternative: str | None = None,
    ) -> "Action":
        """Create an Action from a reviewed Proposal."""
        return cls(
            action_type=proposal.action_type,
            state_version=state_version,
            payload=proposal.payload,
            chosen_alternative=chosen_alternative,
        )
