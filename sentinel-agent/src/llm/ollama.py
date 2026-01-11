"""
Ollama client.

Ollama exposes an OpenAI-compatible API at localhost:11434.
Supports tool calling with compatible models.
"""

import json
import urllib.request
import urllib.error
from urllib.parse import urlparse, urlunparse
from typing import Any

from .base import LLMClient, LLMResponse, Message, ToolCall


class OllamaClient(LLMClient):
    """
    Client for Ollama's local API.

    Ollama runs a local server with OpenAI-compatible endpoints.
    Default: http://localhost:11434/v1

    Tool calling support depends on the loaded model.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        model: str | None = None,
        timeout: int = 120,
    ):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama API base URL
            model: Model name (e.g., "llama3.2", "mistral", "qwen2.5")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self._model = model
        self.timeout = timeout
        self._supports_tools: bool | None = None

    def _candidate_base_urls(self) -> list[str]:
        """Return base URL candidates (handles common localhost/IPv6 issues on Windows)."""
        parsed = urlparse(self.base_url)
        scheme = parsed.scheme or "http"
        hostname = parsed.hostname or "127.0.0.1"
        port = parsed.port
        path = parsed.path or ""

        host_candidates = [hostname]
        if hostname in ("localhost", "127.0.0.1", "::1"):
            host_candidates.extend(["localhost", "127.0.0.1", "::1"])

        def netloc_for(host: str) -> str:
            host_part = f"[{host}]" if ":" in host and not host.startswith("[") else host
            return f"{host_part}:{port}" if port is not None else host_part

        candidates = [
            urlunparse((scheme, netloc_for(host), path, "", "", "")).rstrip("/")
            for host in host_candidates
        ]
        candidates.insert(0, self.base_url)
        return list(dict.fromkeys(candidates))

    @property
    def model_name(self) -> str:
        if self._model:
            return self._model
        # Try to get first available model
        try:
            models = self._get_models()
            if models:
                return models[0]
        except Exception:
            pass
        return "ollama-model"

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
        """Make HTTP request to Ollama API."""
        last_error: Exception | None = None
        for candidate_base_url in self._candidate_base_urls():
            url = f"{candidate_base_url}/{endpoint}"

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
                    self.base_url = candidate_base_url.rstrip("/")
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                last_error = e
                continue

        raise ConnectionError(
            f"Cannot connect to Ollama at {self.base_url}. "
            f"Make sure Ollama is running. "
            f"Error: {last_error}"
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
        # Note: Ollama's OpenAI-compatible API has issues with max_tokens
        # causing empty responses on some models, so we omit it
        request_data = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature,
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
        """Check if Ollama is running and has models available."""
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


def create_ollama_client(
    base_url: str = "http://localhost:11434/v1",
    model: str | None = None,
) -> OllamaClient:
    """
    Create and validate an Ollama client.

    Raises ConnectionError if Ollama is not available.
    """
    client = OllamaClient(base_url=base_url, model=model)

    if not client.is_available():
        raise ConnectionError(
            "Ollama is not running or no models are available.\n"
            "1. Install Ollama: https://ollama.ai\n"
            "2. Pull a model: ollama pull llama3.2\n"
            "3. Ollama runs automatically after install\n"
            f"4. Verify it's running at {base_url}"
        )

    return client
