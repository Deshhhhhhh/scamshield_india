"""Structured JSON logging — every log line is machine-parseable."""

from __future__ import annotations

import json
import logging
import sys
import time

from .config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith(
                (
                    "_",
                    "args",
                    "msg",
                    "levelname",
                    "name",
                    "created",
                    "relativeCreated",
                    "msecs",
                    "pathname",
                    "filename",
                    "module",
                    "exc_text",
                    "exc_info",
                    "funcName",
                    "lineno",
                    "thread",
                    "threadName",
                    "process",
                    "processName",
                    "stack_info",
                )
            ):
                continue
            try:
                json.dumps(value, default=str)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = str(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
