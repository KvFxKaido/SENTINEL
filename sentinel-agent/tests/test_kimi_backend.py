"""Tests for Kimi CLI backend implementation."""

import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from src.llm import KimiClient
from src.llm.kimi import KimiCliClient, create_kimi_client
from src.llm.base import Message


class TestKimiCliClient:
    """Test Kimi CLI backend client."""

    def test_init_defaults(self):
        """Test default initialization."""
        client = KimiCliClient()
        assert client.model_name == "moonshot-v1-32k"
        assert client.timeout == 180

    def test_init_with_model(self):
        """Test initialization with custom model."""
        client = KimiCliClient(model="moonshot-v1-128k")
        assert client.model_name == "moonshot-v1-128k"

    def test_supports_tools_is_false(self):
        """Test that supports_tools returns False (uses skill-based fallback)."""
        client = KimiCliClient()
        assert client.supports_tools is False

    @patch('shutil.which')
    def test_is_available_cli_not_found(self, mock_which):
        """Test availability when CLI is not installed."""
        mock_which.return_value = None

        client = KimiCliClient()
        assert client.is_available() is False

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_is_available_success(self, mock_run, mock_which):
        """Test availability when CLI is installed and working."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(returncode=0)

        client = KimiCliClient()
        assert client.is_available() is True

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_is_available_version_fails(self, mock_run, mock_which):
        """Test availability when version check fails."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(returncode=1)

        client = KimiCliClient()
        assert client.is_available() is False

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_basic(self, mock_run, mock_which):
        """Test basic chat completion."""
        mock_which.return_value = "/usr/bin/kimi"
        # Kimi CLI returns: {"role": "assistant", "content": [{"type": "text", "text": "..."}]}
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"role":"assistant","content":[{"type":"text","text":"Hello!"}]}',
            stderr=""
        )

        client = KimiCliClient()
        messages = [Message(role="user", content="Hi")]

        response = client.chat(messages)

        assert response.content == "Hello!"
        assert not response.has_tool_calls

        # Verify command was called correctly
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "kimi" in cmd[0]
        assert "--print" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "-c" in cmd

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_with_system_prompt(self, mock_run, mock_which):
        """Test chat with system prompt."""
        mock_which.return_value = "/usr/bin/kimi"
        # Kimi CLI returns: {"role": "assistant", "content": [{"type": "text", "text": "..."}]}
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"role":"assistant","content":[{"type":"text","text":"I am helpful!"}]}',
            stderr=""
        )

        client = KimiCliClient()
        messages = [Message(role="user", content="Are you helpful?")]

        response = client.chat(messages, system="You are a helpful assistant.")

        assert response.content == "I am helpful!"

        # Verify system prompt was included in -c argument
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        # Find the -c flag and its argument
        c_index = cmd.index("-c")
        prompt_arg = cmd[c_index + 1]
        assert "<system>" in prompt_arg
        assert "You are a helpful assistant." in prompt_arg

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_plain_text_response(self, mock_run, mock_which):
        """Test handling plain text (non-JSON) response."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Just plain text response",
            stderr=""
        )

        client = KimiCliClient()
        messages = [Message(role="user", content="Hi")]

        response = client.chat(messages)

        assert response.content == "Just plain text response"

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_strips_ansi_codes(self, mock_run, mock_which):
        """Test that ANSI escape codes are stripped from output."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="\x1b[32mColored response\x1b[0m",
            stderr=""
        )

        client = KimiCliClient()
        messages = [Message(role="user", content="Hi")]

        response = client.chat(messages)

        assert response.content == "Colored response"

    @patch('shutil.which')
    def test_chat_cli_not_found(self, mock_which):
        """Test error when CLI is not found during chat."""
        mock_which.return_value = None

        client = KimiCliClient()
        client._available = None  # Reset cached availability

        with pytest.raises(RuntimeError, match="Kimi CLI not found"):
            client.chat([Message(role="user", content="Hi")])

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_cli_error(self, mock_run, mock_which):
        """Test handling CLI errors."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Authentication required"
        )

        client = KimiCliClient()

        with pytest.raises(RuntimeError, match="Kimi CLI error: Authentication required"):
            client.chat([Message(role="user", content="Hi")])

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_chat_timeout(self, mock_run, mock_which):
        """Test handling timeout."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="kimi", timeout=180)

        client = KimiCliClient()

        with pytest.raises(TimeoutError, match="timed out after 180s"):
            client.chat([Message(role="user", content="Hi")])

    def test_set_model(self):
        """Test changing model."""
        client = KimiCliClient(model="moonshot-v1-8k")
        assert client.model_name == "moonshot-v1-8k"

        client.set_model("moonshot-v1-128k")
        assert client.model_name == "moonshot-v1-128k"

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_get_model_info(self, mock_run, mock_which):
        """Test getting model information."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(returncode=0)

        client = KimiCliClient()
        info = client.get_model_info()

        assert info["available"] is True
        assert info["model"] == "moonshot-v1-32k"
        assert info["backend"] == "kimi-cli"
        assert info["supports_tools"] is False
        assert "moonshot-v1-128k" in info["features"]["models"]

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_create_kimi_client_success(self, mock_run, mock_which):
        """Test successful client creation."""
        mock_which.return_value = "/usr/bin/kimi"
        mock_run.return_value = MagicMock(returncode=0)

        client = create_kimi_client()

        assert isinstance(client, KimiCliClient)
        assert client.is_available() is True

    @patch('shutil.which')
    def test_create_kimi_client_failure(self, mock_which):
        """Test client creation failure when CLI unavailable."""
        mock_which.return_value = None

        with pytest.raises(RuntimeError, match="Kimi CLI is not available"):
            create_kimi_client()

    @patch('shutil.which')
    def test_chat_error_message_has_correct_url(self, mock_which):
        """Test that error messages reference the correct Kimi CLI repo."""
        mock_which.return_value = None

        client = KimiCliClient()
        client._available = None

        try:
            client.chat([Message(role="user", content="Hi")])
        except RuntimeError as e:
            assert "MoonshotAI/kimi-cli" in str(e)
            assert "pip install kimi-cli" in str(e)

    def test_messages_to_prompt_basic(self):
        """Test message conversion to prompt string."""
        client = KimiCliClient()
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]

        prompt = client._messages_to_prompt(messages)

        assert "<user>\nHello\n</user>" in prompt
        assert "<assistant>\nHi there!\n</assistant>" in prompt
        assert "<user>\nHow are you?\n</user>" in prompt

    def test_messages_to_prompt_with_system(self):
        """Test message conversion includes system prompt."""
        client = KimiCliClient()
        messages = [Message(role="user", content="Hello")]

        prompt = client._messages_to_prompt(messages, system="Be helpful")

        assert "<system>\nBe helpful\n</system>" in prompt
        assert prompt.index("<system>") < prompt.index("<user>")

    def test_messages_to_prompt_tool_results(self):
        """Test message conversion handles tool results."""
        client = KimiCliClient()
        messages = [
            Message(role="user", content="Roll a die"),
            Message(role="tool", content='{"result": 17}', tool_call_id="call_123"),
        ]

        prompt = client._messages_to_prompt(messages)

        assert "<tool_result>" in prompt
        assert '{"result": 17}' in prompt

    def test_kimi_client_alias(self):
        """Test that KimiClient is an alias for KimiCliClient."""
        assert KimiClient is KimiCliClient

    @patch('shutil.which')
    def test_find_kimi_tries_multiple_names(self, mock_which):
        """Test that _find_kimi tries multiple CLI names."""
        # First call returns None (kimi not found), second returns path (kimi-cli found)
        mock_which.side_effect = [None, "/usr/bin/kimi-cli"]

        client = KimiCliClient()
        path = client._find_kimi()

        assert path == "/usr/bin/kimi-cli"
        assert mock_which.call_count == 2
        mock_which.assert_any_call("kimi")
        mock_which.assert_any_call("kimi-cli")
