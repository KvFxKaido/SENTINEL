"""
CLI Wrapper for external LLM tools.

Wraps CLI tools (gemini, codex, etc.) as LLM backends.
These run as subprocesses and capture output.
"""

import subprocess
import shutil
from abc import abstractmethod
from dataclasses import dataclass

from .base import LLMClient, LLMResponse, Message


@dataclass
class CLIResult:
    """Result from CLI invocation."""
    success: bool
    output: str
    error: str | None = None


class CLIWrapperClient(LLMClient):
    """
    Base class for CLI-wrapped LLM backends.

    Subclasses implement the specific command format for each tool.
    """

    cli_name: str = "unknown"

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self._available = self._check_available()

    def _check_available(self) -> bool:
        """Check if the CLI tool is installed."""
        return shutil.which(self.cli_name) is not None

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def model_name(self) -> str:
        return f"{self.cli_name} (CLI)"

    @property
    def supports_tools(self) -> bool:
        # CLI wrappers don't support tool calling
        return False

    @abstractmethod
    def build_command(self, prompt: str) -> list[str]:
        """Build the CLI command to execute."""
        pass

    def invoke(self, prompt: str) -> CLIResult:
        """Invoke the CLI with the given prompt."""
        if not self._available:
            return CLIResult(
                success=False,
                output="",
                error=f"{self.cli_name} CLI not found"
            )

        cmd = self.build_command(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
            )

            if result.returncode == 0:
                return CLIResult(
                    success=True,
                    output=result.stdout.strip(),
                )
            else:
                return CLIResult(
                    success=False,
                    output=result.stdout.strip(),
                    error=result.stderr.strip() or f"Exit code {result.returncode}",
                )

        except subprocess.TimeoutExpired:
            return CLIResult(
                success=False,
                output="",
                error=f"Timeout after {self.timeout}s",
            )
        except Exception as e:
            return CLIResult(
                success=False,
                output="",
                error=str(e),
            )

    def _format_conversation(
        self,
        messages: list[Message],
        system: str | None = None,
    ) -> str:
        """Format conversation history into a single prompt."""
        parts = []

        if system:
            parts.append(f"<system>\n{system}\n</system>\n")

        for msg in messages:
            role = msg.role.upper()
            parts.append(f"<{role}>\n{msg.content}\n</{role}>\n")

        return "\n".join(parts)

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send messages and get response.

        Note: CLI wrappers ignore tools, temperature, and max_tokens
        as these are not supported by external CLI tools.
        """
        prompt = self._format_conversation(messages, system)
        result = self.invoke(prompt)

        if result.success:
            return LLMResponse(content=result.output)
        else:
            return LLMResponse(content=f"[Error: {result.error}]")

    def chat_with_tools(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list | None = None,
        tool_executor: callable = None,
    ) -> str:
        """CLI wrappers don't support tools, just do regular chat."""
        # Ignore tools parameter
        response = self.chat(messages, system)
        return response.content


class GeminiCLI(CLIWrapperClient):
    """Gemini CLI wrapper."""

    cli_name = "gemini"

    def __init__(self, model: str | None = None, timeout: int = 120):
        self.model = model
        super().__init__(timeout=timeout)

    @property
    def model_name(self) -> str:
        if self.model:
            return f"Gemini ({self.model})"
        return "Gemini (CLI)"

    def build_command(self, prompt: str) -> list[str]:
        """Build gemini CLI command."""
        cmd = ["gemini"]
        if self.model:
            cmd.extend(["-m", self.model])
        cmd.append(prompt)
        return cmd


class CodexCLI(CLIWrapperClient):
    """OpenAI Codex CLI wrapper."""

    cli_name = "codex"

    def __init__(self, timeout: int = 120):
        super().__init__(timeout=timeout)

    def build_command(self, prompt: str) -> list[str]:
        """Build codex CLI command."""
        # Use 'exec' subcommand for non-interactive mode
        return ["codex", "exec", prompt]


# Factory function
def create_cli_client(name: str, **kwargs) -> CLIWrapperClient | None:
    """Create a CLI client by name."""
    clients = {
        "gemini": GeminiCLI,
        "codex": CodexCLI,
    }

    client_class = clients.get(name.lower())
    if client_class:
        client = client_class(**kwargs)
        if client.is_available:
            return client

    return None


def list_available_cli_backends() -> list[str]:
    """List which CLI backends are available."""
    available = []
    for name in ["gemini", "codex"]:
        if shutil.which(name):
            available.append(name)
    return available
