"""
LM Studio client.

LM Studio exposes an OpenAI-compatible API at localhost:1234.
Supports tool calling with compatible models.
"""

import json
import os
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse, urlunparse
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
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str | None = None,
        timeout: int = 120,
        api_key: str | None = None,
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
        self._api_key = api_key

    def _candidate_base_urls(self) -> list[str]:
        """Return OpenAI-compatible API root candidates (hosts + `/v1`).

        Notes:
        - Sentinel expects OpenAI-compatible endpoints (`/models`, `/chat/completions`).
        - We intentionally do not probe LM Studio's non-OpenAI endpoints here; if you
          need a custom path, set `LMSTUDIO_BASE_URL` explicitly.
        """
        parsed = urlparse(self.base_url)
        scheme = parsed.scheme or "http"
        hostname = parsed.hostname or "127.0.0.1"
        port = parsed.port
        path = (parsed.path or "").rstrip("/")

        host_candidates = [hostname]
        if hostname in ("localhost", "127.0.0.1", "::1"):
            host_candidates.extend(["localhost", "127.0.0.1", "::1"])

        # Path fallback: LM Studio's OpenAI-compatible API root is `/v1`.
        def base_path_without(suffix: str) -> str:
            return path[: -len(suffix)] if path.endswith(suffix) else path

        base = base_path_without("/v1")
        # Prefer `/v1` first since some servers return a 200+error JSON for other roots.
        path_candidates = [f"{base}/v1", path, base]

        def netloc_for(host: str) -> str:
            host_part = f"[{host}]" if ":" in host and not host.startswith("[") else host
            return f"{host_part}:{port}" if port is not None else host_part

        candidates: list[str] = [self.base_url]
        for host in host_candidates:
            for candidate_path in path_candidates:
                candidates.append(
                    urlunparse((scheme, netloc_for(host), candidate_path, "", "", "")).rstrip("/")
                )
        return list(dict.fromkeys(candidates))

    def _make_headers(self, *, include_auth: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if not include_auth:
            return headers

        api_key = self._api_key or os.environ.get("LMSTUDIO_API_KEY")
        if not api_key:
            api_key = "lm-studio"
        headers["Authorization"] = f"Bearer {api_key}"
        return headers

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
        if not isinstance(response, dict):
            return []
        data = response.get("data", [])
        if not isinstance(data, list):
            return []
        models: list[str] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id:
                models.append(model_id)
        return models

    def _extract_error_message(self, response: object) -> str:
        if not isinstance(response, dict):
            return f"Unexpected LM Studio response type: {type(response).__name__}"

        err = response.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("error") or err.get("detail")
            if isinstance(msg, str) and msg:
                return msg
            return json.dumps(err)
        if isinstance(err, str) and err:
            return err

        msg = response.get("message")
        if isinstance(msg, str) and msg:
            return msg

        return f"Unexpected LM Studio response (missing 'choices'): keys={list(response.keys())}"

    def _make_request(
        self,
        endpoint: str,
        data: dict | None = None,
        method: str = "POST",
    ) -> dict:
        """Make HTTP request to LM Studio API."""
        def looks_like_success(payload: object) -> bool:
            if not isinstance(payload, dict):
                return False
            if endpoint == "models":
                # OpenAI-compatible: {"data": [...], "object": "list"}
                return isinstance(payload.get("data"), list)
            if endpoint == "chat/completions":
                # OpenAI-compatible: {"choices": [...], ...}
                return isinstance(payload.get("choices"), list)
            return True

        last_error: Exception | None = None
        tried_urls: list[str] = []
        for candidate_base_url in self._candidate_base_urls():
            url = f"{candidate_base_url}/{endpoint}"
            tried_urls.append(url)

            def request_with_auth(include_auth: bool) -> dict:
                if method == "GET":
                    req = urllib.request.Request(url, headers=self._make_headers(include_auth=include_auth))
                else:
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(data).encode("utf-8") if data else None,
                        headers=self._make_headers(include_auth=include_auth),
                        method=method,
                    )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            def request_with_retries(*, include_auth: bool) -> dict:
                # LM Studio can briefly refuse connections when the server (re)starts.
                attempts = 8
                for attempt in range(1, attempts + 1):
                    try:
                        return request_with_auth(include_auth=include_auth)
                    except urllib.error.URLError as e:
                        last = str(getattr(e, "reason", e))
                        # Windows connection refused is typically WinError 10061
                        if "10061" in last and attempt < attempts:
                            # Back off up to ~6s total across retries.
                            time.sleep(min(0.25 * (2 ** (attempt - 1)), 1.5))
                            continue
                        raise

            try:
                response = request_with_retries(include_auth=False)
                if not looks_like_success(response):
                    last_error = RuntimeError(self._extract_error_message(response))
                    continue
                self.base_url = candidate_base_url.rstrip("/")
                return response
            except urllib.error.HTTPError as e:
                # Retry with auth only if the server explicitly denies us.
                if e.code in (401, 403):
                    try:
                        response = request_with_retries(include_auth=True)
                        if not looks_like_success(response):
                            last_error = RuntimeError(self._extract_error_message(response))
                            continue
                        self.base_url = candidate_base_url.rstrip("/")
                        return response
                    except Exception as e2:
                        last_error = e2
                        continue
                last_error = e
                continue
            except urllib.error.URLError as e:
                last_error = e
                continue

        raise ConnectionError(
            f"Cannot connect to LM Studio at {self.base_url}. "
            f"Make sure LM Studio is running with a model loaded. "
            f"Error: {last_error}\n"
            f"Tried: {', '.join(tried_urls[:4])}{'...' if len(tried_urls) > 4 else ''}"
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
            "stream": False,
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
        if not isinstance(response, dict) or "choices" not in response:
            raise RuntimeError(self._extract_error_message(response))

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

    def is_available(self, timeout: float = 1.0) -> bool:
        """Check if LM Studio is running and has a model loaded.

        Uses a short timeout for fast availability detection during startup.

        Args:
            timeout: Connection timeout in seconds (default 1.0 for fast checks)
        """
        # Quick connection test - only try the configured URL
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, headers=self._make_headers(include_auth=False))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                return isinstance(models, list) and len(models) > 0
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
    base_url: str = "http://127.0.0.1:1234/v1",
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
