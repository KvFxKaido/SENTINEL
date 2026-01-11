"""
Claude Code CLI client.

Uses the already-authenticated `claude` CLI to make API calls.
No API keys required - just have Claude Code logged in.
"""

import json
import subprocess
import shutil
from typing import Any

from .base import LLMClient, LLMResponse, Message


class ClaudeCodeClient(LLMClient):
    """
    Client that shells out to Claude Code CLI.

    This allows using Claude models without managing API keys -
    if the user has Claude Code authenticated, it just works.

    Note: Does not support tool calling (Claude Code handles tools internally).
    We're using it as a pure text completion backend.
    """

    MODELS = ["sonnet", "opus", "haiku"]

    def __init__(
        self,
        model: str = "sonnet",
        timeout: int = 120,
    ):
        """
        Initialize Claude Code client.

        Args:
            model: Model alias ("sonnet", "opus", "haiku")
            timeout: Request timeout in seconds
        """
        self._model = model if model in self.MODELS else "sonnet"
        self.timeout = timeout
        self._available: bool | None = None

    @property
    def model_name(self) -> str:
        return f"claude-{self._model}"

    @property
    def supports_tools(self) -> bool:
        # We don't support tools through the CLI - it's text in/text out
        return False

    def _find_claude(self) -> str | None:
        """Find the claude CLI executable."""
        return shutil.which("claude")

    def is_available(self) -> bool:
        """Check if Claude Code CLI is installed and authenticated."""
        if self._available is not None:
            return self._available

        claude_path = self._find_claude()
        if not claude_path:
            self._available = False
            return False

        # Test with a minimal call
        try:
            result = subprocess.run(
                [claude_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._available = result.returncode == 0
        except Exception:
            self._available = False

        return self._available

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Send chat completion via Claude Code CLI.

        Converts messages to a single prompt and calls claude -p.
        """
        claude_path = self._find_claude()
        if not claude_path:
            raise RuntimeError("Claude Code CLI not found. Install from https://claude.ai/code")

        # Build the prompt from messages
        prompt = self._messages_to_prompt(messages)

        # Build command
        cmd = [
            claude_path,
            "-p", prompt,
            "--output-format", "json",
            "--model", self._model,
        ]

        if system:
            cmd.extend(["--append-system-prompt", system])

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=None,  # Use current directory
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Claude Code request timed out after {self.timeout}s")

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Claude Code error: {error_msg}")

        # Parse JSON response
        try:
            data = json.loads(result.stdout)
            content = data.get("result", "")
            return LLMResponse(content=content)
        except json.JSONDecodeError:
            # Fall back to raw output if not JSON
            return LLMResponse(content=result.stdout.strip())

    def _messages_to_prompt(self, messages: list[Message]) -> str:
        """Convert message list to a single prompt string."""
        parts = []
        for msg in messages:
            if msg.role == "user":
                parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")
            elif msg.role == "system":
                parts.append(f"[System: {msg.content}]")

        # Add a final prompt for the assistant to continue
        if parts and not parts[-1].startswith("User:"):
            parts.append("User: Please continue.")

        return "\n\n".join(parts)

    def list_models(self) -> list[str]:
        """List available model aliases."""
        return list(self.MODELS)

    def set_model(self, model: str) -> None:
        """Set the model to use."""
        if model in self.MODELS:
            self._model = model
        else:
            # Accept full model names too
            for alias in self.MODELS:
                if alias in model.lower():
                    self._model = alias
                    return
            raise ValueError(f"Unknown model: {model}. Available: {', '.join(self.MODELS)}")

    def get_model_info(self) -> dict:
        """Get info about the client."""
        return {
            "available": self.is_available(),
            "model": self._model,
            "all_models": self.MODELS,
            "supports_tools": False,
            "backend": "claude-code",
        }


def create_claude_code_client(model: str = "sonnet") -> ClaudeCodeClient:
    """
    Create and validate a Claude Code client.

    Raises RuntimeError if Claude Code is not available.
    """
    client = ClaudeCodeClient(model=model)

    if not client.is_available():
        raise RuntimeError(
            "Claude Code CLI is not available.\n"
            "1. Install Claude Code: https://claude.ai/code\n"
            "2. Run 'claude' and complete authentication\n"
            "3. Try again"
        )

    return client
