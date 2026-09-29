import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import (
    admin,
    ai,
    analytics,
    auth,
    documents,
    health,
    patients,
    scheduling,
    search,
    visits,
)
from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.ratelimit import limiter

settings = get_settings()
setup_logging()
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

app = FastAPI(title="AI Hospital Management Assistant", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(AuditMiddleware)
app.add_middleware(RequestContextMiddleware)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(scheduling.router)
app.include_router(ai.router)
app.include_router(analytics.router)
