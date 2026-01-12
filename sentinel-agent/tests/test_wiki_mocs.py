"""
Tests for WikiAdapter MOC generation and content separation.
"""

import os
from datetime import datetime
from pathlib import Path
import pytest

from src.state.wiki_adapter import WikiAdapter

# A dummy summary dict like the one passed from the game state
DUMMY_SUMMARY = {
    "session": 1,
    "campaign": "test_campaign",
    "text_summary": "This is the main summary of what happened.",
}

DUMMY_REFLECTIONS = {
    "text_summary": "I'm not sure if we made the right choice."
}

@pytest.fixture
def wiki_root(tmp_path: Path) -> Path:
    """Creates a temporary wiki root directory with canon subdir."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "canon").mkdir()
    return wiki_dir

@pytest.fixture
def adapter(wiki_root: Path) -> WikiAdapter:
    """Creates a WikiAdapter instance for testing."""
    return WikiAdapter(wiki_dir=wiki_root, campaign_id="test_campaign", enabled=True)

def test_content_separation(adapter: WikiAdapter, wiki_root: Path):
    """
    Verify that live updates go to _game_log.md and the main session
    note transcludes it.
    """
    # 1. Append some live game events
    adapter.append_to_session_note(session=1, content="First event happened.", event_type="test")
    adapter.append_to_session_note(session=1, content="Second event happened.", event_type="test")

    # 2. Save the final summary
    session_file = adapter.save_session_summary(DUMMY_SUMMARY, DUMMY_REFLECTIONS)

    # 3. Verify file structure and content
    date_str = datetime.now().strftime("%Y-%m-%d")
    session_dir = wiki_root / "campaigns" / "test_campaign" / "sessions" / date_str
    
    assert session_file is not None
    assert session_file.name == f"{date_str}.md"
    assert session_file.parent == session_dir

    # Check the game log file
    game_log_file = session_dir / "_game_log.md"
    assert game_log_file.exists()
    log_content = game_log_file.read_text()
    assert "First event happened." in log_content
    assert "Second event happened." in log_content
    assert "<!-- eid:" in log_content # Check for event ID

    # Check the main session note
    main_note_content = session_file.read_text()
    assert "This is the main summary of what happened." in main_note_content
    assert "I'm not sure if we made the right choice." in main_note_content
    assert "![[_game_log]]" in main_note_content
    assert "Session Debrief" in main_note_content

def test_moc_generation(adapter: WikiAdapter, wiki_root: Path):
    """
    Verify that _index.md files (MOCs) are created and updated correctly.
    """
    campaign_dir = wiki_root / "campaigns" / "test_campaign"
    
    # 1. Pre-populate the wiki with some NPCs and an old session
    # NPCs
    npc_dir = campaign_dir / "NPCs"
    npc_dir.mkdir(parents=True, exist_ok=True)
    (npc_dir / "Alice.md").write_text("""---
faction: Syndicate
---
# Alice""")
    (npc_dir / "Bob.md").write_text("""---
faction: Nexus
---
# Bob""")
    (npc_dir / "Charlie.md").write_text("""---
faction: Syndicate
---
# Charlie""")
    (npc_dir / "David (Deceased).md").write_text("""---
faction: Unknown
---
# David""")

    # Sessions (create one for "yesterday")
    # Note: This is a simplified representation. The test relies on save_session_summary
    # to create the correct structure for "today".
    sessions_dir = campaign_dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    (sessions_dir / "2026-01-11").mkdir()
    (sessions_dir / "2026-01-11" / "2026-01-11.md").write_text("# Yesterday")

    # 2. Trigger MOC generation by saving a session summary
    adapter.save_session_summary(DUMMY_SUMMARY)

    # 3. Verify MOC files exist
    campaign_moc = campaign_dir / "_index.md"
    sessions_moc = sessions_dir / "_index.md"
    npcs_moc = npc_dir / "_index.md"

    assert campaign_moc.exists()
    assert sessions_moc.exists()
    assert npcs_moc.exists()

    # 4. Verify Campaign MOC content
    campaign_content = campaign_moc.read_text()
    assert "[[sessions/_index|All Sessions]]" in campaign_content
    assert "[[NPCs/_index|All NPCs]]" in campaign_content
    assert "[[_events|Timeline of Events]]" in campaign_content

    # 5. Verify Sessions MOC content (sorted newest first)
    sessions_content = sessions_moc.read_text()
    today_str = datetime.now().strftime('%Y-%m-%d')
    assert f"[[{today_str}/{today_str}]]" in sessions_content
    assert "[[2026-01-11/2026-01-11]]" in sessions_content
    # Check order
    today_pos = sessions_content.find(today_str)
    yesterday_pos = sessions_content.find("2026-01-11")
    assert today_pos < yesterday_pos

    # 6. Verify NPCs MOC content (grouped by faction, sorted alphabetically)
    npcs_content = npcs_moc.read_text()
    
    # Check for faction headers
    assert "## Nexus" in npcs_content
    assert "## Syndicate" in npcs_content
    assert "## Unknown" in npcs_content

    # Check for NPC links under correct factions
    assert "## Nexus\n- [[NPCs/Bob.md|Bob]]" in npcs_content
    assert "## Syndicate\n- [[NPCs/Alice.md|Alice]]\n- [[NPCs/Charlie.md|Charlie]]" in npcs_content
    assert "## Unknown\n- [[NPCs/David (Deceased).md|David (Deceased)]]" in npcs_content

    # Check sorting order of factions and npcs within them
    nexus_pos = npcs_content.find("## Nexus")
    syndicate_pos = npcs_content.find("## Syndicate")
    unknown_pos = npcs_content.find("## Unknown")
    assert nexus_pos < syndicate_pos < unknown_pos

    alice_pos = npcs_content.find("Alice")
    charlie_pos = npcs_content.find("Charlie")
    assert alice_pos < charlie_pos
