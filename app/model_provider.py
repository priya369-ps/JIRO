"""Provider-neutral model request and response contracts."""

from dataclasses import dataclass, field
import json
import os
from time import monotonic
from types import MappingProxyType
from typing import Callable, Literal, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.privacy import remove_sensitive_keys


ProviderName = Literal["groq", "byok", "local"]


class ModelProviderError(ValueError):
    """Raised when a model request cannot satisfy the provider contract."""


class ProviderConfigurationError(ModelProviderError):
    """Raised when a provider is not configured for a request."""


class ProviderRequestError(ModelProviderError):
    """Raised when a provider request fails without exposing sensitive data."""


class ProviderRateLimitError(ProviderRequestError):
    """Raised when a provider session exceeds its bounded quota."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("Provider rate limit exceeded; retry later.")


@dataclass(frozen=True)
class ModelConfig:
    """Validated model settings passed to a provider implementation.

    Secret credentials are accepted only as an optional write-only input and are
    excluded from repr and response metadata. Provider implementations must not
    persist or log them.
    """

    provider: ProviderName
    model: str
    endpoint: str | None = None
    options: Mapping[str, object] = field(default_factory=dict)
    api_key: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.provider not in {"groq", "byok", "local"}:
            raise ModelProviderError("Unsupported model provider.")
        if not self.model.strip():
            raise ModelProviderError("Model name cannot be empty.")
        if self.endpoint is not None and not self.endpoint.strip():
            raise ModelProviderError("Model endpoint cannot be blank.")
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))


@dataclass(frozen=True)
class ModelResponse:
    """Provider-neutral generated content and safe diagnostic metadata."""

    content: str
    provider: ProviderName
    model: str
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_status: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise ModelProviderError("Model response content must be text.")
        if not self.provider or not self.model.strip():
            raise ModelProviderError("Model response must identify its provider and model.")
        for field_name in ("input_tokens", "output_tokens"):
            token_count = getattr(self, field_name)
            if token_count is not None and token_count < 0:
                raise ModelProviderError(f"{field_name} cannot be negative.")

    def metadata(self) -> dict[str, object]:
        """Return diagnostics without request configuration or secret values."""
        return {
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "finish_status": self.finish_status,
        }


class ModelProvider(Protocol):
    """Common interface implemented by Groq, BYOK, and local providers."""

    def generate(self, prompt: str, config: ModelConfig) -> ModelResponse:
        ...


def validate_prompt(prompt: str) -> None:
    """Reject empty prompts before provider-specific network code runs."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ModelProviderError("Model prompt cannot be empty.")


Transport = Callable[[str, dict[str, object], dict[str, str]], dict[str, object]]


class SessionRateLimiter:
    """Bound shared-provider calls per caller without persisting resume data."""

    def __init__(self, limit: int = 10, window_seconds: float = 60.0) -> None:
        if limit < 1 or window_seconds <= 0:
            raise ValueError("Rate-limit settings must be positive.")
        self.limit = limit
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = {}

    def check(self, session_id: str) -> None:
        now = monotonic()
        calls = [stamp for stamp in self._calls.get(session_id, []) if now - stamp < self.window_seconds]
        if len(calls) >= self.limit:
            retry_after = int(self.window_seconds - (now - calls[0])) + 1
            raise ProviderRateLimitError(retry_after)
        calls.append(now)
        self._calls[session_id] = calls


def _default_transport(
    endpoint: str,
    payload: dict[str, object],
    headers: dict[str, str],
) -> dict[str, object]:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ProviderRequestError("Model provider request failed.") from error


class OpenAICompatibleProvider:
    """Shared implementation for providers exposing chat completions."""

    provider: ProviderName

    def __init__(self, provider: ProviderName, transport: Transport = _default_transport) -> None:
        self.provider = provider
        self._transport = transport

    def generate(self, prompt: str, config: ModelConfig) -> ModelResponse:
        validate_prompt(prompt)
        if config.provider != self.provider:
            raise ModelProviderError("Model configuration does not match this provider.")
        endpoint = self._endpoint(config)
        headers = self._headers(config)
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            **remove_sensitive_keys(config.options),
        }
        try:
            response = self._transport(endpoint, payload, headers)
        except ProviderRequestError:
            raise
        except (TimeoutError, OSError, ValueError) as error:
            raise ProviderRequestError("Model provider request failed.") from error
        return _response_from_payload(self.provider, config.model, response)

    def _endpoint(self, config: ModelConfig) -> str:
        if not config.endpoint:
            raise ProviderConfigurationError("Model provider endpoint is required.")
        return config.endpoint.rstrip("/") + "/chat/completions"

    def _headers(self, config: ModelConfig) -> dict[str, str]:
        if not config.api_key:
            raise ProviderConfigurationError("Model provider API key is required.")
        return {"Authorization": f"Bearer {config.api_key}"}


class GroqProvider(OpenAICompatibleProvider):
    """Default shared Groq provider using only server-side configuration."""

    def __init__(
        self,
        transport: Transport = _default_transport,
        rate_limiter: SessionRateLimiter | None = None,
    ) -> None:
        super().__init__("groq", transport)
        self.rate_limiter = rate_limiter or SessionRateLimiter()

    def generate(self, prompt: str, config: ModelConfig) -> ModelResponse:
        session_id = str(config.options.get("session_id", "default"))
        self.rate_limiter.check(session_id)
        return super().generate(prompt, config)

    def _endpoint(self, config: ModelConfig) -> str:
        endpoint = config.endpoint or "https://api.groq.com/openai/v1"
        return endpoint.rstrip("/") + "/chat/completions"

    def _headers(self, config: ModelConfig) -> dict[str, str]:
        api_key = config.api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ProviderConfigurationError("GROQ_API_KEY is not configured.")
        return {"Authorization": f"Bearer {api_key}"}


class BYOKProvider(OpenAICompatibleProvider):
    """User-key provider; the key is supplied per request and never stored."""

    def __init__(self, transport: Transport = _default_transport) -> None:
        super().__init__("byok", transport)

    def _endpoint(self, config: ModelConfig) -> str:
        if config.endpoint:
            return super()._endpoint(config)
        provider = config.options.get("upstream_provider")
        endpoints = {
            "groq": "https://api.groq.com/openai/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
        }
        endpoint = endpoints.get(provider)
        if endpoint is None:
            raise ProviderConfigurationError("BYOK provider must specify a supported upstream provider and endpoint.")
        return endpoint + "/chat/completions"


class LocalProvider(OpenAICompatibleProvider):
    """Local Ollama/OpenAI-compatible provider with no shared-key fallback."""

    def __init__(self, transport: Transport = _default_transport) -> None:
        super().__init__("local", transport)

    def _endpoint(self, config: ModelConfig) -> str:
        endpoint = config.endpoint or "http://localhost:11434/v1"
        return endpoint.rstrip("/") + "/chat/completions"

    def _headers(self, config: ModelConfig) -> dict[str, str]:
        return {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}


def _response_from_payload(
    provider: ProviderName,
    model: str,
    payload: dict[str, object],
) -> ModelResponse:
    try:
        choices = payload["choices"]
        message = choices[0]["message"]  # type: ignore[index]
        content = message["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as error:
        raise ProviderRequestError("Model provider returned an invalid response.") from error
    usage = payload.get("usage")
    usage_data = usage if isinstance(usage, dict) else {}
    return ModelResponse(
        content=str(content),
        provider=provider,
        model=model,
        request_id=str(payload["id"]) if payload.get("id") else None,
        input_tokens=usage_data.get("prompt_tokens") if isinstance(usage_data.get("prompt_tokens"), int) else None,
        output_tokens=usage_data.get("completion_tokens") if isinstance(usage_data.get("completion_tokens"), int) else None,
        finish_status=str(choices[0].get("finish_reason")) if choices and isinstance(choices[0], dict) else None,  # type: ignore[index]
    )
