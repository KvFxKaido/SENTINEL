"""Action schemas for the Commitment Gate pipeline."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    TRAVEL = "travel"
    ACCEPT_JOB = "accept_job"
    COMPLETE_JOB = "complete_job"
    CALL_FAVOR = "call_favor"
    COMMIT_ATTENTION = "commit_attention"
    RECON = "recon"
    INITIATE_COMBAT = "initiate_combat"
    LOCAL = "local"


class RequirementStatus(str, Enum):
    MET = "met"
    UNMET = "unmet"
    BYPASSABLE = "bypassable"


class Requirement(BaseModel):
    label: str
    status: RequirementStatus
    detail: str = ""
    bypass: str | None = None


class Risk(BaseModel):
    label: str
    severity: Literal["low", "medium", "high"]
    detail: str = ""


class CostPreview(BaseModel):
    turns: int = 1
    social_energy: int = 0
    credits: int = 0
    fuel: int = 0
    condition: int = 0
    standing_changes: dict[str, int] = Field(default_factory=dict)


class Alternative(BaseModel):
    label: str
    type: str
    description: str
    additional_costs: CostPreview = Field(default_factory=CostPreview)
    consequence: str | None = None


class Proposal(BaseModel):
    action_type: ActionType
    payload: dict = Field(default_factory=dict)


class ProposalResult(BaseModel):
    feasible: bool
    requirements: list[Requirement] = Field(default_factory=list)
    costs: CostPreview = Field(default_factory=CostPreview)
    risks: list[Risk] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    summary: str = ""
    chosen_alternative: str | None = None


class Action(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: ActionType
    state_version: int
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    chosen_alternative: str | None = None

    @classmethod
    def from_proposal(
        cls,
        proposal: Proposal,
        state_version: int,
        chosen_alternative: str | None = None,
    ) -> "Action":
        return cls(
            action_type=proposal.action_type,
            state_version=state_version,
            payload=proposal.payload,
            chosen_alternative=chosen_alternative,
        )
