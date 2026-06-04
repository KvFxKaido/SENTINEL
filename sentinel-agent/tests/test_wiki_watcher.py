"""
Tests for WikiWatcher syncing wiki frontmatter into campaign state.
"""

import time
from datetime import datetime
from pathlib import Path

import pytest

from src.state.manager import CampaignManager
from src.state.schema import Disposition, FactionName, Standing, NPCAgenda, NPC
from src.state.store import MemoryCampaignStore
from src.state.wiki_watcher import WATCHDOG_AVAILABLE, WikiWatcher


def _write_frontmatter(path: Path, lines: list[str]) -> None:
    content = ["---", *lines, "---", "", "# Placeholder"]
    path.write_text("\n".join(content), encoding="utf-8")


def _make_manager() -> CampaignManager:
    return CampaignManager(
        store=MemoryCampaignStore(),
        enable_memvid=False,
        enable_wiki=False,
    )


def _add_npc(manager: CampaignManager, name: str) -> NPC:
    npc = NPC(
        name=name,
        agenda=NPCAgenda(wants="test", fears="test"),
        disposition=Disposition.NEUTRAL,
    )
    manager.add_npc(npc, active=True)
    return npc


def test_npc_frontmatter_sync_updates_state(tmp_path: Path) -> None:
    manager = _make_manager()
    campaign = manager.create_campaign("Test Campaign")
    npc = _add_npc(manager, "Cipher")

    wiki_dir = tmp_path / "wiki"
    npc_dir = wiki_dir / "campaigns" / campaign.meta.id / "NPCs"
    npc_dir.mkdir(parents=True)

    npc_file = npc_dir / "Cipher.md"
    _write_frontmatter(npc_file, [
        "type: npc",
        "faction: Nexus",
        "disposition: warm",
    ])
    file_mtime = npc_file.stat().st_mtime
    campaign.saved_at = datetime.fromtimestamp(file_mtime - 10)

    watcher = WikiWatcher(manager, wiki_dir=wiki_dir, campaign_id=campaign.meta.id)
    watcher.handle_path(npc_file)

    assert npc.faction == FactionName.NEXUS
    assert npc.disposition == Disposition.WARM


def test_faction_frontmatter_sync_updates_state(tmp_path: Path) -> None:
    manager = _make_manager()
    campaign = manager.create_campaign("Test Campaign")

    wiki_dir = tmp_path / "wiki"
    campaign_dir = wiki_dir / "campaigns" / campaign.meta.id
    campaign_dir.mkdir(parents=True)

    faction_file = campaign_dir / "Nexus.md"
    _write_frontmatter(faction_file, [
        "standing: Friendly",
    ])
    file_mtime = faction_file.stat().st_mtime
    campaign.saved_at = datetime.fromtimestamp(file_mtime - 10)

    watcher = WikiWatcher(manager, wiki_dir=wiki_dir, campaign_id=campaign.meta.id)
    watcher.handle_path(faction_file)

    assert campaign.factions.get(FactionName.NEXUS).standing == Standing.FRIENDLY


def test_sync_skips_when_state_newer(tmp_path: Path) -> None:
    manager = _make_manager()
    campaign = manager.create_campaign("Test Campaign")
    npc = _add_npc(manager, "Cipher")

    wiki_dir = tmp_path / "wiki"
    npc_dir = wiki_dir / "campaigns" / campaign.meta.id / "NPCs"
    npc_dir.mkdir(parents=True)

    npc_file = npc_dir / "Cipher.md"
    _write_frontmatter(npc_file, [
        "disposition: warm",
    ])
    file_mtime = npc_file.stat().st_mtime
    campaign.saved_at = datetime.fromtimestamp(file_mtime + 10)

    watcher = WikiWatcher(manager, wiki_dir=wiki_dir, campaign_id=campaign.meta.id)
    watcher.handle_path(npc_file)

    assert npc.disposition == Disposition.NEUTRAL


def _wait_for(predicate, timeout: float = 5.0, interval: float = 0.05) -> bool:
    """Poll ``predicate`` until it is truthy or ``timeout`` elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_observer_thread_syncs_filesystem_change(tmp_path: Path) -> None:
    """End-to-end: the real watchdog Observer picks up a write and syncs state.

    Unlike the other tests, this drives the actual background thread
    (start_watching -> _run -> Observer.schedule/start), so a watchdog
    version bump that breaks the Observer API surfaces here rather than
    silently disabling the wiki watcher at runtime.
    """
    manager = _make_manager()
    campaign = manager.create_campaign("Test Campaign")
    npc = _add_npc(manager, "Cipher")
    # State predates any wiki edit, so filesystem changes are accepted as newer.
    campaign.saved_at = datetime.fromtimestamp(0)

    wiki_dir = tmp_path / "wiki"
    npc_dir = wiki_dir / "campaigns" / campaign.meta.id / "NPCs"
    npc_dir.mkdir(parents=True)

    watcher = WikiWatcher(manager, wiki_dir=wiki_dir, campaign_id=campaign.meta.id)
    assert watcher.start_watching() is True
    try:
        # Give the observer thread a moment to arm its filesystem watch;
        # writes that land before the watch is established are missed.
        time.sleep(0.5)
        npc_file = npc_dir / "Cipher.md"
        _write_frontmatter(npc_file, [
            "type: npc",
            "disposition: warm",
        ])
        synced = _wait_for(lambda: npc.disposition == Disposition.WARM)
    finally:
        watcher.stop_watching()

    assert synced, "watcher did not sync disposition from a filesystem event"
    assert npc.disposition == Disposition.WARM
