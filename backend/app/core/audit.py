import logging
import re
import uuid

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.db import SessionLocal
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


class AuditMiddleware(BaseHTTPMiddleware):
    """Records every /api request (user, action, resource, status, IP) in audit_logs."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        path = request.url.path
        if not path.startswith("/api/"):
            return response
        user_id: uuid.UUID | None = None
        role: str | None = None
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                payload = decode_access_token(auth[7:])
                user_id, role = uuid.UUID(payload["sub"]), payload.get("role")
            except (jwt.PyJWTError, KeyError, ValueError):
                pass
        resource, resource_id = _parse_resource(path)
        action = "auth" if resource.startswith("auth") else _ACTIONS.get(request.method, "read")
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else None
        )
        try:
            async with SessionLocal() as db:
                db.add(
                    AuditLog(
                        user_id=user_id,
                        role=role,
                        action=action,
                        resource_type=resource,
                        resource_id=resource_id,
                        method=request.method,
                        path=path[:300],
                        status_code=response.status_code,
                        ip=ip,
                        request_id=getattr(request.state, "request_id", None),
                    )
                )
                await db.commit()
        except Exception:
            # Never break the user's request, but make the gap visible to operators.
            log.exception("audit log write failed")
        return response
