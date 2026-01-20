"""
Tests for headless mode - the JSON I/O interface for programmatic control.

This is the API surface that the Deno bridge depends on.
Critical tests for frontend stability.
"""

import json
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.interface.headless import HeadlessRunner
from src.state import MemoryCampaignStore, CampaignManager
from src.llm import MockLLMClient


class TestHeadlessBasicCommands:
    """Test basic command handling."""

    @pytest.fixture
    def runner(self, tmp_path):
        """Create a headless runner with in-memory store and captured output."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )
        runner._output_buffer = output
        return runner

    def test_status_returns_ok(self, runner):
        """Status command should return ok with backend info."""
        result = runner.handle_command({"cmd": "status"})

        assert result["ok"] is True
        assert "backend" in result
        assert result["campaign"] is None  # No campaign loaded
        assert result["conversation_length"] == 0

    def test_quit_returns_action(self, runner):
        """Quit command should return quit action."""
        result = runner.handle_command({"cmd": "quit"})

        assert result["ok"] is True
        assert result["action"] == "quit"

    def test_unknown_command_returns_error(self, runner):
        """Unknown commands should return error."""
        result = runner.handle_command({"cmd": "invalid_cmd"})

        assert result["ok"] is False
        assert "error" in result
        assert "Unknown command" in result["error"]

    def test_missing_cmd_field_returns_error(self, runner):
        """Commands without 'cmd' field should error."""
        result = runner.handle_command({"action": "something"})

        assert result["ok"] is False
        assert "Unknown command" in result["error"]

    def test_empty_command_returns_error(self, runner):
        """Empty command dict should error."""
        result = runner.handle_command({})

        assert result["ok"] is False


class TestHeadlessCampaignOperations:
    """Test campaign load/save operations."""

    @pytest.fixture
    def runner_with_campaign(self, tmp_path):
        """Create runner and a campaign to load."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir(parents=True)

        # Create a campaign file
        campaign_data = {
            "_version": 1,
            "meta": {
                "id": "test-campaign-123",
                "name": "Test Campaign",
                "session_count": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            },
            "character": None,
            "npcs": {"npcs": {}},
            "factions": {},
            "history": [],
            "dormant_threads": [],
            "active_mission": None,
            "hinge_moments": [],
        }
        campaign_file = campaigns_dir / "test-campaign-123.json"
        campaign_file.write_text(json.dumps(campaign_data))

        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=campaigns_dir,
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )
        return runner, "test-campaign-123"

    def test_load_valid_campaign(self, runner_with_campaign):
        """Loading a valid campaign should succeed."""
        runner, campaign_id = runner_with_campaign
        result = runner.handle_command({"cmd": "load", "campaign_id": campaign_id})

        assert result["ok"] is True
        assert result["campaign"]["id"] == campaign_id
        assert result["campaign"]["name"] == "Test Campaign"

    def test_load_nonexistent_campaign_fails(self, runner_with_campaign):
        """Loading a nonexistent campaign should fail gracefully."""
        runner, _ = runner_with_campaign
        result = runner.handle_command({"cmd": "load", "campaign_id": "does-not-exist"})

        assert result["ok"] is False
        assert "error" in result

    def test_load_without_id_fails(self, runner_with_campaign):
        """Load without campaign_id should fail."""
        runner, _ = runner_with_campaign
        result = runner.handle_command({"cmd": "load"})

        assert result["ok"] is False
        assert "No campaign_id provided" in result["error"]

    def test_save_without_campaign_fails(self, tmp_path):
        """Save without loaded campaign should fail."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )
        result = runner.handle_command({"cmd": "save"})

        assert result["ok"] is False
        assert "No campaign loaded" in result["error"]

    def test_save_with_campaign_succeeds(self, runner_with_campaign):
        """Save with loaded campaign should succeed."""
        runner, campaign_id = runner_with_campaign
        # First load
        runner.handle_command({"cmd": "load", "campaign_id": campaign_id})
        # Then save
        result = runner.handle_command({"cmd": "save"})

        assert result["ok"] is True

    def test_load_resets_conversation(self, runner_with_campaign):
        """Loading a campaign should reset the conversation history."""
        runner, campaign_id = runner_with_campaign
        # Add some conversation
        runner.conversation = [{"role": "user", "content": "test"}]

        # Load campaign
        runner.handle_command({"cmd": "load", "campaign_id": campaign_id})

        # Conversation should be reset
        assert runner.conversation == []


class TestHeadlessSayCommand:
    """Test the say command for player input."""

    @pytest.fixture
    def runner_with_loaded_campaign(self, tmp_path):
        """Create runner with a loaded campaign and mock LLM."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir(parents=True)

        campaign_data = {
            "_version": 1,
            "meta": {
                "id": "test-campaign",
                "name": "Test",
                "session_count": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            },
            "character": {
                "name": "Test Player",
                "callsign": "Ghost",
                "background": "operative",
            },
            "npcs": {"npcs": {}},
            "factions": {},
            "history": [],
            "dormant_threads": [],
            "active_mission": None,
            "hinge_moments": [],
        }
        (campaigns_dir / "test-campaign.json").write_text(json.dumps(campaign_data))

        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=campaigns_dir,
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )
        runner.handle_command({"cmd": "load", "campaign_id": "test-campaign"})
        return runner

    def test_say_without_campaign_fails(self, tmp_path):
        """Say without loaded campaign should fail."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )
        result = runner.handle_command({"cmd": "say", "text": "Hello"})

        assert result["ok"] is False
        assert "No campaign loaded" in result["error"]

    def test_say_without_text_fails(self, runner_with_loaded_campaign):
        """Say without text should fail."""
        result = runner_with_loaded_campaign.handle_command({"cmd": "say"})

        assert result["ok"] is False
        assert "No text provided" in result["error"]

    def test_say_empty_text_fails(self, runner_with_loaded_campaign):
        """Say with empty text should fail."""
        result = runner_with_loaded_campaign.handle_command({"cmd": "say", "text": ""})

        assert result["ok"] is False
        assert "No text provided" in result["error"]


class TestHeadlessSlashCommands:
    """Test slash command execution."""

    @pytest.fixture
    def runner_with_campaign(self, tmp_path):
        """Create runner with loaded campaign for slash commands."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir(parents=True)

        campaign_data = {
            "_version": 1,
            "meta": {
                "id": "test-campaign",
                "name": "Test",
                "session_count": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            },
            "character": None,
            "npcs": {"npcs": {}},
            "factions": {},
            "history": [],
            "dormant_threads": [],
            "active_mission": None,
            "hinge_moments": [],
        }
        (campaigns_dir / "test-campaign.json").write_text(json.dumps(campaign_data))

        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=campaigns_dir,
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )
        runner.handle_command({"cmd": "load", "campaign_id": "test-campaign"})
        return runner

    def test_unknown_slash_command_fails(self, runner_with_campaign):
        """Unknown slash commands should fail gracefully."""
        result = runner_with_campaign.handle_command({
            "cmd": "slash",
            "command": "/nonexistent_command",
            "args": [],
        })

        assert result["ok"] is False
        assert "Unknown command" in result["error"]

    def test_slash_adds_prefix_if_missing(self, runner_with_campaign):
        """Slash command should work without leading /."""
        result = runner_with_campaign.handle_command({
            "cmd": "slash",
            "command": "nonexistent",
            "args": [],
        })

        # Should still fail but with /nonexistent in error
        assert result["ok"] is False
        assert "/nonexistent" in result["error"]


class TestHeadlessEventEmission:
    """Test that events are properly emitted."""

    def test_event_format(self, tmp_path):
        """Events should be emitted in correct JSON format."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # Manually emit an event
        from src.state import GameEvent, EventType
        from datetime import datetime

        event = GameEvent(
            type=EventType.FACTION_CHANGED,
            data={"faction": "nexus", "old": "neutral", "new": "friendly"},
            campaign_id="test",
            session=1,
            timestamp=datetime.now(),
        )
        runner._emit_event(event)

        # Check output
        output.seek(0)
        line = output.readline()
        parsed = json.loads(line)

        assert parsed["type"] == "event"
        assert parsed["event_type"] == "faction.changed"
        assert parsed["data"]["faction"] == "nexus"
        assert parsed["campaign_id"] == "test"
        assert parsed["session"] == 1
        assert "timestamp" in parsed

    def test_response_format(self, tmp_path):
        """Responses should be emitted in correct JSON format."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        runner._emit_response("result", ok=True, data="test")

        output.seek(0)
        line = output.readline()
        parsed = json.loads(line)

        assert parsed["type"] == "result"
        assert parsed["ok"] is True
        assert parsed["data"] == "test"


class TestHeadlessEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_unicode_text(self, tmp_path):
        """Should handle unicode characters in commands."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # This shouldn't crash
        result = runner.handle_command({"cmd": "status", "note": "测试 тест 🎮"})
        assert result["ok"] is True

    def test_handles_large_text(self, tmp_path):
        """Should handle large text payloads."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # Create campaign for say command
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir(parents=True, exist_ok=True)
        campaign_data = {
            "_version": 1,
            "meta": {"id": "test", "name": "Test", "session_count": 1,
                    "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"},
            "character": None, "npcs": {"npcs": {}}, "factions": {}, "history": [],
            "dormant_threads": [], "active_mission": None, "hinge_moments": [],
        }
        (campaigns_dir / "test.json").write_text(json.dumps(campaign_data))
        runner.handle_command({"cmd": "load", "campaign_id": "test"})

        # Large text - this will fail because no LLM but shouldn't crash
        large_text = "A" * 10000
        result = runner.handle_command({"cmd": "say", "text": large_text})
        # Should either succeed or fail gracefully
        assert "ok" in result

    def test_handles_nested_json_in_args(self, tmp_path):
        """Should handle nested JSON in command args."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        result = runner.handle_command({
            "cmd": "slash",
            "command": "/test",
            "args": [{"nested": {"deeply": "value"}}],
        })
        # Should fail gracefully (unknown command) but not crash
        assert result["ok"] is False

    def test_concurrent_status_calls(self, tmp_path):
        """Multiple rapid status calls shouldn't cause issues."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # Call status many times rapidly
        for _ in range(100):
            result = runner.handle_command({"cmd": "status"})
            assert result["ok"] is True


class TestHeadlessJSONParsing:
    """Test JSON input parsing behavior."""

    def test_run_handles_invalid_json(self, tmp_path, monkeypatch):
        """Run loop should handle invalid JSON gracefully."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # Simulate stdin with invalid JSON followed by quit
        stdin_content = 'invalid json here\n{"cmd": "quit"}\n'
        monkeypatch.setattr('sys.stdin', StringIO(stdin_content))

        # Run should complete without crashing
        runner.run()

        # Check output includes error for invalid JSON
        output.seek(0)
        lines = output.readlines()
        # Should have: ready, error (for invalid JSON), result (for quit)
        assert any("error" in line.lower() for line in lines)

    def test_run_handles_empty_lines(self, tmp_path, monkeypatch):
        """Run loop should skip empty lines."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # Simulate stdin with empty lines
        stdin_content = '\n\n{"cmd": "status"}\n\n{"cmd": "quit"}\n'
        monkeypatch.setattr('sys.stdin', StringIO(stdin_content))

        runner.run()

        output.seek(0)
        lines = [l for l in output.readlines() if l.strip()]
        # Should have: ready, result (status), result (quit)
        assert len(lines) == 3

    def test_ready_message_on_startup(self, tmp_path, monkeypatch):
        """Run should emit ready message immediately."""
        output = StringIO()
        runner = HeadlessRunner(
            campaigns_dir=tmp_path / "campaigns",
            prompts_dir=Path(__file__).parent.parent / "prompts",
            backend="mock",
            output=output,
        )

        # Simulate empty stdin (EOF immediately)
        monkeypatch.setattr('sys.stdin', StringIO(''))

        runner.run()

        output.seek(0)
        first_line = output.readline()
        parsed = json.loads(first_line)

        assert parsed["type"] == "ready"
        assert "version" in parsed
        assert "backend" in parsed
