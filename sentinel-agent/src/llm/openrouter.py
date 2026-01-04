"""
OpenRouter client.

OpenRouter provides access to many LLM models through a unified API.
Uses OpenAI-compatible format.
https://openrouter.ai/docs
"""

import json
import os
import urllib.request
import urllib.error
from typing import Any

from .base import LLMClient, LLMResponse, Message, ToolCall


# Popular models on OpenRouter
OPENROUTER_MODELS = {
    # Anthropic
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-haiku": "anthropic/claude-3-haiku",
    # OpenAI
    "gpt-4o": "openai/gpt-4o",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    # Google
    "gemini-pro": "google/gemini-pro",
    "gemini-pro-1.5": "google/gemini-pro-1.5",
    # Meta
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
    # Mistral
    "mistral-large": "mistralai/mistral-large",
    "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
    # Free tier
    "llama-3.1-8b-free": "meta-llama/llama-3.1-8b-instruct:free",
    "gemma-7b-free": "google/gemma-7b-it:free",
}


class OpenRouterClient(LLMClient):
    """
    Client for OpenRouter API.

    OpenRouter provides unified access to models from multiple providers.
    Requires OPENROUTER_API_KEY environment variable.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3.5-sonnet",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 120,
        site_url: str | None = None,  # For rankings
        site_name: str | None = None,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (or use OPENROUTER_API_KEY env var)
            model: Model name (short name or full provider/model path)
            base_url: OpenRouter API base URL
            timeout: Request timeout in seconds
            site_url: Your site URL (for leaderboard attribution)
            site_name: Your site name (for leaderboard attribution)
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = base_url.rstrip("/")
        self._model = self._resolve_model(model)
        self.timeout = timeout
        self.site_url = site_url
        self.site_name = site_name or "SENTINEL TTRPG"
        self._supports_tools: bool | None = None

    def _resolve_model(self, model: str) -> str:
        """Resolve short model name to full path."""
        if "/" in model:
            return model  # Already full path
        return OPENROUTER_MODELS.get(model, model)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supports_tools(self) -> bool:
        """Check if current model supports tools."""
        # Most OpenRouter models support tools
        # Could do a test call, but for now assume yes for major models
        if self._supports_tools is not None:
            return self._supports_tools

        # Models known to support tools
        tool_models = [
            "claude", "gpt-4", "gpt-3.5", "mistral",
            "llama-3.1", "gemini"
        ]
        self._supports_tools = any(m in self._model.lower() for m in tool_models)
        return self._supports_tools

    def _make_request(
        self,
        endpoint: str,
        data: dict | None = None,
        method: str = "POST",
    ) -> dict:
        """Make HTTP request to OpenRouter API."""
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not set. "
                "Set OPENROUTER_API_KEY environment variable or pass api_key."
            )

        url = f"{self.base_url}/{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url or "https://github.com/SENTINEL",
            "X-Title": self.site_name,
        }

        if method == "GET":
            req = urllib.request.Request(url, headers=headers)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8") if data else None,
                headers=headers,
                method=method,
            )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise ConnectionError(
                f"OpenRouter API error {e.code}: {error_body}"
            )
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot connect to OpenRouter: {e}")

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
            "model": self._model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add tools if provided
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
        """Check if OpenRouter is accessible."""
        if not self.api_key:
            return False
        try:
            # Simple validation - check if we can reach the API
            self._make_request("models", method="GET")
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            response = self._make_request("models", method="GET")
            return [m["id"] for m in response.get("data", [])]
        except Exception:
            # Return known models as fallback
            return list(OPENROUTER_MODELS.values())

    def set_model(self, model: str) -> None:
        """Set the model to use for requests."""
        self._model = self._resolve_model(model)
        self._supports_tools = None  # Reset tool check

    def get_credits(self) -> dict | None:
        """Get current credits/usage info."""
        try:
            response = self._make_request("auth/key", method="GET")
            return response.get("data", {})
        except Exception:
            return None


def create_openrouter_client(
    api_key: str | None = None,
    model: str = "claude-3.5-sonnet",
) -> OpenRouterClient:
    """Create and validate an OpenRouter client."""
    client = OpenRouterClient(api_key=api_key, model=model)

    if not client.api_key:
        raise ValueError(
            "OpenRouter API key required.\n"
            "Set OPENROUTER_API_KEY environment variable or pass api_key.\n"
            "Get a key at: https://openrouter.ai/keys"
        )

    return client
