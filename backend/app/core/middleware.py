"""Pure-ASGI middleware (cheaper than BaseHTTPMiddleware): request id, access log, security headers,
and a last-resort JSON 500 for unhandled errors."""

import json
import logging
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var

log = logging.getLogger("app.request")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Cache-Control": "no-store",
}


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        rid = headers.get(b"x-request-id", b"").decode()[:64] or uuid.uuid4().hex
        request_id_var.set(rid)
        scope.setdefault("state", {})["request_id"] = rid
        start = time.perf_counter()
        status_holder = {"status": 500, "started": False}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                status_holder["started"] = True
                h = MutableHeaders(scope=message)
                h["X-Request-ID"] = rid
                for k, v in SECURITY_HEADERS.items():
                    if k not in h:
                        h[k] = v
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("unhandled error", extra={"path": scope["path"]})
            if not status_holder["started"]:
                body = json.dumps({"detail": "Internal server error", "request_id": rid}).encode()
                await send_wrapper(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send_wrapper({"type": "http.response.body", "body": body})
        log.info(
            "request",
            extra={
                "method": scope["method"],
                "path": scope["path"],
                "status": status_holder["status"],
                "ms": round((time.perf_counter() - start) * 1000, 1),
            },
        )
