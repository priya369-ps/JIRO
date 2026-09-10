"""Provider-neutral model request and response contracts."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping, Protocol


ProviderName = Literal["groq", "byok", "local"]


class ModelProviderError(ValueError):
    """Raised when a model request cannot satisfy the provider contract."""


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
