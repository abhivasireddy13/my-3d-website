"""
Structured JSON logging for the NEXUS AI backend.

Every log record emits a single-line JSON object containing:
  timestamp   – ISO-8601 with milliseconds
  level       – DEBUG / INFO / WARNING / ERROR / CRITICAL
  logger      – dotted module name
  message     – the formatted log message
  correlation_id – per-request UUID propagated from the X-Request-ID header

Usage
-----
    from app.core.logging import configure_logging, get_correlation_id
    configure_logging(level="INFO")   # call once at startup
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

# ── Per-request context variable ─────────────────────────────────────────────
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the correlation ID for the current request context."""
    return _correlation_id.get()


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set (or generate) a correlation ID and return it."""
    value = cid or str(uuid.uuid4())
    _correlation_id.set(value)
    return value


# ── JSON formatter ────────────────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        # Millisecond-precision UTC timestamp
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"

        payload: dict = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id() or None,
        }

        # Attach exception traceback when present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Merge only user-supplied extra= fields; skip all standard LogRecord attrs
        _STANDARD = frozenset({
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs", "message",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "taskName", "thread", "threadName",
            "exc_info", "exc_text", "asctime",
        })
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


# ── Public setup function ─────────────────────────────────────────────────────

def configure_logging(level: str = "INFO") -> None:
    """
    Replace the root handler with a JSON-streaming handler on stdout.

    Call this once from app startup (before any log records are emitted).
    Silences noisy third-party loggers that flood production logs.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Reduce verbosity from noisy libraries
    for _noisy in ("uvicorn.access", "httpx", "httpcore", "multipart"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)
