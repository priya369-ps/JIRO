"""Non-secret runtime configuration for the JIRO application."""

from dataclasses import dataclass
import os
from typing import Final, Literal


ConfigurationProvider = Literal["groq", "byok", "local"]
DEFAULT_GROQ_MODEL: Final = "openai/gpt-oss-120b"
DEFAULT_OLLAMA_ENDPOINT: Final = "http://localhost:11434"
DEFAULT_PROVIDER_TIMEOUT_SECONDS: Final = 30.0


class ConfigurationError(ValueError):
    """Raised when an environment setting is invalid."""


@dataclass(frozen=True)
class Settings:
    """Validated non-secret settings safe to expose as operational metadata."""

    default_provider: ConfigurationProvider
    groq_model: str
    ollama_endpoint: str
    provider_timeout_seconds: float

    @property
    def default_model(self) -> str:
        return self.groq_model if self.default_provider == "groq" else ""

    def public_metadata(self) -> dict[str, object]:
        """Return configuration status without credentials or source content."""
        return {
            "default_provider": self.default_provider,
            "default_model": self.default_model,
            "ollama_endpoint": self.ollama_endpoint,
            "provider_timeout_seconds": self.provider_timeout_seconds,
            "privacy_mode": "ephemeral",
        }


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Load and validate configuration without reading or storing API keys."""
    values = os.environ if environ is None else environ
    provider = values.get("JIRO_DEFAULT_PROVIDER", "groq").strip().lower()
    if provider not in {"groq", "byok", "local"}:
        raise ConfigurationError("JIRO_DEFAULT_PROVIDER must be groq, byok, or local.")

    groq_model = values.get("JIRO_GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()
    if not groq_model:
        raise ConfigurationError("JIRO_GROQ_MODEL cannot be empty.")

    ollama_endpoint = values.get("JIRO_OLLAMA_ENDPOINT", DEFAULT_OLLAMA_ENDPOINT).strip()
    if not ollama_endpoint.startswith(("http://", "https://")):
        raise ConfigurationError("JIRO_OLLAMA_ENDPOINT must be an HTTP URL.")

    timeout_value = values.get(
        "JIRO_PROVIDER_TIMEOUT_SECONDS",
        str(DEFAULT_PROVIDER_TIMEOUT_SECONDS),
    )
    try:
        timeout = float(timeout_value)
    except ValueError as error:
        raise ConfigurationError("JIRO_PROVIDER_TIMEOUT_SECONDS must be a number.") from error
    if timeout <= 0:
        raise ConfigurationError("JIRO_PROVIDER_TIMEOUT_SECONDS must be positive.")

    return Settings(
        default_provider=provider,  # type: ignore[arg-type]
        groq_model=groq_model,
        ollama_endpoint=ollama_endpoint,
        provider_timeout_seconds=min(timeout, 120.0),
    )
