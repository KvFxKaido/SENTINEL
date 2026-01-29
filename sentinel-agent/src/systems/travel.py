"""
Travel resolver for SENTINEL's turn-based engine.

Pure function: resolve(action, campaign, seed) -> (events, changes)

This is the first resolver implemented — the vertical slice proving
the full stack works end-to-end without LLM involvement.

Travel resolution:
1. Move player to target region
2. Update connectivity (disconnected → aware → connected)
3. Apply vehicle costs (fuel, condition)
4. Emit events for cascade processing
5. Return events and narrative hooks

Design invariants:
- Pure function: same (action, state, seed) → same (events, changes)
- No globals, no side effects beyond the campaign model
- Costs are fully transparent (previewed in ProposalResult)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ..state.schemas.action import Action
from ..state.schemas.event import TurnEvent
from ..state.event_bus import get_event_bus, EventType

if TYPE_CHECKING:
    from ..state.schema import Campaign


# Default regions data path
REGIONS_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "regions.json"


class TravelResolver:
    """
    Resolves travel actions between regions.

    Pure function design: resolve() takes an action, campaign, and seed,
    and returns events plus a changes dict. The orchestrator applies
    state changes; the resolver only computes what should change.

    In practice, for simplicity, the resolver mutates the campaign
    model directly (Pydantic models are mutable) and returns events.
    The orchestrator handles persistence.
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

    def resolve(
        self,
        action: Action,
        campaign: "Campaign",
        seed: int,
    ) -> tuple[list[TurnEvent], dict]:
        """
        Resolve a travel action.

        Args:
            action: Committed travel action with payload {"to": "region_id"}
            campaign: Campaign state to mutate
            seed: Deterministic seed (for future random elements)

        Returns:
            Tuple of (events, changes_dict)
        """
        from ..state.schema import Region

        target_id = action.payload.get("to", "")
        alternative = action.chosen_alternative

        try:
            target = Region(target_id)
        except ValueError:
            return [TurnEvent(
                event_type="travel.failed",
                source_action=action.action_id,
                payload={"reason": f"Unknown region: {target_id}"},
                summary=f"Travel failed: unknown region {target_id}",
            )], {}

        old_region = campaign.map_state.current_region
        old_region_id = old_region.value

        if target == old_region:
            return [TurnEvent(
                event_type="travel.failed",
                source_action=action.action_id,
                payload={"reason": "Already in this region"},
                summary="Travel failed: already here",
            )], {}

        events: list[TurnEvent] = []
        bus = get_event_bus()

        # ── 1. Move to target region ────────────────────────
        campaign.map_state.current_region = target
        campaign.region = target

        # Get region names for narrative
        regions = self._load_regions()
        old_name = regions.get(old_region_id, {}).get("name", old_region_id)
        target_name = regions.get(target_id, {}).get("name", target_id)

        events.append(TurnEvent(
            event_type="travel.arrived",
            source_action=action.action_id,
            payload={
                "from": old_region_id,
                "to": target_id,
                "from_name": old_name,
                "to_name": target_name,
                "alternative_used": alternative,
            },
            summary=f"Arrived in {target_name}",
        ))

        # ── 2. Update connectivity ──────────────────────────
        session = campaign.meta.session_count
        old_connectivity = None
        region_state = campaign.map_state.regions.get(target)
        if region_state:
            old_connectivity = region_state.connectivity.value

        campaign.map_state.make_connected(target, session)

        region_state = campaign.map_state.regions.get(target)
        new_connectivity = region_state.connectivity.value if region_state else "connected"

        if old_connectivity != new_connectivity:
            events.append(TurnEvent(
                event_type="connectivity.changed",
                source_action=action.action_id,
                payload={
                    "region": target_id,
                    "from": old_connectivity or "disconnected",
                    "to": new_connectivity,
                },
                summary=f"Connection to {target_name}: {new_connectivity}",
            ))

            # Emit for map UI
            bus.emit(
                EventType.CONNECTIVITY_UPDATED,
                campaign_id=campaign.meta.id,
                session=session,
                region=target_id,
                connectivity=new_connectivity,
            )

        # ── 3. Apply vehicle costs ──────────────────────────
        if campaign.characters:
            char = campaign.characters[0]
            vehicle = next(
                (v for v in char.vehicles if v.is_operational), None,
            )
            if vehicle:
                old_fuel = vehicle.fuel
                old_condition = vehicle.condition

                vehicle.fuel = max(0, vehicle.fuel - vehicle.fuel_cost_per_trip)
                vehicle.condition = max(0, vehicle.condition - vehicle.condition_loss_per_trip)

                if old_fuel != vehicle.fuel or old_condition != vehicle.condition:
                    events.append(TurnEvent(
                        event_type="vehicle.consumed",
                        source_action=action.action_id,
                        payload={
                            "vehicle": vehicle.name,
                            "fuel_used": old_fuel - vehicle.fuel,
                            "condition_lost": old_condition - vehicle.condition,
                            "fuel_remaining": vehicle.fuel,
                            "condition_remaining": vehicle.condition,
                            "status": vehicle.status,
                        },
                        summary=f"{vehicle.name}: {vehicle.status} (fuel {vehicle.fuel}, condition {vehicle.condition})",
                    ))

        # ── 4. Apply alternative consequences ───────────────
        if alternative:
            route_data = regions.get(old_region_id, {}).get("routes", {}).get(target_id, {})
            for alt in route_data.get("alternatives", []):
                if alt.get("type") == alternative:
                    # Apply costs from the alternative
                    alt_cost = alt.get("cost", {})
                    if "social_energy" in alt_cost and campaign.characters:
                        char = campaign.characters[0]
                        drain = alt_cost["social_energy"]
                        char.social_energy.current = max(
                            0, char.social_energy.current - drain,
                        )
                        events.append(TurnEvent(
                            event_type="social_energy.drained",
                            source_action=action.action_id,
                            payload={
                                "amount": drain,
                                "remaining": char.social_energy.current,
                                "state": char.social_energy.state,
                            },
                            summary=f"Social energy drained by {drain}",
                        ))

                        bus.emit(
                            EventType.SOCIAL_ENERGY_CHANGED,
                            campaign_id=campaign.meta.id,
                            session=session,
                            current=char.social_energy.current,
                            state=char.social_energy.state,
                        )

                    if "credits" in alt_cost and campaign.characters:
                        char = campaign.characters[0]
                        cost = alt_cost["credits"]
                        char.credits = max(0, char.credits - cost)
                        events.append(TurnEvent(
                            event_type="credits.spent",
                            source_action=action.action_id,
                            payload={
                                "amount": cost,
                                "remaining": char.credits,
                            },
                            summary=f"Spent {cost} credits",
                        ))

                    # Queue consequence as dormant thread if specified
                    consequence = alt.get("consequence")
                    if consequence:
                        events.append(TurnEvent(
                            event_type="consequence.queued",
                            source_action=action.action_id,
                            payload={
                                "consequence": consequence,
                                "source": f"Travel to {target_name} via {alternative}",
                            },
                            summary=f"Consequence queued: {consequence.replace('_', ' ')}",
                        ))

                    break

        # ── 5. Emit region changed event ────────────────────
        bus.emit(
            EventType.REGION_CHANGED,
            campaign_id=campaign.meta.id,
            session=session,
            from_region=old_region_id,
            to_region=target_id,
        )

        return events, {
            "region": target_id,
            "old_region": old_region_id,
        }
