"""
Interrupt detection system for SENTINEL.

Scans campaign state for conditions that warrant NPC interrupts.
Stateless - regenerates candidates each check from existing state.

Interrupt triggers:
- DEMAND_DEADLINE: Leverage demands with upcoming or past deadlines
- NPC_SILENCE: NPCs with disposition WARM+ who haven't appeared in 3+ sessions
- THREAD_ESCALATION: MAJOR dormant threads that have aged 3+ sessions
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state.schema import Campaign


class InterruptTrigger(str, Enum):
    """Types of conditions that can trigger an NPC interrupt."""
    DEMAND_DEADLINE = "demand_deadline"
    NPC_SILENCE = "npc_silence"
    THREAD_ESCALATION = "thread_escalation"


class InterruptUrgency(str, Enum):
    """Urgency levels for interrupts (affects presentation)."""
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Priority ordering for urgency (higher = more important)
URGENCY_PRIORITY = {
    InterruptUrgency.CRITICAL: 3,
    InterruptUrgency.HIGH: 2,
    InterruptUrgency.MEDIUM: 1,
}


@dataclass
class InterruptCandidate:
    """
    A potential interrupt (not persisted).

    Candidates are regenerated each check from campaign state.
    They represent an NPC who has reason to interrupt the player.
    """
    npc_id: str
    npc_name: str
    faction: str
    trigger: InterruptTrigger
    urgency: InterruptUrgency
    context: str  # Injected into GM prompt to guide the interrupt

    @property
    def key(self) -> str:
        """Unique key for deduplication within a session."""
        return f"{self.npc_id}:{self.trigger.value}"


class InterruptDetector:
    """
    Detects interrupt-worthy conditions from campaign state.

    The detector is stateless with respect to campaign data - it regenerates
    candidates each check. The only state it maintains is which interrupts
    have been delivered this session to avoid repetition.
    """

    def __init__(self):
        # Track delivered interrupts per campaign per session
        # Key: campaign_id, Value: set of candidate keys delivered this session
        self._delivered_this_session: dict[str, set[str]] = {}

    def reset_session(self, campaign_id: str) -> None:
        """Clear delivered set for new session."""
        self._delivered_this_session[campaign_id] = set()

    def check_triggers(self, campaign: "Campaign") -> InterruptCandidate | None:
        """
        Check for interrupt conditions. Returns highest priority candidate.

        Scans campaign state for:
        1. Leverage demands with upcoming deadlines
        2. NPCs with 3+ session silence (WARM/LOYAL only)
        3. MAJOR dormant threads aged 3+ sessions

        Returns None if no interrupts are pending or all have been delivered.
        """
        if not campaign:
            return None

        campaign_id = campaign.meta.id
        session = campaign.meta.session_count

        # Gather all candidates from different triggers
        candidates: list[InterruptCandidate] = []

        candidates.extend(self._check_demand_deadlines(campaign, session))
        candidates.extend(self._check_npc_silence(campaign, session))
        candidates.extend(self._check_thread_escalation(campaign, session))

        if not candidates:
            return None

        # Filter out already-delivered
        delivered = self._delivered_this_session.get(campaign_id, set())
        candidates = [c for c in candidates if c.key not in delivered]

        if not candidates:
            return None

        # Sort by urgency priority (highest first), then by trigger type for stability
        candidates.sort(
            key=lambda c: (
                -URGENCY_PRIORITY.get(c.urgency, 0),
                c.trigger.value,
            )
        )

        return candidates[0]

    def mark_delivered(self, campaign_id: str, candidate: InterruptCandidate) -> None:
        """Mark an interrupt as delivered this session."""
        delivered = self._delivered_this_session.setdefault(campaign_id, set())
        delivered.add(candidate.key)

    def _check_demand_deadlines(
        self, campaign: "Campaign", session: int
    ) -> list[InterruptCandidate]:
        """
        Check for leverage demands with upcoming deadlines.

        Access demands via: campaign.characters -> enhancements -> leverage.pending_demand

        Trigger if: deadline_session - session <= 1
        Urgency: CRITICAL if deadline_session == session, else HIGH
        """
        from ..state.schema import Disposition

        candidates: list[InterruptCandidate] = []

        for char in campaign.characters:
            for enhancement in char.enhancements:
                demand = enhancement.leverage.pending_demand
                if not demand:
                    continue

                if demand.deadline_session is None:
                    continue

                sessions_until = demand.deadline_session - session

                # Only trigger if deadline is imminent (within 1 session) or passed
                if sessions_until > 1:
                    continue

                # Determine urgency
                if sessions_until <= 0:
                    urgency = InterruptUrgency.CRITICAL
                    context_prefix = "DEADLINE PASSED"
                else:
                    urgency = InterruptUrgency.HIGH
                    context_prefix = "DEADLINE IMMINENT"

                # Find an NPC to deliver the interrupt
                # Look for faction contacts in the NPC registry
                faction_npc = None
                for npc in campaign.npcs.active:
                    if npc.faction and npc.faction.value == demand.faction.value:
                        faction_npc = npc
                        break

                # If no faction NPC found, use a generic faction contact
                if faction_npc:
                    npc_id = faction_npc.id
                    npc_name = faction_npc.name
                else:
                    # Create a synthetic ID for the faction contact
                    npc_id = f"faction_contact_{demand.faction.value.lower().replace(' ', '_')}"
                    npc_name = f"{demand.faction.value} Contact"

                context = (
                    f"{context_prefix}: {demand.faction.value} demands '{demand.demand}' "
                    f"via {enhancement.name}. "
                )
                if demand.consequences:
                    context += f"If ignored: {'; '.join(demand.consequences)}"
                if demand.threat_basis:
                    context += f" They have leverage: {', '.join(demand.threat_basis)}"

                candidates.append(InterruptCandidate(
                    npc_id=npc_id,
                    npc_name=npc_name,
                    faction=demand.faction.value,
                    trigger=InterruptTrigger.DEMAND_DEADLINE,
                    urgency=urgency,
                    context=context,
                ))

        return candidates

    def _check_npc_silence(
        self, campaign: "Campaign", session: int
    ) -> list[InterruptCandidate]:
        """
        Check for NPCs who haven't appeared in 3+ sessions.

        Only for NPCs with disposition WARM or LOYAL.
        Access via: campaign.npcs.active
        Last interaction: npc.interactions[-1].session if npc.interactions else None

        Urgency: MEDIUM
        """
        from ..state.schema import Disposition

        candidates: list[InterruptCandidate] = []
        SILENCE_THRESHOLD = 3

        for npc in campaign.npcs.active:
            # Only check WARM or LOYAL NPCs
            if npc.disposition not in (Disposition.WARM, Disposition.LOYAL):
                continue

            # Get last interaction session
            if npc.interactions:
                last_session = npc.interactions[-1].session
            else:
                # If no interactions recorded, skip (can't determine silence)
                continue

            sessions_silent = session - last_session

            if sessions_silent < SILENCE_THRESHOLD:
                continue

            # Build context for the interrupt
            faction_name = npc.faction.value if npc.faction else "Independent"

            context = (
                f"NPC SILENCE: {npc.name} ({faction_name}) has been silent for "
                f"{sessions_silent} sessions. Disposition: {npc.disposition.value}. "
            )
            if npc.agenda:
                if npc.agenda.wants:
                    context += f"They want: {npc.agenda.wants}. "
                if npc.agenda.fears:
                    context += f"They fear: {npc.agenda.fears}. "

            if npc.last_interaction:
                context += f"Last seen: {npc.last_interaction}"

            candidates.append(InterruptCandidate(
                npc_id=npc.id,
                npc_name=npc.name,
                faction=faction_name,
                trigger=InterruptTrigger.NPC_SILENCE,
                urgency=InterruptUrgency.MEDIUM,
                context=context,
            ))

        return candidates

    def _check_thread_escalation(
        self, campaign: "Campaign", session: int
    ) -> list[InterruptCandidate]:
        """
        Check for dormant threads that have escalated.

        Access via: campaign.dormant_threads
        Trigger if: severity == MAJOR and (session - created_session) >= 3

        Note: threads don't always have an origin NPC. Skip if no associated NPC.

        Urgency: HIGH
        """
        from ..state.schema import ThreadSeverity

        candidates: list[InterruptCandidate] = []
        AGE_THRESHOLD = 3

        for thread in campaign.dormant_threads:
            # Only MAJOR threads trigger interrupts
            if thread.severity != ThreadSeverity.MAJOR:
                continue

            age = session - thread.created_session
            if age < AGE_THRESHOLD:
                continue

            # Try to find an associated NPC from the thread origin
            # The origin field often contains faction or NPC names
            associated_npc = None
            origin_lower = thread.origin.lower()

            # Check if origin mentions any active NPC by name
            for npc in campaign.npcs.active:
                if npc.name.lower() in origin_lower:
                    associated_npc = npc
                    break

            # If no NPC found, check for faction mentions
            if not associated_npc:
                from ..state.schema import FactionName
                for faction in FactionName:
                    if faction.value.lower() in origin_lower:
                        # Find any NPC from this faction
                        for npc in campaign.npcs.active:
                            if npc.faction == faction:
                                associated_npc = npc
                                break
                        if associated_npc:
                            break

            # Skip if no associated NPC found
            if not associated_npc:
                continue

            faction_name = associated_npc.faction.value if associated_npc.faction else "Independent"

            context = (
                f"THREAD ESCALATION: A major thread from '{thread.origin}' has aged "
                f"{age} sessions. Trigger condition: '{thread.trigger_condition}'. "
                f"Consequence: {thread.consequence}. "
                f"Associated NPC {associated_npc.name} may have news or warnings."
            )

            candidates.append(InterruptCandidate(
                npc_id=associated_npc.id,
                npc_name=associated_npc.name,
                faction=faction_name,
                trigger=InterruptTrigger.THREAD_ESCALATION,
                urgency=InterruptUrgency.HIGH,
                context=context,
            ))

        return candidates
