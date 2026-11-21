"""Structured JSON logs with the job's ids (AI-011), job context and redaction (AI-092).

- **Job context.** While a job runs, `job_log_context` holds its ids (`job_id`, `run_id`, queue,
  job type), and every line logged in that time carries them, also lines logged deep inside a
  handler that never saw the ids. Fields passed to `log_event` win over the context.
- **Redaction.** Manifest data is commercially sensitive (§42 isolation): values under the keys
  in `SENSITIVE_KEYS`, at any depth, are replaced, and an ISO 6346 container number inside any
  string is masked. Exception text was already never logged (AI-011).
"""

import json
import logging
import re
import sys
import traceback
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Final

LOGGER: Final = logging.getLogger("common.runtime")

REDACTED: Final = "[REDACTED]"
REDACTED_CONTAINER: Final = "[CONTAINER]"
# Manifest fields (CT-12 `staged_payload` line names) and the payloads that carry them.
SENSITIVE_KEYS: Final = frozenset(
    {
        "staged_payload",
        "lines",
        "container_number",
        "container_numbers",
        "iso_size_type",
        "weight_kg",
        "imdg_class",
        "reefer_set_temperature",
        "oog",
        "stowage",
        "port_of_load",
        "port_of_discharge",
        "placements",
        "manifest",
    }
)
# ISO 6346: owner code, category letter U, J or Z, six digits, check digit (spaces allowed).
_CONTAINER: Final = re.compile(r"\b[A-Z]{3}[UJZ]\s?\d{6}\s?\d\b")

_JOB_FIELDS: ContextVar[Mapping[str, object] | None] = ContextVar("job_fields", default=None)


def redact(value: Any) -> Any:
    """A copy of `value` with sensitive keys replaced and container numbers masked."""
    if isinstance(value, Mapping):
        return {
            key: REDACTED if str(key) in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _CONTAINER.sub(REDACTED_CONTAINER, value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        entry.update(redact(dict(getattr(record, "fields", {}))))
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


@contextmanager
def job_log_context(fields: Mapping[str, object]) -> Iterator[None]:
    """Every line logged inside this block carries `fields` (the job's ids)."""
    token = _JOB_FIELDS.set(dict(fields))
    try:
        yield
    finally:
        _JOB_FIELDS.reset(token)


def log_event(
    level: int, event: str, fields: Mapping[str, object], *, exc_info: bool = False
) -> None:
    merged = {**(_JOB_FIELDS.get() or {}), **fields}
    LOGGER.log(level, event, extra={"fields": merged}, exc_info=exc_info)
