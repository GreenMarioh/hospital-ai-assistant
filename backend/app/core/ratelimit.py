import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
    storage_uri=get_settings().redis_url or None,
)
AUTH_LIMIT = "10/minute"
