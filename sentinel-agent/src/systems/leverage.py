"""
Enhancement and leverage system for SENTINEL.

Handles enhancement grants, refusals, leverage calls, and demands.
Extracted from manager.py to separate domain logic from persistence.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from ..state.schema import (
    FactionName,
    HistoryType,
    LeverageDemand,
    LeverageWeight,
)
from ..lore.chunker import extract_keywords

if TYPE_CHECKING:
    from ..state.manager import CampaignManager
    from ..state.schema import Enhancement, RefusedEnhancement


# Factions that can grant enhancements (Wanderers and Cultivators don't)
ENHANCEMENT_FACTIONS = [
    FactionName.NEXUS,
    FactionName.EMBER_COLONIES,
    FactionName.LATTICE,
    FactionName.CONVERGENCE,
    FactionName.COVENANT,
    FactionName.STEEL_SYNDICATE,
    FactionName.WITNESSES,
    FactionName.ARCHITECTS,
    FactionName.GHOST_NETWORKS,
]


class LeverageSystem:
    """
    Manages enhancement grants, refusals, and leverage mechanics.

    Requires a CampaignManager for state access and persistence.
    """

    def __init__(self, manager: "CampaignManager"):
        self.manager = manager

    @property
    def _campaign(self):
        return self.manager.current

    def grant_enhancement(
        self,
        character_id: str,
        name: str,
        source: FactionName,
        benefit: str,
        cost: str,
    ) -> "Enhancement":
        """
        Grant an enhancement to a character.

        Sets up leverage tracking with session info.
        Raises ValueError if faction doesn't offer enhancements.
        """
        from ..state.schema import Enhancement

        if not self._campaign:
            raise ValueError("No campaign loaded")

        if source not in ENHANCEMENT_FACTIONS:
            raise ValueError(
                f"{source.value} does not offer enhancements. "
                "Wanderers and Cultivators resist permanent ties."
            )

        char = self.manager.get_character(character_id)
        if not char:
            raise ValueError(f"Character not found: {character_id}")

        # Extract keywords for hint matching
        keywords = list(extract_keywords(
            f"{name} {benefit} {source.value}"
        ))[:8]

        enhancement = Enhancement(
            name=name,
            source=source,
            benefit=benefit,
            cost=cost,
            granted_session=self._campaign.meta.session_count,
            leverage_keywords=keywords,
        )

        char.enhancements.append(enhancement)

        # Log as hinge moment (enhancement acceptance is irreversible)
        self.manager.log_history(
            type=HistoryType.HINGE,
            summary=f"Accepted {source.value} enhancement: {name}",
            is_permanent=True,
        )

        self.manager.save_campaign()
        return enhancement

    def refuse_enhancement(
        self,
        character_id: str,
        name: str,
        source: FactionName,
        benefit: str,
        reason_refused: str,
    ) -> "RefusedEnhancement":
        """
        Record a refused enhancement offer.

        Refusal is meaningful — it builds reputation that NPCs react to.
        """
        from ..state.schema import RefusedEnhancement

        if not self._campaign:
            raise ValueError("No campaign loaded")

        char = self.manager.get_character(character_id)
        if not char:
            raise ValueError(f"Character not found: {character_id}")

        refusal = RefusedEnhancement(
            name=name,
            source=source,
            benefit=benefit,
            reason_refused=reason_refused,
        )

        char.refused_enhancements.append(refusal)

        # Log as hinge moment (refusal is an identity-defining choice)
        self.manager.log_history(
            type=HistoryType.HINGE,
            summary=f"Refused {source.value} enhancement: {name}",
            is_permanent=True,
        )

        self.manager.save_campaign()
        return refusal

    def get_refusal_reputation(self, character_id: str) -> dict | None:
        """
        Calculate refusal reputation based on refused enhancements.

        Returns title, count, and faction breakdown for GM context.
        """
        char = self.manager.get_character(character_id)
        if not char:
            return None

        refusals = char.refused_enhancements
        count = len(refusals)

        if count == 0:
            return {
                "title": None,
                "count": 0,
                "by_faction": {},
                "narrative_hint": None,
            }

        # Count by faction
        by_faction: dict[str, int] = {}
        for r in refusals:
            faction = r.source.value
            by_faction[faction] = by_faction.get(faction, 0) + 1

        # Determine title
        title = None
        narrative_hint = None

        # Check for faction-specific defiance (3+ from same faction)
        max_faction = max(by_faction.items(), key=lambda x: x[1])
        if max_faction[1] >= 3:
            title = f"The {max_faction[0]} Defiant"
            narrative_hint = f"Known for repeatedly refusing {max_faction[0]} offers"
        elif count >= 3:
            title = "The Undaunted"
            narrative_hint = "Has refused multiple faction offers — values autonomy"
        elif count >= 2:
            title = "The Unbought"
            narrative_hint = "Has turned down enhancement offers before"
        else:
            narrative_hint = "Refused an enhancement — some NPCs may notice"

        return {
            "title": title,
            "count": count,
            "by_faction": by_faction,
            "narrative_hint": narrative_hint,
        }

    def call_leverage(
        self,
        character_id: str,
        enhancement_id: str,
        demand: str,
        weight: str = "medium",
        threat_basis: list[str] | None = None,
        deadline: str | None = None,
        deadline_sessions: int | None = None,
        consequences: list[str] | None = None,
    ) -> dict:
        """
        A faction calls in leverage on an enhancement.

        Creates a LeverageDemand with optional threat basis, deadline, and consequences.
        Player must respond.
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        char = self.manager.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        enhancement = next(
            (e for e in char.enhancements if e.id == enhancement_id),
            None
        )
        if not enhancement:
            return {"error": "Enhancement not found"}

        # Check for existing demand (new system) or obligation (legacy)
        if enhancement.leverage.pending_demand or enhancement.leverage.pending_obligation:
            return {"error": "Already has pending demand - resolve that first"}

        # Calculate deadline session if relative deadline given
        deadline_session = None
        if deadline_sessions is not None:
            deadline_session = self._campaign.meta.session_count + deadline_sessions

        # Create rich demand object
        leverage_demand = LeverageDemand(
            faction=enhancement.source,
            enhancement_id=enhancement.id,
            enhancement_name=enhancement.name,
            demand=demand,
            threat_basis=threat_basis or [],
            deadline=deadline,
            deadline_session=deadline_session,
            consequences=consequences or [],
            created_session=self._campaign.meta.session_count,
            weight=LeverageWeight(weight),
        )

        enhancement.leverage.pending_demand = leverage_demand
        enhancement.leverage.last_called = datetime.now()
        enhancement.leverage.weight = LeverageWeight(weight)

        self.manager.save_campaign()

        return {
            "enhancement": enhancement.name,
            "faction": enhancement.source.value,
            "demand": demand,
            "demand_id": leverage_demand.id,
            "weight": weight,
            "threat_basis": threat_basis or [],
            "deadline": deadline,
            "deadline_session": deadline_session,
            "consequences": consequences or [],
            "compliance_history": enhancement.leverage.compliance_count,
            "resistance_history": enhancement.leverage.resistance_count,
        }

    def resolve_leverage(
        self,
        character_id: str,
        enhancement_id: str,
        response: str,  # "comply", "resist", "negotiate"
        outcome: str,
    ) -> dict:
        """
        Resolve a pending leverage demand or obligation.

        - Comply: weight may decrease
        - Resist: weight increases
        - Negotiate: weight stays, resets hint counter
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        char = self.manager.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        enhancement = next(
            (e for e in char.enhancements if e.id == enhancement_id),
            None
        )
        if not enhancement:
            return {"error": "Enhancement not found"}

        # Check for demand (new) or obligation (legacy)
        demand = enhancement.leverage.pending_demand
        legacy_obligation = enhancement.leverage.pending_obligation

        if not demand and not legacy_obligation:
            return {"error": "No pending demand or obligation"}

        # Get the demand text for logging
        old_demand_text = demand.demand if demand else legacy_obligation

        weights = list(LeverageWeight)
        current_weight_idx = weights.index(enhancement.leverage.weight)

        if response == "comply":
            enhancement.leverage.compliance_count += 1
            # Compliance may reduce weight
            if current_weight_idx > 0:
                enhancement.leverage.weight = weights[current_weight_idx - 1]
        elif response == "resist":
            enhancement.leverage.resistance_count += 1
            # Resistance escalates weight
            if current_weight_idx < len(weights) - 1:
                enhancement.leverage.weight = weights[current_weight_idx + 1]
        # negotiate: weight stays same

        # Clear both fields
        enhancement.leverage.pending_demand = None
        enhancement.leverage.pending_obligation = None
        enhancement.leverage.hint_count = 0  # Reset hint counter

        # Log to history
        self.manager.log_history(
            type=HistoryType.CONSEQUENCE,
            summary=f"Leverage {response}: {enhancement.source.value} demanded '{old_demand_text}', outcome: {outcome}",
            is_permanent=False,
        )

        self.manager.save_campaign()

        return {
            "enhancement": enhancement.name,
            "response": response,
            "outcome": outcome,
            "new_weight": enhancement.leverage.weight.value,
            "compliance_count": enhancement.leverage.compliance_count,
            "resistance_count": enhancement.leverage.resistance_count,
        }

    def check_leverage_hints(self, player_input: str) -> list[dict]:
        """
        Check if player input should trigger leverage hints.

        Returns hints for GM injection, not auto-calls.
        Requires 2+ keyword matches (like dormant threads).
        """
        if not self._campaign:
            return []

        hints = []
        input_keywords = extract_keywords(player_input)
        if not input_keywords:
            return []

        current_session = self._campaign.meta.session_count

        for char in self._campaign.characters:
            for enhancement in char.enhancements:
                # Skip if already has pending demand or obligation
                if enhancement.leverage.pending_demand or enhancement.leverage.pending_obligation:
                    continue

                # Skip if hinted this session already
                if enhancement.leverage.last_hint_session == current_session:
                    continue

                # Check keyword match
                enh_keywords = set(enhancement.leverage_keywords)
                matched = enh_keywords & input_keywords

                # Require 2+ matches
                if len(matched) >= 2:
                    sessions_since = current_session - enhancement.granted_session

                    hints.append({
                        "character_id": char.id,
                        "character_name": char.name,
                        "enhancement_id": enhancement.id,
                        "enhancement_name": enhancement.name,
                        "faction": enhancement.source.value,
                        "weight": enhancement.leverage.weight.value,
                        "matched_keywords": list(matched),
                        "sessions_since_grant": sessions_since,
                        "hint_count": enhancement.leverage.hint_count,
                        "compliance_count": enhancement.leverage.compliance_count,
                        "resistance_count": enhancement.leverage.resistance_count,
                    })

        return hints

    def _compute_urgency_score(
        self,
        demand: LeverageDemand,
        current_session: int,
    ) -> tuple[str, int]:
        """
        Compute urgency tier and score for a demand.

        Returns (urgency_tier, numeric_score) where:
        - "critical": past deadline
        - "urgent": deadline this session
        - "pending": no deadline or future deadline
        """
        age = current_session - demand.created_session

        if demand.deadline_session is not None:
            if current_session > demand.deadline_session:
                return ("critical", 1000 + age)  # Past deadline
            elif current_session == demand.deadline_session:
                return ("urgent", 500 + age)  # Deadline is now

        # Weight adds urgency even without deadline
        weight_bonus = {"light": 0, "medium": 50, "heavy": 100}
        return ("pending", weight_bonus.get(demand.weight.value, 0) + age)

    def get_pending_demands(self) -> list[dict]:
        """
        Get all pending leverage demands for GM context.

        Returns demands sorted by urgency (critical > urgent > pending).
        """
        if not self._campaign:
            return []

        demands = []
        current_session = self._campaign.meta.session_count

        for char in self._campaign.characters:
            for enh in char.enhancements:
                demand = enh.leverage.pending_demand
                if not demand:
                    continue

                urgency, score = self._compute_urgency_score(demand, current_session)
                age = current_session - demand.created_session
                overdue = (
                    demand.deadline_session is not None
                    and current_session > demand.deadline_session
                )

                demands.append({
                    "id": demand.id,
                    "character_id": char.id,
                    "character_name": char.name,
                    "enhancement_id": enh.id,
                    "enhancement_name": demand.enhancement_name,
                    "faction": demand.faction.value,
                    "demand": demand.demand,
                    "threat_basis": demand.threat_basis,
                    "deadline": demand.deadline,
                    "deadline_session": demand.deadline_session,
                    "consequences": demand.consequences,
                    "weight": demand.weight.value,
                    "age_sessions": age,
                    "overdue": overdue,
                    "urgency": urgency,
                    "_score": score,  # For sorting
                })

        # Sort by score descending (most urgent first)
        demands.sort(key=lambda d: -d["_score"])

        # Remove internal score field
        for d in demands:
            del d["_score"]

        return demands

    def check_demand_deadlines(self) -> list[dict]:
        """
        Check for demands past their deadline.

        Returns list of overdue/urgent demands for GM attention.
        """
        all_demands = self.get_pending_demands()
        return [d for d in all_demands if d["urgency"] in ("critical", "urgent")]

    def escalate_demand(
        self,
        character_id: str,
        enhancement_id: str,
        escalation_type: str,  # "queue_consequence" | "increase_weight" | "faction_action"
        narrative: str = "",
    ) -> dict:
        """
        Escalate an unresolved leverage demand.

        escalation_type:
        - queue_consequence: Creates dormant thread from demand consequences
        - increase_weight: Bumps demand weight (light->medium->heavy)
        - faction_action: Logs faction taking independent action
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        char = self.manager.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        enhancement = next(
            (e for e in char.enhancements if e.id == enhancement_id),
            None
        )
        if not enhancement:
            return {"error": "Enhancement not found"}

        demand = enhancement.leverage.pending_demand
        if not demand:
            return {"error": "No pending demand to escalate"}

        result = {
            "success": True,
            "enhancement": enhancement.name,
            "faction": enhancement.source.value,
            "escalation_type": escalation_type,
        }

        if escalation_type == "queue_consequence":
            # Create dormant thread from consequences
            consequence_text = (
                "; ".join(demand.consequences)
                if demand.consequences
                else f"Faction {demand.faction.value} acts on ignored demand"
            )
            thread = self.manager.queue_dormant_thread(
                origin=f"DEMAND IGNORED: {demand.demand}",
                trigger_condition="When the faction's patience runs out",
                consequence=consequence_text,
                severity="moderate",
            )
            result["thread_id"] = thread.id
            result["consequence"] = consequence_text

        elif escalation_type == "increase_weight":
            # Bump weight on both demand and leverage
            weights = list(LeverageWeight)
            current_idx = weights.index(enhancement.leverage.weight)
            if current_idx < len(weights) - 1:
                new_weight = weights[current_idx + 1]
                enhancement.leverage.weight = new_weight
                demand.weight = new_weight
                result["old_weight"] = weights[current_idx].value
                result["new_weight"] = new_weight.value
            else:
                result["note"] = "Already at maximum weight (heavy)"
                result["new_weight"] = enhancement.leverage.weight.value

        elif escalation_type == "faction_action":
            # Log faction taking action
            action_desc = narrative or f"{demand.faction.value} acts on unmet demand"
            self.manager.log_history(
                type=HistoryType.CONSEQUENCE,
                summary=f"FACTION ACTION: {action_desc}",
                is_permanent=False,
            )
            result["action"] = action_desc

        else:
            return {"error": f"Unknown escalation type: {escalation_type}"}

        self.manager.save_campaign()
        return result
