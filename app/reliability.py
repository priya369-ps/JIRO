"""Bounded HTTP reliability controls for the JIRO API."""

import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send


MAX_REQUEST_BODY_BYTES = 6 * 1024 * 1024
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def cors_origins() -> list[str]:
    """Return explicitly configured origins without enabling a wildcard."""
    configured = os.getenv("JIRO_CORS_ORIGINS", "")
    if not configured.strip():
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


class RequestSizeLimitMiddleware:
    """Reject oversized HTTP bodies before application handlers process them."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        if max_bytes < 1:
            raise ValueError("Request size limit must be positive.")
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
            None,
        )
        if content_length is not None and int(content_length) > self.max_bytes:
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"detail":"Request body exceeds the configured size limit."}',
                }
            )
            return
        await self.app(scope, receive, send)


def bounded_timeout(seconds: float) -> float:
    """Clamp provider/request timeouts to a finite operational range."""
    if seconds <= 0:
        raise ValueError("Timeout must be positive.")
    return min(seconds, 120.0)