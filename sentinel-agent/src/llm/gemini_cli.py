"""
Gemini CLI client.

Uses the `gemini` CLI to make API calls with Gemini 2.5 Pro.
Supports native tool calling through MCP integration.

Free tier: 60 requests/min, 1000/day with 1M token context.
"""

import json
import subprocess
import shutil
from typing import Any

from .base import LLMClient, LLMResponse, Message, ToolCall


class GeminiCliClient(LLMClient):
    """
    Client that shells out to Gemini CLI.

    Gemini CLI provides:
    - Native MCP tool support (can use sentinel-campaign server)
    - 1M token context window
    - Free tier (60 req/min, 1000/day)

    When tools are requested, runs in --yolo mode for autonomous operation.
    """

    def __init__(
        self,
        timeout: int = 180,
        yolo: bool = True,
        sandbox: bool = False,
    ):
        """
        Initialize Gemini CLI client.

        Args:
            timeout: Request timeout in seconds (longer for complex tasks)
            yolo: Auto-approve tool execution (recommended for GM use)
            sandbox: Run in sandbox mode (safer but more limited)
        """
        self.timeout = timeout
        self.yolo = yolo
        self.sandbox = sandbox
        self._available: bool | None = None

    @property
    def model_name(self) -> str:
        return "gemini-2.5-pro"

    @property
    def supports_tools(self) -> bool:
        # Gemini CLI supports tools natively through MCP
        # However, we'll use skill-based fallback for SENTINEL's tool format
        # Set to True if you want to use MCP-based tools
        return False

    def _find_gemini(self) -> str | None:
        """Find the gemini CLI executable."""
        return shutil.which("gemini")

    def is_available(self) -> bool:
        """Check if Gemini CLI is installed."""
        if self._available is not None:
            return self._available

        gemini_path = self._find_gemini()
        if not gemini_path:
            self._available = False
            return False

        # Test with a version call
        try:
            result = subprocess.run(
                [gemini_path, "--version"],
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
        Send chat completion via Gemini CLI.

        Uses stdin for the prompt to handle large contexts.
        Returns JSON output for structured parsing.
        """
        gemini_path = self._find_gemini()
        if not gemini_path:
            raise RuntimeError(
                "Gemini CLI not found. Install from https://github.com/google-gemini/gemini-cli"
            )

        # Build the prompt from messages
        prompt = self._messages_to_prompt(messages, system)

        # Build command
        cmd = [
            gemini_path,
            "--output-format", "json",
        ]

        # Add yolo mode for autonomous tool use
        if self.yolo:
            cmd.append("--yolo")

        if self.sandbox:
            cmd.append("--sandbox")

        # Use stdin for prompt to avoid Windows command line length limits
        # Windows has ~8191 char limit; SENTINEL prompts can be 10K+ chars
        cmd.append("-")  # Tell gemini to read from stdin

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
            raise TimeoutError(f"Gemini CLI request timed out after {self.timeout}s")

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Gemini CLI error: {error_msg}")

        # Parse JSON response
        return self._parse_response(result.stdout)

    def _parse_response(self, output: str) -> LLMResponse:
        """Parse Gemini CLI JSON output."""
        try:
            # Gemini CLI outputs JSON with the response
            data = json.loads(output)

            # The response structure may vary - try common fields
            content = ""
            if isinstance(data, dict):
                # Try various possible response fields
                content = (
                    data.get("response", "") or
                    data.get("result", "") or
                    data.get("content", "") or
                    data.get("text", "") or
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
        Stream chat completion via Gemini CLI.

        Uses stream-json output format for real-time updates.
        """
        gemini_path = self._find_gemini()
        if not gemini_path:
            raise RuntimeError("Gemini CLI not found")

        prompt = self._messages_to_prompt(messages, system)

        cmd = [
            gemini_path,
            "--output-format", "stream-json",
            "-",  # Read from stdin
        ]

        if self.yolo:
            cmd.append("--yolo")

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

    def get_model_info(self) -> dict:
        """Get info about the client."""
        return {
            "available": self.is_available(),
            "model": self.model_name,
            "supports_tools": self.supports_tools,
            "backend": "gemini-cli",
            "features": {
                "context_window": "1M tokens",
                "mcp_support": True,
                "free_tier": "60 req/min, 1000/day",
            },
        }


def create_gemini_cli_client(
    yolo: bool = True,
    timeout: int = 180,
) -> GeminiCliClient:
    """
    Create and validate a Gemini CLI client.

    Args:
        yolo: Auto-approve tool execution
        timeout: Request timeout in seconds

    Raises:
        RuntimeError if Gemini CLI is not available.
    """
    client = GeminiCliClient(yolo=yolo, timeout=timeout)

    if not client.is_available():
        raise RuntimeError(
            "Gemini CLI is not available.\n"
            "Install: npm install -g @google/gemini-cli\n"
            "Or: https://github.com/google-gemini/gemini-cli"
        )

    return client
