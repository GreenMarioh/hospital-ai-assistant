import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
)
AUTH_LIMIT = "10/minute"
