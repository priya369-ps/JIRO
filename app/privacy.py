"""Privacy boundaries for sensitive resume and job-description data."""

from collections.abc import Mapping
import re
from typing import Final


MAX_FILENAME_LENGTH: Final = 255
_SECRET_KEY_PATTERN: Final = re.compile(
    r"(?:api[_-]?key|authorization|password|secret|token|credential)",
    re.IGNORECASE,
)
_CONTROL_CHARACTER_PATTERN: Final = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_FILENAME_PATTERN: Final = re.compile(r"[\\/]")


class PrivacyError(ValueError):
    """Raised when input or diagnostic data violates privacy boundaries."""


def sanitize_filename(filename: str) -> str:
    """Accept a single safe filename without paths or control characters."""
    if not isinstance(filename, str) or not filename.strip():
        raise PrivacyError("Filename must be a non-empty file name without a path.")
    if len(filename) > MAX_FILENAME_LENGTH:
        raise PrivacyError("Filename is too long.")
    if _UNSAFE_FILENAME_PATTERN.search(filename):
        raise PrivacyError("Filename must be a non-empty file name without a path.")
    if _CONTROL_CHARACTER_PATTERN.search(filename):
        raise PrivacyError("Filename contains unsafe characters.")
    if filename in {".", ".."} or filename.startswith("."):
        raise PrivacyError("Hidden or traversal filenames are not allowed.")
    return filename


def redact_mapping(values: Mapping[str, object]) -> dict[str, object]:
    """Remove secret-like values before diagnostics or provider payload reuse."""
    return {
        key: "[REDACTED]" if _SECRET_KEY_PATTERN.search(key) else value
        for key, value in values.items()
    }


def remove_sensitive_keys(values: Mapping[str, object]) -> dict[str, object]:
    """Remove secret-like options before sending a request to a provider."""
    return {
        key: value
        for key, value in values.items()
        if not _SECRET_KEY_PATTERN.search(key)
    }


def ensure_text_input(value: object, *, label: str) -> str:
    """Validate text while keeping content out of exception messages."""
    if not isinstance(value, str):
        raise PrivacyError(f"{label} must be text.")
    if not value.strip():
        raise PrivacyError(f"{label} cannot be empty.")
    return value
