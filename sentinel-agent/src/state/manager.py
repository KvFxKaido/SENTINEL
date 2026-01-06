"""
Campaign lifecycle management.

Adapted from Sovwren's session_manager pattern.
Handles create, resume, list, save, delete operations.
"""

from datetime import datetime, timedelta
from pathlib import Path

from .schema import (
    AvoidedSituation,
    Campaign,
    CampaignMeta,
    Character,
    HistoryEntry,
    HistoryType,
    HingeMoment,
    DormantThread,
    LeverageDemand,
    LeverageWeight,
    MissionPhase,
    NPC,
    FactionName,
    SessionState,
    SessionReflection,
    MissionOutcome,
    ThreadSeverity,
)
from .store import CampaignStore, JsonCampaignStore, EventQueueStore
from .memvid_adapter import MemvidAdapter, create_memvid_adapter, MEMVID_AVAILABLE


def _version_tuple(version: str) -> tuple[int, ...]:
    """Convert version string to tuple for proper numeric comparison.

    Fixes lexicographic comparison bug where "1.10.0" < "1.2.0" would be True.
    """
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        # Fallback for malformed versions
        return (0, 0, 0)


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

    def __init__(
        self,
        store: CampaignStore | Path | str = "campaigns",
        event_queue: EventQueueStore | None = None,
        enable_memvid: bool = True,
    ):
        """
        Initialize with a store.

        Args:
            store: CampaignStore instance, or path for JsonCampaignStore
            event_queue: Optional EventQueueStore for MCP event processing
            enable_memvid: Whether to enable memvid memory (requires memvid-sdk)
        """
        if isinstance(store, (Path, str)):
            # Backwards compatible: path creates JsonCampaignStore
            campaigns_path = Path(store)
            self.store = JsonCampaignStore(campaigns_path)
            # Auto-create event queue store with same path
            self.event_queue = event_queue or EventQueueStore(campaigns_path)
            self._campaigns_path = campaigns_path
        else:
            self.store = store
            self.event_queue = event_queue
            self._campaigns_path = Path("campaigns")

        self.current: Campaign | None = None
        self._cache: dict[str, Campaign] = {}

        # Memvid adapter (lazily initialized per campaign)
        self._enable_memvid = enable_memvid and MEMVID_AVAILABLE
        self._memvid: MemvidAdapter | None = None
        self._turn_counter: int = 0  # Track turns within session

    # -------------------------------------------------------------------------
    # Memvid Integration
    # -------------------------------------------------------------------------

    def _init_memvid_for_campaign(self, campaign_id: str) -> None:
        """Initialize memvid adapter for a campaign."""
        if self._enable_memvid:
            self._memvid = create_memvid_adapter(
                campaign_id,
                campaigns_dir=self._campaigns_path,
                enabled=True,
            )
            self._turn_counter = 0
        else:
            self._memvid = None

    def _close_memvid(self) -> None:
        """Close current memvid adapter."""
        if self._memvid:
            self._memvid.close()
            self._memvid = None

    @property
    def memvid(self) -> MemvidAdapter | None:
        """Access the memvid adapter (may be None if disabled)."""
        return self._memvid

    def record_turn(
        self,
        choices_made: list[dict] | None = None,
        npcs_affected: list[str] | None = None,
        narrative_summary: str = "",
    ) -> str | None:
        """
        Record a turn state to memvid.

        Call this at the end of each turn to snapshot state.
        Returns frame ID if successful.
        """
        if not self.current or not self._memvid:
            return None

        self._turn_counter += 1
        return self._memvid.save_turn(
            campaign=self.current,
            turn_number=self._turn_counter,
            choices_made=choices_made,
            npcs_affected=npcs_affected,
            narrative_summary=narrative_summary,
        )

    def record_npc_interaction(
        self,
        npc_id: str,
        player_action: str,
        npc_reaction: str,
        disposition_change: int = 0,
        context: dict | None = None,
    ) -> str | None:
        """
        Record an NPC interaction to memvid.

        Call this when meaningful NPC interactions occur.
        Returns frame ID if successful.
        """
        if not self.current or not self._memvid:
            return None

        npc = self.get_npc(npc_id)
        if not npc:
            return None

        return self._memvid.save_npc_interaction(
            npc=npc,
            player_action=player_action,
            npc_reaction=npc_reaction,
            disposition_change=disposition_change,
            session=self.current.meta.session_count,
            context=context,
        )

    def query_campaign_history(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Semantic search across campaign history via memvid.

        Returns matching frames if memvid enabled, empty list otherwise.
        """
        if not self._memvid:
            return []
        return self._memvid.query(query, top_k=top_k)

    def get_npc_memory(self, npc_id: str, limit: int = 20) -> list[dict]:
        """
        Get interaction history for a specific NPC via memvid.

        Returns interaction frames if memvid enabled.
        """
        if not self._memvid:
            return []
        return self._memvid.get_npc_history(npc_id, limit=limit)

    # -------------------------------------------------------------------------
    # Campaign Lifecycle
    # -------------------------------------------------------------------------

    def create_campaign(self, name: str) -> Campaign:
        """Create a new campaign and set it as current."""
        meta = CampaignMeta(name=name)
        campaign = Campaign(meta=meta)

        # Close any existing memvid
        self._close_memvid()

        self.current = campaign
        self._cache[meta.id] = campaign
        self.save_campaign()

        # Initialize memvid for new campaign
        self._init_memvid_for_campaign(meta.id)

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
            # Close any existing memvid
            self._close_memvid()

            # Run migrations if needed
            migrated = self._migrate_campaign(campaign)

            # Process pending events from MCP
            events_processed = self._process_pending_events(campaign)

            self.current = campaign
            self._cache[campaign.meta.id] = campaign

            # Persist if migrations or events were processed
            if migrated or events_processed > 0:
                self.save_campaign()

            # Initialize memvid for this campaign
            self._init_memvid_for_campaign(campaign.meta.id)

            return campaign

        return None

    def _migrate_campaign(self, campaign: Campaign) -> bool:
        """
        Migrate campaign to current schema version.

        Returns True if any migration was performed.
        """
        migrated = False

        # v1.0.0 -> v1.1.0: Migrate pending_obligation to pending_demand
        if _version_tuple(campaign.schema_version) < _version_tuple("1.1.0"):
            for char in campaign.characters:
                for enh in char.enhancements:
                    # If legacy field set but new field not set, migrate
                    if enh.leverage.pending_obligation and not enh.leverage.pending_demand:
                        enh.leverage.pending_demand = LeverageDemand(
                            faction=enh.source,
                            enhancement_id=enh.id,
                            enhancement_name=enh.name,
                            demand=enh.leverage.pending_obligation,
                            weight=enh.leverage.weight,
                            created_session=campaign.meta.session_count,
                        )
                        # Clear legacy field
                        enh.leverage.pending_obligation = None
                        migrated = True

            campaign.schema_version = "1.1.0"
            migrated = True

        return migrated

    def _process_pending_events(self, campaign: Campaign) -> int:
        """
        Process pending events from the MCP event queue.

        This is called automatically when loading a campaign.
        Returns the number of events processed.
        """
        if not self.event_queue:
            return 0

        events = self.event_queue.get_pending_events(campaign.meta.id)
        processed = 0

        for event in events:
            try:
                self._process_single_event(campaign, event)
                self.event_queue.mark_processed(event.id)
                processed += 1
            except Exception as e:
                # Log error but continue processing other events
                # In production, this would use proper logging
                print(f"[Warning] Failed to process event {event.id}: {e}")

        # Clean up processed events
        if processed > 0:
            self.event_queue.clear_processed()

        return processed

    def _process_single_event(self, campaign: Campaign, event) -> None:
        """Process a single event from the queue."""
        from .schema import HistoryEntry, HistoryType

        if event.event_type == "faction_event":
            payload = event.payload
            faction = payload.get("faction", "unknown")
            event_type = payload.get("event_type", "contact")
            summary = payload.get("summary", "")
            session = payload.get("session", campaign.meta.session_count)
            is_permanent = payload.get("is_permanent", False)

            # Create history entry (what log_faction_event used to do directly)
            entry = HistoryEntry(
                session=session,
                type=HistoryType.FACTION_SHIFT,
                summary=f"[{faction.replace('_', ' ').title()}] {summary}",
                is_permanent=is_permanent,
            )
            campaign.history.append(entry)

        # Future: handle other event types here
        # elif event.event_type == "npc_update":
        #     ...

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

    def set_phase(self, phase: str) -> dict:
        """
        Set the current mission phase.

        Phases: briefing, planning, execution, resolution, debrief, between
        """
        if not self.current:
            return {"error": "No campaign loaded"}

        if not self.current.session:
            return {"error": "No active session"}

        # Validate phase
        try:
            new_phase = MissionPhase(phase.lower())
        except ValueError:
            valid = [p.value for p in MissionPhase]
            return {"error": f"Invalid phase. Valid phases: {', '.join(valid)}"}

        old_phase = self.current.session.phase
        self.current.session.phase = new_phase

        # Log phase transition
        self.log_history(
            type=HistoryType.PHASE_CHANGE,
            summary=f"Phase: {old_phase.value} → {new_phase.value}",
            is_permanent=False,
        )

        self.save_campaign()

        return {
            "old_phase": old_phase.value,
            "new_phase": new_phase.value,
            "narrative_hint": self._get_phase_hint(new_phase),
        }

    def _get_phase_hint(self, phase: MissionPhase) -> str:
        """Return a brief narrative hint for the phase transition."""
        hints = {
            MissionPhase.BRIEFING: "Time to present the situation. Keep it tight.",
            MissionPhase.PLANNING: "Let the players strategize. Support, don't lead.",
            MissionPhase.EXECUTION: "This is where play happens. Complications arise from choices.",
            MissionPhase.RESOLUTION: "Land the consequences. Don't rush past the ending.",
            MissionPhase.DEBRIEF: "Close with intention. Ask the four questions.",
            MissionPhase.BETWEEN: "Downtime is character time. The world keeps moving.",
        }
        return hints.get(phase, "Phase changed.")

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

    def invoke_restorer(
        self,
        character_id: str,
        action: str,
    ) -> dict:
        """
        Spend 10% social energy for advantage when acting in your element.

        The action must match one of the character's restorers. This is the
        "carrot" for social energy — not just penalties, but strategic use.

        Args:
            character_id: Character invoking their restorer
            action: What the character is doing (matched against restorers)

        Returns:
            Dict with success status, matched restorer, energy change, and narrative
        """
        if not self.current:
            return {"error": "No campaign loaded"}

        char = self.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        energy = char.social_energy
        cost = 10

        # Check if action matches any restorer (case-insensitive substring match)
        action_lower = action.lower()
        matched_restorer = None
        for restorer in energy.restorers:
            # Check if restorer keywords appear in the action
            restorer_words = restorer.lower().split()
            if any(word in action_lower for word in restorer_words if len(word) > 3):
                matched_restorer = restorer
                break

        if not matched_restorer:
            return {
                "success": False,
                "reason": "not_in_element",
                "narrative_hint": (
                    f"This doesn't feel like {char.name}'s element. "
                    f"They find renewal in: {', '.join(energy.restorers[:3])}"
                ),
                "restorers": energy.restorers,
            }

        if energy.current < cost:
            return {
                "success": False,
                "reason": "insufficient_energy",
                "narrative_hint": "Not enough reserves to push right now.",
                "current_energy": energy.current,
            }

        # Deduct energy
        old_energy = energy.current
        energy.current = max(0, energy.current - cost)
        new_energy = energy.current

        # Generate narrative based on new state
        if new_energy >= 51:
            hint = f"You lean into what centers you—{matched_restorer}. Advantage gained."
        elif new_energy >= 26:
            hint = f"You draw on {matched_restorer}. It helps, but the edges are showing."
        else:
            hint = f"You push through {matched_restorer}. Running on fumes now, but you're ready."

        self.save_campaign()

        return {
            "success": True,
            "advantage_granted": True,
            "restorer_matched": matched_restorer,
            "old_energy": old_energy,
            "new_energy": new_energy,
            "energy_state": energy.state,
            "narrative_hint": hint,
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

        # Save to memvid
        if self._memvid:
            self._memvid.save_faction_shift(
                faction=faction,
                from_standing=before.value,
                to_standing=after.value,
                cause=reason,
                session=self.current.meta.session_count,
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
        immediate_effects: list[str] | None = None,
        dormant_threads_created: list[str] | None = None,
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

        # Save to memvid
        if self._memvid:
            self._memvid.save_hinge_moment(
                hinge,
                session=self.current.meta.session_count,
                immediate_effects=immediate_effects,
                dormant_threads_created=dormant_threads_created,
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

        # Save to memvid
        if self._memvid:
            self._memvid.save_dormant_thread(thread)

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
    # Player Push Mechanic
    # -------------------------------------------------------------------------

    def declare_push(
        self,
        character_id: str,
        goal: str,
        consequence: str,
        severity: str = "moderate",
    ) -> dict:
        """
        Player explicitly invites a consequence for advantage.

        The Push mechanic gives players agency over the risk/reward tradeoff.
        They get advantage now, but a dormant thread is queued.

        Args:
            character_id: Character making the push
            goal: What they're pushing for ("to convince the guard", "to crack the lock")
            consequence: What will happen later as a result
            severity: minor/moderate/major for the dormant thread

        Returns:
            Dict with confirmation, thread ID, and narrative
        """
        if not self.current:
            return {"error": "No campaign loaded"}

        char = self.get_character(character_id)
        if not char:
            return {"error": "Character not found"}

        # Queue the consequence as a dormant thread
        thread = self.queue_dormant_thread(
            origin=f"PUSH: {goal}",
            trigger_condition="When the cost comes due",
            consequence=consequence,
            severity=severity,
        )

        # Log to history
        self.log_history(
            type=HistoryType.HINGE,
            summary=f"PUSHED: {char.name} accepted future cost for {goal}",
            is_permanent=False,
        )

        return {
            "success": True,
            "advantage_granted": True,
            "thread_id": thread.id,
            "goal": goal,
            "consequence": consequence,
            "severity": severity,
            "narrative_hint": (
                f"You reach deeper. This will cost you—but not today. "
                f"Advantage granted."
            ),
        }

    # -------------------------------------------------------------------------
    # Non-Action / Avoidance Tracking
    # -------------------------------------------------------------------------

    def log_avoidance(
        self,
        situation: str,
        what_was_at_stake: str,
        potential_consequence: str,
        severity: str = "moderate",
    ) -> AvoidedSituation:
        """
        Log when a player chooses not to engage with a significant situation.

        Avoidance is content. The world doesn't wait.

        Args:
            situation: What was presented that they avoided
            what_was_at_stake: What they were avoiding (confrontation, decision, etc.)
            potential_consequence: What may happen because they didn't act
            severity: minor/moderate/major
        """
        if not self.current:
            raise ValueError("No campaign loaded")

        avoided = AvoidedSituation(
            situation=situation,
            what_was_at_stake=what_was_at_stake,
            potential_consequence=potential_consequence,
            severity=ThreadSeverity(severity),
            created_session=self.current.meta.session_count,
        )

        self.current.avoided_situations.append(avoided)

        # Log to history as a hinge (non-action is a choice)
        self.log_history(
            type=HistoryType.HINGE,
            summary=f"AVOIDED: {situation}",
            is_permanent=False,  # Not permanent until consequences surface
        )

        self.save_campaign()
        return avoided

    def surface_avoidance(
        self,
        avoidance_id: str,
        what_happened: str,
    ) -> AvoidedSituation | None:
        """
        Mark an avoidance as surfaced when its consequences come due.

        Args:
            avoidance_id: ID of the avoided situation
            what_happened: Description of how the consequence manifested
        """
        if not self.current:
            return None

        for avoided in self.current.avoided_situations:
            if avoided.id == avoidance_id and not avoided.surfaced:
                avoided.surfaced = True
                avoided.surfaced_session = self.current.meta.session_count

                # Log the consequence
                self.log_history(
                    type=HistoryType.CONSEQUENCE,
                    summary=f"AVOIDANCE CONSEQUENCE: {what_happened}",
                    is_permanent=avoided.severity == ThreadSeverity.MAJOR,
                )

                self.save_campaign()
                return avoided

        return None

    def get_pending_avoidances(self) -> list[dict]:
        """
        Get all unsurfaced avoided situations for GM context.

        Returns avoidances sorted by severity and age.
        """
        if not self.current:
            return []

        pending = []
        current_session = self.current.meta.session_count

        for avoided in self.current.avoided_situations:
            if not avoided.surfaced:
                age = current_session - avoided.created_session
                pending.append({
                    "id": avoided.id,
                    "situation": avoided.situation,
                    "what_was_at_stake": avoided.what_was_at_stake,
                    "potential_consequence": avoided.potential_consequence,
                    "severity": avoided.severity.value,
                    "age_sessions": age,
                    "overdue": age >= 3,  # Hint that it's been a while
                })

        # Sort by severity (major first) then age (oldest first)
        severity_order = {"major": 0, "moderate": 1, "minor": 2}
        pending.sort(key=lambda a: (severity_order.get(a["severity"], 99), -a["age_sessions"]))

        return pending

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
        from .schema import RefusedEnhancement

        if not self.current:
            raise ValueError("No campaign loaded")

        char = self.get_character(character_id)
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
        self.log_history(
            type=HistoryType.HINGE,
            summary=f"Refused {source.value} enhancement: {name}",
            is_permanent=True,
        )

        self.save_campaign()
        return refusal

    def get_refusal_reputation(self, character_id: str) -> dict | None:
        """
        Calculate refusal reputation based on refused enhancements.

        Returns title, count, and faction breakdown for GM context.
        """
        char = self.get_character(character_id)
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

        Args:
            character_id: Character being leveraged
            enhancement_id: Enhancement being leveraged
            demand: What the faction is asking
            weight: Pressure level (light/medium/heavy)
            threat_basis: Why leverage works (info or functional leverage)
            deadline: Human-facing deadline ("Before the convoy leaves")
            deadline_sessions: Sessions until must resolve (e.g., 2)
            consequences: What happens if ignored
        """
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

        # Check for existing demand (new system) or obligation (legacy)
        if enhancement.leverage.pending_demand or enhancement.leverage.pending_obligation:
            return {"error": "Already has pending demand - resolve that first"}

        # Calculate deadline session if relative deadline given
        deadline_session = None
        if deadline_sessions is not None:
            deadline_session = self.current.meta.session_count + deadline_sessions

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
            created_session=self.current.meta.session_count,
            weight=LeverageWeight(weight),
        )

        enhancement.leverage.pending_demand = leverage_demand
        enhancement.leverage.last_called = datetime.now()
        enhancement.leverage.weight = LeverageWeight(weight)

        self.save_campaign()

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

        Works with both new LeverageDemand system and legacy pending_obligation.
        """
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
        self.log_history(
            type=HistoryType.CONSEQUENCE,
            summary=f"Leverage {response}: {enhancement.source.value} demanded '{old_demand_text}', outcome: {outcome}",
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

        Score is for sorting: higher = more urgent.
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
        Does NOT auto-escalate - returns hints for GM judgment.
        """
        if not self.current:
            return []

        demands = []
        current_session = self.current.meta.session_count

        for char in self.current.characters:
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
        Does NOT auto-escalate - the GM decides how to handle.
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

        Called by GM when a deadline passes or player ignores faction pressure.

        escalation_type:
        - queue_consequence: Creates dormant thread from demand consequences
        - increase_weight: Bumps demand weight (light→medium→heavy)
        - faction_action: Logs faction taking independent action

        All types log to history. Does NOT auto-resolve the demand.
        """
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
            thread = self.queue_dormant_thread(
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
            self.log_history(
                type=HistoryType.CONSEQUENCE,
                summary=f"FACTION ACTION: {action_desc}",
                is_permanent=False,
            )
            result["action"] = action_desc

        else:
            return {"error": f"Unknown escalation type: {escalation_type}"}

        self.save_campaign()
        return result

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
