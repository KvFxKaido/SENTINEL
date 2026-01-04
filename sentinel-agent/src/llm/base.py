"""
Base LLM client abstraction.

Defines the interface that all backends must implement.
Adapted from Sovwren's multi-backend pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class Message:
    """A message in the conversation."""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list["ToolCall"] = field(default_factory=list)
    tool_call_id: str | None = None  # For tool results


@dataclass
class ToolCall:
    """A tool call from the assistant."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_call_id: str
    content: str  # JSON string


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMClient(ABC):
    """
    Abstract base class for LLM backends.

    All backends must implement:
    - chat(): Send messages and get a response
    - supports_tools: Whether the backend supports tool calling
    """

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this backend supports native tool calling."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages: Conversation history
            system: System prompt
            tools: Tool definitions (if supported)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            LLMResponse with content and optional tool calls
        """
        pass

    def chat_with_tools(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        tool_executor: callable = None,
        max_iterations: int = 5,
        **kwargs,
    ) -> str:
        """
        Chat with automatic tool execution loop.

        For backends that support tools natively, this handles
        the back-and-forth of tool calls and results.

        For backends without tool support, tools are injected
        into the prompt and responses are parsed.

        Args:
            messages: Conversation history
            system: System prompt
            tools: Tool definitions
            tool_executor: Function(name, args) -> result dict
            max_iterations: Max tool call rounds

        Returns:
            Final text response
        """
        if not self.supports_tools or not tools:
            # Simple path: no tools
            response = self.chat(messages, system=system, **kwargs)
            return response.content

        current_messages = list(messages)

        for _ in range(max_iterations):
            response = self.chat(
                current_messages,
                system=system,
                tools=tools,
                **kwargs,
            )

            if not response.has_tool_calls:
                return response.content

            # Add assistant message with tool calls
            current_messages.append(Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            ))

            # Execute tools and add results
            for tool_call in response.tool_calls:
                if tool_executor:
                    result = tool_executor(tool_call.name, tool_call.arguments)
                else:
                    result = {"error": "No tool executor provided"}

                import json
                current_messages.append(Message(
                    role="tool",
                    content=json.dumps(result),
                    tool_call_id=tool_call.id,
                ))

        # Hit max iterations
        return response.content
