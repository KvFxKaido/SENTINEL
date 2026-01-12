"""
Tests for WikiWatcher syncing wiki frontmatter into campaign state.
"""

from datetime import datetime
from pathlib import Path

from src.state.manager import CampaignManager
from src.state.schema import Disposition, FactionName, Standing, NPCAgenda, NPC
from src.state.store import MemoryCampaignStore
from src.state.wiki_watcher import WikiWatcher


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
