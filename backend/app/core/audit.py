import logging
import re
import uuid

import jwt
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.db import AuditSessionLocal
from app.core.tokens import decode_access_token
from app.models import AuditLog

log = logging.getLogger("app.audit")
_ACTIONS = {"GET": "read", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}
_UUID = re.compile(r"^[0-9a-fA-F-]{36}$")


def _parse_resource(path: str) -> tuple[str, str | None]:
    """'/api/patients/<id>/visits' -> ('patients/visits', '<id>'): names of path segments, first id."""
    parts = [p for p in path.split("/") if p][1:]  # drop leading "api"
    names = [p for p in parts if not _UUID.match(p)][:3]
    resource_id = next((p for p in parts if _UUID.match(p)), None)
    return "/".join(names) or "unknown", resource_id


class AuditMiddleware:
    """Records every /api request (user, action, resource, status, IP) in audit_logs.

    Pure ASGI: the row is written after the response has been sent, so it adds no client latency.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return
        holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            await self._record(scope, path, holder["status"])

    async def _record(self, scope: Scope, path: str, status_code: int) -> None:
        headers = {k.decode().lower(): v.decode("latin-1") for k, v in scope["headers"]}
        user_id: uuid.UUID | None = None
        role: str | None = None
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                payload = decode_access_token(auth[7:])
                user_id, role = uuid.UUID(payload["sub"]), payload.get("role")
            except (jwt.PyJWTError, KeyError, ValueError):
                pass
        resource, resource_id = _parse_resource(path)
        method = scope["method"]
        action = "auth" if resource.startswith("auth") else _ACTIONS.get(method, "read")
        client = scope.get("client")
        # scope["client"] is rewritten by uvicorn from trusted proxy headers only
        # (--forwarded-allow-ips); reading X-Forwarded-For here would let callers forge the audited IP.
        ip = client[0] if client else None
        try:
            async with AuditSessionLocal() as db:
                db.add(
                    AuditLog(
                        user_id=user_id,
                        role=role,
                        action=action,
                        resource_type=resource,
                        resource_id=resource_id,
                        method=method,
                        path=path[:300],
                        status_code=status_code,
                        ip=ip,
                        request_id=scope.get("state", {}).get("request_id"),
                    )
                )
                await db.commit()
        except Exception:
            # Never break the user's request, but make the gap visible to operators.
            log.exception("audit log write failed")
