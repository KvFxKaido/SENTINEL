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

import hashlib
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .templates import create_template_engine, TemplateEngine

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

        # Track last session for header insertion
        self._last_session: int | None = None

        # Lock for serializing write operations
        self._write_lock = threading.Lock()

        # Buffer for failed writes (retry on next operation)
        self._write_buffer: list[tuple[Path, str]] = []
        self._max_buffer_size = 50  # Prevent unbounded growth

        # Template engine for page generation
        self._templates: TemplateEngine | None = None

        if self.enabled:
            self._init_overlay_dir()
            self._templates = create_template_engine(self.wiki_dir)

    def _init_overlay_dir(self) -> None:
        """Create campaign overlay directory if needed."""
        self.overlay_dir = self.wiki_dir / "campaigns" / self.campaign_id
        try:
            self.overlay_dir.mkdir(parents=True, exist_ok=True)
            # Also create NPCs subdirectory
            (self.overlay_dir / "NPCs").mkdir(exist_ok=True)
            logger.debug(f"Wiki overlay directory: {self.overlay_dir}")
        except Exception as e:
            logger.error(f"Failed to create overlay directory: {e}")
            self.enabled = False

    def _do_atomic_write(self, filepath: Path, content: str) -> bool:
        """
        Perform atomic write without locking or buffering.

        Low-level helper used by _atomic_write and _retry_buffered_writes.

        Args:
            filepath: Target file path
            content: Content to write

        Returns:
            True if successful
        """
        try:
            # Create temp file in same directory (ensures same filesystem for rename)
            fd, temp_path = tempfile.mkstemp(
                dir=filepath.parent,
                prefix=f".{filepath.stem}_",
                suffix=".tmp",
            )
            try:
                # Write content to temp file
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                # Atomic rename (overwrites target on POSIX, may need replace on Windows)
                temp_file = Path(temp_path)
                temp_file.replace(filepath)
                return True
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"Atomic write failed for {filepath}: {e}")
            return False

    def _retry_buffered_writes(self) -> None:
        """
        Attempt to retry any buffered failed writes.

        Called at start of each write operation. Successfully retried
        writes are removed from buffer.
        """
        if not self._write_buffer:
            return

        # Try each buffered write
        still_failed = []
        for filepath, content in self._write_buffer:
            if self._do_atomic_write(filepath, content):
                logger.info(f"Retried buffered write succeeded: {filepath.name}")
            else:
                still_failed.append((filepath, content))

        self._write_buffer = still_failed

        if still_failed:
            logger.warning(f"{len(still_failed)} buffered writes still pending")

    def _buffer_failed_write(self, filepath: Path, content: str) -> None:
        """
        Add a failed write to the retry buffer.

        Args:
            filepath: Target file path
            content: Content that failed to write
        """
        # Check if already buffered (same file) - update content
        for i, (buf_path, _) in enumerate(self._write_buffer):
            if buf_path == filepath:
                self._write_buffer[i] = (filepath, content)
                logger.debug(f"Updated buffered write: {filepath.name}")
                return

        # Add new entry if under limit
        if len(self._write_buffer) < self._max_buffer_size:
            self._write_buffer.append((filepath, content))
            logger.warning(f"Buffered failed write for retry: {filepath.name}")
        else:
            logger.error(f"Write buffer full, dropping: {filepath.name}")

    def _atomic_write(self, filepath: Path, content: str) -> bool:
        """
        Write content to file atomically with serialization and error buffering.

        Uses write-to-temp-then-rename pattern to prevent corruption
        from interrupted writes. Lock ensures only one write at a time
        to prevent race conditions from rapid event firing. Failed writes
        are buffered for retry on subsequent operations.

        Args:
            filepath: Target file path
            content: Content to write

        Returns:
            True if successful (or buffered for retry)
        """
        with self._write_lock:
            # First, try to flush any buffered writes
            self._retry_buffered_writes()

            # Now attempt this write
            if self._do_atomic_write(filepath, content):
                return True

            # Failed - buffer for retry
            self._buffer_failed_write(filepath, content)
            return False

    def _generate_event_id(self, event_type: str, content: str, session: int) -> str:
        """
        Generate a unique event ID for idempotent appends.

        ID is based on content hash + session + type, so identical events
        in the same session produce the same ID (for deduplication).

        Args:
            event_type: Type of event (hinge, faction, npc, thread)
            content: Event content
            session: Session number

        Returns:
            Short hash string (12 chars)
        """
        # Combine identifying factors
        id_source = f"{event_type}:{session}:{content}"
        # Generate short hash
        return hashlib.sha256(id_source.encode()).hexdigest()[:12]

    def _has_event_id(self, filepath: Path, event_id: str) -> bool:
        """
        Check if an event ID already exists in a file.

        Args:
            filepath: File to check
            event_id: Event ID to look for

        Returns:
            True if event ID found (duplicate)
        """
        if not filepath.exists():
            return False
        try:
            content = filepath.read_text(encoding="utf-8")
            # Look for event ID marker
            return f"<!-- eid:{event_id} -->" in content
        except Exception:
            return False

    def _add_event_id(self, content: str, event_id: str) -> str:
        """
        Add event ID marker to content.

        Appends HTML comment that won't render but can be detected.

        Args:
            content: Original content
            event_id: Event ID to embed

        Returns:
            Content with event ID marker
        """
        # Add marker at end of content (before trailing newline if present)
        marker = f"<!-- eid:{event_id} -->"
        if content.endswith("\n"):
            return content.rstrip("\n") + f" {marker}\n"
        return f"{content} {marker}"

    def _get_last_session_from_file(self, events_file: Path) -> int | None:
        """Parse the events file to find the last session number."""
        if not events_file.exists():
            return None
        try:
            content = events_file.read_text(encoding="utf-8")
            # Look for ## Session N headers
            import re
            matches = re.findall(r"^## Session (\d+)", content, re.MULTILINE)
            if matches:
                return int(matches[-1])
            # Fall back to inline session references
            matches = re.findall(r"\*\*Session (\d+)\*\*", content)
            if matches:
                return int(matches[-1])
        except Exception:
            pass
        return None

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

        # Check if we need a session header
        if self._last_session is None:
            self._last_session = self._get_last_session_from_file(events_file)

        needs_session_header = (
            self._last_session is None or session > self._last_session
        )

        # Format entry
        type_badge = f"[{event_type.upper()}]" if event_type != "event" else ""
        entry = f"- ({timestamp}) {type_badge}: {event}"

        if related_pages:
            links = ", ".join(f"[[{p}]]" for p in related_pages)
            entry += f" — {links}"

        try:
            if events_file.exists():
                content = events_file.read_text(encoding="utf-8")
                if needs_session_header:
                    new_content = (
                        content.rstrip() + f"\n\n## Session {session}\n\n" + entry + "\n"
                    )
                else:
                    new_content = content.rstrip() + "\n" + entry + "\n"
            else:
                # New file - add header and first session
                new_content = (
                    "# Campaign Timeline\n\n"
                    "Significant events from this campaign.\n\n"
                    f"## Session {session}\n\n"
                    f"{entry}\n"
                )

            if not self._atomic_write(events_file, new_content):
                return False
            self._last_session = session
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

            if not self._atomic_write(page_file, new_content):
                return False
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
        Also appends to live session note.
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

        # Append to live session note using template
        if self._templates:
            callout = self._templates.render("callouts/hinge.md.j2", {
                "choice": hinge.choice,
                "situation": hinge.situation,
                "effects": immediate_effects[:3] if immediate_effects else None,
            })
        else:
            callout = f"> [!hinge] {hinge.choice}\n"
            if hinge.situation:
                callout += f"> **Situation:** {hinge.situation}\n"
            if immediate_effects:
                callout += f"> **Effects:** {', '.join(immediate_effects[:3])}\n"
        self.append_to_session_note(session, callout, section="Key Choices", event_type="hinge")

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

        Creates timeline entry, extends faction page, and appends to live session note.
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

        # Extend faction page using template
        if self._templates:
            content = self._templates.render("faction_extension.md.j2", {
                "session": session,
                "from_standing": from_standing,
                "to_standing": to_standing,
                "cause": cause,
            })
        else:
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

        # Append to live session note using template
        if self._templates:
            callout = self._templates.render("callouts/faction.md.j2", {
                "faction": faction_name,
                "from_standing": from_standing,
                "to_standing": to_standing,
                "cause": cause,
            })
        else:
            callout = f"> [!faction] [[{faction_name}]]: {from_standing} → {to_standing}\n"
            callout += f"> {cause}\n"
        self.append_to_session_note(session, callout, section="Faction Changes", event_type="faction")

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
        Log NPC interaction to wiki.

        Creates/updates NPC page and logs to timeline if disposition changed.
        """
        if not self.enabled:
            return False

        faction_name = npc.faction.value.replace("_", " ").title() if npc.faction else "Independent"

        # Always update NPC page with interaction history
        self._update_npc_page(
            npc=npc,
            faction_name=faction_name,
            player_action=player_action,
            npc_reaction=npc_reaction,
            disposition_change=disposition_change,
            session=session,
        )

        # Only log to timeline if disposition changed
        if disposition_change != 0:
            direction = "improved" if disposition_change > 0 else "worsened"
            event = f"Interaction with [[NPCs/{npc.name}|{npc.name}]] ({faction_name}): relationship {direction}"
            self._log_event(
                session=session,
                event=event,
                event_type="npc",
                related_pages=[faction_name] if npc.faction else None,
            )

        # Append to live session note
        npc_link = f"[[NPCs/{npc.name}|{npc.name}]]"
        faction_link = f"([[{faction_name}]])" if npc.faction else ""
        if disposition_change > 0:
            disp_text = f" *(+{disposition_change})*"
        elif disposition_change < 0:
            disp_text = f" *({disposition_change})*"
        else:
            disp_text = ""
        npc_line = f"- {npc_link} {faction_link}{disp_text}\n"
        self.append_to_session_note(session, npc_line, section="NPCs Encountered", event_type="npc")

        return True

    def _update_npc_page(
        self,
        npc: NPC,
        faction_name: str,
        player_action: str,
        npc_reaction: str,
        disposition_change: int,
        session: int,
    ) -> bool:
        """
        Create or update an NPC overlay page.

        Creates NPCs/{name}.md with interaction history.
        """
        if not self.enabled or not self._templates:
            return False

        # Sanitize name for filename
        safe_name = npc.name.replace("/", "-").replace("\\", "-")
        npc_file = self.overlay_dir / "NPCs" / f"{safe_name}.md"

        # Build disposition change text
        change_text = ""
        if disposition_change > 0:
            change_text = "*(disposition improved)*"
        elif disposition_change < 0:
            change_text = "*(disposition worsened)*"

        try:
            if npc_file.exists():
                # Append to existing page using entry template
                content = npc_file.read_text(encoding="utf-8")
                entry = self._templates.render("npc_entry.md.j2", {
                    "session": session,
                    "name": npc.name,
                    "player_action": player_action,
                    "npc_reaction": npc_reaction,
                    "disposition_change_text": change_text,
                })
                new_content = content.rstrip() + "\n" + entry

            else:
                # Create new NPC page
                disposition = getattr(npc, 'disposition', 'neutral')
                if hasattr(disposition, 'value'):
                    disposition = disposition.value

                # Check if canon NPC exists
                canon_npc_file = self.wiki_dir / "canon" / "NPCs" / f"{safe_name}.md"
                extends = f"NPCs/{safe_name}" if canon_npc_file.exists() else None

                new_content = self._templates.render("npc.md.j2", {
                    "name": npc.name,
                    "faction": faction_name,
                    "disposition": disposition,
                    "extends": extends,
                    "session": session,
                    "first_meeting": True,
                    "player_action": player_action,
                    "npc_reaction": npc_reaction,
                    "disposition_change_text": change_text,
                })

            if not self._atomic_write(npc_file, new_content):
                return False
            logger.debug(f"Updated NPC page: {npc.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update NPC page: {e}")
            return False

    def save_dormant_thread(
        self,
        thread: DormantThread,
    ) -> bool:
        """Log a new dormant thread to wiki timeline and live session note."""
        if not self.enabled:
            return False

        event = f"Thread queued: {thread.origin} (severity: {thread.severity.value})"
        self._log_event(
            session=thread.created_session,
            event=event,
            event_type="thread",
        )

        # Append to live session note using template
        if self._templates:
            callout = self._templates.render("callouts/thread.md.j2", {
                "origin": thread.origin,
                "severity": thread.severity.value,
                "trigger": thread.trigger,
            })
        else:
            severity = thread.severity.value.upper()
            callout = f"> [!thread] {thread.origin}\n"
            callout += f"> **Severity:** {severity}\n"
            if thread.trigger:
                callout += f"> **Trigger:** {thread.trigger}\n"
        self.append_to_session_note(
            thread.created_session, callout, section="Threads Queued", event_type="thread"
        )

        return True

    def save_thread_triggered(
        self,
        thread: DormantThread,
        session: int,
        outcome: str,
    ) -> bool:
        """Log when a dormant thread triggers and append to live session note."""
        if not self.enabled:
            return False

        event = f"Thread triggered: {thread.origin}. Outcome: {outcome}"
        self._log_event(
            session=session,
            event=event,
            event_type="thread",
        )

        # Append to live session note
        callout = f"> [!success] {thread.origin}\n"
        callout += f"> **Outcome:** {outcome}\n"
        callout += f"> *Dormant since session {thread.created_session}*\n"
        self.append_to_session_note(session, callout, section="Threads Resolved", event_type="thread")

        return True

    # -------------------------------------------------------------------------
    # Session Summary (Daily Notes)
    # -------------------------------------------------------------------------

    def save_session_summary(
        self,
        summary: dict,
        reflections: dict | None = None,
    ) -> Path | None:
        """
        Save session summary as a wiki daily note.

        Creates wiki/campaigns/{id}/sessions/YYYY-MM-DD.md with:
        - Frontmatter (session, date, campaign)
        - Callouts for hinges, faction changes, threads
        - Wikilinks for NPCs, factions

        Args:
            summary: Session summary dict from generate_session_summary()
            reflections: Optional player reflections dict

        Returns:
            Path to created file, or None if failed
        """
        if not self.enabled:
            return None

        # Create sessions directory
        sessions_dir = self.overlay_dir / "sessions"
        try:
            sessions_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create sessions directory: {e}")
            return None

        # Generate filename from current date
        date_str = datetime.now().strftime("%Y-%m-%d")
        session_num = summary.get("session", 0)
        campaign_name = summary.get("campaign", self.campaign_id)

        # Enrich faction changes with wikilinks
        faction_changes = summary.get("faction_changes", [])
        for change in faction_changes:
            change["faction_link"] = self._extract_faction_link(change.get("summary", ""))

        # Build session content using template
        if self._templates:
            content = self._templates.render("session.md.j2", {
                "session": session_num,
                "date": date_str,
                "campaign": self.campaign_id,
                "date_display": datetime.now().strftime('%B %d, %Y'),
                "hinges": summary.get("hinges", []),
                "faction_changes": faction_changes,
                "threads_created": summary.get("threads_created", []),
                "threads_resolved": summary.get("threads_resolved", []),
                "npcs_encountered": summary.get("npcs_encountered", []),
                "reflections": reflections,
            })
        else:
            # Fallback to inline generation
            lines = [
                "---",
                f"session: {session_num}",
                f"date: {date_str}",
                f"campaign: {self.campaign_id}",
                "type: session",
                "---",
                "",
                f"# Session {session_num} — {datetime.now().strftime('%B %d, %Y')}",
                "",
            ]

            if summary.get("hinges"):
                lines.append("## Key Choices")
                lines.append("")
                for hinge in summary["hinges"]:
                    lines.append(f"> [!hinge] {hinge['choice']}")
                    if hinge.get("situation"):
                        lines.append(f"> **Situation:** {hinge['situation']}")
                    if hinge.get("what_shifted"):
                        lines.append(f"> **Shifted:** {hinge['what_shifted']}")
                    lines.append("")

            if faction_changes:
                lines.append("## Faction Changes")
                lines.append("")
                for change in faction_changes:
                    callout_type = "danger" if change.get("is_permanent") else "faction"
                    lines.append(f"> [!{callout_type}] {change['summary']}")
                    if change.get("faction_link"):
                        lines.append(f"> Related: {change['faction_link']}")
                    lines.append("")

            if summary.get("threads_created"):
                lines.append("## Threads Queued")
                lines.append("")
                for thread in summary["threads_created"]:
                    severity = thread.get("severity", "minor").upper()
                    lines.append(f"> [!thread] {thread['origin']}")
                    lines.append(f"> **Severity:** {severity}")
                    lines.append(f"> **Trigger:** {thread['trigger']}")
                    lines.append("")

            if summary.get("threads_resolved"):
                lines.append("## Threads Resolved")
                lines.append("")
                for thread in summary["threads_resolved"]:
                    lines.append(f"- {thread['summary']}")
                lines.append("")

            if summary.get("npcs_encountered"):
                lines.append("## NPCs Encountered")
                lines.append("")
                for npc in summary["npcs_encountered"]:
                    name = npc.get("name", "Unknown")
                    faction = npc.get("faction", "")
                    disp_change = npc.get("disposition_change", 0)
                    npc_link = f"[[NPCs/{name}|{name}]]"
                    faction_link = f"([[{faction.replace('_', ' ').title()}]])" if faction else ""
                    if disp_change > 0:
                        disposition = f"*(+{disp_change} disposition)*"
                    elif disp_change < 0:
                        disposition = f"*({disp_change} disposition)*"
                    else:
                        disposition = ""
                    lines.append(f"- {npc_link} {faction_link} {disposition}".strip())
                lines.append("")

            if reflections:
                lines.append("## Player Reflections")
                lines.append("")
                if reflections.get("cost"):
                    lines.append(f"- **What it cost:** {reflections['cost']}")
                if reflections.get("learned"):
                    lines.append(f"- **What I learned:** {reflections['learned']}")
                if reflections.get("would_refuse"):
                    lines.append(f"- **What I'd refuse:** {reflections['would_refuse']}")
                lines.append("")

            content = "\n".join(lines)

        # Write file atomically
        filename = f"{date_str}.md"
        filepath = sessions_dir / filename

        if not self._atomic_write(filepath, content):
            return None
        logger.info(f"Saved session summary to wiki: {filepath}")
        return filepath

    def _extract_faction_link(self, summary_text: str) -> str | None:
        """Extract faction wikilink from summary text if possible."""
        factions = [
            "Nexus", "Ember Colonies", "Lattice", "Convergence", "Covenant",
            "Wanderers", "Cultivators", "Steel Syndicate", "Witnesses",
            "Architects", "Ghost Networks",
        ]
        for faction in factions:
            if faction.lower() in summary_text.lower():
                return f"[[{faction}]]"
        return None

    def append_to_session_note(
        self,
        session: int,
        content: str,
        section: str | None = None,
        event_type: str = "update",
    ) -> bool:
        """
        Append content to today's session note during active play.

        Creates the session note if it doesn't exist. Appends to the
        specified section or creates a new "## Live Updates" section.
        Uses event IDs for idempotent appends (skips duplicates).

        Args:
            session: Session number
            content: Content to append (markdown)
            section: Optional section header to append under
            event_type: Event type for ID generation (hinge, faction, npc, thread)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        sessions_dir = self.overlay_dir / "sessions"
        try:
            sessions_dir.mkdir(exist_ok=True)
        except Exception:
            return False

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = sessions_dir / f"{date_str}.md"

        # Generate event ID and check for duplicates
        event_id = self._generate_event_id(event_type, content, session)
        if self._has_event_id(filepath, event_id):
            logger.debug(f"Skipping duplicate event: {event_id}")
            return True  # Already exists, consider it success

        # Add event ID marker to content
        content_with_id = self._add_event_id(content, event_id)

        try:
            if filepath.exists():
                existing = filepath.read_text(encoding="utf-8")

                # Find or create the target section
                if section:
                    section_header = f"## {section}"
                    if section_header in existing:
                        # Append under existing section
                        parts = existing.split(section_header, 1)
                        if len(parts) == 2:
                            # Find next section or end of file
                            rest = parts[1]
                            next_section = rest.find("\n## ")
                            if next_section != -1:
                                insert_point = next_section
                                new_content = (
                                    parts[0] + section_header +
                                    rest[:insert_point].rstrip() + "\n" + content_with_id + "\n" +
                                    rest[insert_point:]
                                )
                            else:
                                new_content = existing.rstrip() + "\n" + content_with_id + "\n"
                        else:
                            new_content = existing.rstrip() + f"\n\n{section_header}\n\n{content_with_id}\n"
                    else:
                        # Create new section
                        new_content = existing.rstrip() + f"\n\n{section_header}\n\n{content_with_id}\n"
                else:
                    # Append to "Live Updates" section
                    live_header = "## Live Updates"
                    if live_header in existing:
                        new_content = existing.rstrip() + "\n" + content_with_id + "\n"
                    else:
                        new_content = existing.rstrip() + f"\n\n{live_header}\n\n{content_with_id}\n"
            else:
                # Create new file with minimal structure using template
                if self._templates:
                    new_content = self._templates.render("session_live.md.j2", {
                        "session": session,
                        "date": date_str,
                        "campaign": self.campaign_id,
                        "date_display": datetime.now().strftime('%B %d, %Y'),
                        "content": content_with_id,
                    })
                else:
                    new_content = (
                        "---\n"
                        f"session: {session}\n"
                        f"date: {date_str}\n"
                        f"campaign: {self.campaign_id}\n"
                        "type: session\n"
                        "---\n\n"
                        f"# Session {session} — {datetime.now().strftime('%B %d, %Y')}\n\n"
                        "## Live Updates\n\n"
                        f"{content_with_id}\n"
                    )

            if not self._atomic_write(filepath, new_content):
                return False
            logger.debug(f"Appended to session note: {filepath.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to session note: {e}")
            return False

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        """Check if wiki logging is enabled."""
        return self.enabled

    @property
    def pending_writes(self) -> int:
        """Return number of buffered writes pending retry."""
        return len(self._write_buffer)

    def flush_buffer(self) -> int:
        """
        Force retry of all buffered writes.

        Useful to call at session end (/debrief) to ensure all
        writes are attempted before closing.

        Returns:
            Number of writes that still failed after retry
        """
        with self._write_lock:
            self._retry_buffered_writes()
            return len(self._write_buffer)


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
