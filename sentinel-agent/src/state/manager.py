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
    CharacterArc,
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
    get_faction_relation,
    get_faction_allies,
    get_faction_rivals,
)
from .store import CampaignStore, JsonCampaignStore, EventQueueStore
from .memvid_adapter import MemvidAdapter, create_memvid_adapter, MEMVID_AVAILABLE
from .wiki_adapter import WikiAdapter, create_wiki_adapter
from .wiki_watcher import WikiWatcher
from .event_bus import get_event_bus, EventType

# Lazy import for systems to avoid circular imports
_leverage_system = None
_arc_system = None


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
        enable_wiki: bool = True,
        wiki_dir: str | Path = "wiki",
    ):
        """
        Initialize with a store.

        Args:
            store: CampaignStore instance, or path for JsonCampaignStore
            event_queue: Optional EventQueueStore for MCP event processing
            enable_memvid: Whether to enable memvid memory (requires memvid-sdk)
            enable_wiki: Whether to enable wiki event logging
            wiki_dir: Path to wiki directory for event logging
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

        # Wiki adapter (lazily initialized per campaign)
        self._enable_wiki = enable_wiki
        self._wiki_dir = Path(wiki_dir)
        self._wiki: WikiAdapter | None = None
        self._wiki_watcher: WikiWatcher | None = None

        # Game systems (lazily initialized)
        self._leverage_system = None
        self._arc_system = None

    @property
    def leverage(self):
        """Get the leverage system (lazy initialization)."""
        if self._leverage_system is None:
            from ..systems.leverage import LeverageSystem
            self._leverage_system = LeverageSystem(self)
        return self._leverage_system

    @property
    def arcs(self):
        """Get the arc system (lazy initialization)."""
        if self._arc_system is None:
            from ..systems.arcs import ArcSystem
            self._arc_system = ArcSystem(self)
        return self._arc_system

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

    # -------------------------------------------------------------------------
    # Wiki Integration
    # -------------------------------------------------------------------------

    def _init_wiki_for_campaign(self, campaign_id: str) -> None:
        """Initialize wiki adapter for a campaign."""
        if self._enable_wiki:
            self._wiki = create_wiki_adapter(
                campaign_id,
                wiki_dir=self._wiki_dir,
                enabled=True,
            )
            self._wiki_watcher = WikiWatcher(
                manager=self,
                wiki_dir=self._wiki_dir,
                campaign_id=campaign_id,
            )
            self._wiki_watcher.start_watching()
        else:
            self._wiki = None
            self._wiki_watcher = None

    def _close_wiki(self) -> None:
        """Close current wiki adapter."""
        if self._wiki_watcher:
            self._wiki_watcher.stop_watching()
            self._wiki_watcher = None
        self._wiki = None

    @property
    def wiki(self) -> WikiAdapter | None:
        """Access the wiki adapter (may be None if disabled)."""
        return self._wiki

    @property
    def wiki_watcher(self) -> WikiWatcher | None:
        """Access the wiki watcher (may be None if disabled/unavailable)."""
        return self._wiki_watcher

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
        standing_change: int = 0,
        tags: list[str] | None = None,
        context: dict | None = None,
    ) -> dict | None:
        """
        Record an NPC interaction, updating personal standing and saving to memvid.

        This is the primary method for recording meaningful NPC interactions.
        It updates the NPC's personal_standing (separate from faction) and
        stores the interaction in both the NPC's local history and memvid.

        Args:
            npc_id: NPC identifier
            player_action: What the player did
            npc_reaction: How the NPC responded
            standing_change: Change to personal standing (-20 to +20)
            tags: Tags for searching/triggers
            context: Additional context for memvid

        Returns:
            Dict with interaction details and updated disposition
        """
        if not self.current:
            return None

        npc = self.get_npc(npc_id)
        if not npc:
            return None

        session = self.current.meta.session_count

        # Record interaction on the NPC (updates personal_standing)
        interaction = npc.record_interaction(
            session=session,
            action=player_action,
            outcome=npc_reaction,
            standing_change=standing_change,
            tags=tags,
        )

        # Get faction standing for effective disposition calculation
        faction_standing = None
        if npc.faction:
            faction_standing = self.current.factions.get(npc.faction).standing

        # Calculate effective disposition
        effective_disposition = npc.get_effective_disposition(faction_standing)

        # Update NPC's displayed disposition if it changed
        old_disposition = npc.disposition
        if effective_disposition != old_disposition:
            npc.disposition = effective_disposition

        self.save_campaign()

        # Also save to memvid for semantic search
        frame_id = None
        if self._memvid:
            frame_id = self._memvid.save_npc_interaction(
                npc=npc,
                player_action=player_action,
                npc_reaction=npc_reaction,
                disposition_change=standing_change,
                session=session,
                context=context,
            )

        # Also save to wiki (auto-creates NPC page on first encounter)
        if self._wiki:
            self._wiki.save_npc_interaction(
                npc=npc,
                player_action=player_action,
                npc_reaction=npc_reaction,
                disposition_change=standing_change,
                session=session,
                context=context,
            )

        return {
            "npc_id": npc_id,
            "npc_name": npc.name,
            "action": player_action,
            "outcome": npc_reaction,
            "standing_change": standing_change,
            "personal_standing": npc.personal_standing,
            "old_disposition": old_disposition.value,
            "new_disposition": effective_disposition.value,
            "disposition_changed": effective_disposition != old_disposition,
            "frame_id": frame_id,
        }

    def get_npc_status(self, npc_id: str) -> dict | None:
        """
        Get comprehensive NPC status including personal and faction standings.

        Returns dict with:
        - NPC info (name, faction, agenda)
        - Personal standing (-100 to +100)
        - Faction standing (if applicable)
        - Effective disposition (combining both)
        - Recent interactions
        """
        if not self.current:
            return None

        npc = self.get_npc(npc_id)
        if not npc:
            return None

        # Get faction standing
        faction_standing = None
        faction_standing_value = None
        if npc.faction:
            faction_obj = self.current.factions.get(npc.faction)
            faction_standing = faction_obj.standing
            faction_standing_value = faction_standing.value

        # Calculate effective disposition
        effective_disposition = npc.get_effective_disposition(faction_standing)

        return {
            "id": npc.id,
            "name": npc.name,
            "faction": npc.faction.value if npc.faction else None,
            "agenda": {
                "wants": npc.agenda.wants,
                "fears": npc.agenda.fears,
                "leverage": npc.agenda.leverage,
                "owes": npc.agenda.owes,
            },
            "personal_standing": npc.personal_standing,
            "faction_standing": faction_standing_value,
            "base_disposition": npc.disposition.value,
            "effective_disposition": effective_disposition.value,
            "interactions": [
                {
                    "session": i.session,
                    "action": i.action,
                    "outcome": i.outcome,
                    "standing_change": i.standing_change,
                }
                for i in npc.interactions[-5:]  # Last 5
            ],
            "remembers": npc.remembers[-5:],  # Last 5 memories
        }

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

        # Close any existing adapters
        self._close_memvid()
        self._close_wiki()

        self.current = campaign
        self._cache[meta.id] = campaign
        self.save_campaign()

        # Initialize adapters for new campaign
        self._init_memvid_for_campaign(meta.id)
        self._init_wiki_for_campaign(meta.id)

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
            # Close any existing adapters
            self._close_memvid()
            self._close_wiki()

            # Run migrations if needed
            migrated = self._migrate_campaign(campaign)

            # Process pending events from MCP
            events_processed = self._process_pending_events(campaign)

            self.current = campaign
            self._cache[campaign.meta.id] = campaign

            # Persist if migrations or events were processed
            if migrated or events_processed > 0:
                self.save_campaign()

            # Initialize adapters for this campaign
            self._init_memvid_for_campaign(campaign.meta.id)
            self._init_wiki_for_campaign(campaign.meta.id)

            # Emit event for UI updates
            get_event_bus().emit(
                EventType.CAMPAIGN_LOADED,
                campaign_id=campaign.meta.id,
                session=campaign.meta.session_count,
                name=campaign.meta.name,
            )

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

    def poll_events(self) -> int:
        """
        Poll and process pending MCP events.

        Call this at the start of each input loop to ensure
        faction events from MCP are processed immediately,
        not just on campaign load.

        Returns the number of events processed.
        """
        if not self.current:
            return 0
        return self._process_pending_events(self.current)

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

            # Create history entry with provenance (event ID links MCP → history)
            entry = HistoryEntry(
                session=session,
                type=HistoryType.FACTION_SHIFT,
                summary=f"[{faction.replace('_', ' ').title()}] {summary}",
                is_permanent=is_permanent,
                event_id=event.id,  # Provenance: links to MCP event
            )
            campaign.history.append(entry)

            # Also save to memvid with same event_id for provenance tracking
            if self._memvid:
                from .schema import FactionName
                try:
                    faction_enum = FactionName(faction)
                    self._memvid.save_faction_shift(
                        faction=faction_enum,
                        from_standing="Unknown",  # MCP doesn't track this
                        to_standing="Unknown",
                        cause=f"{summary} (event_id: {event.id})",
                        session=session,
                    )
                except ValueError:
                    pass  # Invalid faction name

            # Also save to wiki
            if self._wiki:
                from .schema import FactionName
                try:
                    faction_enum = FactionName(faction)
                    self._wiki.save_faction_shift(
                        faction=faction_enum,
                        from_standing="Unknown",
                        to_standing="Unknown",
                        cause=f"{summary} (via MCP)",
                        session=session,
                    )
                except ValueError:
                    pass  # Invalid faction name

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

    def generate_session_summary(self, session_number: int | None = None) -> dict:
        """
        Generate a summary of a session's events.

        Args:
            session_number: Session to summarize (defaults to current)

        Returns:
            Dict with keys: session, hinges, faction_changes, npcs_encountered,
            threads_created, threads_resolved, key_choices
        """
        if not self.current:
            return {"error": "No campaign loaded"}

        session = session_number or self.current.meta.session_count

        summary = {
            "session": session,
            "campaign": self.current.meta.name,
            "hinges": [],
            "faction_changes": [],
            "npcs_encountered": [],
            "threads_created": [],
            "threads_resolved": [],
            "key_choices": [],
        }

        # Gather hinges from this session
        for entry in self.current.history:
            if entry.session != session:
                continue

            if entry.type == HistoryType.HINGE and entry.hinge:
                summary["hinges"].append({
                    "choice": entry.hinge.choice,
                    "situation": entry.hinge.situation,
                    "what_shifted": entry.hinge.what_shifted,
                })
                summary["key_choices"].append(entry.hinge.choice)

            elif entry.type == HistoryType.FACTION_SHIFT:
                # Parse faction shift from summary
                # Format: "Faction: Standing1 → Standing2"
                summary["faction_changes"].append({
                    "summary": entry.summary,
                    "is_permanent": entry.is_permanent,
                })

            elif entry.type == HistoryType.CONSEQUENCE:
                summary["threads_resolved"].append({
                    "summary": entry.summary,
                    "timestamp": entry.timestamp.isoformat(),
                })

        # Gather threads created this session
        for thread in self.current.dormant_threads:
            if thread.created_session == session:
                summary["threads_created"].append({
                    "origin": thread.origin,
                    "trigger": thread.trigger_condition,
                    "severity": thread.severity.value if hasattr(thread.severity, 'value') else thread.severity,
                })

        # Gather NPCs from memvid if available
        if self._memvid and self._memvid.is_enabled:
            npc_frames = self._memvid.get_session_timeline(session)
            seen_npcs = set()
            for frame in npc_frames:
                if frame.get("type") == "npc_interaction":
                    npc_name = frame.get("npc_name", "Unknown")
                    if npc_name not in seen_npcs:
                        seen_npcs.add(npc_name)
                        summary["npcs_encountered"].append({
                            "name": npc_name,
                            "faction": frame.get("faction"),
                            "disposition_change": frame.get("disposition_change", 0),
                        })

        return summary

    def format_session_summary_markdown(self, summary: dict) -> str:
        """Format a session summary as markdown for export."""
        lines = [
            f"# SESSION {summary['session']} SUMMARY",
            f"**Campaign:** {summary['campaign']}",
            "",
        ]

        # Key Choices / Hinges
        if summary["hinges"]:
            lines.append("## KEY CHOICES")
            for hinge in summary["hinges"]:
                lines.append(f"- {hinge['choice']}")
                if hinge.get("what_shifted"):
                    lines.append(f"  - *Shifted: {hinge['what_shifted']}*")
            lines.append("")

        # Faction Changes
        if summary["faction_changes"]:
            lines.append("## FACTION STANDING CHANGES")
            for change in summary["faction_changes"]:
                marker = "★" if change.get("is_permanent") else ""
                lines.append(f"- {change['summary']} {marker}")
            lines.append("")

        # Threads Created
        if summary["threads_created"]:
            lines.append("## NEW CONSEQUENCE THREADS")
            for thread in summary["threads_created"]:
                sev = thread["severity"].upper()
                lines.append(f"- [{sev}] {thread['origin']}")
                lines.append(f"  - *Trigger: {thread['trigger']}*")
            lines.append("")

        # Threads Resolved
        if summary["threads_resolved"]:
            lines.append("## RESOLVED THREADS")
            for thread in summary["threads_resolved"]:
                lines.append(f"- {thread['summary']}")
            lines.append("")

        # NPCs Encountered
        if summary["npcs_encountered"]:
            lines.append("## NPCs ENCOUNTERED")
            for npc in summary["npcs_encountered"]:
                disp = npc.get("disposition_change", 0)
                if disp > 0:
                    change = f"(+{disp})"
                elif disp < 0:
                    change = f"({disp})"
                else:
                    change = ""
                faction = f" [{npc['faction']}]" if npc.get("faction") else ""
                lines.append(f"- {npc['name']}{faction} {change}")
            lines.append("")

        return "\n".join(lines)

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

        # Emit events for reactive UI updates
        if self.current and social_energy_delta != 0:
            get_event_bus().emit(
                EventType.SOCIAL_ENERGY_CHANGED,
                campaign_id=self.current.meta.id,
                session=self.current.meta.session_count,
                character_id=character_id,
                before=before["social_energy"],
                after=after["social_energy"],
                delta=social_energy_delta,
            )
            # Special event if energy depleted
            if after["social_energy"] == 0 and before["social_energy"] > 0:
                get_event_bus().emit(
                    EventType.SOCIAL_ENERGY_DEPLETED,
                    campaign_id=self.current.meta.id,
                    session=self.current.meta.session_count,
                    character_id=character_id,
                )

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

        # Emit event for UI updates
        get_event_bus().emit(
            EventType.NPC_ADDED,
            campaign_id=self.current.meta.id,
            session=self.current.meta.session_count,
            npc_id=npc.id,
            npc_name=npc.name,
            faction=npc.faction.value if npc.faction else None,
            active=active,
        )

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

        # Emit event for UI updates
        get_event_bus().emit(
            EventType.NPC_DISPOSITION_CHANGED,
            campaign_id=self.current.meta.id,
            session=self.current.meta.session_count,
            npc_id=npc_id,
            npc_name=npc.name,
            before=before,
            after=after,
        )

        return {
            "npc_id": npc_id,
            "npc_name": npc.name,
            "before": before,
            "after": after,
        }

    # -------------------------------------------------------------------------
    # Faction Management
    # -------------------------------------------------------------------------

    def shift_faction(
        self,
        faction: FactionName,
        delta: int,
        reason: str,
        apply_cascades: bool = True,
    ) -> dict:
        """
        Shift faction standing with optional cascade effects.

        When you help or oppose a faction, their allies and rivals react:
        - Allies of a helped faction warm slightly to you
        - Rivals of a helped faction cool slightly toward you
        - (Inverse for opposing a faction)

        Args:
            faction: Target faction
            delta: Standing shift (-2 betray, -1 oppose, +1 help, +2 major help)
            reason: Description of what caused the shift
            apply_cascades: Whether to apply ripple effects to related factions

        Returns:
            Dict with before/after, cascades, and NPC reactions
        """
        if not self.current:
            raise ValueError("No campaign loaded")

        standing = self.current.factions.get(faction)
        before = standing.standing
        after = standing.shift(delta)

        # Log to history
        self.log_history(
            type=HistoryType.FACTION_SHIFT,
            summary=f"{faction.value}: {before.value} → {after.value} ({reason})",
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

        # Save to wiki
        if self._wiki:
            self._wiki.save_faction_shift(
                faction=faction,
                from_standing=before.value,
                to_standing=after.value,
                cause=reason,
                session=self.current.meta.session_count,
            )

        # Calculate and apply cascade effects
        cascades = []
        if apply_cascades and abs(delta) >= 1:
            cascades = self._calculate_faction_cascades(faction, delta, reason)

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

        # Emit event for UI updates
        get_event_bus().emit(
            EventType.FACTION_CHANGED,
            campaign_id=self.current.meta.id,
            session=self.current.meta.session_count,
            faction=faction.value,
            before=before.value,
            after=after.value,
            reason=reason,
            cascades=cascades,
        )

        return {
            "faction": faction.value,
            "before": before.value,
            "after": after.value,
            "reason": reason,
            "cascades": cascades,
            "npc_reactions": triggered,
        }

    def _calculate_faction_cascades(
        self,
        primary_faction: FactionName,
        delta: int,
        reason: str,
    ) -> list[dict]:
        """
        Calculate cascade effects on related factions.

        When player helps a faction:
        - Strong allies (relation >= 30): +15% of delta
        - Moderate allies (relation >= 20): +10% of delta
        - Strong rivals (relation <= -30): -25% of delta
        - Moderate rivals (relation <= -20): -15% of delta

        Returns list of cascade effects applied.
        """
        cascades = []

        for other_faction in FactionName:
            if other_faction == primary_faction:
                continue

            relation = get_faction_relation(primary_faction, other_faction)
            if relation == 0:
                continue  # No defined relationship

            cascade_delta = 0
            cascade_reason = ""

            if delta > 0:  # Player helped the primary faction
                if relation >= 30:  # Strong ally
                    cascade_delta = max(1, int(abs(delta) * 0.15))
                    cascade_reason = f"Ally of {primary_faction.value}"
                elif relation >= 20:  # Moderate ally
                    # Only cascade on larger shifts
                    if abs(delta) >= 2:
                        cascade_delta = 1
                        cascade_reason = f"Ally of {primary_faction.value}"
                elif relation <= -30:  # Strong rival
                    cascade_delta = -max(1, int(abs(delta) * 0.25))
                    cascade_reason = f"Rival of {primary_faction.value}"
                elif relation <= -20:  # Moderate rival
                    if abs(delta) >= 2:
                        cascade_delta = -1
                        cascade_reason = f"Rival of {primary_faction.value}"

            elif delta < 0:  # Player opposed the primary faction
                if relation >= 30:  # Strong ally (of the opposed faction)
                    cascade_delta = -max(1, int(abs(delta) * 0.15))
                    cascade_reason = f"Ally of {primary_faction.value}"
                elif relation >= 20:  # Moderate ally
                    if abs(delta) >= 2:
                        cascade_delta = -1
                        cascade_reason = f"Ally of {primary_faction.value}"
                elif relation <= -30:  # Strong rival (pleased you opposed their enemy)
                    cascade_delta = max(1, int(abs(delta) * 0.20))
                    cascade_reason = f"Rival of {primary_faction.value}"
                elif relation <= -20:  # Moderate rival
                    if abs(delta) >= 2:
                        cascade_delta = 1
                        cascade_reason = f"Rival of {primary_faction.value}"

            if cascade_delta != 0:
                # Apply the cascade (without further cascades to prevent infinite loops)
                other_standing = self.current.factions.get(other_faction)
                before = other_standing.standing
                after = other_standing.shift(cascade_delta)

                cascades.append({
                    "faction": other_faction.value,
                    "before": before.value,
                    "after": after.value,
                    "delta": cascade_delta,
                    "reason": cascade_reason,
                    "relation": relation,
                })

                # Log subtle cascades (don't spam history with minor shifts)
                if before != after:
                    self.log_history(
                        type=HistoryType.FACTION_SHIFT,
                        summary=f"{other_faction.value}: {before.value} → {after.value} ({cascade_reason})",
                        is_permanent=False,
                    )

        return cascades

    def get_faction_web(self, faction: FactionName) -> dict:
        """
        Get a faction's relationship web for display.

        Returns dict with allies, rivals, and neutral factions.
        """
        allies = []
        rivals = []
        neutral = []

        for other in FactionName:
            if other == faction:
                continue

            relation = get_faction_relation(faction, other)
            player_standing = self.current.factions.get(other).standing.value if self.current else "Unknown"

            entry = {
                "faction": other.value,
                "relation": relation,
                "player_standing": player_standing,
            }

            if relation >= 20:
                allies.append(entry)
            elif relation <= -20:
                rivals.append(entry)
            else:
                neutral.append(entry)

        # Sort by relation strength
        allies.sort(key=lambda x: x["relation"], reverse=True)
        rivals.sort(key=lambda x: x["relation"])

        return {
            "faction": faction.value,
            "allies": allies,
            "rivals": rivals,
            "neutral": neutral,
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

        # Save to wiki
        if self._wiki:
            self._wiki.save_hinge_moment(
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

        # Save to wiki
        if self._wiki:
            self._wiki.save_dormant_thread(thread)

        self.save_campaign()

        # Emit event for UI updates
        get_event_bus().emit(
            EventType.THREAD_QUEUED,
            campaign_id=self.current.meta.id,
            session=self.current.meta.session_count,
            thread_id=thread.id,
            origin=origin,
            trigger_condition=trigger_condition,
            severity=severity,
        )

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

                # Log thread triggering to wiki
                if self._wiki:
                    self._wiki.save_thread_triggered(
                        thread=activated,
                        session=self.current.meta.session_count,
                        outcome=activation_context,
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
    # Enhancement Leverage (delegated to LeverageSystem)
    # -------------------------------------------------------------------------

    # Backwards compatibility constant
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

    def grant_enhancement(self, character_id: str, name: str, source: FactionName, benefit: str, cost: str):
        """Grant an enhancement to a character. Delegates to LeverageSystem."""
        return self.leverage.grant_enhancement(character_id, name, source, benefit, cost)

    def refuse_enhancement(self, character_id: str, name: str, source: FactionName, benefit: str, reason_refused: str):
        """Record a refused enhancement. Delegates to LeverageSystem."""
        return self.leverage.refuse_enhancement(character_id, name, source, benefit, reason_refused)

    def get_refusal_reputation(self, character_id: str) -> dict | None:
        """Get refusal reputation. Delegates to LeverageSystem."""
        return self.leverage.get_refusal_reputation(character_id)

    def call_leverage(self, character_id: str, enhancement_id: str, demand: str, weight: str = "medium",
                      threat_basis: list[str] | None = None, deadline: str | None = None,
                      deadline_sessions: int | None = None, consequences: list[str] | None = None) -> dict:
        """Call leverage on an enhancement. Delegates to LeverageSystem."""
        return self.leverage.call_leverage(character_id, enhancement_id, demand, weight,
                                           threat_basis, deadline, deadline_sessions, consequences)

    def resolve_leverage(self, character_id: str, enhancement_id: str, response: str, outcome: str) -> dict:
        """Resolve a leverage demand. Delegates to LeverageSystem."""
        return self.leverage.resolve_leverage(character_id, enhancement_id, response, outcome)

    def check_leverage_hints(self, player_input: str) -> list[dict]:
        """Check for leverage hints. Delegates to LeverageSystem."""
        return self.leverage.check_leverage_hints(player_input)

    def get_pending_demands(self) -> list[dict]:
        """Get pending leverage demands. Delegates to LeverageSystem."""
        return self.leverage.get_pending_demands()

    def check_demand_deadlines(self) -> list[dict]:
        """Check demand deadlines. Delegates to LeverageSystem."""
        return self.leverage.check_demand_deadlines()

    def escalate_demand(self, character_id: str, enhancement_id: str, escalation_type: str, narrative: str = "") -> dict:
        """Escalate a demand. Delegates to LeverageSystem."""
        return self.leverage.escalate_demand(character_id, enhancement_id, escalation_type, narrative)

    # -------------------------------------------------------------------------
    # Character Arc Detection (delegated to ArcSystem)
    # -------------------------------------------------------------------------

    def detect_arcs(self, character_id: str | None = None) -> list[dict]:
        """Detect emergent character arcs. Delegates to ArcSystem."""
        return self.arcs.detect_arcs(character_id)

    def suggest_arc(self, character_id: str | None = None) -> dict | None:
        """Get strongest arc candidate. Delegates to ArcSystem."""
        return self.arcs.suggest_arc(character_id)

    def accept_arc(self, character_id: str, arc_type: str) -> CharacterArc | None:
        """Accept a character arc. Delegates to ArcSystem."""
        return self.arcs.accept_arc(character_id, arc_type)

    def reject_arc(self, character_id: str, arc_type: str) -> bool:
        """Reject a character arc. Delegates to ArcSystem."""
        return self.arcs.reject_arc(character_id, arc_type)

    def get_active_arcs(self, character_id: str | None = None) -> list[CharacterArc]:
        """Get accepted arcs. Delegates to ArcSystem."""
        return self.arcs.get_active_arcs(character_id)

    def format_arcs_for_gm(self, character_id: str | None = None) -> str:
        """Format arcs for GM context. Delegates to ArcSystem."""
        return self.arcs.format_arcs_for_gm(character_id)

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
