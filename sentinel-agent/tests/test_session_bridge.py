
import pytest
from datetime import datetime
from src.state.manager import CampaignManager, Campaign
from src.state.schema import FactionName, Standing, Disposition, ThreadSeverity

@pytest.fixture
def manager(tmp_path):
    return CampaignManager(store=tmp_path)

def test_migration_creates_snapshot(manager):
    """Test that migrating from old versions creates an initial snapshot and reaches current version."""
    # Create a campaign manually with old version
    campaign = manager.create_campaign("Test Campaign")
    campaign.schema_version = "1.5.0"
    campaign.last_session_snapshot = None
    # Use persist_campaign() to actually save to disk (save_campaign is no-op for ephemeral)
    manager.persist_campaign()

    # Clear cache to force reload from disk
    del manager._cache[campaign.meta.id]

    # Reload to trigger migration
    loaded = manager.load_campaign(campaign.meta.id)

    # Should migrate to current version (1.7.0)
    assert loaded.schema_version == "1.7.0"
    assert loaded.last_session_snapshot is not None
    assert loaded.last_session_snapshot.session == 0
    assert len(loaded.last_session_snapshot.factions) == len(FactionName)

def test_get_session_changes_no_change(manager):
    """Test that no changes are reported if state hasn't changed."""
    campaign = manager.create_campaign("Test Campaign")
    # Snapshot is created on migration/creation
    assert campaign.last_session_snapshot is not None
    
    changes = manager.get_session_changes()
    assert len(changes) == 0

def test_get_session_changes_faction(manager):
    """Test detection of faction standing changes."""
    campaign = manager.create_campaign("Test Campaign")
    
    # Modify faction standing directly to simulate offline change
    campaign.factions.nexus.standing = Standing.FRIENDLY
    
    changes = manager.get_session_changes()
    assert len(changes) == 1
    assert changes[0]["type"] == "faction"
    assert changes[0]["id"] == "Nexus"
    assert changes[0]["old"] == "Neutral"
    assert changes[0]["new"] == "Friendly"

def test_get_session_changes_npc(manager):
    """Test detection of NPC changes."""
    campaign = manager.create_campaign("Test Campaign")
    
    # Add an NPC
    from src.state.schema import NPC, NPCAgenda
    npc = NPC(
        name="Test NPC", 
        agenda=NPCAgenda(wants="A", fears="B"),
        disposition=Disposition.NEUTRAL
    )
    manager.add_npc(npc)
    
    # Snapshot doesn't have this NPC yet (unless we recreate it)
    # Wait, create_campaign -> initializes snapshot? 
    # Current implementation of create_campaign calls save_campaign but doesn't explicitly call _create_snapshot 
    # EXCEPT: load_campaign calls _migrate_campaign which creates snapshot if missing.
    # But create_campaign creates a fresh campaign with 1.6.0 version (default in schema class definition is 1.6.0 now).
    # If the schema definition has 1.6.0, then _migrate_campaign won't run.
    # So `last_session_snapshot` might be None for a brand new campaign created with 1.6.0 schema?
    # Let's check schema.py default.
    
    # If I updated schema.py:
    # class Campaign(BaseModel):
    #     schema_version: str = "1.6.0"
    #     last_session_snapshot: CampaignSnapshot | None = None
    
    # So a new campaign has None.
    # When is the snapshot created for a NEW campaign?
    # Ideally, at the end of session 0 (creation)?
    # Or maybe we should initialize it in create_campaign?
    
    # If last_session_snapshot is None, get_session_changes returns [].
    # So we need to establish a baseline.
    
    campaign.last_session_snapshot = manager._create_snapshot(campaign)

    # Now modify NPC
    npc.disposition = Disposition.WARM

    changes = manager.get_session_changes()
    assert len(changes) == 1
    assert changes[0]["type"] == "npc_disposition"
    assert changes[0]["old"] == "neutral"
    assert changes[0]["new"] == "warm"

def test_end_session_updates_snapshot(manager):
    """Test that end_session updates the snapshot."""
    campaign = manager.create_campaign("Test Campaign")
    
    # Make a change
    campaign.factions.nexus.standing = Standing.HOSTILE
    
    # End session
    manager.end_session("Summary")
    
    # Now snapshot should reflect the change
    snap = campaign.last_session_snapshot
    assert snap.factions[FactionName.NEXUS] == Standing.HOSTILE
    
    # And diff should be empty (since snapshot == current)
    changes = manager.get_session_changes()
    assert len(changes) == 0
