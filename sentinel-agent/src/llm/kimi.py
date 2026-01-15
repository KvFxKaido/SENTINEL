"""
Kimi CLI client.

Uses the `kimi` CLI to make API calls with Moonshot AI models.
Supports tool calling through skill-based parsing.

Piggybacks on existing kimi CLI authentication - if you're logged in, it just works.

Install: pip install kimi-cli
Docs: https://github.com/MoonshotAI/kimi-cli

NOTE: The exact CLI flags may need adjustment based on the Kimi CLI version.
Check `kimi --help` for available options.
"""

import json
import subprocess
import shutil
from typing import Any

from .base import LLMClient, LLMResponse, Message, ToolCall


class KimiCliClient(LLMClient):
    """
    Client that shells out to Kimi CLI.

    Kimi CLI provides:
    - Authentication via existing CLI login
    - Access to Moonshot AI models (moonshot-v1-8k/32k/128k)
    - Large context windows (up to 128K)

    When tools are requested, uses skill-based parsing (prompt injection + tag parsing).
    """

    def __init__(
        self,
        timeout: int = 180,
        model: str = "moonshot-v1-32k",
    ):
        """
        Initialize Kimi CLI client.

        Args:
            timeout: Request timeout in seconds (longer for complex tasks)
            model: Model to use (moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k)
        """
        self.timeout = timeout
        self._model = model
        self._available: bool | None = None

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        # Use skill-based fallback for SENTINEL's tool format
        return False

    def _find_kimi(self) -> str | None:
        """Find the kimi CLI executable."""
        # Try common names for the CLI
        for name in ["kimi", "kimi-cli"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def is_available(self) -> bool:
        """Check if Kimi CLI is installed and authenticated."""
        if self._available is not None:
            return self._available

        kimi_path = self._find_kimi()
        if not kimi_path:
            self._available = False
            return False

        # Test with a version call
        try:
            result = subprocess.run(
                [kimi_path, "--version"],
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
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send chat completion via Kimi CLI.

        Uses stdin for the prompt to handle large contexts.
        """
        kimi_path = self._find_kimi()
        if not kimi_path:
            raise RuntimeError(
                "Kimi CLI not found.\n"
                "Install: pip install kimi-cli\n"
                "Then run: kimi (and use /setup to configure)\n"
                "Docs: https://github.com/MoonshotAI/kimi-cli"
            )

        # Build the prompt from messages
        prompt = self._messages_to_prompt(messages, system)

        # Build command for non-interactive mode
        # kimi --print -c "prompt" --output-format stream-json -y
        cmd = [
            kimi_path,
            "--print",  # Non-interactive mode
            "-c", prompt,  # Pass prompt via -c flag
            "--output-format", "stream-json",
            "-y",  # Auto-approve (yolo mode)
        ]

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace",  # Handle encoding errors gracefully
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Kimi CLI request timed out after {self.timeout}s")

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Kimi CLI error: {error_msg}")

        # Parse response (handle None stdout)
        output = result.stdout or ""
        return self._parse_response(output)

    def _parse_response(self, output: str) -> LLMResponse:
        """Parse Kimi CLI stream-json output.

        Kimi outputs JSON with structure:
        {"role": "assistant", "content": [{"type": "think", ...}, {"type": "text", "text": "..."}]}
        """
        import re

        content_parts = []

        for line in output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)

                if isinstance(data, dict):
                    # Kimi format: content is an array of items
                    content_array = data.get("content", [])
                    if isinstance(content_array, list):
                        for item in content_array:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text", "")
                                if text:
                                    content_parts.append(text)
                    # Fallback for simpler formats
                    elif isinstance(content_array, str):
                        content_parts.append(content_array)
                    else:
                        # Try other common fields
                        for field in ["text", "response", "result", "message"]:
                            if data.get(field):
                                content_parts.append(str(data[field]))
                                break
                elif isinstance(data, str):
                    content_parts.append(data)

            except json.JSONDecodeError:
                # Not JSON, might be plain text - strip ANSI codes
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                if clean_line:
                    content_parts.append(clean_line)

        content = "\n".join(content_parts) if content_parts else ""

        # If we got nothing from JSON parsing, fall back to raw output
        if not content:
            content = re.sub(r'\x1b\[[0-9;]*m', '', output).strip()

        return LLMResponse(content=content)

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
        Stream chat completion via Kimi CLI.

        Uses streaming output format for real-time updates.
        """
        kimi_path = self._find_kimi()
        if not kimi_path:
            raise RuntimeError("Kimi CLI not found")

        prompt = self._messages_to_prompt(messages, system)

        cmd = [
            kimi_path,
            "--model", self._model,
            "--output-format", "stream-json",
            "-",  # Read from stdin
        ]

        # Stream output with stdin for prompt
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
                        chunk = data.get("text", "") or data.get("content", "")
                        if chunk:
                            callback(chunk)
                            full_response.append(chunk)
                    except json.JSONDecodeError:
                        callback(line)
                        full_response.append(line)
        finally:
            process.wait()

        return "".join(full_response)

    def set_model(self, model: str) -> None:
        """Set the model to use for requests."""
        self._model = model

    def get_model_info(self) -> dict:
        """Get info about the client."""
        return {
            "available": self.is_available(),
            "model": self.model_name,
            "supports_tools": self.supports_tools,
            "backend": "kimi-cli",
            "features": {
                "context_window": "8K-128K depending on model",
                "cli_auth": True,
                "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            },
        }


# Keep the old class name as an alias for backwards compatibility
KimiClient = KimiCliClient


def create_kimi_client(
    model: str = "moonshot-v1-32k",
    timeout: int = 180,
) -> KimiCliClient:
    """
    Create and validate a Kimi CLI client.

    Args:
        model: Model to use (e.g., 'moonshot-v1-32k')
        timeout: Request timeout in seconds

    Raises:
        RuntimeError if Kimi CLI is not available.
    """
    client = KimiCliClient(model=model, timeout=timeout)

    if not client.is_available():
        raise RuntimeError(
            "Kimi CLI is not available.\n"
            "Install: pip install kimi-cli\n"
            "Then run: kimi (and use /setup to configure)\n"
            "Docs: https://github.com/MoonshotAI/kimi-cli"
        )

    return client
