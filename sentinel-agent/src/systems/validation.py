"""
Action validator for SENTINEL's turn-based engine.

Pure function: validate(proposal, campaign) -> ProposalResult.
No state mutation, no side effects, no globals.

Checks requirements, calculates cost previews, and lists alternatives
for any proposed action. The player sees exactly what will happen
before committing.

Design principles:
- Every route has alternatives (Sentinel 2D §12: "what does it cost?")
- Requirements are explicit and typed
- Costs are fully transparent — no hidden penalties
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ..state.schemas.action import (
    ActionType,
    Alternative,
    CostPreview,
    Proposal,
    ProposalResult,
    Requirement,
    RequirementStatus,
    Risk,
)

if TYPE_CHECKING:
    from ..state.schema import Campaign


# Default regions data path
REGIONS_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "regions.json"


class ActionValidator:
    """
    Validates proposals and returns ProposalResults.

    Each action type has a dedicated validation method that checks
    requirements, calculates costs, and lists alternatives.

    This class is stateless — all state comes from the campaign parameter.
    """

    def __init__(self, regions_path: Path | None = None):
        self._regions_path = regions_path or REGIONS_DATA_PATH
        self._regions_data: dict | None = None

    def _load_regions(self) -> dict:
        """Load regions data from JSON (cached)."""
        if self._regions_data is None:
            if self._regions_path.exists():
                with open(self._regions_path, "r", encoding="utf-8") as f:
                    self._regions_data = json.load(f).get("regions", {})
            else:
                self._regions_data = {}
        return self._regions_data

    def validate(self, proposal: Proposal, campaign: "Campaign") -> ProposalResult:
        """
        Validate a proposal and return a preview.

        Routes to type-specific validators based on action_type.
        No state mutation occurs.
        """
        validators = {
            ActionType.TRAVEL: self._validate_travel,
            ActionType.ACCEPT_JOB: self._validate_accept_job,
            ActionType.COMPLETE_JOB: self._validate_complete_job,
            ActionType.CALL_FAVOR: self._validate_call_favor,
            ActionType.COMMIT_ATTENTION: self._validate_commit_attention,
            ActionType.RECON: self._validate_recon,
            ActionType.INITIATE_COMBAT: self._validate_combat,
            ActionType.LOCAL: self._validate_local,
        }

        validator_fn = validators.get(proposal.action_type)
        if validator_fn is None:
            return ProposalResult(
                feasible=False,
                summary=f"Unknown action type: {proposal.action_type.value}",
            )

        return validator_fn(proposal, campaign)

    # ─── Travel Validation ───────────────────────────────────────

    def _validate_travel(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate a travel proposal."""
        from ..state.schema import Region, FactionName, Standing

        target_region = proposal.payload.get("to")
        if not target_region:
            return ProposalResult(
                feasible=False,
                summary="No destination specified.",
            )

        # Check target region exists
        try:
            target = Region(target_region)
        except ValueError:
            return ProposalResult(
                feasible=False,
                summary=f"Unknown region: {target_region}",
            )

        # Can't travel to current region
        current = campaign.map_state.current_region
        if target == current:
            return ProposalResult(
                feasible=False,
                summary="Already in this region.",
            )

        # Check route exists
        regions = self._load_regions()
        current_data = regions.get(current.value, {})
        routes = current_data.get("routes", {})
        route = routes.get(target.value)

        if route is None:
            return ProposalResult(
                feasible=False,
                summary=f"No route from {current.value} to {target.value}.",
            )

        # Check requirements
        requirements: list[Requirement] = []
        all_met = True

        for req in route.get("requirements", []):
            req_type = req.get("type")

            if req_type == "faction":
                # Check faction standing
                faction_id = req.get("faction", "")
                min_standing = req.get("min_standing", "neutral")
                standing_obj = self._get_faction_standing(campaign, faction_id)

                if standing_obj:
                    current_standing = standing_obj.standing.value.lower()
                    meets = self._standing_meets_minimum(
                        current_standing, min_standing,
                    )
                    faction_name = standing_obj.faction.value
                else:
                    meets = False
                    faction_name = faction_id

                status = (
                    RequirementStatus.MET if meets
                    else RequirementStatus.BYPASSABLE  # Routes are negotiable
                )
                if not meets:
                    all_met = False

                requirements.append(Requirement(
                    label=f"{min_standing.title()} standing with {faction_name}",
                    status=status,
                    detail=f"Current: {current_standing if standing_obj else 'unknown'}",
                    bypass="Use alternative route" if not meets else None,
                ))

            elif req_type == "vehicle":
                # Check vehicle capability
                capability = req.get("capability", "")
                has_vehicle = self._has_vehicle_capability(campaign, capability)

                status = (
                    RequirementStatus.MET if has_vehicle
                    else RequirementStatus.BYPASSABLE
                )
                if not has_vehicle:
                    all_met = False

                requirements.append(Requirement(
                    label=f"Vehicle with {capability} capability",
                    status=status,
                    detail="Have suitable vehicle" if has_vehicle else "No suitable vehicle",
                    bypass="Use alternative route" if not has_vehicle else None,
                ))

            elif req_type == "contact":
                # Check faction contact
                faction_id = req.get("faction", "")
                standing_obj = self._get_faction_standing(campaign, faction_id)
                has_contact = (
                    standing_obj is not None
                    and standing_obj.standing.value.lower()
                    not in ("hostile", "unfriendly")
                )

                status = (
                    RequirementStatus.MET if has_contact
                    else RequirementStatus.BYPASSABLE
                )
                if not has_contact:
                    all_met = False

                requirements.append(Requirement(
                    label=f"Contact in {faction_id}",
                    status=status,
                    detail="Have contact" if has_contact else "No contact available",
                    bypass="Use alternative route" if not has_contact else None,
                ))

        # Calculate costs
        costs = CostPreview(turns=1)

        # Vehicle fuel cost if traveling with vehicle
        active_vehicle = self._get_active_vehicle(campaign)
        if active_vehicle:
            costs.fuel = active_vehicle.fuel_cost_per_trip
            costs.condition = active_vehicle.condition_loss_per_trip

        # Build risks
        risks: list[Risk] = []
        route_terrain = route.get("terrain", [])
        if "hazard" in route_terrain or "off-road" in route_terrain:
            risks.append(Risk(
                label="Rough terrain",
                severity="low",
                detail="Vehicle condition may degrade faster",
            ))

        # Build alternatives from route data
        alternatives: list[Alternative] = []
        for alt in route.get("alternatives", []):
            alt_costs = CostPreview(turns=1)
            alt_cost_data = alt.get("cost", {})
            if "social_energy" in alt_cost_data:
                alt_costs.social_energy = alt_cost_data["social_energy"]
            if "credits" in alt_cost_data:
                alt_costs.credits = alt_cost_data["credits"]

            alternatives.append(Alternative(
                label=alt.get("description", alt.get("type", "Unknown")),
                type=alt.get("type", "unknown"),
                description=alt.get("description", ""),
                additional_costs=alt_costs,
                consequence=alt.get("consequence"),
            ))

        # Travel description
        travel_desc = route.get("travel_description", f"Travel to {target.value}")
        target_data = regions.get(target.value, {})
        target_name = target_data.get("name", target.value)

        feasible = all_met or len(alternatives) > 0
        summary = (
            f"Travel to {target_name}. {travel_desc}."
            if feasible
            else f"Cannot reach {target_name} — requirements not met and no alternatives."
        )

        return ProposalResult(
            feasible=feasible,
            requirements=requirements,
            costs=costs,
            risks=risks,
            alternatives=alternatives,
            summary=summary,
        )

    # ─── Job Validation ──────────────────────────────────────────

    def _validate_accept_job(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate accepting a job from the board."""
        template_id = proposal.payload.get("template_id")
        if not template_id:
            return ProposalResult(feasible=False, summary="No job specified.")

        if template_id not in campaign.jobs.available:
            return ProposalResult(
                feasible=False,
                summary="This job is not currently available.",
            )

        # Check if already at max active jobs (3)
        active_count = len([
            j for j in campaign.jobs.active if j.status.value == "active"
        ])
        requirements = []
        if active_count >= 3:
            requirements.append(Requirement(
                label="Active job limit (3)",
                status=RequirementStatus.UNMET,
                detail=f"Currently have {active_count} active jobs",
            ))
            return ProposalResult(
                feasible=False,
                requirements=requirements,
                summary="Too many active jobs. Complete or abandon one first.",
            )

        return ProposalResult(
            feasible=True,
            costs=CostPreview(turns=1),
            summary=f"Accept job: {template_id}",
        )

    def _validate_complete_job(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate completing an active job."""
        job_id = proposal.payload.get("job_id")
        if not job_id:
            return ProposalResult(feasible=False, summary="No job specified.")

        active_job = next(
            (j for j in campaign.jobs.active if j.id == job_id and j.status.value == "active"),
            None,
        )
        if not active_job:
            return ProposalResult(
                feasible=False,
                summary="No active job with this ID.",
            )

        return ProposalResult(
            feasible=True,
            costs=CostPreview(turns=1),
            summary=f"Complete job: {active_job.title}",
        )

    # ─── Favor Validation ────────────────────────────────────────

    def _validate_call_favor(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate calling a favor from an NPC."""
        npc_id = proposal.payload.get("npc_id")
        if not npc_id:
            return ProposalResult(feasible=False, summary="No NPC specified.")

        # Check favor token availability
        session = campaign.meta.session_count
        requirements = []

        if not campaign.favor_tracker.can_call_favor(session):
            requirements.append(Requirement(
                label="Favor tokens remaining",
                status=RequirementStatus.UNMET,
                detail="No favor tokens left this session",
            ))

        npc = campaign.npcs.get(npc_id)
        if not npc:
            return ProposalResult(
                feasible=False,
                summary=f"NPC not found: {npc_id}",
            )

        # Check disposition (need at least warm)
        if npc.disposition.value in ("hostile", "wary", "neutral"):
            requirements.append(Requirement(
                label=f"NPC disposition (need warm+)",
                status=RequirementStatus.UNMET,
                detail=f"Current: {npc.disposition.value}",
            ))

        feasible = all(r.status != RequirementStatus.UNMET for r in requirements)

        return ProposalResult(
            feasible=feasible,
            requirements=requirements,
            costs=CostPreview(turns=1),
            summary=f"Call favor from {npc.name}" if feasible else "Cannot call this favor.",
        )

    # ─── Stub Validators ─────────────────────────────────────────

    def _validate_commit_attention(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate committing attention to a target. Stub for Phase 9."""
        return ProposalResult(
            feasible=True,
            costs=CostPreview(turns=1, social_energy=5),
            summary="Commit attention (resolver not yet implemented).",
        )

    def _validate_recon(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate a recon action. Stub for Phase 9."""
        return ProposalResult(
            feasible=True,
            costs=CostPreview(turns=1, social_energy=10),
            summary="Recon (resolver not yet implemented).",
        )

    def _validate_combat(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate initiating combat. Stub for Phase 9."""
        return ProposalResult(
            feasible=True,
            costs=CostPreview(turns=1),
            risks=[Risk(
                label="Combat is dangerous",
                severity="high",
                detail="Social energy will be consumed. NPCs may be lost.",
            )],
            summary="Initiate combat (resolver not yet implemented).",
        )

    def _validate_local(
        self, proposal: Proposal, campaign: "Campaign",
    ) -> ProposalResult:
        """Validate a generic local action. Stub for Phase 9."""
        return ProposalResult(
            feasible=True,
            costs=CostPreview(turns=1),
            summary="Local action (resolver not yet implemented).",
        )

    # ─── Helpers ─────────────────────────────────────────────────

    def _get_faction_standing(self, campaign: "Campaign", faction_id: str):
        """Look up a faction standing by faction ID string."""
        from ..state.schema import FactionName
        try:
            faction_enum = FactionName(faction_id.lower().replace(" ", "_"))
        except ValueError:
            return None
        return campaign.factions.get(faction_enum)

    @staticmethod
    def _standing_meets_minimum(current: str, minimum: str) -> bool:
        """Check if current standing meets minimum requirement."""
        order = ["hostile", "unfriendly", "neutral", "friendly", "allied"]
        current_idx = order.index(current.lower()) if current.lower() in order else 2
        minimum_idx = order.index(minimum.lower()) if minimum.lower() in order else 2
        return current_idx >= minimum_idx

    @staticmethod
    def _has_vehicle_capability(campaign: "Campaign", capability: str) -> bool:
        """Check if player has a vehicle with the required capability."""
        if not campaign.characters:
            return False
        char = campaign.characters[0]
        for vehicle in char.vehicles:
            if not vehicle.is_operational:
                continue
            # Check terrain capabilities
            if capability.lower() in [t.lower() for t in vehicle.terrain]:
                return True
            # Check type match
            if capability.lower() == vehicle.type.lower():
                return True
        return False

    @staticmethod
    def _get_active_vehicle(campaign: "Campaign"):
        """Get the player's first operational vehicle, or None."""
        if not campaign.characters:
            return None
        char = campaign.characters[0]
        for vehicle in char.vehicles:
            if vehicle.is_operational:
                return vehicle
        return None
