"""Optional stateless API authentication for deployed account boundaries."""

import hmac
import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class AuthenticationMiddleware:
    """Require a configured bearer token without storing user documents."""

    def __init__(self, app: ASGIApp, token: str | None = None) -> None:
        self.app = app
        self.token = token if token is not None else os.getenv("JIRO_API_TOKEN", "")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.token or scope.get("path") in {"/health", "/docs", "/openapi.json"}:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, _, supplied = authorization.partition(" ")
        if scheme.casefold() == "bearer" and hmac.compare_digest(supplied, self.token):
            await self.app(scope, receive, send)
            return

        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"detail":"Authentication required.","category":"configuration"}',
        })
