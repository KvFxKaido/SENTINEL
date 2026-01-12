"""
Wiki integration for SENTINEL campaign events.

Logs significant campaign events to wiki overlay files for
campaign-specific lore that persists across sessions.

Events are written to:
- wiki/campaigns/{campaign_id}/_events.md (timeline)
- wiki/campaigns/{campaign_id}/{Page}.md (page extensions)

This adapter mirrors the MemvidAdapter interface for consistency.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import (
        Campaign,
        HingeMoment,
        NPC,
        FactionName,
        DormantThread,
    )

logger = logging.getLogger(__name__)


class WikiAdapter:
    """
    Adapter for logging campaign events to wiki overlay files.

    Features:
    - Auto-creates campaign overlay directory
    - Logs events to _events.md timeline
    - Creates/extends page overlays for faction and NPC updates
    - Graceful degradation if wiki directory doesn't exist
    """

    def __init__(
        self,
        wiki_dir: str | Path,
        campaign_id: str,
        enabled: bool = True,
    ):
        """
        Initialize wiki adapter.

        Args:
            wiki_dir: Path to wiki root directory
            campaign_id: Campaign ID for overlay directory
            enabled: If False, all operations are no-ops
        """
        self.wiki_dir = Path(wiki_dir)
        self.campaign_id = campaign_id
        self.enabled = enabled

        # Validate wiki directory exists
        if not self.wiki_dir.exists():
            logger.warning(f"Wiki directory not found: {self.wiki_dir}")
            self.enabled = False
        elif not (self.wiki_dir / "canon").exists():
            logger.warning(f"Wiki canon directory not found: {self.wiki_dir / 'canon'}")
            self.enabled = False

        if self.enabled:
            self._init_overlay_dir()

    def _init_overlay_dir(self) -> None:
        """Create campaign overlay directory if needed."""
        self.overlay_dir = self.wiki_dir / "campaigns" / self.campaign_id
        try:
            self.overlay_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Wiki overlay directory: {self.overlay_dir}")
        except Exception as e:
            logger.error(f"Failed to create overlay directory: {e}")
            self.enabled = False

    # -------------------------------------------------------------------------
    # Event Logging
    # -------------------------------------------------------------------------

    def _log_event(
        self,
        session: int,
        event: str,
        event_type: str = "event",
        related_pages: list[str] | None = None,
    ) -> bool:
        """
        Append an event to the campaign timeline.

        Args:
            session: Session number
            event: Event description
            event_type: Type tag (hinge, faction, npc, thread)
            related_pages: Wiki pages to link

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        events_file = self.overlay_dir / "_events.md"
        timestamp = datetime.now().strftime("%Y-%m-%d")

        # Format entry
        type_badge = f"[{event_type.upper()}]" if event_type != "event" else ""
        entry = f"- **Session {session}** ({timestamp}) {type_badge}: {event}"

        if related_pages:
            links = ", ".join(f"[[{p}]]" for p in related_pages)
            entry += f" — {links}"

        try:
            if events_file.exists():
                content = events_file.read_text(encoding="utf-8")
                new_content = content.rstrip() + "\n" + entry + "\n"
            else:
                new_content = (
                    "# Campaign Timeline\n\n"
                    "Significant events from this campaign.\n\n"
                    f"{entry}\n"
                )

            events_file.write_text(new_content, encoding="utf-8")
            logger.debug(f"Logged wiki event: {event[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to log wiki event: {e}")
            return False

    def _extend_page(
        self,
        page: str,
        content: str,
        section: str | None = None,
    ) -> bool:
        """
        Extend a wiki page with campaign content.

        Creates an overlay file with extends: frontmatter.

        Args:
            page: Page name to extend
            content: Content to add
            section: Section to append to (optional)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        page_file = self.overlay_dir / f"{page}.md"

        try:
            if page_file.exists():
                # Append to existing overlay
                existing = page_file.read_text(encoding="utf-8")
                # Check if it already has frontmatter
                if existing.startswith("---"):
                    # Find end of frontmatter and append after
                    parts = existing.split("---", 2)
                    if len(parts) >= 3:
                        new_content = (
                            f"---{parts[1]}---\n\n"
                            f"{parts[2].strip()}\n\n{content}"
                        )
                    else:
                        new_content = existing.rstrip() + "\n\n" + content
                else:
                    new_content = existing.rstrip() + "\n\n" + content
            else:
                # Create new overlay with extends frontmatter
                frontmatter = f"---\nextends: {page}\n"
                if section:
                    frontmatter += f'append_to: "{section}"\n'
                frontmatter += "---\n\n"
                new_content = frontmatter + content

            page_file.write_text(new_content, encoding="utf-8")
            logger.debug(f"Extended wiki page: {page}")
            return True

        except Exception as e:
            logger.error(f"Failed to extend wiki page: {e}")
            return False

    # -------------------------------------------------------------------------
    # High-Level Event Methods (mirror MemvidAdapter interface)
    # -------------------------------------------------------------------------

    def save_hinge_moment(
        self,
        hinge: HingeMoment,
        session: int,
        immediate_effects: list[str] | None = None,
        dormant_threads_created: list[str] | None = None,
    ) -> bool:
        """
        Log a hinge moment to wiki.

        Creates timeline entry and optionally extends related pages.
        """
        if not self.enabled:
            return False

        # Log to timeline
        effects_text = ""
        if immediate_effects:
            effects_text = f" Effects: {', '.join(immediate_effects[:3])}"

        event = f"**HINGE:** {hinge.choice}{effects_text}"
        self._log_event(
            session=session,
            event=event,
            event_type="hinge",
            related_pages=None,  # Could extract from what_shifted
        )

        return True

    def save_faction_shift(
        self,
        faction: FactionName,
        from_standing: str,
        to_standing: str,
        cause: str,
        session: int,
    ) -> bool:
        """
        Log a faction standing change to wiki.

        Creates timeline entry and extends faction page.
        """
        if not self.enabled:
            return False

        faction_name = faction.value.replace("_", " ").title()

        # Log to timeline
        event = f"{faction_name}: {from_standing} → {to_standing}. {cause}"
        self._log_event(
            session=session,
            event=event,
            event_type="faction",
            related_pages=[faction_name],
        )

        # Extend faction page
        content = (
            f"### Session {session}\n\n"
            f"- Standing changed: {from_standing} → {to_standing}\n"
            f"- Cause: {cause}\n"
        )
        self._extend_page(
            page=faction_name,
            content=content,
            section="## Campaign History",
        )

        return True

    def save_npc_interaction(
        self,
        npc: NPC,
        player_action: str,
        npc_reaction: str,
        disposition_change: int = 0,
        session: int = 0,
        context: dict | None = None,
    ) -> bool:
        """
        Log a significant NPC interaction to wiki.

        Only logs interactions with disposition changes or high significance.
        """
        if not self.enabled:
            return False

        # Only log significant interactions (disposition changes)
        if disposition_change == 0:
            return True  # Silent success, not worth logging

        faction_name = npc.faction.value.replace("_", " ").title() if npc.faction else "Independent"
        direction = "improved" if disposition_change > 0 else "worsened"

        event = f"Interaction with {npc.name} ({faction_name}): relationship {direction}"
        self._log_event(
            session=session,
            event=event,
            event_type="npc",
            related_pages=[faction_name] if npc.faction else None,
        )

        return True

    def save_dormant_thread(
        self,
        thread: DormantThread,
    ) -> bool:
        """Log a new dormant thread to wiki timeline."""
        if not self.enabled:
            return False

        event = f"Thread queued: {thread.origin} (severity: {thread.severity.value})"
        self._log_event(
            session=thread.created_session,
            event=event,
            event_type="thread",
        )

        return True

    def save_thread_triggered(
        self,
        thread: DormantThread,
        session: int,
        outcome: str,
    ) -> bool:
        """Log when a dormant thread triggers."""
        if not self.enabled:
            return False

        event = f"Thread triggered: {thread.origin}. Outcome: {outcome}"
        self._log_event(
            session=session,
            event=event,
            event_type="thread",
        )

        return True

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        """Check if wiki logging is enabled."""
        return self.enabled


# -----------------------------------------------------------------------------
# Factory Function
# -----------------------------------------------------------------------------

def create_wiki_adapter(
    campaign_id: str,
    wiki_dir: str | Path = "wiki",
    enabled: bool = True,
) -> WikiAdapter:
    """
    Create a wiki adapter for a campaign.

    Args:
        campaign_id: Campaign ID for overlay directory
        wiki_dir: Path to wiki root directory
        enabled: Whether to enable wiki logging

    Returns:
        Configured WikiAdapter instance
    """
    return WikiAdapter(
        wiki_dir=wiki_dir,
        campaign_id=campaign_id,
        enabled=enabled,
    )
