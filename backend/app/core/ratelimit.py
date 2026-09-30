import os

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
    storage_uri=get_settings().redis_url or None,
)
AUTH_LIMIT = "10/minute"


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Same error shape as every other API error (`detail`), so the UI can show it."""
    return JSONResponse(
        {"detail": "Too many requests. Please wait a minute and try again."},
        status_code=429,
        headers={"Retry-After": "60"},
    )
