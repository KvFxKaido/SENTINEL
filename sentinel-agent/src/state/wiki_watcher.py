"""
Watch wiki files for frontmatter changes and sync into campaign state.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .schema import Disposition, FactionName, Standing

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    FileSystemEventHandler = object
    Observer = None
    WATCHDOG_AVAILABLE = False

if TYPE_CHECKING:
    from .manager import CampaignManager
    from .schema import Campaign, NPC

logger = logging.getLogger(__name__)


class _WikiEventHandler(FileSystemEventHandler):
    """Forward file events to the watcher handler."""

    def __init__(self, watcher: "WikiWatcher") -> None:
        self._watcher = watcher

    def on_modified(self, event) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._watcher.handle_path(Path(event.src_path))

    def on_created(self, event) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._watcher.handle_path(Path(event.src_path))


class WikiWatcher:
    """
    Monitor wiki markdown files and sync frontmatter changes into campaign state.
    """

    def __init__(
        self,
        manager: "CampaignManager",
        wiki_dir: str | Path,
        campaign_id: str,
    ) -> None:
        self._manager = manager
        self.wiki_dir = Path(wiki_dir)
        self.campaign_id = campaign_id

        self._observer = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def campaign_dir(self) -> Path:
        return self.wiki_dir / "campaigns" / self.campaign_id

    def start_watching(self) -> bool:
        """Start the wiki watcher in a background thread."""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog not installed; wiki watcher disabled")
            return False

        if self._thread and self._thread.is_alive():
            return True

        if not self.campaign_dir.exists():
            logger.warning(f"Wiki campaign directory not found: {self.campaign_dir}")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"WikiWatcher-{self.campaign_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"Started wiki watcher for campaign: {self.campaign_id}")
        return True

    def stop_watching(self) -> None:
        """Stop the wiki watcher and wait for shutdown."""
        if not self._thread:
            return

        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None
        logger.info(f"Stopped wiki watcher for campaign: {self.campaign_id}")

    def handle_path(self, path: Path) -> None:
        """Process a changed markdown file."""
        if path.suffix.lower() != ".md":
            return
        if path.name.startswith("."):
            return

        try:
            path.relative_to(self.campaign_dir)
        except ValueError:
            return

        if "sessions" in path.parts:
            return

        campaign = self._manager.current
        if not campaign or campaign.meta.id != self.campaign_id:
            return

        if not path.exists():
            return

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed reading wiki file {path}: {exc}")
            return

        frontmatter = self._parse_frontmatter(content)
        if not frontmatter:
            return

        file_mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if not self._is_wiki_newer(campaign, file_mtime):
            logger.warning(
                f"Wiki change ignored (state newer): {path.name}"
            )
            return

        with self._lock:
            if "NPCs" in path.parts:
                self._apply_npc_updates(campaign, path, frontmatter)
            else:
                self._apply_faction_updates(campaign, path, frontmatter)

    def _run(self) -> None:
        """Observer loop running in a background thread."""
        if not WATCHDOG_AVAILABLE:
            return

        observer = Observer()
        self._observer = observer
        handler = _WikiEventHandler(self)

        try:
            observer.schedule(handler, str(self.campaign_dir), recursive=True)
            observer.start()
            while not self._stop_event.is_set():
                time.sleep(0.2)
        except Exception as exc:
            logger.error(f"Wiki watcher failed: {exc}")
        finally:
            try:
                observer.stop()
                observer.join(timeout=2)
            except Exception:
                pass
            self._observer = None

    def _parse_frontmatter(self, content: str) -> dict[str, str]:
        """Parse simple YAML frontmatter (key: value)."""
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}

        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx is None:
            return {}

        frontmatter: dict[str, str] = {}
        for line in lines[1:end_idx]:
            if not line.strip() or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            frontmatter[key] = value

        return frontmatter

    def _is_wiki_newer(self, campaign: "Campaign", file_mtime: datetime) -> bool:
        """Return True if wiki file is newer than last saved state."""
        if not campaign.saved_at:
            return True
        return file_mtime > campaign.saved_at

    def _apply_npc_updates(
        self,
        campaign: "Campaign",
        path: Path,
        frontmatter: dict[str, str],
    ) -> None:
        npc = self._find_npc(campaign, path, frontmatter.get("name"))
        if not npc:
            logger.warning(f"No NPC match for wiki file: {path.name}")
            return

        changed = False
        if "disposition" in frontmatter:
            disposition = self._parse_disposition(frontmatter["disposition"])
            if disposition and npc.disposition != disposition:
                npc.disposition = disposition
                changed = True
                logger.info(
                    f"Synced NPC disposition from wiki: {npc.name} -> {disposition.value}"
                )

        if "faction" in frontmatter:
            raw_faction = frontmatter["faction"]
            faction = self._parse_faction(raw_faction)
            if faction is None and raw_faction.strip().lower() not in ("", "none"):
                logger.warning(
                    f"Invalid NPC faction in wiki file: {path.name}"
                )
            elif faction != npc.faction:
                npc.faction = faction
                changed = True
                faction_name = faction.value if faction else "None"
                logger.info(
                    f"Synced NPC faction from wiki: {npc.name} -> {faction_name}"
                )

        if changed:
            self._manager.save_campaign()

    def _apply_faction_updates(
        self,
        campaign: "Campaign",
        path: Path,
        frontmatter: dict[str, str],
    ) -> None:
        if "standing" not in frontmatter:
            return

        faction = self._resolve_faction(frontmatter, path)
        if not faction:
            logger.warning(f"No faction match for wiki file: {path.name}")
            return

        standing = self._parse_standing(frontmatter["standing"])
        if not standing:
            logger.warning(
                f"Invalid faction standing in wiki file: {path.name}"
            )
            return

        faction_entry = campaign.factions.get(faction)
        if faction_entry.standing != standing:
            faction_entry.standing = standing
            self._manager.save_campaign()
            logger.info(
                f"Synced faction standing from wiki: {faction.value} -> {standing.value}"
            )

    def _find_npc(
        self,
        campaign: "Campaign",
        path: Path,
        name_hint: str | None,
    ) -> "NPC | None":
        stem = path.stem.lower()
        name_hint = (name_hint or "").strip().lower()

        for npc in campaign.npcs.active + campaign.npcs.dormant:
            candidate = self._sanitize_name(npc.name).lower()
            if candidate == stem or (name_hint and npc.name.lower() == name_hint):
                return npc
        return None

    def _resolve_faction(
        self,
        frontmatter: dict[str, str],
        path: Path,
    ) -> FactionName | None:
        if "faction" in frontmatter:
            return self._parse_faction(frontmatter["faction"])
        return self._parse_faction(path.stem)

    def _parse_faction(self, raw_value: str) -> FactionName | None:
        value = raw_value.replace("_", " ").strip().lower()
        for faction in FactionName:
            if faction.value.lower() == value:
                return faction
        if value == "" or value == "none":
            return None
        return None

    def _parse_disposition(self, raw_value: str) -> Disposition | None:
        value = raw_value.strip().lower()
        try:
            return Disposition(value)
        except ValueError:
            return None

    def _parse_standing(self, raw_value: str) -> Standing | None:
        value = raw_value.strip().title()
        try:
            return Standing(value)
        except ValueError:
            return None

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return name.replace("/", "-").replace("\\", "-")
