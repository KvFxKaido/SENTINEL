"""
LM Studio client.

LM Studio exposes an OpenAI-compatible API at localhost:1234.
Supports tool calling with compatible models.
"""

import json
import urllib.request
import urllib.error
from typing import Any

from .base import LLMClient, LLMResponse, Message, ToolCall


class LMStudioClient(LLMClient):
    """
    Client for LM Studio's local API.

    LM Studio runs a local server with OpenAI-compatible endpoints.
    Default: http://localhost:1234/v1

    Tool calling support depends on the loaded model.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str | None = None,
        timeout: int = 120,
    ):
        """
        Initialize LM Studio client.

        Args:
            base_url: LM Studio API base URL
            model: Model name (or None to use whatever's loaded)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self._model = model
        self.timeout = timeout
        self._supports_tools: bool | None = None

    @property
    def model_name(self) -> str:
        if self._model:
            return self._model
        # Try to get loaded model from server
        try:
            models = self._get_models()
            if models:
                return models[0]
        except Exception:
            pass
        return "local-model"

    @property
    def supports_tools(self) -> bool:
        """Check if current model supports tools."""
        if self._supports_tools is not None:
            return self._supports_tools

        # Test with a simple tool call
        try:
            response = self._make_request(
                "chat/completions",
                {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "test"}],
                    "tools": [{
                        "type": "function",
                        "function": {
                            "name": "test",
                            "description": "test",
                            "parameters": {"type": "object", "properties": {}},
                        }
                    }],
                    "max_tokens": 1,
                },
            )
            self._supports_tools = True
        except Exception:
            self._supports_tools = False

        return self._supports_tools

    def _get_models(self) -> list[str]:
        """Get list of available models."""
        response = self._make_request("models", method="GET")
        return [m["id"] for m in response.get("data", [])]

    def _make_request(
        self,
        endpoint: str,
        data: dict | None = None,
        method: str = "POST",
    ) -> dict:
        """Make HTTP request to LM Studio API."""
        url = f"{self.base_url}/{endpoint}"

        if method == "GET":
            req = urllib.request.Request(url)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8") if data else None,
                headers={"Content-Type": "application/json"},
                method=method,
            )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot connect to LM Studio at {self.base_url}. "
                f"Make sure LM Studio is running with a model loaded. "
                f"Error: {e}"
            )

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send chat completion request."""

        # Convert messages to OpenAI format
        api_messages = []

        if system:
            api_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg.role == "tool":
                api_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                })
            elif msg.tool_calls:
                api_messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            else:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        # Build request
        request_data = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add tools if supported
        if tools and self.supports_tools:
            request_data["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", t.get("parameters", {})),
                    },
                }
                for t in tools
            ]

        # Make request
        response = self._make_request("chat/completions", request_data)

        # Parse response
        choice = response["choices"][0]
        message = choice["message"]

        tool_calls = []
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                ))

        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def is_available(self) -> bool:
        """Check if LM Studio is running and has a model loaded."""
        try:
            models = self._get_models()
            return len(models) > 0
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List all available models."""
        try:
            return self._get_models()
        except Exception:
            return []

    def set_model(self, model: str) -> None:
        """Set the model to use for requests."""
        self._model = model
        # Reset tool support check for new model
        self._supports_tools = None

    def get_model_info(self) -> dict:
        """Get info about the currently loaded model."""
        try:
            models = self._get_models()
            return {
                "available": True,
                "model": self._model or (models[0] if models else None),
                "all_models": models,
                "supports_tools": self.supports_tools,
            }
        except ConnectionError as e:
            return {
                "available": False,
                "error": str(e),
            }


def create_lmstudio_client(
    base_url: str = "http://localhost:1234/v1",
    model: str | None = None,
) -> LMStudioClient:
    """
    Create and validate an LM Studio client.

    Raises ConnectionError if LM Studio is not available.
    """
    client = LMStudioClient(base_url=base_url, model=model)

    if not client.is_available():
        raise ConnectionError(
            "LM Studio is not running or no model is loaded.\n"
            "1. Open LM Studio\n"
            "2. Load a model (recommend: Mistral, Llama, or Qwen)\n"
            "3. Start the local server (Server tab)\n"
            f"4. Verify it's running at {base_url}"
        )

    return client
