from __future__ import annotations

import json
import logging
import logging.config
from datetime import datetime, timezone

_BASE_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {"message", "asctime"}

_CONTEXT_FIELDS = ("request_id", "subject", "method", "path", "client_ip")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _CONTEXT_FIELDS:
            payload[field] = getattr(record, field, None)
        for key, value in record.__dict__.items():
            if key in _BASE_RECORD_ATTRS or key in payload:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def build_logging_config(level: str = "INFO") -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {"()": "app.core.log_context.RequestContextFilter"},
        },
        "formatters": {
            "json": {"()": "app.core.logging_config.JsonLogFormatter"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["request_context"],
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            "app": {"level": level, "propagate": True},
            "uvicorn": {"level": level, "propagate": True},
            "uvicorn.error": {"level": level, "propagate": True},
            # Kendi app.access logger'ımız (RequestIdMiddleware) zaten her istek için
            # zengin bir access log satırı üretiyor; uvicorn'unkini bastırmazsak her
            # istek için iki kez, farklı biçimlerde loglanır.
            "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": False},
        },
    }


def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(build_logging_config(level))
