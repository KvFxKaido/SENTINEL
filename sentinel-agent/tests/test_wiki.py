"""
Tests for WikiAdapter hardening features.

Tests atomic writes, write serialization, event IDs, and error buffering.
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.state.wiki_adapter import WikiAdapter, create_wiki_adapter


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def wiki_dir(tmp_path):
    """Create a temporary wiki directory structure."""
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    return tmp_path


@pytest.fixture
def wiki_adapter(wiki_dir):
    """Create a WikiAdapter instance for testing."""
    return WikiAdapter(
        wiki_dir=wiki_dir,
        campaign_id="test_campaign",
        enabled=True,
    )


# -----------------------------------------------------------------------------
# Atomic Writes
# -----------------------------------------------------------------------------


class TestAtomicWrites:
    """Tests for atomic write functionality."""

    def test_atomic_write_creates_file(self, wiki_adapter):
        """Atomic write should create target file."""
        test_file = wiki_adapter.overlay_dir / "test.md"
        content = "Test content"

        result = wiki_adapter._atomic_write(test_file, content)

        assert result is True
        assert test_file.exists()
        assert test_file.read_text() == content

    def test_atomic_write_overwrites_existing(self, wiki_adapter):
        """Atomic write should overwrite existing file."""
        test_file = wiki_adapter.overlay_dir / "test.md"
        test_file.write_text("Old content")

        result = wiki_adapter._atomic_write(test_file, "New content")

        assert result is True
        assert test_file.read_text() == "New content"

    def test_atomic_write_no_partial_writes(self, wiki_adapter):
        """Atomic write should not leave partial content on failure."""
        test_file = wiki_adapter.overlay_dir / "test.md"
        original_content = "Original content"
        test_file.write_text(original_content)

        # Simulate failure during rename by mocking Path.replace
        with patch.object(Path, 'replace', side_effect=OSError("Simulated failure")):
            result = wiki_adapter._do_atomic_write(test_file, "New content")

        assert result is False
        # Original content should be preserved
        assert test_file.read_text() == original_content

    def test_atomic_write_cleans_up_temp_file(self, wiki_adapter):
        """Atomic write should clean up temp file on failure."""
        test_file = wiki_adapter.overlay_dir / "test.md"

        # Count temp files before
        temp_files_before = list(wiki_adapter.overlay_dir.glob(".*_*.tmp"))

        with patch.object(Path, 'replace', side_effect=OSError("Simulated failure")):
            wiki_adapter._do_atomic_write(test_file, "Content")

        # Count temp files after
        temp_files_after = list(wiki_adapter.overlay_dir.glob(".*_*.tmp"))

        assert len(temp_files_after) == len(temp_files_before)


# -----------------------------------------------------------------------------
# Write Serialization
# -----------------------------------------------------------------------------


class TestWriteSerialization:
    """Tests for write serialization via threading lock."""

    def test_adapter_has_write_lock(self, wiki_adapter):
        """WikiAdapter should have a threading lock."""
        assert hasattr(wiki_adapter, '_write_lock')
        assert isinstance(wiki_adapter._write_lock, type(threading.Lock()))

    def test_concurrent_writes_are_serialized(self, wiki_adapter):
        """Concurrent writes should not interleave."""
        test_file = wiki_adapter.overlay_dir / "concurrent.md"
        results = []
        write_order = []

        def write_content(content, delay=0):
            if delay:
                time.sleep(delay)
            write_order.append(f"start_{content}")
            result = wiki_adapter._atomic_write(test_file, content)
            write_order.append(f"end_{content}")
            results.append(result)

        # Start two threads that try to write concurrently
        t1 = threading.Thread(target=write_content, args=("Thread1",))
        t2 = threading.Thread(target=write_content, args=("Thread2", 0.01))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both writes should succeed
        assert all(results)

        # Writes should be serialized (no interleaving)
        # Either start_1, end_1, start_2, end_2 or start_2, end_2, start_1, end_1
        assert (
            (write_order.index("end_Thread1") < write_order.index("start_Thread2")) or
            (write_order.index("end_Thread2") < write_order.index("start_Thread1"))
        )


# -----------------------------------------------------------------------------
# Event IDs
# -----------------------------------------------------------------------------


class TestEventIds:
    """Tests for event ID generation and deduplication."""

    def test_generate_event_id_deterministic(self, wiki_adapter):
        """Same input should produce same event ID."""
        id1 = wiki_adapter._generate_event_id("hinge", "Test content", 1)
        id2 = wiki_adapter._generate_event_id("hinge", "Test content", 1)

        assert id1 == id2

    def test_generate_event_id_varies_by_content(self, wiki_adapter):
        """Different content should produce different event IDs."""
        id1 = wiki_adapter._generate_event_id("hinge", "Content A", 1)
        id2 = wiki_adapter._generate_event_id("hinge", "Content B", 1)

        assert id1 != id2

    def test_generate_event_id_varies_by_session(self, wiki_adapter):
        """Different sessions should produce different event IDs."""
        id1 = wiki_adapter._generate_event_id("hinge", "Content", 1)
        id2 = wiki_adapter._generate_event_id("hinge", "Content", 2)

        assert id1 != id2

    def test_generate_event_id_varies_by_type(self, wiki_adapter):
        """Different event types should produce different event IDs."""
        id1 = wiki_adapter._generate_event_id("hinge", "Content", 1)
        id2 = wiki_adapter._generate_event_id("faction", "Content", 1)

        assert id1 != id2

    def test_generate_event_id_length(self, wiki_adapter):
        """Event ID should be 12 characters."""
        event_id = wiki_adapter._generate_event_id("hinge", "Content", 1)

        assert len(event_id) == 12

    def test_has_event_id_finds_existing(self, wiki_adapter):
        """Should find event ID in file content."""
        test_file = wiki_adapter.overlay_dir / "test.md"
        test_file.write_text("Some content <!-- eid:abc123def456 --> more content")

        assert wiki_adapter._has_event_id(test_file, "abc123def456") is True

    def test_has_event_id_missing(self, wiki_adapter):
        """Should not find non-existent event ID."""
        test_file = wiki_adapter.overlay_dir / "test.md"
        test_file.write_text("Some content without event ID")

        assert wiki_adapter._has_event_id(test_file, "abc123def456") is False

    def test_has_event_id_nonexistent_file(self, wiki_adapter):
        """Should return False for non-existent file."""
        test_file = wiki_adapter.overlay_dir / "nonexistent.md"

        assert wiki_adapter._has_event_id(test_file, "abc123def456") is False

    def test_add_event_id_to_content(self, wiki_adapter):
        """Should add event ID marker to content."""
        content = "Test content\n"
        event_id = "abc123def456"

        result = wiki_adapter._add_event_id(content, event_id)

        assert "<!-- eid:abc123def456 -->" in result
        assert "Test content" in result

    def test_append_skips_duplicate(self, wiki_adapter):
        """Append should skip if event ID already exists."""
        # First append
        result1 = wiki_adapter.append_to_session_note(
            session=1,
            content="> [!hinge] Test choice\n",
            section="Key Choices",
            event_type="hinge",
        )

        # Read file to verify first append (now in sessions/{date}/_game_log.md)
        sessions_dir = wiki_adapter.overlay_dir / "sessions"
        game_logs = list(sessions_dir.glob("*/_game_log.md"))
        assert len(game_logs) == 1
        content_after_first = game_logs[0].read_text()

        # Second append with same content (should be skipped)
        result2 = wiki_adapter.append_to_session_note(
            session=1,
            content="> [!hinge] Test choice\n",
            section="Key Choices",
            event_type="hinge",
        )

        content_after_second = game_logs[0].read_text()

        assert result1 is True
        assert result2 is True  # Returns True even when skipped
        # Content should not be duplicated
        assert content_after_first == content_after_second


# -----------------------------------------------------------------------------
# Error Buffering
# -----------------------------------------------------------------------------


class TestErrorBuffering:
    """Tests for error buffering and retry functionality."""

    def test_adapter_has_write_buffer(self, wiki_adapter):
        """WikiAdapter should have a write buffer."""
        assert hasattr(wiki_adapter, '_write_buffer')
        assert isinstance(wiki_adapter._write_buffer, list)
        assert len(wiki_adapter._write_buffer) == 0

    def test_pending_writes_property(self, wiki_adapter):
        """pending_writes should return buffer size."""
        assert wiki_adapter.pending_writes == 0

        # Manually add to buffer for testing
        wiki_adapter._write_buffer.append((Path("test.md"), "content"))
        assert wiki_adapter.pending_writes == 1

    def test_buffer_failed_write(self, wiki_adapter):
        """Failed write should be buffered."""
        test_file = wiki_adapter.overlay_dir / "test.md"

        wiki_adapter._buffer_failed_write(test_file, "Content")

        assert wiki_adapter.pending_writes == 1
        assert wiki_adapter._write_buffer[0] == (test_file, "Content")

    def test_buffer_updates_existing_file(self, wiki_adapter):
        """Buffering same file should update content, not duplicate."""
        test_file = wiki_adapter.overlay_dir / "test.md"

        wiki_adapter._buffer_failed_write(test_file, "Content 1")
        wiki_adapter._buffer_failed_write(test_file, "Content 2")

        assert wiki_adapter.pending_writes == 1
        assert wiki_adapter._write_buffer[0] == (test_file, "Content 2")

    def test_buffer_max_size(self, wiki_adapter):
        """Buffer should respect max size limit."""
        wiki_adapter._max_buffer_size = 3

        for i in range(5):
            wiki_adapter._buffer_failed_write(
                wiki_adapter.overlay_dir / f"file{i}.md",
                f"Content {i}",
            )

        assert wiki_adapter.pending_writes == 3

    def test_retry_buffered_writes_success(self, wiki_adapter):
        """Successful retry should remove from buffer."""
        test_file = wiki_adapter.overlay_dir / "test.md"

        # Add to buffer
        wiki_adapter._write_buffer.append((test_file, "Test content"))
        assert wiki_adapter.pending_writes == 1

        # Retry should succeed
        wiki_adapter._retry_buffered_writes()

        assert wiki_adapter.pending_writes == 0
        assert test_file.exists()
        assert test_file.read_text() == "Test content"

    def test_retry_buffered_writes_keeps_failures(self, wiki_adapter):
        """Failed retry should keep entry in buffer."""
        # Use a path that can't be written (non-existent parent)
        bad_file = Path("/nonexistent/path/test.md")

        wiki_adapter._write_buffer.append((bad_file, "Content"))

        wiki_adapter._retry_buffered_writes()

        # Should still be in buffer
        assert wiki_adapter.pending_writes == 1

    def test_flush_buffer_returns_pending_count(self, wiki_adapter):
        """flush_buffer should return count of still-pending writes."""
        test_file = wiki_adapter.overlay_dir / "test.md"
        bad_file = Path("/nonexistent/path/test.md")

        wiki_adapter._write_buffer.append((test_file, "Good content"))
        wiki_adapter._write_buffer.append((bad_file, "Bad content"))

        pending = wiki_adapter.flush_buffer()

        # One should succeed, one should fail
        assert pending == 1
        assert test_file.exists()

    def test_atomic_write_buffers_on_failure(self, wiki_adapter):
        """_atomic_write should buffer content on failure."""
        test_file = wiki_adapter.overlay_dir / "test.md"

        # Mock _do_atomic_write to fail
        with patch.object(wiki_adapter, '_do_atomic_write', return_value=False):
            result = wiki_adapter._atomic_write(test_file, "Content")

        assert result is False
        assert wiki_adapter.pending_writes == 1

    def test_atomic_write_retries_buffer_first(self, wiki_adapter):
        """_atomic_write should retry buffered writes before new write."""
        buffered_file = wiki_adapter.overlay_dir / "buffered.md"
        new_file = wiki_adapter.overlay_dir / "new.md"

        # Add to buffer
        wiki_adapter._write_buffer.append((buffered_file, "Buffered content"))

        # Write new file
        wiki_adapter._atomic_write(new_file, "New content")

        # Both files should exist
        assert buffered_file.exists()
        assert new_file.exists()
        assert wiki_adapter.pending_writes == 0


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------


class TestWikiAdapterIntegration:
    """Integration tests for WikiAdapter hardening."""

    def test_full_session_flow(self, wiki_adapter):
        """Test full session flow with multiple events."""
        # Simulate session events
        wiki_adapter.append_to_session_note(
            session=1,
            content="> [!hinge] Made a choice\n",
            section="Key Choices",
            event_type="hinge",
        )

        wiki_adapter.append_to_session_note(
            session=1,
            content="> [!faction] Nexus: Neutral → Friendly\n",
            section="Faction Changes",
            event_type="faction",
        )

        wiki_adapter.append_to_session_note(
            session=1,
            content="- [[NPCs/Cipher|Cipher]] ([[Nexus]])\n",
            section="NPCs Encountered",
            event_type="npc",
        )

        # Verify game log was created with all content (now in _game_log.md)
        sessions_dir = wiki_adapter.overlay_dir / "sessions"
        game_logs = list(sessions_dir.glob("*/_game_log.md"))
        assert len(game_logs) == 1

        content = game_logs[0].read_text()
        # Content separation: all live updates go to game log
        assert "Made a choice" in content
        assert "Nexus" in content
        assert "Cipher" in content

    def test_duplicate_events_not_repeated(self, wiki_adapter):
        """Duplicate events should not create duplicate entries."""
        # Same event twice
        for _ in range(3):
            wiki_adapter.append_to_session_note(
                session=1,
                content="> [!hinge] Same choice\n",
                section="Key Choices",
                event_type="hinge",
            )

        sessions_dir = wiki_adapter.overlay_dir / "sessions"
        game_logs = list(sessions_dir.glob("*/_game_log.md"))
        content = game_logs[0].read_text()

        # Should only appear once
        assert content.count("Same choice") == 1

    def test_factory_function(self, wiki_dir):
        """Factory function should create configured adapter."""
        adapter = create_wiki_adapter(
            campaign_id="factory_test",
            wiki_dir=wiki_dir,
            enabled=True,
        )

        assert adapter.is_enabled
        assert adapter.campaign_id == "factory_test"
        assert adapter.pending_writes == 0
