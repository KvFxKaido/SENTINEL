"""
Memvid integration for SENTINEL campaign memory.

Provides append-only, queryable storage for campaign events using memvid's
single-file memory system. Designed to complement (not replace) JSON saves.

Phase 1: Internal GM retrieval only - no player-facing access.

Usage:
    adapter = MemvidAdapter("campaigns/my_campaign.mv2")
    adapter.save_turn(campaign, choices_made, npcs_affected)
    results = adapter.query("what happened with Nexus")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .schema import (
        Campaign,
        Character,
        DormantThread,
        HingeMoment,
        NPC,
        FactionName,
    )

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Check for memvid-sdk availability
# -----------------------------------------------------------------------------

try:
    from memvid import Memvid, PutOptions, SearchRequest
    MEMVID_AVAILABLE = True
except ImportError:
    MEMVID_AVAILABLE = False
    logger.info("memvid-sdk not installed. Run: pip install memvid-sdk")


# -----------------------------------------------------------------------------
# Frame Types (for tagging and filtering)
# -----------------------------------------------------------------------------

class FrameType:
    """Constants for frame type tags."""
    TURN = "turn_state"
    HINGE = "hinge_moment"
    NPC_INTERACTION = "npc_interaction"
    FACTION_SHIFT = "faction_shift"
    DORMANT_THREAD = "dormant_thread"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


# -----------------------------------------------------------------------------
# Memvid Adapter
# -----------------------------------------------------------------------------

class MemvidAdapter:
    """
    Adapter for storing SENTINEL campaign events in memvid.

    Features:
    - Append-only turn snapshots
    - Tagged hinge moments for easy retrieval
    - NPC interaction history (per-NPC queryable)
    - Dormant thread tracking
    - Semantic search across campaign history

    Design Philosophy:
    - Memvid is evidence, not memory (see memvid_integration_design.md)
    - Raw frames are never exposed to players
    - All queries are filtered through faction bias before use
    """

    def __init__(self, campaign_file: str | Path, enabled: bool = True):
        """
        Initialize memvid adapter.

        Args:
            campaign_file: Path to .mv2 file (created if doesn't exist)
            enabled: If False, all operations are no-ops (for graceful degradation)
        """
        self.campaign_file = Path(campaign_file)
        self.enabled = enabled and MEMVID_AVAILABLE
        self._mv: Memvid | None = None

        if self.enabled:
            self._init_memvid()
        elif not MEMVID_AVAILABLE:
            logger.warning(
                "Memvid disabled: SDK not installed. "
                "Install with: pip install memvid-sdk"
            )

    def _init_memvid(self) -> None:
        """Initialize or open the memvid file."""
        try:
            if self.campaign_file.exists():
                self._mv = Memvid.open(str(self.campaign_file))
                logger.info(f"Opened existing memvid: {self.campaign_file}")
            else:
                self.campaign_file.parent.mkdir(parents=True, exist_ok=True)
                self._mv = Memvid.create(str(self.campaign_file))
                logger.info(f"Created new memvid: {self.campaign_file}")
        except Exception as e:
            logger.error(f"Failed to initialize memvid: {e}")
            self.enabled = False

    # -------------------------------------------------------------------------
    # Write Operations
    # -------------------------------------------------------------------------

    def save_turn(
        self,
        campaign: Campaign,
        turn_number: int,
        choices_made: list[dict] | None = None,
        npcs_affected: list[str] | None = None,
        narrative_summary: str = "",
    ) -> str | None:
        """
        Save a complete turn state as a Smart Frame.

        Args:
            campaign: Current campaign state
            turn_number: Sequential turn number
            choices_made: List of choices the player made this turn
            npcs_affected: List of NPC IDs affected by this turn
            narrative_summary: Brief GM summary of what happened

        Returns:
            Frame ID if successful, None otherwise
        """
        if not self.enabled or not self._mv:
            return None

        # Extract relevant state for the frame
        player = campaign.characters[0] if campaign.characters else None

        frame_data = {
            "turn": turn_number,
            "session": campaign.meta.session_count,
            "timestamp": datetime.now().isoformat(),
            "player": {
                "name": player.name if player else "Unknown",
                "social_energy": player.social_energy.current if player else 100,
                "social_state": player.social_energy.state if player else "Centered",
            } if player else None,
            "faction_standings": self._extract_faction_standings(campaign),
            "choices_made": choices_made or [],
            "npcs_affected": npcs_affected or [],
            "active_threads": len(campaign.dormant_threads),
            "narrative_summary": narrative_summary,
            "phase": campaign.session.phase.value if campaign.session else "between",
        }

        try:
            opts = (
                PutOptions.builder()
                .title(f"Turn {turn_number} - Session {campaign.meta.session_count}")
                .tag("type", FrameType.TURN)
                .tag("session", str(campaign.meta.session_count))
                .tag("turn", str(turn_number))
                .build()
            )

            frame_id = self._mv.put_json(frame_data, opts)
            self._mv.commit()
            logger.debug(f"Saved turn {turn_number} as frame {frame_id}")
            return frame_id

        except Exception as e:
            logger.error(f"Failed to save turn: {e}")
            return None

    def save_hinge_moment(
        self,
        hinge: HingeMoment,
        session: int,
        immediate_effects: list[str] | None = None,
        dormant_threads_created: list[str] | None = None,
    ) -> str | None:
        """
        Save a hinge moment as a tagged keyframe.

        Hinge frames are immutable and never decay - the fact of the choice
        is permanent, even if interpretations shift over time.

        Args:
            hinge: The hinge moment data
            session: Session number when this occurred
            immediate_effects: List of immediate consequences
            dormant_threads_created: IDs of dormant threads spawned by this choice

        Returns:
            Frame ID if successful, None otherwise
        """
        if not self.enabled or not self._mv:
            return None

        frame_data = {
            "hinge_id": hinge.id,
            "session": session,
            "situation": hinge.situation,
            "choice": hinge.choice,
            "reasoning": hinge.reasoning,
            "what_shifted": hinge.what_shifted,
            "timestamp": hinge.timestamp.isoformat(),
            "immediate_effects": immediate_effects or [],
            "dormant_threads_created": dormant_threads_created or [],
        }

        try:
            opts = (
                PutOptions.builder()
                .title(f"HINGE: {hinge.choice[:50]}...")
                .tag("type", FrameType.HINGE)
                .tag("session", str(session))
                .tag("hinge_id", hinge.id)
                .tag("severity", "high")
                .build()
            )

            frame_id = self._mv.put_json(frame_data, opts)
            self._mv.commit()
            logger.info(f"Saved hinge moment: {hinge.id}")
            return frame_id

        except Exception as e:
            logger.error(f"Failed to save hinge: {e}")
            return None

    def save_npc_interaction(
        self,
        npc: NPC,
        player_action: str,
        npc_reaction: str,
        disposition_change: int = 0,
        session: int = 0,
        context: dict | None = None,
    ) -> str | None:
        """
        Save an NPC interaction for per-NPC memory retrieval.

        This enables NPCs to "remember" specific interactions when
        queried later (filtered through their faction bias).

        Args:
            npc: The NPC involved
            player_action: What the player did/said
            npc_reaction: How the NPC responded
            disposition_change: Change in disposition (-2 to +2)
            session: Session number
            context: Additional context (location, witnesses, etc.)

        Returns:
            Frame ID if successful, None otherwise
        """
        if not self.enabled or not self._mv:
            return None

        frame_data = {
            "npc_id": npc.id,
            "npc_name": npc.name,
            "faction": npc.faction.value if npc.faction else None,
            "player_action": player_action,
            "npc_reaction": npc_reaction,
            "disposition_before": npc.disposition.value,
            "disposition_change": disposition_change,
            "session": session,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            # Include agenda hints for bias filtering later
            "npc_fears": npc.agenda.fears if npc.agenda else None,
            "npc_wants": npc.agenda.wants if npc.agenda else None,
        }

        try:
            opts = (
                PutOptions.builder()
                .title(f"Interaction: {npc.name}")
                .tag("type", FrameType.NPC_INTERACTION)
                .tag("npc_id", npc.id)
                .tag("npc_name", npc.name)
                .tag("session", str(session))
                .build()
            )

            if npc.faction:
                opts = opts.tag("faction", npc.faction.value)

            frame_id = self._mv.put_json(frame_data, opts)
            self._mv.commit()
            logger.debug(f"Saved interaction with {npc.name}")
            return frame_id

        except Exception as e:
            logger.error(f"Failed to save NPC interaction: {e}")
            return None

    def save_faction_shift(
        self,
        faction: FactionName,
        from_standing: str,
        to_standing: str,
        cause: str,
        session: int,
    ) -> str | None:
        """Save a faction standing change."""
        if not self.enabled or not self._mv:
            return None

        frame_data = {
            "faction": faction.value,
            "from_standing": from_standing,
            "to_standing": to_standing,
            "cause": cause,
            "session": session,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            opts = (
                PutOptions.builder()
                .title(f"Faction Shift: {faction.value}")
                .tag("type", FrameType.FACTION_SHIFT)
                .tag("faction", faction.value)
                .tag("session", str(session))
                .build()
            )

            frame_id = self._mv.put_json(frame_data, opts)
            self._mv.commit()
            return frame_id

        except Exception as e:
            logger.error(f"Failed to save faction shift: {e}")
            return None

    def save_dormant_thread(self, thread: DormantThread) -> str | None:
        """Save a new dormant thread for tracking."""
        if not self.enabled or not self._mv:
            return None

        frame_data = {
            "thread_id": thread.id,
            "origin": thread.origin,
            "trigger_condition": thread.trigger_condition,
            "consequence": thread.consequence,
            "severity": thread.severity.value,
            "created_session": thread.created_session,
            "trigger_keywords": thread.trigger_keywords,
            "status": "dormant",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            opts = (
                PutOptions.builder()
                .title(f"Thread: {thread.origin[:50]}...")
                .tag("type", FrameType.DORMANT_THREAD)
                .tag("thread_id", thread.id)
                .tag("status", "dormant")
                .tag("severity", thread.severity.value)
                .build()
            )

            frame_id = self._mv.put_json(frame_data, opts)
            self._mv.commit()
            return frame_id

        except Exception as e:
            logger.error(f"Failed to save dormant thread: {e}")
            return None

    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        frame_type: str | None = None,
    ) -> list[dict]:
        """
        Semantic search across campaign history.

        Args:
            query_text: Natural language query
            top_k: Maximum results to return
            frame_type: Optional filter by FrameType constant

        Returns:
            List of matching frame data dicts
        """
        if not self.enabled or not self._mv:
            return []

        try:
            request = SearchRequest(
                query=query_text,
                top_k=top_k,
                snippet_chars=300,
            )

            if frame_type:
                request = request.filter("type", frame_type)

            results = self._mv.search(request)
            return [hit.json_data for hit in results.hits]

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_npc_history(self, npc_id: str, limit: int = 20) -> list[dict]:
        """
        Get all interactions with a specific NPC.

        Args:
            npc_id: The NPC's ID
            limit: Maximum interactions to return

        Returns:
            List of interaction frames, newest first
        """
        if not self.enabled or not self._mv:
            return []

        try:
            request = SearchRequest(
                query=f"npc_id:{npc_id}",
                top_k=limit,
            ).filter("type", FrameType.NPC_INTERACTION)

            results = self._mv.search(request)
            return [hit.json_data for hit in results.hits]

        except Exception as e:
            logger.error(f"NPC history query failed: {e}")
            return []

    def npc_remembers(self, npc_id: str, topic: str) -> tuple[bool, list[dict]]:
        """
        Check if an NPC has memory related to a topic.

        Args:
            npc_id: The NPC's ID
            topic: Topic to search for

        Returns:
            Tuple of (has_memory, matching_frames)
        """
        if not self.enabled or not self._mv:
            return False, []

        try:
            request = SearchRequest(
                query=f"npc_id:{npc_id} {topic}",
                top_k=5,
            ).filter("type", FrameType.NPC_INTERACTION)

            results = self._mv.search(request)
            hits = [hit.json_data for hit in results.hits]
            return len(hits) > 0, hits

        except Exception as e:
            logger.error(f"NPC memory query failed: {e}")
            return False, []

    def get_hinges(self, limit: int = 10) -> list[dict]:
        """Get all hinge moments, newest first."""
        if not self.enabled or not self._mv:
            return []

        try:
            request = SearchRequest(
                query="type:hinge_moment",
                top_k=limit,
            ).filter("type", FrameType.HINGE)

            results = self._mv.search(request)
            return [hit.json_data for hit in results.hits]

        except Exception as e:
            logger.error(f"Hinge query failed: {e}")
            return []

    def get_session_timeline(self, session: int) -> list[dict]:
        """Get all frames from a specific session."""
        if not self.enabled or not self._mv:
            return []

        try:
            request = SearchRequest(
                query=f"session:{session}",
                top_k=100,
            )

            results = self._mv.search(request)
            return [hit.json_data for hit in results.hits]

        except Exception as e:
            logger.error(f"Session timeline query failed: {e}")
            return []

    def get_active_threads(self) -> list[dict]:
        """Get all dormant threads that haven't been resolved."""
        if not self.enabled or not self._mv:
            return []

        try:
            request = SearchRequest(
                query="status:dormant",
                top_k=50,
            ).filter("type", FrameType.DORMANT_THREAD)

            results = self._mv.search(request)
            return [hit.json_data for hit in results.hits]

        except Exception as e:
            logger.error(f"Thread query failed: {e}")
            return []

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _extract_faction_standings(self, campaign: Campaign) -> dict[str, str]:
        """Extract faction standings as a simple dict."""
        standings = {}
        for faction in [
            "nexus", "ember_colonies", "lattice", "convergence", "covenant",
            "wanderers", "cultivators", "steel_syndicate", "witnesses",
            "architects", "ghost_networks"
        ]:
            standing = getattr(campaign.factions, faction, None)
            if standing:
                standings[faction] = standing.standing.value
        return standings

    @property
    def is_enabled(self) -> bool:
        """Check if memvid is enabled and operational."""
        return self.enabled and self._mv is not None

    def close(self) -> None:
        """Close the memvid file (called on shutdown)."""
        if self._mv:
            try:
                self._mv.close()
                logger.info("Memvid closed")
            except Exception as e:
                logger.error(f"Error closing memvid: {e}")
            finally:
                self._mv = None


# -----------------------------------------------------------------------------
# Factory Function
# -----------------------------------------------------------------------------

def create_memvid_adapter(
    campaign_id: str,
    campaigns_dir: str | Path = "campaigns",
    enabled: bool = True,
) -> MemvidAdapter:
    """
    Create a memvid adapter for a campaign.

    Args:
        campaign_id: The campaign ID (used to derive .mv2 filename)
        campaigns_dir: Directory where campaigns are stored
        enabled: Whether to enable memvid (False for graceful degradation)

    Returns:
        Configured MemvidAdapter instance
    """
    campaigns_path = Path(campaigns_dir)
    mv2_file = campaigns_path / f"{campaign_id}.mv2"
    return MemvidAdapter(mv2_file, enabled=enabled)
