"""
Turn orchestrator for SENTINEL's turn-based engine.

Owns the phase state machine and sequences the turn pipeline:
    IDLE → PROPOSED → RESOLVING → RESOLVED → NARRATING → COMPLETE → IDLE

Design principles (from Sentinel 2D §16):
- Orchestrator sequences and delegates — it never resolves.
- State is persisted after RESOLVED, before NARRATING (invariant 4a).
- Actions during RESOLVING are rejected (concurrency lock).
- Each phase transition emits events via the EventBus.

Usage:
    orchestrator = TurnOrchestrator(campaign)

    # Player proposes an action
    result = orchestrator.propose(Proposal(action_type="travel", payload={"to": "gulf_passage"}))

    # Player reviews and commits
    turn_result = orchestrator.commit(
        Action.from_proposal(proposal, campaign.state_version)
    )
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Callable

from ..state.event_bus import get_event_bus, EventType
from ..state.schemas.action import (
    Action,
    Proposal,
    ProposalResult,
)
from ..state.schemas.turn_result import TurnResult
from ..state.schemas.event import TurnEvent

if TYPE_CHECKING:
    from ..state.schema import Campaign


class TurnPhase(str, Enum):
    """Phase state machine for a single turn."""
    IDLE = "idle"              # No turn in progress
    PROPOSED = "proposed"      # Player submitted proposal, reviewing ProposalResult
    RESOLVING = "resolving"    # Action committed, engine processing
    RESOLVED = "resolved"      # Resolution complete, state persisted
    NARRATING = "narrating"    # LLM generating flavor text (optional)
    COMPLETE = "complete"      # Turn fully complete, ready for next


# Valid phase transitions — each phase maps to allowed next phases
VALID_TRANSITIONS: dict[TurnPhase, set[TurnPhase]] = {
    TurnPhase.IDLE: {TurnPhase.PROPOSED},
    TurnPhase.PROPOSED: {TurnPhase.RESOLVING, TurnPhase.IDLE},  # Can cancel
    TurnPhase.RESOLVING: {TurnPhase.RESOLVED},
    TurnPhase.RESOLVED: {TurnPhase.NARRATING, TurnPhase.COMPLETE},  # Narration optional
    TurnPhase.NARRATING: {TurnPhase.COMPLETE},
    TurnPhase.COMPLETE: {TurnPhase.IDLE},
}


class TurnError(Exception):
    """Error during turn processing."""
    pass


class StaleStateError(TurnError):
    """Action's state_version doesn't match current state."""
    def __init__(self, expected: int, got: int):
        self.expected = expected
        self.got = got
        super().__init__(
            f"Stale state: expected version {expected}, got {got}. "
            "Re-propose to get fresh state."
        )


class InvalidPhaseError(TurnError):
    """Attempted operation not valid in current phase."""
    def __init__(self, current: TurnPhase, attempted: str):
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"Cannot {attempted} during {current.value} phase."
        )


# Type alias for resolver functions
# Resolver: (action, campaign, seed) -> (list[TurnEvent], dict_state_changes)
Resolver = Callable[["Action", "Campaign", int], tuple[list[TurnEvent], dict]]


class TurnOrchestrator:
    """
    Sequences the turn pipeline. Delegates, never resolves.

    Responsibilities:
    - Phase state machine enforcement
    - Concurrency lock (reject during RESOLVING)
    - Event emission for TUI reactivity
    - Coordinating validator, resolver, and cascade processor

    NOT responsible for:
    - Validating requirements (ActionValidator)
    - Resolving actions (typed Resolvers)
    - Processing cascades (CascadeProcessor)
    - Generating narrative (NarrativeAdapter)
    """

    def __init__(self, campaign: "Campaign"):
        self._campaign = campaign
        self._phase = TurnPhase.IDLE
        self._current_proposal: Proposal | None = None
        self._current_proposal_result: ProposalResult | None = None
        self._current_action: Action | None = None
        self._bus = get_event_bus()

        # Pluggable components (set by caller or registry)
        self._validator: Callable[[Proposal, "Campaign"], ProposalResult] | None = None
        self._resolvers: dict[str, Resolver] = {}
        self._cascade_processor: Callable | None = None
        self._persist_fn: Callable[["Campaign"], None] | None = None

    @property
    def phase(self) -> TurnPhase:
        """Current phase of the turn state machine."""
        return self._phase

    @property
    def campaign(self) -> "Campaign":
        return self._campaign

    def set_validator(
        self,
        validator: Callable[[Proposal, "Campaign"], ProposalResult],
    ) -> None:
        """Register the action validator."""
        self._validator = validator

    def register_resolver(self, action_type: str, resolver: Resolver) -> None:
        """Register a resolver for a specific action type."""
        self._resolvers[action_type] = resolver

    def set_cascade_processor(self, processor: Callable) -> None:
        """Register the cascade processor."""
        self._cascade_processor = processor

    def set_persist_fn(self, fn: Callable[["Campaign"], None]) -> None:
        """Register the persistence function (called after resolution)."""
        self._persist_fn = fn

    def _transition(self, to: TurnPhase) -> None:
        """Transition to a new phase, enforcing valid transitions."""
        if to not in VALID_TRANSITIONS.get(self._phase, set()):
            raise InvalidPhaseError(
                self._phase,
                f"transition to {to.value}",
            )
        self._phase = to

    # ─── Turn Pipeline ───────────────────────────────────────────

    def propose(self, proposal: Proposal) -> ProposalResult:
        """
        Phase 1: Player submits a proposal.

        Validates requirements, calculates costs, returns preview.
        No state mutation occurs.

        Args:
            proposal: The player's intended action

        Returns:
            ProposalResult with feasibility, costs, risks, alternatives

        Raises:
            InvalidPhaseError: If not in IDLE phase
        """
        if self._phase != TurnPhase.IDLE:
            raise InvalidPhaseError(self._phase, "propose")

        if self._validator is None:
            raise TurnError("No validator registered. Call set_validator() first.")

        # Validate and preview
        result = self._validator(proposal, self._campaign)

        # Store for commit reference
        self._current_proposal = proposal
        self._current_proposal_result = result

        # Transition
        self._transition(TurnPhase.PROPOSED)
        self._bus.emit(
            EventType.TURN_PROPOSED,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            action_type=proposal.action_type.value,
            feasible=result.feasible,
        )

        return result

    def cancel(self) -> None:
        """
        Cancel a proposal. Returns to IDLE with zero side effects.

        Can only be called during PROPOSED phase.
        """
        if self._phase != TurnPhase.PROPOSED:
            raise InvalidPhaseError(self._phase, "cancel")

        self._current_proposal = None
        self._current_proposal_result = None
        self._transition(TurnPhase.IDLE)

    def commit(self, action: Action) -> TurnResult:
        """
        Phase 2-4: Commit an action and resolve it.

        This is the commitment gate. Once called:
        1. Validates state_version (idempotency check)
        2. Transitions to RESOLVING (locks against concurrent actions)
        3. Runs the typed resolver
        4. Runs cascade processing
        5. Persists state (invariant 4a: before narrative)
        6. Returns TurnResult

        Args:
            action: The committed action with action_id and state_version

        Returns:
            TurnResult with events, state_snapshot, and narrative hooks

        Raises:
            InvalidPhaseError: If not in PROPOSED phase
            StaleStateError: If state_version doesn't match
            TurnError: If no resolver registered for this action type
        """
        if self._phase != TurnPhase.PROPOSED:
            raise InvalidPhaseError(self._phase, "commit")

        # Idempotency check (invariant 4d)
        if action.state_version != self._campaign.state_version:
            # Reset to IDLE so player can re-propose
            self._current_proposal = None
            self._current_proposal_result = None
            self._phase = TurnPhase.IDLE
            raise StaleStateError(
                expected=self._campaign.state_version,
                got=action.state_version,
            )

        # Lock: enter RESOLVING
        self._current_action = action
        self._transition(TurnPhase.RESOLVING)
        self._bus.emit(
            EventType.TURN_RESOLVING,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            action_id=action.action_id,
            action_type=action.action_type.value,
        )

        # Resolve
        resolver = self._resolvers.get(action.action_type.value)
        if resolver is None:
            raise TurnError(
                f"No resolver registered for action type: {action.action_type.value}"
            )

        # Generate seed for deterministic resolution (invariant 4b)
        seed = hash(action.action_id) % (2**31)

        # Resolution is a pure function: (action, state, seed) -> (events, changes)
        events, _ = resolver(action, self._campaign, seed)

        # Increment state version and turn count
        self._campaign.state_version += 1
        self._campaign.turn_count += 1

        # Run cascade processing if registered
        cascade_notices = []
        if self._cascade_processor and events:
            for event in list(events):  # Iterate copy since cascades may add
                cascade_events, notices = self._cascade_processor(
                    event, self._campaign,
                )
                events.extend(cascade_events)
                cascade_notices.extend(notices)

        # Remove surfaced dormant threads (deferred from CascadeProcessor)
        surfaced_thread_ids = {
            e.payload.get("thread_id")
            for e in events
            if e.event_type == "thread.surfaced" and e.payload.get("thread_id")
        }
        if surfaced_thread_ids:
            self._campaign.dormant_threads = [
                t for t in self._campaign.dormant_threads
                if t.id not in surfaced_thread_ids
            ]

        # Transition to RESOLVED
        self._transition(TurnPhase.RESOLVED)
        self._bus.emit(
            EventType.TURN_RESOLVED,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            action_id=action.action_id,
            event_count=len(events),
        )

        # Persist state BEFORE narrative (invariant 4a)
        if self._persist_fn:
            self._persist_fn(self._campaign)

        # Build state snapshot for UI
        state_snapshot = self._build_snapshot()

        # Build narrative hooks from events
        narrative_hooks = [e.summary for e in events if e.summary]

        # Build result
        turn_result = TurnResult(
            action_id=action.action_id,
            success=True,
            state_version=self._campaign.state_version,
            events=events,
            state_snapshot=state_snapshot,
            seed=seed,
            narrative_hooks=narrative_hooks,
            cascade_notices=[n if isinstance(n, dict) else n.model_dump() for n in cascade_notices],
            turn_number=self._campaign.turn_count,
        )

        # Skip narrating, go straight to complete (narration is optional)
        self._transition(TurnPhase.COMPLETE)

        # Emit turn end
        self._bus.emit(
            EventType.TURN_END,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            action_id=action.action_id,
            turn_number=self._campaign.turn_count,
        )

        # Reset for next turn
        self._complete_turn()

        return turn_result

    def _complete_turn(self) -> None:
        """Reset orchestrator state for the next turn."""
        self._transition(TurnPhase.IDLE)
        self._current_proposal = None
        self._current_proposal_result = None
        self._current_action = None

    def _build_snapshot(self) -> dict:
        """
        Build a state snapshot for the UI.

        This is the authoritative state that the UI renders from.
        Contains only what the UI needs — not the full campaign.
        """
        campaign = self._campaign
        snapshot: dict = {
            "turn_count": campaign.turn_count,
            "state_version": campaign.state_version,
            "region": campaign.region.value if campaign.region else None,
            "location": campaign.location.value if campaign.location else None,
        }

        # Character summary
        if campaign.characters:
            char = campaign.characters[0]
            snapshot["character"] = {
                "name": char.name,
                "credits": char.credits,
                "social_energy": char.social_energy.current,
                "social_state": char.social_energy.state,
            }

        # Faction standings
        snapshot["factions"] = {}
        for faction_name in [
            "nexus", "ember_colonies", "lattice", "convergence",
            "covenant", "wanderers", "cultivators", "steel_syndicate",
            "witnesses", "architects", "ghost_networks",
        ]:
            standing = getattr(campaign.factions, faction_name, None)
            if standing:
                snapshot["factions"][standing.faction.value] = standing.standing.value

        # Map state
        snapshot["map"] = {
            "current_region": campaign.map_state.current_region.value,
            "regions": {
                r.value: {
                    "connectivity": s.connectivity.value,
                    "npcs_met": len(s.npcs_met),
                }
                for r, s in campaign.map_state.regions.items()
            },
        }

        return snapshot
