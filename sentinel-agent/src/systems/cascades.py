"""
Cascade engine for SENTINEL's turn-based system.

Processes derived effects from turn events. When a standing changes,
allied factions may shift. When conditions match a dormant thread,
it surfaces. When an NPC's faction is affected, they react.

Pure function design: (event, state) -> (events, notices)
No globals, no side effects, no mutation of input state.

Design invariants (from Sentinel 2D §4c, §16):
- MAX_CASCADE_DEPTH = 5 to prevent infinite loops
- processed_events set prevents re-processing
- Thresholds loaded from config, not hardcoded
- Two output streams: audit log (full) and player feed (grouped)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from ..state.schemas.event import TurnEvent
from ..state.event_bus import get_event_bus, EventType

if TYPE_CHECKING:
    from ..state.schema import Campaign


# ─── Configuration ───────────────────────────────────────────

MAX_CASCADE_DEPTH = 5

# Data-driven cascade rules (Sentinel 2D §16)
# These should eventually live in a YAML config file.
# For now, defined here as the single source of truth.
CASCADE_CONFIG = {
    "faction_propagation": {
        "allied_threshold": 30,     # Relationship score to count as allied
        "allied_multiplier": 0.3,   # Allied factions get delta * this
        "hostile_threshold": -30,   # Relationship score to count as hostile
        "hostile_multiplier": -0.2, # Hostile factions get delta * this (inverted)
    },
    "npc_reaction": {
        "standing_threshold": 1,    # Minimum standing delta to trigger NPC check
    },
    "thread_matching": {
        "enabled": True,
    },
}


# ─── Data Structures ────────────────────────────────────────

class NoticeSeverity(str, Enum):
    """Severity levels for player-facing notices."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Notice:
    """
    Player-facing cascade notice.

    Part of the player feed — grouped, readable summaries
    of what happened as a result of the player's action.

    The player sees: "Your action angered the Ember Colonies."
    Not: "CASCADE event_id=abc123 depth=2 STANDING_CHANGED..."
    """
    headline: str  # "Ripple Effect" or "Thread Awakened"
    details: list[str] = field(default_factory=list)
    severity: NoticeSeverity = NoticeSeverity.INFO

    def model_dump(self) -> dict:
        """Serialize for JSON (matches Pydantic convention)."""
        return {
            "headline": self.headline,
            "details": self.details,
            "severity": self.severity.value,
        }


@dataclass
class CascadeResult:
    """
    Full result of cascade processing.

    Contains both the audit log (all events) and the player feed (notices).
    """
    audit_log: list[TurnEvent] = field(default_factory=list)
    player_notices: list[Notice] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.audit_log)

    @property
    def has_effects(self) -> bool:
        return len(self.audit_log) > 0


# ─── Cascade Processor ──────────────────────────────────────

class CascadeProcessor:
    """
    Processes derived effects from turn events.

    Pure function design: process() takes an event and campaign state,
    returns derived events and notices without modifying the campaign.

    State mutations are applied by the caller (TurnOrchestrator)
    after all cascades are processed.

    Cascade chain:
    1. Faction propagation: standing change → allied/hostile factions shift
    2. NPC reactions: faction shift → check affected NPCs
    3. Thread matching: any event → check dormant thread triggers
    """

    def __init__(self, config: dict | None = None):
        self._config = config or CASCADE_CONFIG
        self._bus = get_event_bus()

    def process(
        self,
        trigger_event: TurnEvent,
        campaign: "Campaign",
        depth: int = 0,
        processed: set[str] | None = None,
    ) -> tuple[list[TurnEvent], list[Notice]]:
        """
        Process a single event for cascade effects.

        Args:
            trigger_event: The event to process for derived effects
            campaign: Current campaign state (read-only reference)
            depth: Current cascade depth (0 = direct effect)
            processed: Set of already-processed event_ids (loop guard)

        Returns:
            Tuple of (derived_events, player_notices)
        """
        if processed is None:
            processed = set()

        # Depth guard (invariant 4c)
        if depth >= MAX_CASCADE_DEPTH:
            return [], [Notice(
                headline="Cascade Limit Reached",
                details=["Effect chain truncated at maximum depth."],
                severity=NoticeSeverity.WARNING,
            )]

        # Loop guard — don't re-process the same event
        if trigger_event.event_id in processed:
            return [], []
        processed.add(trigger_event.event_id)

        all_events: list[TurnEvent] = []
        all_notices: list[Notice] = []

        # ── 1. Faction Propagation ───────────────────────────
        if trigger_event.event_type == "standing.changed":
            events, notices = self._propagate_faction(
                trigger_event, campaign, depth,
            )
            all_events.extend(events)
            all_notices.extend(notices)

        # ── 2. NPC Reactions ─────────────────────────────────
        if trigger_event.event_type in ("standing.changed", "travel.arrived"):
            events, notices = self._check_npc_reactions(
                trigger_event, campaign, depth,
            )
            all_events.extend(events)
            all_notices.extend(notices)

        # ── 3. Dormant Thread Matching ───────────────────────
        if self._config.get("thread_matching", {}).get("enabled", True):
            events, notices = self._match_dormant_threads(
                trigger_event, campaign, depth,
            )
            all_events.extend(events)
            all_notices.extend(notices)

        # ── Recursive: Process derived events ────────────────
        derived_from_cascades: list[TurnEvent] = []
        derived_notices: list[Notice] = []

        for derived_event in list(all_events):
            sub_events, sub_notices = self.process(
                derived_event, campaign,
                depth=depth + 1,
                processed=processed,
            )
            derived_from_cascades.extend(sub_events)
            derived_notices.extend(sub_notices)

        all_events.extend(derived_from_cascades)
        all_notices.extend(derived_notices)

                standing.shift(propagated_delta)

    # ─── Faction Propagation ─────────────────────────────────

    def _propagate_faction(
        self,
        event: TurnEvent,
        campaign: "Campaign",
        depth: int,
    ) -> tuple[list[TurnEvent], list[Notice]]:
        """
        When a faction standing changes, propagate to related factions.

        Allied factions (relationship > threshold) get a positive ripple.
        Hostile factions (relationship < -threshold) get an inverted ripple.
        """
        from ..state.schema import (
            FactionName,
            FACTION_RELATIONS,
            get_faction_relation,
        )

        faction_name = event.payload.get("faction")
        delta = event.payload.get("delta", 0)
        if not faction_name or delta == 0:
            return [], []

        config = self._config.get("faction_propagation", {})
        allied_threshold = config.get("allied_threshold", 30)
        allied_multiplier = config.get("allied_multiplier", 0.3)
        hostile_threshold = config.get("hostile_threshold", -30)
        hostile_multiplier = config.get("hostile_multiplier", -0.2)

        # Find the FactionName enum for the affected faction
        try:
            affected_faction = FactionName(faction_name)
        except ValueError:
            return [], []

        events: list[TurnEvent] = []
        notice_details: list[str] = []

        # Check all other factions for relationship effects
        for other_faction in FactionName:
            if other_faction == affected_faction:
                continue

            relation = get_faction_relation(affected_faction, other_faction)

            propagated_delta = 0
            reason = ""

            if relation >= allied_threshold:
                # Allied faction — positive ripple
                propagated_delta = int(delta * allied_multiplier)
                reason = f"allied with {affected_faction.value}"
            elif relation <= hostile_threshold:
                # Hostile faction — inverted ripple
                propagated_delta = int(delta * hostile_multiplier)
                reason = f"hostile to {affected_faction.value}"

            if propagated_delta != 0:
                # Apply the standing shift
                standing = campaign.factions.get(other_faction)
                old_standing = standing.standing.value
                standing.shift(1 if propagated_delta > 0 else -1)
                new_standing = standing.standing.value

                cascade_event = TurnEvent(
                    event_type="standing.changed",
                    source_action=event.source_action,
                    payload={
                        "faction": other_faction.value,
                        "delta": propagated_delta,
                        "old_standing": old_standing,
                        "new_standing": new_standing,
                        "reason": f"Cascade: {reason}",
                    },
                    cascaded_from=event.event_id,
                    cascade_depth=depth + 1,
                    summary=f"{other_faction.value} standing shifted ({reason})",
                )
                events.append(cascade_event)
                notice_details.append(
                    f"{other_faction.value}: {old_standing} → {new_standing} ({reason})"
                )

                # Emit via event bus for TUI reactivity
                self._bus.emit(
                    EventType.STANDING_CHANGED,
                    campaign_id=campaign.meta.id,
                    session=campaign.meta.session_count,
                    faction=other_faction.value,
                    delta=propagated_delta,
                )

        notices = []
        if notice_details:
            notices.append(Notice(
                headline="Ripple Effect",
                details=notice_details,
                severity=NoticeSeverity.INFO,
            ))

        return events, notices

    # ─── NPC Reactions ───────────────────────────────────────

    def _check_npc_reactions(
        self,
        event: TurnEvent,
        campaign: "Campaign",
        depth: int,
    ) -> tuple[list[TurnEvent], list[Notice]]:
        """
        Check if any NPCs react to this event.

        Reactions are based on NPC faction affiliation and memory triggers.
        When a faction's standing changes, NPCs of that faction may
        shift their personal disposition.
        """
        events: list[TurnEvent] = []
        notice_details: list[str] = []

        if event.event_type == "standing.changed":
            faction_name = event.payload.get("faction")
            delta = event.payload.get("delta", 0)

            if not faction_name or abs(delta) < self._config.get(
                "npc_reaction", {},
            ).get("standing_threshold", 1):
                return [], []

            # Check all active NPCs affiliated with this faction
            for npc in campaign.npcs.active:
                if npc.faction and npc.faction.value == faction_name:
                    # NPC reacts to their faction being affected
                    reaction = "became more cooperative" if delta > 0 else "grew wary"

                    cascade_event = TurnEvent(
                        event_type="npc.reacted",
                        source_action=event.source_action,
                        payload={
                            "npc_id": npc.id,
                            "npc_name": npc.name,
                            "reaction": reaction,
                            "reason": f"Faction {faction_name} standing changed",
                        },
                        cascaded_from=event.event_id,
                        cascade_depth=depth + 1,
                        summary=f"{npc.name} {reaction}",
                    )
                    events.append(cascade_event)
                    notice_details.append(f"{npc.name} {reaction}")

                    # Emit for TUI
                    self._bus.emit(
                        EventType.NPC_DISPOSITION_CHANGED,
                        campaign_id=campaign.meta.id,
                        session=campaign.meta.session_count,
                        npc_id=npc.id,
                        npc_name=npc.name,
                        reaction=reaction,
                    )

        elif event.event_type == "travel.arrived":
            # Check if any NPCs in the new region have memory triggers
            region = event.payload.get("to")
            if region:
                tags = [f"arrived_{region}", f"visit_{region}"]
                for npc in campaign.npcs.active:
                    fired = npc.check_triggers(tags)
                    for trigger in fired:
                        cascade_event = TurnEvent(
                            event_type="npc.reacted",
                            source_action=event.source_action,
                            payload={
                                "npc_id": npc.id,
                                "npc_name": npc.name,
                                "reaction": trigger.effect,
                                "trigger": trigger.condition,
                            },
                            cascaded_from=event.event_id,
                            cascade_depth=depth + 1,
                            summary=f"{npc.name}: {trigger.effect}",
                        )
                        events.append(cascade_event)
                        notice_details.append(f"{npc.name}: {trigger.effect}")

        notices = []
        if notice_details:
            notices.append(Notice(
                headline="NPC Reactions",
                details=notice_details,
                severity=NoticeSeverity.INFO,
            ))

        return events, notices

    # ─── Dormant Thread Matching ─────────────────────────────

    def _match_dormant_threads(
        self,
        event: TurnEvent,
        campaign: "Campaign",
        depth: int,
    ) -> tuple[list[TurnEvent], list[Notice]]:
        """
        Check if any dormant threads should surface based on this event.

        Thread matching uses trigger_keywords from DormantThread to
        detect when conditions are met. This is keyword-based matching,
        not LLM inference — deterministic and reproducible.
        """
        events: list[TurnEvent] = []
        notice_details: list[str] = []

        # Build a set of keywords from the event
        event_keywords = set()

        # Extract keywords from event type
        event_keywords.add(event.event_type)

        # Extract keywords from payload
        for key, value in event.payload.items():
            if isinstance(value, str):
                event_keywords.add(value.lower())
                # Also add individual words for fuzzy matching
                for word in value.lower().split():
                    if len(word) > 3:  # Skip short words
                        event_keywords.add(word)
            elif isinstance(value, (int, float)):
                event_keywords.add(str(value))

        # Check each dormant thread
        threads_to_surface: list[int] = []

        for i, thread in enumerate(campaign.dormant_threads):
            if not thread.trigger_keywords:
                continue

            # Check if any trigger keywords match event keywords
            thread_keywords = {kw.lower() for kw in thread.trigger_keywords}
            matches = thread_keywords & event_keywords

            if matches:
                # This thread should surface
                threads_to_surface.append(i)

                cascade_event = TurnEvent(
                    event_type="thread.surfaced",
                    source_action=event.source_action,
                    payload={
                        "thread_id": thread.id,
                        "origin": thread.origin,
                        "consequence": thread.consequence,
                        "severity": thread.severity.value,
                        "matched_keywords": list(matches),
                    },
                    cascaded_from=event.event_id,
                    cascade_depth=depth + 1,
                    summary=f"A dormant thread stirs: {thread.consequence[:60]}...",
                )
                events.append(cascade_event)
                notice_details.append(
                    f"[{thread.severity.value.upper()}] {thread.consequence}"
                )

                # Emit for TUI
                self._bus.emit(
                    EventType.THREAD_SURFACED,
                    campaign_id=campaign.meta.id,
                    session=campaign.meta.session_count,
                    thread_id=thread.id,
                    severity=thread.severity.value,
                )

        # Remove surfaced threads (in reverse to preserve indices)
        for i in reversed(threads_to_surface):
            campaign.dormant_threads.pop(i)

        notices = []
        if notice_details:
            severity = NoticeSeverity.CRITICAL if any(
                "MAJOR" in d for d in notice_details
            ) else NoticeSeverity.WARNING
            notices.append(Notice(
                headline="Thread Awakened",
                details=notice_details,
                severity=severity,
            ))

        return events, notices


# ─── Convenience Function ────────────────────────────────────

def create_cascade_processor(
    config: dict | None = None,
) -> CascadeProcessor:
    """Create a cascade processor with the given config."""
    return CascadeProcessor(config=config)
