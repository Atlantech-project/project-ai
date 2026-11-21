"""Job metrics (AI-092): duration, queue wait and outcome counts per job type.

No log-aggregation or metrics tool is documented for the port server, so metrics are exported
the way the logs are: one `job_metrics` JSON line per handled message, which any collector can
count and sum, plus an in-process `snapshot()` for tests and a future exporter. Nothing is sent
anywhere by this module.
"""

import logging
import threading
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from common.runtime.logs import log_event

EVENT: Final = "job_metrics"
NOT_SENT: Final = "NOT_SENT"  # no completion message: not claimed, lost to the Backend, or crashed


@dataclass
class _Durations:
    count: int = 0
    total_ms: int = 0
    max_ms: int = 0

    def add(self, value_ms: int) -> None:
        self.count += 1
        self.total_ms += value_ms
        self.max_ms = max(self.max_ms, value_ms)


@dataclass
class JobMetrics:
    """Thread-safe counters and duration sums, keyed by job type."""

    _outcomes: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    _durations: dict[str, _Durations] = field(default_factory=dict)
    _waits: dict[str, _Durations] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def observe(
        self,
        *,
        job_type: str,
        completion: Mapping[str, object] | None,
        duration_ms: int,
        queue_wait_ms: int | None,
        fields: Mapping[str, object],
    ) -> None:
        """Record one handled message and log its `job_metrics` line."""
        status = str(completion.get("status")) if completion else NOT_SENT
        outcome = completion.get("outcome") if completion else None
        category = completion.get("error_category") if completion else None
        key = (job_type, status, str(outcome or category or ""))
        with self._lock:
            self._outcomes[key] += 1
            self._durations.setdefault(job_type, _Durations()).add(duration_ms)
            if queue_wait_ms is not None:
                self._waits.setdefault(job_type, _Durations()).add(queue_wait_ms)
        log_event(
            logging.INFO,
            EVENT,
            {
                **fields,
                "status": status,
                "outcome": outcome,
                "error_category": category,
                "duration_ms": duration_ms,
                "queue_wait_ms": queue_wait_ms,
            },
        )

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "outcomes": [
                    {"job_type": t, "status": s, "result": r, "count": n}
                    for (t, s, r), n in sorted(self._outcomes.items())
                ],
                "duration_ms": {t: vars(d).copy() for t, d in sorted(self._durations.items())},
                "queue_wait_ms": {t: vars(d).copy() for t, d in sorted(self._waits.items())},
            }


def queue_wait_ms(enqueued_at: str | None, started: datetime) -> int | None:
    """Milliseconds from the envelope's `enqueued_at` to `started`; None if unknown.

    A negative wait (clocks out of step between the Backend and the port server) is reported as
    it is, never clamped, so the skew stays visible.
    """
    if not enqueued_at:
        return None
    try:
        enqueued = datetime.fromisoformat(enqueued_at)
    except ValueError:
        return None
    if enqueued.utcoffset() is None or started.utcoffset() is None:
        return None
    return round((started - enqueued).total_seconds() * 1000)


METRICS: Final = JobMetrics()
