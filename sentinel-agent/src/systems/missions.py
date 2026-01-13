"""
Mission system for SENTINEL.

Handles time-sensitive story missions with urgency tiers and escalation.
Unlike jobs (transactional work-for-hire), missions are organic story
opportunities that come with deadlines and consequences.

Urgency tiers:
- ROUTINE: No deadline, opportunity passes quietly
- PRESSING: 2 sessions, minor consequence if ignored
- URGENT: 1 session, dormant thread created
- CRITICAL: This session only, immediate fallout
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..state.schema import (
    DormantThread,
    FactionName,
    MissionOffer,
    ThreadSeverity,
    Urgency,
)
from ..state.event_bus import get_event_bus, EventType

if TYPE_CHECKING:
    from ..state.manager import CampaignManager


# Deadline sessions by urgency (None = no deadline)
URGENCY_DEADLINES: dict[Urgency, int | None] = {
    Urgency.ROUTINE: None,      # No deadline
    Urgency.PRESSING: 2,        # 2 sessions from offer
    Urgency.URGENT: 1,          # 1 session from offer
    Urgency.CRITICAL: 0,        # This session only
}

# Standing penalty when ignoring missions
URGENCY_STANDING_PENALTY: dict[Urgency, int] = {
    Urgency.ROUTINE: 0,         # No penalty
    Urgency.PRESSING: -1,       # Minor
    Urgency.URGENT: -2,         # Moderate
    Urgency.CRITICAL: -3,       # Significant
}

# Thread severity when creating dormant threads from ignored missions
URGENCY_THREAD_SEVERITY: dict[Urgency, ThreadSeverity] = {
    Urgency.ROUTINE: ThreadSeverity.MINOR,
    Urgency.PRESSING: ThreadSeverity.MINOR,
    Urgency.URGENT: ThreadSeverity.MODERATE,
    Urgency.CRITICAL: ThreadSeverity.MAJOR,
}


class MissionSystem:
    """
    Manages time-sensitive mission offers.

    Missions are story-driven opportunities with deadlines. When deadlines
    pass without player action, consequences trigger:
    - Faction standing loss
    - Dormant threads created
    - NPC disposition shifts
    """

    def __init__(self, manager: "CampaignManager"):
        self.manager = manager

    @property
    def _campaign(self):
        return self.manager.current

    def get_current_session(self) -> int:
        """Get current session number."""
        return self._campaign.meta.session_count if self._campaign else 0

    # -------------------------------------------------------------------------
    # Offer Management
    # -------------------------------------------------------------------------

    def create_offer(
        self,
        title: str,
        situation: str,
        requestor: str,
        stakes: str,
        consequence_if_ignored: str,
        urgency: Urgency = Urgency.PRESSING,
        faction: FactionName | None = None,
        requestor_npc_id: str | None = None,
    ) -> MissionOffer:
        """
        Create a new mission offer.

        Args:
            title: Short mission title
            situation: What's happening
            requestor: Who's asking (NPC name or faction)
            stakes: What's at stake
            consequence_if_ignored: What happens if deadline passes
            urgency: Urgency tier (determines deadline)
            faction: Requesting faction (for standing penalties)
            requestor_npc_id: Link to NPC if applicable

        Returns:
            The created MissionOffer
        """
        current_session = self.get_current_session()
        deadline_offset = URGENCY_DEADLINES.get(urgency)

        offer = MissionOffer(
            title=title,
            situation=situation,
            requestor=requestor,
            requestor_npc_id=requestor_npc_id,
            faction=faction,
            urgency=urgency,
            offered_session=current_session,
            deadline_session=(
                current_session + deadline_offset
                if deadline_offset is not None
                else None
            ),
            stakes=stakes,
            consequence_if_ignored=consequence_if_ignored,
        )

        self._campaign.mission_offers.append(offer)
        self.manager.save_campaign()

        # Emit event for UI
        bus = get_event_bus()
        bus.emit(EventType.STATE_CHANGED, {
            "type": "mission_offer",
            "title": title,
            "urgency": urgency.value,
        })

        return offer

    def get_pending_offers(self) -> list[MissionOffer]:
        """Get all pending (not accepted, declined, or expired) mission offers."""
        return [
            offer for offer in self._campaign.mission_offers
            if not offer.accepted and not offer.declined and not offer.expired
        ]

    def get_offer_by_id(self, offer_id: str) -> MissionOffer | None:
        """Find a mission offer by ID."""
        for offer in self._campaign.mission_offers:
            if offer.id == offer_id:
                return offer
        return None

    def accept_offer(self, offer_id: str) -> dict:
        """
        Accept a mission offer.

        Returns dict with result or error.
        """
        offer = self.get_offer_by_id(offer_id)
        if not offer:
            return {"error": "Mission offer not found"}

        if offer.accepted:
            return {"error": "Mission already accepted"}

        if offer.expired:
            return {"error": "Mission offer has expired"}

        current_session = self.get_current_session()
        if offer.is_expired(current_session):
            offer.expired = True
            return {"error": "Mission deadline has passed"}

        offer.accepted = True
        self.manager.save_campaign()

        return {
            "success": True,
            "offer": offer,
            "message": f"Accepted mission: {offer.title}",
        }

    def decline_offer(self, offer_id: str) -> dict:
        """
        Explicitly decline a mission offer.

        Declining is different from ignoring — it's a conscious choice.
        May still have consequences for CRITICAL missions.
        """
        offer = self.get_offer_by_id(offer_id)
        if not offer:
            return {"error": "Mission offer not found"}

        offer.declined = True
        self.manager.save_campaign()

        return {
            "success": True,
            "offer": offer,
            "message": f"Declined mission: {offer.title}",
        }

    # -------------------------------------------------------------------------
    # Deadline Checking & Escalation
    # -------------------------------------------------------------------------

    def check_deadlines(self) -> list[dict]:
        """
        Check all pending offers for expired deadlines.

        Call this at session boundaries (end of session or start of new one).
        Returns list of triggered consequences.
        """
        current_session = self.get_current_session()
        consequences = []

        for offer in self._campaign.mission_offers:
            # Skip already processed offers
            if offer.accepted or offer.declined or offer.expired:
                continue

            # Check if deadline passed
            if offer.is_expired(current_session):
                consequence = self._trigger_escalation(offer)
                consequences.append(consequence)

        if consequences:
            self.manager.save_campaign()

        return consequences

    def _trigger_escalation(self, offer: MissionOffer) -> dict:
        """
        Trigger escalation for an expired mission offer.

        Creates consequences based on urgency tier:
        - Standing loss with requesting faction
        - Dormant thread created
        - NPC disposition shift (if applicable)
        """
        offer.expired = True
        offer.consequence_triggered = True

        result = {
            "offer_id": offer.id,
            "title": offer.title,
            "urgency": offer.urgency.value,
            "consequence": offer.consequence_if_ignored,
            "effects": [],
        }

        # 1. Faction standing penalty
        if offer.faction:
            penalty = URGENCY_STANDING_PENALTY.get(offer.urgency, 0)
            if penalty != 0:
                self.manager.shift_faction(offer.faction, penalty)
                result["effects"].append({
                    "type": "standing_loss",
                    "faction": offer.faction.value,
                    "delta": penalty,
                })

        # 2. Create dormant thread (for URGENT and CRITICAL)
        if offer.urgency in (Urgency.URGENT, Urgency.CRITICAL):
            severity = URGENCY_THREAD_SEVERITY.get(offer.urgency, ThreadSeverity.MODERATE)
            thread = DormantThread(
                origin=f"Ignored mission: {offer.title}",
                trigger_condition=f"When {offer.requestor} or their associates are encountered",
                consequence=offer.consequence_if_ignored,
                severity=severity,
                created_session=self.get_current_session(),
                trigger_keywords=[
                    offer.requestor.lower(),
                    offer.faction.value.lower() if offer.faction else "",
                ],
            )
            self._campaign.dormant_threads.append(thread)
            result["effects"].append({
                "type": "dormant_thread",
                "thread_id": thread.id,
                "severity": severity.value,
            })

        # 3. NPC disposition shift (if NPC-linked)
        if offer.requestor_npc_id:
            npc = self._campaign.npcs.get(offer.requestor_npc_id)
            if npc:
                # Shift disposition negatively based on urgency
                from ..state.schema import Disposition
                dispositions = list(Disposition)
                current_idx = dispositions.index(npc.disposition)
                shift = -1 if offer.urgency == Urgency.PRESSING else -2
                new_idx = max(0, current_idx + shift)
                npc.disposition = dispositions[new_idx]
                result["effects"].append({
                    "type": "npc_disposition",
                    "npc_id": npc.id,
                    "npc_name": npc.name,
                    "new_disposition": npc.disposition.value,
                })

        # Emit event
        bus = get_event_bus()
        bus.emit(EventType.STATE_CHANGED, {
            "type": "mission_expired",
            "title": offer.title,
            "consequence": offer.consequence_if_ignored,
        })

        return result

    # -------------------------------------------------------------------------
    # Display Helpers
    # -------------------------------------------------------------------------

    def get_urgency_indicator(self, urgency: Urgency) -> str:
        """Get visual indicator for urgency level."""
        indicators = {
            Urgency.ROUTINE: "○",      # Open circle
            Urgency.PRESSING: "◐",     # Half circle
            Urgency.URGENT: "●",       # Filled circle
            Urgency.CRITICAL: "◉",     # Double circle
        }
        return indicators.get(urgency, "○")

    def get_deadline_text(self, offer: MissionOffer) -> str:
        """Get human-readable deadline text."""
        current = self.get_current_session()

        if offer.deadline_session is None:
            return "No deadline"

        remaining = offer.deadline_session - current
        if remaining < 0:
            return "EXPIRED"
        elif remaining == 0:
            return "THIS SESSION"
        elif remaining == 1:
            return "Next session"
        else:
            return f"{remaining} sessions"

    def format_offer_summary(self, offer: MissionOffer) -> str:
        """Format a mission offer for display."""
        indicator = self.get_urgency_indicator(offer.urgency)
        deadline = self.get_deadline_text(offer)
        return f"{indicator} {offer.title} [{deadline}] — {offer.requestor}"
