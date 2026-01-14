"""
Codex CLI client.

Uses the `codex` CLI (OpenAI's agentic coding tool) as an LLM backend.
Supports native tool calling through MCP integration.

Requires OpenAI subscription for full access.
"""

import json
import subprocess
import shutil
import tempfile
import os
from typing import Any

from .base import LLMClient, LLMResponse, Message, ToolCall


class CodexCliClient(LLMClient):
    """
    Client that shells out to Codex CLI.

    Codex CLI provides:
    - Native MCP tool support (experimental)
    - OpenAI model access (o3, gpt-4, etc.)
    - Agentic capabilities with sandbox support

    When tools are requested, runs in --full-auto mode for autonomous operation.
    """

    def __init__(
        self,
        timeout: int = 180,
        full_auto: bool = True,
        model: str | None = None,
    ):
        """
        Initialize Codex CLI client.

        Args:
            timeout: Request timeout in seconds (longer for complex tasks)
            full_auto: Auto-approve tool execution (recommended for GM use)
            model: Model to use (e.g., 'o3', 'gpt-4o'). None uses default.
        """
        self.timeout = timeout
        self.full_auto = full_auto
        self.model = model
        self._available: bool | None = None
        self._detected_model: str | None = None

    @property
    def model_name(self) -> str:
        return self._detected_model or self.model or "codex-default"

    @property
    def supports_tools(self) -> bool:
        # Codex CLI supports tools natively through MCP (experimental)
        # However, we'll use skill-based fallback for SENTINEL's tool format
        return False

    def _find_codex(self) -> str | None:
        """Find the codex CLI executable."""
        return shutil.which("codex")

    def is_available(self) -> bool:
        """Check if Codex CLI is installed."""
        if self._available is not None:
            return self._available

        codex_path = self._find_codex()
        if not codex_path:
            self._available = False
            return False

        # Test with a version call
        try:
            result = subprocess.run(
                [codex_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._available = result.returncode == 0
            if self._available and result.stdout:
                # Parse version output like "codex-cli 0.80.0"
                self._detected_model = result.stdout.strip()
        except Exception:
            self._available = False

        return self._available

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send chat completion via Codex CLI.

        Uses stdin for the prompt to handle large contexts.
        Uses -o flag to capture output to temp file.
        """
        codex_path = self._find_codex()
        if not codex_path:
            raise RuntimeError(
                "Codex CLI not found. Install from https://github.com/openai/codex"
            )

        # Build the prompt from messages
        prompt = self._messages_to_prompt(messages, system)

        # Create temp file for output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name

        try:
            # Build command
            cmd = [
                codex_path,
                "exec",
                "-o", output_file,  # Write last message to file
                "--skip-git-repo-check",  # Don't require git repo
            ]

            # Add full-auto mode for autonomous operation
            if self.full_auto:
                cmd.append("--full-auto")

            # Add model if specified
            if self.model:
                cmd.extend(["-m", self.model])

            # Use stdin for prompt (read from -)
            cmd.append("-")

            # Execute with prompt via stdin
            try:
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding="utf-8",
                )
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"Codex CLI request timed out after {self.timeout}s")

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(f"Codex CLI error: {error_msg}")

            # Read output from file
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            else:
                # Fall back to stdout if file wasn't created
                content = result.stdout.strip()

            return self._parse_response(content)

        finally:
            # Clean up temp file
            if os.path.exists(output_file):
                os.unlink(output_file)

    def _parse_response(self, output: str) -> LLMResponse:
        """Parse Codex CLI output."""
        # Try to parse as JSON first
        try:
            data = json.loads(output)

            # The response structure may vary - try common fields
            content = ""
            if isinstance(data, dict):
                content = (
                    data.get("response", "") or
                    data.get("result", "") or
                    data.get("content", "") or
                    data.get("text", "") or
                    data.get("message", "") or
                    str(data)
                )
            elif isinstance(data, str):
                content = data
            else:
                content = str(data)

            return LLMResponse(content=content)

        except json.JSONDecodeError:
            # Fall back to raw output if not JSON
            # Strip any ANSI codes that might be present
            import re
            clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
            return LLMResponse(content=clean_output.strip())

    def _messages_to_prompt(self, messages: list[Message], system: str | None = None) -> str:
        """Convert message list to a single prompt string."""
        parts = []

        # Embed system prompt at the start
        if system:
            parts.append(f"<system>\n{system}\n</system>")

        for msg in messages:
            if msg.role == "user":
                parts.append(f"<user>\n{msg.content}\n</user>")
            elif msg.role == "assistant":
                parts.append(f"<assistant>\n{msg.content}\n</assistant>")
            elif msg.role == "system":
                parts.append(f"<system>\n{msg.content}\n</system>")
            elif msg.role == "tool":
                parts.append(f"<tool_result>\n{msg.content}\n</tool_result>")

        return "\n\n".join(parts)

    def chat_streaming(
        self,
        messages: list[Message],
        system: str | None = None,
        callback: callable = None,
    ) -> str:
        """
        Stream chat completion via Codex CLI.

        Uses --json flag for JSONL streaming output.
        """
        codex_path = self._find_codex()
        if not codex_path:
            raise RuntimeError("Codex CLI not found")

        prompt = self._messages_to_prompt(messages, system)

        cmd = [
            codex_path,
            "exec",
            "--json",  # JSONL output for streaming
            "--skip-git-repo-check",
            "-",  # Read from stdin
        ]

        if self.full_auto:
            cmd.append("--full-auto")

        if self.model:
            cmd.extend(["-m", self.model])

        # Stream output with stdin for prompt (avoids Windows cmd length limit)
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        # Write prompt to stdin and close it
        process.stdin.write(prompt)
        process.stdin.close()

        full_response = []
        try:
            for line in process.stdout:
                line = line.strip()
                if line and callback:
                    try:
                        data = json.loads(line)
                        # Codex JSONL events have various types
                        chunk = (
                            data.get("text", "") or
                            data.get("content", "") or
                            data.get("message", "")
                        )
                        if chunk:
                            callback(chunk)
                            full_response.append(chunk)
                    except json.JSONDecodeError:
                        callback(line)
                        full_response.append(line)
        finally:
            process.wait()

        return "".join(full_response)

    def get_model_info(self) -> dict:
        """Get info about the client."""
        return {
            "available": self.is_available(),
            "model": self.model_name,
            "supports_tools": self.supports_tools,
            "backend": "codex-cli",
            "features": {
                "mcp_support": True,
                "sandbox_modes": ["read-only", "workspace-write", "full-access"],
                "models": ["o3", "gpt-4o", "gpt-4o-mini"],
            },
        }


def create_codex_cli_client(
    full_auto: bool = True,
    timeout: int = 180,
    model: str | None = None,
) -> CodexCliClient:
    """
    Create and validate a Codex CLI client.

    Args:
        full_auto: Auto-approve tool execution
        timeout: Request timeout in seconds
        model: Model to use (e.g., 'o3', 'gpt-4o')

    Raises:
        RuntimeError if Codex CLI is not available.
    """
    client = CodexCliClient(full_auto=full_auto, timeout=timeout, model=model)

    if not client.is_available():
        raise RuntimeError(
            "Codex CLI is not available.\n"
            "Install: npm install -g @openai/codex\n"
            "Or: https://github.com/openai/codex"
        )

    return client
