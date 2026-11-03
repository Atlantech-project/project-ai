"""Structured JSON logs with the job's ids (AI-011). AI-092 adds metrics on top."""

import json
import logging
import sys
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

LOGGER: Final = logging.getLogger("common.runtime")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info and record.exc_info[0] is not None:
            # The type and location only: exception text can hold a provider key or a URL.
            entry["exception"] = record.exc_info[0].__name__
            entry["traceback"] = "".join(traceback.format_tb(record.exc_info[2]))
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    LOGGER.handlers[:] = [handler]
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def log_event(
    level: int, event: str, fields: Mapping[str, object], *, exc_info: bool = False
) -> None:
    LOGGER.log(level, event, extra={"fields": dict(fields)}, exc_info=exc_info)
