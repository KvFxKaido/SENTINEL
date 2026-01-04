"""LLM backend clients for SENTINEL agent."""

from .base import LLMClient, Message, ToolCall, ToolResult
from .lmstudio import LMStudioClient
from .cli_wrapper import GeminiCLI, CodexCLI, CLIWrapperClient

__all__ = [
    "LLMClient",
    "Message",
    "ToolCall",
    "ToolResult",
    "LMStudioClient",
    "GeminiCLI",
    "CodexCLI",
    "CLIWrapperClient",
]

# Optional Claude client
try:
    from .claude import ClaudeClient
    __all__.append("ClaudeClient")
except ImportError:
    pass

# Optional OpenRouter client
try:
    from .openrouter import OpenRouterClient
    __all__.append("OpenRouterClient")
except ImportError:
    pass
