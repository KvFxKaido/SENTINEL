"""LLM backend clients for SENTINEL agent."""

import os
from typing import Callable, Literal

from .base import LLMClient, LLMResponse, Message, ToolCall, ToolResult
from .lmstudio import LMStudioClient
from .ollama import OllamaClient
from .kimi import KimiClient, KimiCliClient
from .claude_code import ClaudeCodeClient
from .gemini_cli import GeminiCliClient
from .codex_cli import CodexCliClient
from .mistral_vibe import MistralVibeClient
from .skills import parse_skills, format_tools_for_prompt, strip_skill_tags

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Message",
    "ToolCall",
    "ToolResult",
    "LMStudioClient",
    "OllamaClient",
    "KimiClient",
    "KimiCliClient",
    "ClaudeCodeClient",
    "GeminiCliClient",
    "CodexCliClient",
    "MistralVibeClient",
    "MockLLMClient",
    "create_llm_client",
    "detect_backend",
    # Backend categories
    "CLI_BACKENDS",
    "LOCAL_BACKENDS",
    # Skill system
    "parse_skills",
    "format_tools_for_prompt",
    "strip_skill_tags",
]


# -----------------------------------------------------------------------------
# Mock Client for Testing
# -----------------------------------------------------------------------------

class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing.

    Allows configuring responses without actual API calls.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        model_name: str = "mock-model",
    ):
        """
        Initialize mock client.

        Args:
            responses: List of responses to return in order.
                       Cycles through if more calls than responses.
            model_name: Name to report as model_name property.
        """
        self._responses = responses or ["Mock response"]
        self._call_count = 0
        self._model_name = model_name
        self.calls: list[dict] = []  # Record of all calls made

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def supports_tools(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Return next mock response."""
        self.calls.append({
            "method": "chat",
            "messages": messages,
            "system": system,
            "tools": tools,
        })
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return LLMResponse(content=response_text)

    def chat_with_tools(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        tool_executor: Callable[[str, dict], dict] | None = None,
    ) -> str:
        """Return next mock response (no tool execution)."""
        self.calls.append({
            "method": "chat_with_tools",
            "messages": messages,
            "system": system,
            "tools": tools,
        })
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return response

    def set_responses(self, responses: list[str]) -> None:
        """Update the list of responses."""
        self._responses = responses
        self._call_count = 0

    def reset(self) -> None:
        """Reset call count and recorded calls."""
        self._call_count = 0
        self.calls.clear()


# -----------------------------------------------------------------------------
# Backend Detection and Factory
# -----------------------------------------------------------------------------

BackendType = Literal["lmstudio", "ollama", "kimi", "claude", "gemini", "codex", "vibe", "auto"]

# CLI-based backends with massive context windows (no meaningful pressure tracking)
# These use existing CLI authentication and have 100K+ token context
CLI_BACKENDS = frozenset({"claude", "gemini", "codex", "kimi", "vibe"})

# Local backends with finite context (pressure tracking relevant)
LOCAL_BACKENDS = frozenset({"lmstudio", "ollama"})


def detect_backend(
    lmstudio_url: str = "http://127.0.0.1:1234/v1",
    ollama_url: str = "http://127.0.0.1:11434/v1",
) -> tuple[str, LLMClient] | tuple[None, None]:
    """
    Auto-detect available LLM backend.

    Preference order: LM Studio > Ollama > Kimi CLI > Gemini CLI > Codex CLI > Claude Code

    Local backends are preferred over cloud for privacy and cost.
    API-based backends require authentication but have large context windows.
    CLI backends use existing CLI authentication.

    Returns:
        Tuple of (backend_name, client) or (None, None) if nothing available.
    """
    lmstudio_url = os.environ.get("LMSTUDIO_BASE_URL", lmstudio_url)
    ollama_url = os.environ.get("OLLAMA_BASE_URL", ollama_url)

    # Try LM Studio first (free, local)
    try:
        client = LMStudioClient(base_url=lmstudio_url)
        if client.is_available():
            return ("lmstudio", client)
    except Exception:
        pass

    # Try Ollama (free, local)
    try:
        client = OllamaClient(base_url=ollama_url)
        if client.is_available():
            return ("ollama", client)
    except Exception:
        pass

    # Try Kimi CLI (uses existing CLI auth, large context)
    try:
        client = KimiClient()
        if client.is_available():
            return ("kimi", client)
    except Exception:
        pass

    # Try Gemini CLI (free tier, 1M context)
    try:
        client = GeminiCliClient()
        if client.is_available():
            return ("gemini", client)
    except Exception:
        pass

    # Try Codex CLI (OpenAI's agentic CLI)
    try:
        client = CodexCliClient()
        if client.is_available():
            return ("codex", client)
    except Exception:
        pass

    # Try Claude Code CLI (uses existing auth)
    try:
        client = ClaudeCodeClient()
        if client.is_available():
            return ("claude", client)
    except Exception:
        pass

    # Try Mistral Vibe CLI (uses existing auth)
    try:
        client = MistralVibeClient()
        if client.is_available():
            return ("vibe", client)
    except Exception:
        pass

    return (None, None)


def create_llm_client(
    backend: BackendType = "auto",
    lmstudio_url: str = "http://127.0.0.1:1234/v1",
    ollama_url: str = "http://127.0.0.1:11434/v1",
) -> tuple[str, LLMClient | None]:
    """
    Create an LLM client for the specified backend.

    Args:
        backend: Backend to use ("auto" for auto-detection)
        lmstudio_url: URL for LM Studio server
        ollama_url: URL for Ollama server

    Returns:
        Tuple of (backend_name, client). Client may be None if unavailable.
    """
    lmstudio_url = os.environ.get("LMSTUDIO_BASE_URL", lmstudio_url)
    ollama_url = os.environ.get("OLLAMA_BASE_URL", ollama_url)

    if backend == "auto":
        name, client = detect_backend(lmstudio_url, ollama_url)
        return (name or "none", client)

    if backend == "lmstudio":
        try:
            from .lmstudio import create_lmstudio_client
            return ("lmstudio", create_lmstudio_client(base_url=lmstudio_url))
        except Exception as e:
            print(f"LM Studio error: {e}")
            return ("lmstudio", None)

    if backend == "ollama":
        try:
            from .ollama import create_ollama_client
            return ("ollama", create_ollama_client(base_url=ollama_url))
        except Exception as e:
            print(f"Ollama error: {e}")
            return ("ollama", None)

    if backend == "kimi":
        try:
            from .kimi import create_kimi_client
            return ("kimi", create_kimi_client())
        except Exception as e:
            print(f"Kimi CLI error: {e}")
            return ("kimi", None)

    if backend == "claude":
        try:
            from .claude_code import create_claude_code_client
            return ("claude", create_claude_code_client())
        except Exception as e:
            print(f"Claude Code error: {e}")
            return ("claude", None)

    if backend == "gemini":
        try:
            from .gemini_cli import create_gemini_cli_client
            return ("gemini", create_gemini_cli_client())
        except Exception as e:
            print(f"Gemini CLI error: {e}")
            return ("gemini", None)

    if backend == "codex":
        try:
            from .codex_cli import create_codex_cli_client
            return ("codex", create_codex_cli_client())
        except Exception as e:
            print(f"Codex CLI error: {e}")
            return ("codex", None)

    if backend == "vibe":
        try:
            from .mistral_vibe import create_mistral_vibe_client
            return ("vibe", create_mistral_vibe_client())
        except Exception as e:
            print(f"Mistral Vibe error: {e}")
            return ("vibe", None)

    print(f"Unknown backend: {backend}")
    return (backend, None)
