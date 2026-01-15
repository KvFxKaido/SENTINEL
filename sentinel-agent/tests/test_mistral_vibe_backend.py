"""Tests for Mistral Vibe CLI backend."""

import pytest
from unittest.mock import patch, MagicMock

from src.llm.mistral_vibe import MistralVibeClient, create_mistral_vibe_client
from src.llm.base import Message


class TestMistralVibeClient:
    """Tests for MistralVibeClient class."""

    def test_init_defaults(self):
        """Test default initialization."""
        client = MistralVibeClient()
        assert client.model_name == "codestral-latest"
        assert client.timeout == 180

    def test_init_with_model(self):
        """Test initialization with custom model."""
        client = MistralVibeClient(model="mistral-large-latest")
        assert client.model_name == "mistral-large-latest"

    def test_supports_tools_is_false(self):
        """Test that supports_tools returns False (uses skill-based fallback)."""
        client = MistralVibeClient()
        assert client.supports_tools is False

    @patch('shutil.which')
    def test_is_available_cli_not_found(self, mock_which):
        """Test is_available when vibe CLI is not found."""
        mock_which.return_value = None
        client = MistralVibeClient()
        assert client.is_available() is False

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_is_available_success(self, mock_run, mock_which):
        """Test is_available when vibe CLI is installed."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(returncode=0)
        client = MistralVibeClient()
        assert client.is_available() is True

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_is_available_version_fails(self, mock_run, mock_which):
        """Test is_available when version check fails."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(returncode=1)
        client = MistralVibeClient()
        assert client.is_available() is False

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_basic(self, mock_run, mock_which):
        """Test basic chat completion."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Hello! I'm here to help you with your code.",
            stderr=""
        )

        client = MistralVibeClient()
        messages = [Message(role="user", content="Hi")]

        response = client.chat(messages)

        assert "Hello" in response.content
        # Verify the command was called correctly
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "vibe" in cmd[0]
        assert "--prompt" in cmd
        assert "--auto-approve" in cmd

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_with_system_prompt(self, mock_run, mock_which):
        """Test chat with system prompt."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="I am a helpful Game Master!",
            stderr=""
        )

        client = MistralVibeClient()
        messages = [Message(role="user", content="What are you?")]

        response = client.chat(messages, system="You are a Game Master.")

        assert "Game Master" in response.content

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_strips_ansi_codes(self, mock_run, mock_which):
        """Test that ANSI escape codes are stripped from output."""
        mock_which.return_value = "/usr/bin/vibe"
        # Include ANSI color codes in output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="\x1b[32mGreen text\x1b[0m and \x1b[31mred text\x1b[0m",
            stderr=""
        )

        client = MistralVibeClient()
        messages = [Message(role="user", content="Test")]

        response = client.chat(messages)

        assert "\x1b[" not in response.content
        assert "Green text" in response.content
        assert "red text" in response.content

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_filters_tool_logs(self, mock_run, mock_which):
        """Test that tool execution logs are filtered from output."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Reading file: test.py\nThe file contains a function.\nExecuting: ls\nDone!",
            stderr=""
        )

        client = MistralVibeClient()
        messages = [Message(role="user", content="Read the file")]

        response = client.chat(messages)

        assert "Reading file:" not in response.content
        assert "Executing:" not in response.content
        assert "function" in response.content

    @patch('shutil.which')
    def test_chat_cli_not_found(self, mock_which):
        """Test chat raises error when CLI not found."""
        mock_which.return_value = None
        client = MistralVibeClient()
        messages = [Message(role="user", content="Hi")]

        with pytest.raises(RuntimeError) as exc_info:
            client.chat(messages)

        assert "Mistral Vibe CLI not found" in str(exc_info.value)
        assert "pip install mistral-vibe" in str(exc_info.value)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_cli_error(self, mock_run, mock_which):
        """Test chat handles CLI errors."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Authentication required"
        )

        client = MistralVibeClient()
        messages = [Message(role="user", content="Hi")]

        with pytest.raises(RuntimeError) as exc_info:
            client.chat(messages)

        assert "Authentication required" in str(exc_info.value)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_timeout(self, mock_run, mock_which):
        """Test chat handles timeout."""
        import subprocess
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="vibe", timeout=180)

        client = MistralVibeClient()
        messages = [Message(role="user", content="Hi")]

        with pytest.raises(TimeoutError):
            client.chat(messages)

    def test_set_model(self):
        """Test model can be changed."""
        client = MistralVibeClient()
        assert client.model_name == "codestral-latest"

        client.set_model("mistral-large-latest")
        assert client.model_name == "mistral-large-latest"

    def test_get_model_info(self):
        """Test get_model_info returns expected structure."""
        client = MistralVibeClient()
        info = client.get_model_info()

        assert info["backend"] == "mistral-vibe"
        assert info["model"] == "codestral-latest"
        assert info["supports_tools"] is False
        assert "features" in info
        assert info["features"]["agentic"] is True

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_create_mistral_vibe_client_success(self, mock_run, mock_which):
        """Test factory function success."""
        mock_which.return_value = "/usr/bin/vibe"
        mock_run.return_value = MagicMock(returncode=0)

        client = create_mistral_vibe_client()
        assert isinstance(client, MistralVibeClient)

    @patch('shutil.which')
    def test_create_mistral_vibe_client_failure(self, mock_which):
        """Test factory function raises on unavailable."""
        mock_which.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            create_mistral_vibe_client()

        assert "Mistral Vibe CLI is not available" in str(exc_info.value)

    def test_messages_to_prompt_basic(self):
        """Test message conversion to prompt."""
        client = MistralVibeClient()
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]

        prompt = client._messages_to_prompt(messages)

        assert "<user>" in prompt
        assert "Hello" in prompt
        assert "<assistant>" in prompt
        assert "Hi there!" in prompt
        assert "How are you?" in prompt

    def test_messages_to_prompt_with_system(self):
        """Test message conversion includes system prompt."""
        client = MistralVibeClient()
        messages = [Message(role="user", content="Test")]

        prompt = client._messages_to_prompt(messages, system="You are helpful.")

        assert "<system>" in prompt
        assert "You are helpful." in prompt

    def test_messages_to_prompt_tool_results(self):
        """Test message conversion handles tool results."""
        client = MistralVibeClient()
        messages = [
            Message(role="user", content="Roll a d20"),
            Message(role="tool", content='{"result": 15}'),
        ]

        prompt = client._messages_to_prompt(messages)

        assert "<tool_result>" in prompt
        assert '{"result": 15}' in prompt

    @patch('shutil.which')
    def test_find_vibe_tries_multiple_names(self, mock_which):
        """Test that _find_vibe tries multiple executable names."""
        # First call returns None (vibe not found), second returns path
        mock_which.side_effect = [None, "/usr/local/bin/mistral-vibe"]

        client = MistralVibeClient()
        result = client._find_vibe()

        assert result == "/usr/local/bin/mistral-vibe"
        # Should have tried both names
        assert mock_which.call_count == 2
