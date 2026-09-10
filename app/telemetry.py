"""Allowlisted operational telemetry that excludes sensitive document content."""

from dataclasses import dataclass
import logging
from time import monotonic
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


@dataclass(frozen=True)
class SafeEvent:
    """Safe operational event fields only."""

    request_id: str
    route: str
    stage: str
    duration_ms: float | None = None
    provider: str | None = None
    model: str | None = None
    status: str | None = None
    error_category: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            key: value
            for key, value in {
                "request_id": self.request_id,
                "route": self.route,
                "stage": self.stage,
                "duration_ms": self.duration_ms,
                "provider": self.provider,
                "model": self.model,
                "status": self.status,
                "error_category": self.error_category,
            }.items()
            if value is not None
        }


class SafeEventLogger:
    """Emit only explicitly allowlisted event metadata."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("jiro")

    def emit(self, event: SafeEvent) -> None:
        self.logger.info("jiro_event %s", event.as_dict())


class CorrelationIdMiddleware:
    """Attach a request ID without inspecting request bodies or headers."""

    def __init__(self, app: ASGIApp, event_logger: SafeEventLogger | None = None) -> None:
        self.app = app
        self.event_logger = event_logger or SafeEventLogger()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        started = monotonic()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            self.event_logger.emit(
                SafeEvent(
                    request_id=request_id,
                    route=str(scope.get("path", "unknown")),
                    stage="http",
                    duration_ms=round((monotonic() - started) * 1000, 2),
                    status=str(status_code),
                )
            )
