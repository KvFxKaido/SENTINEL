"""
Campaign lifecycle management.

Adapted from Sovwren's session_manager pattern.
Handles create, resume, list, save, delete operations.
"""

from datetime import datetime, timedelta
from pathlib import Path

from .schema import (
    Campaign,
    CampaignMeta,
    Character,
    HistoryEntry,
    HistoryType,
    HingeMoment,
    DormantThread,
    NPC,
    FactionName,
    SessionState,
    SessionReflection,
    MissionOutcome,
)
from .store import CampaignStore, JsonCampaignStore
from ..lore.chunker import extract_keywords


class CampaignManager:
    """
    Manages campaign lifecycle and domain operations.

    Storage is delegated to a CampaignStore implementation:
    - JsonCampaignStore for production (file-based)
    - MemoryCampaignStore for testing (in-memory)

    Pattern adapted from Sovwren's SessionManager:
    - create_campaign() -> new campaign
    - load_campaign(id) -> resume existing
    - list_campaigns() -> show available
    - save_campaign() -> persist
    - delete_campaign(id) -> remove
    """

    def __init__(self, store: CampaignStore | Path | str = "campaigns"):
        """
        Initialize with a store.

        Args:
            store: CampaignStore instance, or path for JsonCampaignStore
        """
        if isinstance(store, (Path, str)):
            # Backwards compatible: path creates JsonCampaignStore
            self.store = JsonCampaignStore(store)
        else:
            self.store = store

        self.current: Campaign | None = None
        self._cache: dict[str, Campaign] = {}

    # -------------------------------------------------------------------------
    # Campaign Lifecycle
    # -------------------------------------------------------------------------

    def create_campaign(self, name: str) -> Campaign:
        """Create a new campaign and set it as current."""
        meta = CampaignMeta(name=name)
        campaign = Campaign(meta=meta)

        self.current = campaign
        self._cache[meta.id] = campaign
        self.save_campaign()

        return campaign

    def load_campaign(self, campaign_id: str) -> Campaign | None:
        """
        Load a campaign by ID or partial match.

        Supports:
        - Full UUID: "a1b2c3d4"
        - Numeric index from list: "1", "2", etc.
        """
        # Try cache first
        if campaign_id in self._cache:
            self.current = self._cache[campaign_id]
            return self.current

        # Try numeric index
        if campaign_id.isdigit():
            campaigns = self.list_campaigns()
            idx = int(campaign_id) - 1
            if 0 <= idx < len(campaigns):
                campaign_id = campaigns[idx]["id"]

        # Load from store
        campaign = self.store.load(campaign_id)
        if campaign:
            self.current = campaign
            self._cache[campaign.meta.id] = campaign
            return campaign

        return None

    def save_campaign(self) -> bool:
        """Save current campaign to store."""
        if not self.current:
            return False

        self.store.save(self.current)
        return True

    def delete_campaign(self, campaign_id: str) -> str | None:
        """Delete a campaign by ID. Returns deleted ID or None."""
        # Resolve numeric index
        if campaign_id.isdigit():
            campaigns = self.list_campaigns()
            idx = int(campaign_id) - 1
            if 0 <= idx < len(campaigns):
                campaign_id = campaigns[idx]["id"]

        if self.store.delete(campaign_id):
            # Clear from cache
            if campaign_id in self._cache:
                del self._cache[campaign_id]

            # Clear current if it was this campaign
            if self.current and self.current.meta.id == campaign_id:
                self.current = None

            return campaign_id

        return None

    def list_campaigns(self) -> list[dict]:
        """
        List all campaigns with relative timestamps.

        Returns list of dicts with: id, name, session_count, phase, updated_at, display_time
        """
        campaigns = self.store.list_all()

        # Add display_time for each campaign
        for campaign in campaigns:
            campaign["display_time"] = self._format_relative_time(
                campaign["updated_at"]
            )

        return campaigns

    def rename_campaign(self, new_name: str) -> bool:
        """Rename current campaign."""
        if not self.current:
            return False

        self.current.meta.name = new_name
        self.save_campaign()
        return True

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def start_session(self, session_state: SessionState) -> None:
        """Begin a new mission session."""
        if not self.current:
            raise ValueError("No campaign loaded")

        self.current.meta.session_count += 1
        self.current.session = session_state
        self.save_campaign()

    def end_session(
        self,
        summary: str,
        reset_social_energy: bool = True,
        reflections: SessionReflection | None = None,
        mission_title: str | None = None,
    ) -> HistoryEntry | None:
        """End current session with optional reflections and mission outcome."""
        if not self.current:
            return None

        # Build mission outcome if we have mission data
        mission_outcome = None
        if mission_title or (self.current.session and self.current.session.mission):
            title = mission_title or (
                self.current.session.mission.title
                if self.current.session and self.current.session.mission
                else "Untitled Session"
            )
            mission_outcome = MissionOutcome(
                title=title,
                what_we_tried=summary,
                result="Session concluded",
                immediate_consequence="To be determined",
                reflections=reflections,
            )

        # Log session end to history
        entry = self.log_history(
            type=HistoryType.MISSION,
            summary=f"Session {self.current.meta.session_count}: {summary}",
            is_permanent=False,
            mission=mission_outcome,
        )

        # Reset social energy for all characters
        if reset_social_energy:
            for char in self.current.characters:
                char.social_energy.current = 100

        # Clear session
        self.current.session = None
        self.save_campaign()
        return entry

    # -------------------------------------------------------------------------
    # Character Management
    # -------------------------------------------------------------------------

    def add_character(self, character: Character) -> None:
        """Add a character to the current campaign."""
        if not self.current:
            raise ValueError("No campaign loaded")

        self.current.characters.append(character)
        self.save_campaign()

    def get_character(self, character_id: str) -> Character | None:
        """Get character by ID."""
        if not self.current:
            return None

        for char in self.current.characters:
            if char.id == character_id:
                return char
        return None

    def update_character(
        self,
        character_id: str,
        credits_delta: int = 0,
        social_energy_delta: int = 0,
    ) -> dict | None:
        """
        Update character state. Returns before/after snapshot.
        """
        char = self.get_character(character_id)
        if not char:
            return None

        before = {
            "credits": char.credits,
            "social_energy": char.social_energy.current,
        }

        char.credits += credits_delta
        char.social_energy.current = max(0, min(100,
            char.social_energy.current + social_energy_delta
        ))

        after = {
            "credits": char.credits,
            "social_energy": char.social_energy.current,
        }

        self.save_campaign()

        return {
            "before": before,
            "after": after,
            "narrative_hint": char.social_energy.narrative_hint,
        }

    # -------------------------------------------------------------------------
    # NPC Management
    # -------------------------------------------------------------------------

    def add_npc(self, npc: NPC, active: bool = True) -> None:
        """Add an NPC to the campaign."""
        if not self.current:
            raise ValueError("No campaign loaded")

        if active:
            self.current.npcs.active.append(npc)
        else:
            self.current.npcs.dormant.append(npc)

        self.save_campaign()

    def get_npc(self, npc_id: str) -> NPC | None:
        """Get NPC by ID."""
        if not self.current:
            return None
        return self.current.npcs.get(npc_id)

    def update_npc_memory(self, npc_id: str, memory: str) -> bool:
        """Add a memory to an NPC."""
        npc = self.get_npc(npc_id)
        if not npc:
            return False

        npc.remembers.append(memory)
        self.save_campaign()
        return True

    def check_npc_triggers(self, tags: list[str]) -> list[dict]:
        """
        Check memory triggers for all active NPCs.

        Args:
            tags: Event tags like ["helped_ember", "betrayed_lattice"]

        Returns:
            List of triggered effects with NPC context
        """
        if not self.current:
            return []

        results = []
        for npc in self.current.npcs.active:
            fired = npc.check_triggers(tags)
            for trigger in fired:
                results.append({
                    "npc_id": npc.id,
                    "npc_name": npc.name,
                    "condition": trigger.condition,
                    "effect": trigger.effect,
                    "new_disposition": npc.disposition.value,
                })

        if results:
            self.save_campaign()

        return results

    def update_npc_disposition(
        self,
        npc_id: str,
        disposition: str,
    ) -> dict | None:
        """
        Set NPC disposition directly.

        Returns before/after snapshot.
        """
        from .schema import Disposition

        npc = self.get_npc(npc_id)
        if not npc:
            return None

        before = npc.disposition.value
        npc.disposition = Disposition(disposition)
        after = npc.disposition.value

        self.save_campaign()

        return {
            "npc_id": npc_id,
            "npc_name": npc.name,
            "before": before,
            "after": after,
        }

    # -------------------------------------------------------------------------
    # Faction Management
    # -------------------------------------------------------------------------

    def shift_faction(self, faction: FactionName, delta: int, reason: str) -> dict:
        """
        Shift faction standing. Returns before/after.

        delta: -2 (betray), -1 (oppose), +1 (help)
        """
        if not self.current:
            raise ValueError("No campaign loaded")

        standing = self.current.factions.get(faction)
        before = standing.standing
        after = standing.shift(delta)

        # Log to history
        self.log_history(
            type=HistoryType.FACTION_SHIFT,
            summary=f"{faction.value}: {before.value} -> {after.value} ({reason})",
            is_permanent=False,
        )

        # Generate tags for NPC triggers
        faction_tag = faction.value.lower().replace(" ", "_")
        tags = []
        if delta > 0:
            tags.append(f"helped_{faction_tag}")
        elif delta < 0:
            tags.append(f"opposed_{faction_tag}")
            if delta <= -2:
                tags.append(f"betrayed_{faction_tag}")

        # Check NPC triggers
        triggered = self.check_npc_triggers(tags)

        self.save_campaign()

        return {
            "faction": faction.value,
            "before": before.value,
            "after": after.value,
            "reason": reason,
            "npc_reactions": triggered,
        }

    # -------------------------------------------------------------------------
    # Chronicle Management
    # -------------------------------------------------------------------------

    def log_history(
        self,
        type: HistoryType,
        summary: str,
        is_permanent: bool = False,
        **kwargs,
    ) -> HistoryEntry:
        """Log an event to campaign history."""
        if not self.current:
            raise ValueError("No campaign loaded")

        entry = HistoryEntry(
            session=self.current.meta.session_count,
            type=type,
            summary=summary,
            is_permanent=is_permanent,
            **kwargs,
        )

        self.current.history.append(entry)
        self.save_campaign()

        return entry

    def log_hinge_moment(
        self,
        situation: str,
        choice: str,
        reasoning: str,
    ) -> HistoryEntry:
        """Log an irreversible hinge moment."""
        if not self.current:
            raise ValueError("No campaign loaded")

        hinge = HingeMoment(
            session=self.current.meta.session_count,
            situation=situation,
            choice=choice,
            reasoning=reasoning,
        )

        return self.log_history(
            type=HistoryType.HINGE,
            summary=f"HINGE: {choice}",
            is_permanent=True,
            hinge=hinge,
        )

    # -------------------------------------------------------------------------
    # Dormant Threads
    # -------------------------------------------------------------------------

    def queue_dormant_thread(
        self,
        origin: str,
        trigger_condition: str,
        consequence: str,
        severity: str = "moderate",
    ) -> DormantThread:
        """Schedule a delayed consequence."""
        if not self.current:
            raise ValueError("No campaign loaded")

        # Extract keywords from trigger condition for matching
        keywords = list(extract_keywords(trigger_condition))[:10]

        thread = DormantThread(
            origin=origin,
            trigger_condition=trigger_condition,
            consequence=consequence,
            severity=severity,
            created_session=self.current.meta.session_count,
            trigger_keywords=keywords,
        )

        self.current.dormant_threads.append(thread)
        self.save_campaign()

        return thread

    def surface_dormant_thread(
        self,
        thread_id: str,
        activation_context: str,
    ) -> DormantThread | None:
        """Activate a dormant thread and move to history."""
        if not self.current:
            return None

        for i, thread in enumerate(self.current.dormant_threads):
            if thread.id == thread_id:
                activated = self.current.dormant_threads.pop(i)

                self.log_history(
                    type=HistoryType.CONSEQUENCE,
                    summary=f"THREAD ACTIVATED: {activated.consequence}",
                    is_permanent=activated.severity == "major",
                )

                self.save_campaign()
                return activated

        return None

    def check_thread_triggers(self, player_input: str) -> list[dict]:
        """
        Check which dormant threads might be triggered by player input.

        Uses keyword matching to find relevant threads. Requires 2+ keyword
        matches to reduce false positives.

        Returns threads with match info, sorted by relevance.
        Does NOT auto-surface - returns hints for GM judgment.
        """
        if not self.current or not self.current.dormant_threads:
            return []

        input_keywords = extract_keywords(player_input)
        if not input_keywords:
            return []

        matches = []
        for thread in self.current.dormant_threads:
            thread_keywords = set(thread.trigger_keywords)
            matched = thread_keywords & input_keywords

            # Require 2+ matches to reduce false positives
            if len(matched) >= 2:
                score = len(matched) / max(len(thread_keywords), 1)
                age = self.current.meta.session_count - thread.created_session
                matches.append({
                    "thread_id": thread.id,
                    "trigger_condition": thread.trigger_condition,
                    "consequence": thread.consequence,
                    "severity": thread.severity.value,
                    "matched_keywords": list(matched),
                    "score": score,
                    "origin": thread.origin,
                    "age_sessions": age,
                })

        # Sort by score descending, then severity (major first)
        severity_order = {"major": 0, "moderate": 1, "minor": 2}
        matches.sort(key=lambda m: (-m["score"], severity_order.get(m["severity"], 99)))

        return matches

    # -------------------------------------------------------------------------
    # Enhancement Leverage
    # -------------------------------------------------------------------------

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
        from .schema import Enhancement

        if not self.current:
            raise ValueError("No campaign loaded")

        if source not in self.ENHANCEMENT_FACTIONS:
            raise ValueError(
                f"{source.value} does not offer enhancements. "
                "Wanderers and Cultivators resist permanent ties."
            )

        char = self.get_character(character_id)
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
            granted_session=self.current.meta.session_count,
            leverage_keywords=keywords,
        )

        char.enhancements.append(enhancement)

        # Log as hinge moment (enhancement acceptance is irreversible)
        self.log_history(
            type=HistoryType.HINGE,
            summary=f"Accepted {source.value} enhancement: {name}",
            is_permanent=True,
        )

        self.save_campaign()
        return enhancement

    def call_leverage(
        self,
        character_id: str,
        enhancement_id: str,
        demand: str,
        weight: str = "medium",
    ) -> dict:
        """
        A faction calls in leverage on an enhancement.

        Records pending obligation. Player must respond.
        """
        from .schema import LeverageWeight

        if not self.current:
            return {"error": "No campaign loaded"}

        char = self.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        enhancement = next(
            (e for e in char.enhancements if e.id == enhancement_id),
            None
        )
        if not enhancement:
            return {"error": "Enhancement not found"}

        if enhancement.leverage.pending_obligation:
            return {"error": "Already has pending obligation - resolve that first"}

        enhancement.leverage.pending_obligation = demand
        enhancement.leverage.last_called = datetime.now()
        enhancement.leverage.weight = LeverageWeight(weight)

        self.save_campaign()

        return {
            "enhancement": enhancement.name,
            "faction": enhancement.source.value,
            "demand": demand,
            "weight": weight,
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
        Resolve a pending leverage obligation.

        - Comply: weight may decrease
        - Resist: weight increases
        - Negotiate: weight stays, resets hint counter
        """
        from .schema import LeverageWeight

        if not self.current:
            return {"error": "No campaign loaded"}

        char = self.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        enhancement = next(
            (e for e in char.enhancements if e.id == enhancement_id),
            None
        )
        if not enhancement or not enhancement.leverage.pending_obligation:
            return {"error": "No pending obligation"}

        old_obligation = enhancement.leverage.pending_obligation
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

        enhancement.leverage.pending_obligation = None
        enhancement.leverage.hint_count = 0  # Reset hint counter

        # Log to history
        self.log_history(
            type=HistoryType.CONSEQUENCE,
            summary=f"Leverage {response}: {enhancement.source.value} demanded '{old_obligation}', outcome: {outcome}",
            is_permanent=False,
        )

        self.save_campaign()

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
        if not self.current:
            return []

        hints = []
        input_keywords = extract_keywords(player_input)
        if not input_keywords:
            return []

        current_session = self.current.meta.session_count

        for char in self.current.characters:
            for enhancement in char.enhancements:
                # Skip if already has pending obligation
                if enhancement.leverage.pending_obligation:
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

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _format_relative_time(self, dt: datetime) -> str:
        """Format timestamp as relative time (Today, Yesterday, etc.)."""
        now = datetime.now()
        diff = now - dt

        if diff < timedelta(days=1) and dt.date() == now.date():
            return "Today"
        elif diff < timedelta(days=2) and (now.date() - dt.date()).days == 1:
            return "Yesterday"
        elif diff < timedelta(days=7):
            return dt.strftime("%A")  # Weekday name
        else:
            return dt.strftime("%b %d")  # "Jan 04"

    def get_summary(self) -> str:
        """Generate a brief summary of current campaign state."""
        if not self.current:
            return "No campaign loaded."

        c = self.current
        lines = [
            f"Campaign: {c.meta.name}",
            f"Phase: {c.meta.phase} | Sessions: {c.meta.session_count}",
            f"Characters: {len(c.characters)}",
            f"Active NPCs: {len(c.npcs.active)}",
            f"Dormant Threads: {len(c.dormant_threads)}",
        ]

        if c.session:
            lines.append(f"Mission: {c.session.mission_title} ({c.session.phase.value})")

        return "\n".join(lines)


# Module-level instance for global access
campaign_manager = CampaignManager()
