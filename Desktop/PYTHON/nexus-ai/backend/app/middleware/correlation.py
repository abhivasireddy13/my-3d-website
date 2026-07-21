"""
Correlation-ID middleware.

Reads X-Request-ID from incoming headers (or generates a UUID), stores it
in the request context variable, and echoes it back in the response so
callers can correlate frontend errors with backend log lines.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import set_correlation_id

_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get(_HEADER) or str(uuid.uuid4())
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers[_HEADER] = cid
        return response
