"""
Structured JSON logging for the NEXUS AI ML service.

Mirrors the backend logging module so log aggregators see a consistent schema
across all services.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(cid: Optional[str] = None) -> str:
    value = cid or str(uuid.uuid4())
    _correlation_id.set(value)
    return value


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"

        payload: dict = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "ml-service",
            "correlation_id": get_correlation_id() or None,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        _SKIP = frozenset(logging.LogRecord.__dict__.keys()) | {
            "message", "asctime", "args", "exc_text",
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for _noisy in ("uvicorn.access", "httpx", "httpcore", "mlflow"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)
