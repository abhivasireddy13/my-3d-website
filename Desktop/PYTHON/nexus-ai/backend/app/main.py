"""
NEXUS AI — FastAPI application entry point.

Startup order
-------------
1. configure_logging() — structured JSON output, correlation_id in every record
2. CorrelationIdMiddleware — assigns X-Request-ID to every request
3. SecurityHeadersMiddleware — adds HSTS / X-Content-Type / etc. in prod
4. CORSMiddleware — restricted to configured ALLOWED_ORIGINS
5. Rate limiter (slowapi)
6. Router registration
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.limiter import limiter
from app.core.logging import configure_logging
from app.middleware.correlation import CorrelationIdMiddleware
from app.api.v1 import auth, uploads, internal, reports, analytics, predictions, admin

# ── Logging ───────────────────────────────────────────────────────────────────
configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="NEXUS AI Backend",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware (applied in reverse order — last added = outermost) ─────────────

# 1. Security headers (outermost so every response is covered)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS — allow origins from env; falls back to localhost in development
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Correlation ID (innermost — runs after CORS so header is always present)
app.add_middleware(CorrelationIdMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api/v1")
app.include_router(uploads.router,     prefix="/api/v1")
app.include_router(reports.router,     prefix="/api/v1")
app.include_router(internal.router)                       # /internal/* — no /api/v1 prefix
app.include_router(analytics.router,   prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(admin.router,       prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def _startup():
    logger.info("NEXUS AI backend started", extra={"origins": _origins})
