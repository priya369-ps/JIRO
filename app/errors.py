"""Safe API error mapping without exposing sensitive request content."""

from dataclasses import dataclass
from typing import Literal

from app.schemas import SafeError


ErrorCategory = Literal["input", "configuration", "provider", "validation", "export", "unknown"]


@dataclass(frozen=True)
class PublicError:
    status_code: int
    payload: SafeError


def public_error(category: ErrorCategory, detail: str) -> PublicError:
    """Map an already-safe detail into a stable user-facing error shape."""
    statuses = {
        "input": 400,
        "configuration": 503,
        "provider": 502,
        "validation": 422,
        "export": 422,
        "unknown": 500,
    }
    return PublicError(statuses[category], SafeError(detail=detail, category=category))
