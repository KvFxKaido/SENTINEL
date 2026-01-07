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


def _extract_hits(results: Any) -> list:
    """
    Extract hits from memvid query results.

    Handles both object-style (_extract_hits(results)) and dict-style (results['hits'])
    return formats for compatibility across memvid-sdk versions.
    """
    if results is None:
        return []
    # Try object attribute first
    if hasattr(results, 'hits'):
        return _extract_hits(results)
    # Try dict access
    if isinstance(results, dict):
        return results.get('hits', [])
    # If it's already a list, return it
    if isinstance(results, list):
        return results
    return []


# -----------------------------------------------------------------------------
# Check for memvid-sdk availability
# -----------------------------------------------------------------------------

try:
    import memvid_sdk
    MEMVID_AVAILABLE = True
except ImportError:
    memvid_sdk = None  # type: ignore
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
        self._mv: Any = None  # memvid_sdk.Memvid instance

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
            self.campaign_file.parent.mkdir(parents=True, exist_ok=True)

            if self.campaign_file.exists():
                self._mv = memvid_sdk.use("basic", str(self.campaign_file))
                logger.info(f"Opened existing memvid: {self.campaign_file}")
            else:
                self._mv = memvid_sdk.use(
                    "basic",
                    str(self.campaign_file),
                    mode="create"
                )
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
            "type": FrameType.TURN,
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
            frame_id = self._mv.put(
                title=f"Turn {turn_number} - Session {campaign.meta.session_count}",
                label=FrameType.TURN,
                text=json.dumps(frame_data),
                tags=[
                    f"type:{FrameType.TURN}",
                    f"session:{campaign.meta.session_count}",
                    f"turn:{turn_number}",
                ],
            )
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
            "type": FrameType.HINGE,
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
            frame_id = self._mv.put(
                title=f"HINGE: {hinge.choice[:50]}...",
                label=FrameType.HINGE,
                text=json.dumps(frame_data),
                tags=[
                    f"type:{FrameType.HINGE}",
                    f"session:{session}",
                    f"hinge_id:{hinge.id}",
                    "severity:high",
                ],
            )
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
            "type": FrameType.NPC_INTERACTION,
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

        tags = [
            f"type:{FrameType.NPC_INTERACTION}",
            f"npc_id:{npc.id}",
            f"npc_name:{npc.name}",
            f"session:{session}",
        ]
        if npc.faction:
            tags.append(f"faction:{npc.faction.value}")

        try:
            frame_id = self._mv.put(
                title=f"Interaction: {npc.name}",
                label=FrameType.NPC_INTERACTION,
                text=json.dumps(frame_data),
                tags=tags,
            )
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
            "type": FrameType.FACTION_SHIFT,
            "faction": faction.value,
            "from_standing": from_standing,
            "to_standing": to_standing,
            "cause": cause,
            "session": session,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            frame_id = self._mv.put(
                title=f"Faction Shift: {faction.value}",
                label=FrameType.FACTION_SHIFT,
                text=json.dumps(frame_data),
                tags=[
                    f"type:{FrameType.FACTION_SHIFT}",
                    f"faction:{faction.value}",
                    f"session:{session}",
                ],
            )
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
            "type": FrameType.DORMANT_THREAD,
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
            frame_id = self._mv.put(
                title=f"Thread: {thread.origin[:50]}...",
                label=FrameType.DORMANT_THREAD,
                text=json.dumps(frame_data),
                tags=[
                    f"type:{FrameType.DORMANT_THREAD}",
                    f"thread_id:{thread.id}",
                    "status:dormant",
                    f"severity:{thread.severity.value}",
                ],
            )
            self._mv.commit()
            return frame_id

        except Exception as e:
            logger.error(f"Failed to save dormant thread: {e}")
            return None

    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------

    def _parse_frame_data(self, hit: Any) -> dict:
        """Parse frame data from a search hit."""
        try:
            # Get full frame data using the URI
            frame = self._mv.frame(hit.uri)
            # The text field contains our JSON data
            if "text" in frame:
                return json.loads(frame["text"])
            # Fallback: try to parse from snippet
            return json.loads(hit.snippet) if hit.snippet else {}
        except (json.JSONDecodeError, KeyError, TypeError):
            # Return basic hit info if parsing fails
            return {
                "title": hit.title,
                "tags": hit.tags,
                "snippet": hit.snippet,
            }

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
            # Add type filter to query if specified
            search_query = query_text
            if frame_type:
                search_query = f"type:{frame_type} {query_text}"

            results = self._mv.find(search_query, k=top_k, snippet_chars=500)
            return [self._parse_frame_data(hit) for hit in _extract_hits(results)]

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
            results = self._mv.find(
                f"type:{FrameType.NPC_INTERACTION} npc_id:{npc_id}",
                k=limit,
                snippet_chars=500,
            )
            return [self._parse_frame_data(hit) for hit in _extract_hits(results)]

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
            results = self._mv.find(
                f"type:{FrameType.NPC_INTERACTION} npc_id:{npc_id} {topic}",
                k=5,
                snippet_chars=500,
            )
            hits = [self._parse_frame_data(hit) for hit in _extract_hits(results)]
            return len(hits) > 0, hits

        except Exception as e:
            logger.error(f"NPC memory query failed: {e}")
            return False, []

    def get_hinges(self, limit: int = 10) -> list[dict]:
        """Get all hinge moments, newest first."""
        if not self.enabled or not self._mv:
            return []

        try:
            results = self._mv.find(
                f"type:{FrameType.HINGE}",
                k=limit,
                snippet_chars=500,
            )
            return [self._parse_frame_data(hit) for hit in _extract_hits(results)]

        except Exception as e:
            logger.error(f"Hinge query failed: {e}")
            return []

    def get_session_timeline(self, session: int) -> list[dict]:
        """Get all frames from a specific session."""
        if not self.enabled or not self._mv:
            return []

        try:
            results = self._mv.find(
                f"session:{session}",
                k=100,
                snippet_chars=500,
            )
            return [self._parse_frame_data(hit) for hit in _extract_hits(results)]

        except Exception as e:
            logger.error(f"Session timeline query failed: {e}")
            return []

    def get_active_threads(self) -> list[dict]:
        """Get all dormant threads that haven't been resolved."""
        if not self.enabled or not self._mv:
            return []

        try:
            results = self._mv.find(
                f"type:{FrameType.DORMANT_THREAD} status:dormant",
                k=50,
                snippet_chars=500,
            )
            return [self._parse_frame_data(hit) for hit in _extract_hits(results)]

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
