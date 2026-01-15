"""
Mistral Vibe CLI client.

Uses the `vibe` CLI to interact with Mistral AI models.
Supports tool calling through skill-based parsing.

Piggybacks on existing vibe CLI authentication - if you're logged in, it just works.

Install: pip install mistral-vibe
        OR: uv tool install mistral-vibe
        OR: curl -LsSf https://mistral.ai/vibe/install.sh | bash
Docs: https://github.com/mistralai/mistral-vibe
"""

import re
import subprocess
import shutil

from .base import LLMClient, LLMResponse, Message


class MistralVibeClient(LLMClient):
    """
    Client that shells out to Mistral Vibe CLI.

    Vibe CLI provides:
    - Authentication via existing CLI login
    - Access to Mistral models (Codestral, etc.)
    - Agentic coding capabilities

    When tools are requested, uses skill-based parsing (prompt injection + tag parsing).
    """

    def __init__(
        self,
        timeout: int = 180,
        model: str = "codestral-latest",
    ):
        """
        Initialize Mistral Vibe CLI client.

        Args:
            timeout: Request timeout in seconds (longer for complex tasks)
            model: Model to use (codestral-latest, mistral-large-latest, etc.)
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

    def _find_vibe(self) -> str | None:
        """Find the vibe CLI executable."""
        for name in ["vibe", "mistral-vibe"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def is_available(self) -> bool:
        """Check if Vibe CLI is installed and authenticated."""
        if self._available is not None:
            return self._available

        vibe_path = self._find_vibe()
        if not vibe_path:
            self._available = False
            return False

        # Test with a version call
        try:
            result = subprocess.run(
                [vibe_path, "--version"],
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
        Send chat completion via Vibe CLI.

        Uses --prompt flag for non-interactive mode.
        """
        vibe_path = self._find_vibe()
        if not vibe_path:
            raise RuntimeError(
                "Mistral Vibe CLI not found.\n"
                "Install: pip install mistral-vibe\n"
                "     OR: uv tool install mistral-vibe\n"
                "     OR: curl -LsSf https://mistral.ai/vibe/install.sh | bash\n"
                "Docs: https://github.com/mistralai/mistral-vibe"
            )

        # Build the prompt from messages
        prompt = self._messages_to_prompt(messages, system)

        # Build command for non-interactive mode
        # vibe --prompt "text" --auto-approve
        cmd = [
            vibe_path,
            "--prompt", prompt,
            "--auto-approve",  # Don't prompt for tool execution
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
            raise TimeoutError(f"Vibe CLI request timed out after {self.timeout}s")

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Vibe CLI error: {error_msg}")

        # Parse response
        output = result.stdout or ""
        return self._parse_response(output)

    def _parse_response(self, output: str) -> LLMResponse:
        """Parse Vibe CLI output.

        Vibe outputs conversational text, possibly with tool execution logs.
        We extract the final response, stripping ANSI codes and tool logs.
        """
        # Strip ANSI escape codes
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)

        # Strip common tool execution prefixes/markers if present
        # Vibe may show things like "Running command: ..." or "Reading file: ..."
        lines = clean_output.strip().split('\n')
        content_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip obvious tool execution logs (heuristic)
            if any(marker in line.lower() for marker in [
                'running command:',
                'reading file:',
                'writing file:',
                'executing:',
                '>>> ',  # Common prompt marker
            ]):
                continue
            content_lines.append(line)

        content = '\n'.join(content_lines)

        # If we filtered everything out, fall back to raw cleaned output
        if not content.strip():
            content = clean_output.strip()

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

    def set_model(self, model: str) -> None:
        """Set the model to use for requests."""
        self._model = model

    def get_model_info(self) -> dict:
        """Get info about the client."""
        return {
            "available": self.is_available(),
            "model": self.model_name,
            "supports_tools": self.supports_tools,
            "backend": "mistral-vibe",
            "features": {
                "context_window": "32K-128K depending on model",
                "cli_auth": True,
                "models": ["codestral-latest", "mistral-large-latest", "mistral-small-latest"],
                "agentic": True,
            },
        }


def create_mistral_vibe_client(
    model: str = "codestral-latest",
    timeout: int = 180,
) -> MistralVibeClient:
    """
    Create and validate a Mistral Vibe CLI client.

    Args:
        model: Model to use (e.g., 'codestral-latest')
        timeout: Request timeout in seconds

    Raises:
        RuntimeError if Vibe CLI is not available.
    """
    client = MistralVibeClient(model=model, timeout=timeout)

    if not client.is_available():
        raise RuntimeError(
            "Mistral Vibe CLI is not available.\n"
            "Install: pip install mistral-vibe\n"
            "     OR: uv tool install mistral-vibe\n"
            "     OR: curl -LsSf https://mistral.ai/vibe/install.sh | bash\n"
            "Docs: https://github.com/mistralai/mistral-vibe"
        )

    return client
