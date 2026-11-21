"""Observability (AI-092): run ids on every job line, metrics per job, redaction."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from common import observability
from common.observability import NOT_SENT, JobMetrics, queue_wait_ms
from common.runtime.envelope import JobType, Schemas, load_schemas
from common.runtime.logs import (
    REDACTED,
    REDACTED_CONTAINER,
    JsonFormatter,
    job_log_context,
    log_event,
    redact,
)
from common.runtime.worker import JobContext, JobResult
from tests.support.runtime_messages import raw
from tests.unit.common.runtime.test_worker import DONE, SCHEMA_DIR, FakeConnection, _worker


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return load_schemas(SCHEMA_DIR)


@pytest.fixture
def metrics(monkeypatch: pytest.MonkeyPatch) -> JobMetrics:
    fresh = JobMetrics()
    monkeypatch.setattr("common.runtime.worker.METRICS", fresh)
    return fresh


def _lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    formatter = JsonFormatter()
    return [json.loads(formatter.format(record)) for record in caplog.records]


def _deep_handler(result: JobResult) -> Any:
    def handler(_context: JobContext) -> JobResult:
        # Code deep in a handler logs without the job's ids, as the port-state loader does.
        log_event(logging.INFO, "deep_step", {"seconds": 0.1})
        return result

    return handler


@pytest.mark.parametrize("job_type", [JobType.PART2_SOLVE, JobType.BAPLIE_PARSE])
def test_every_job_log_line_has_the_run_id(
    schemas: Schemas, metrics: JobMetrics, caplog: pytest.LogCaptureFixture, job_type: JobType
) -> None:
    worker, _ = _worker(schemas, job_type, _deep_handler(DONE[job_type]), FakeConnection())
    message = raw(job_type)
    run_id = json.loads(message)["run_id"]
    with caplog.at_level(logging.INFO, logger="common.runtime"):
        worker.process_message(message)

    lines = _lines(caplog)
    assert {"deep_step", "job_claimed", "job_done", "job_metrics"} <= {
        line["event"] for line in lines
    }
    assert all(line["run_id"] == run_id for line in lines)
    assert all(line["job_type"] == job_type.value for line in lines)


def test_context_ends_with_the_job() -> None:
    with job_log_context({"run_id": 5}):
        pass
    record = logging.LogRecord("common.runtime", logging.INFO, "", 0, "after", (), None)
    record.fields = {}
    assert "run_id" not in json.loads(JsonFormatter().format(record))


def test_explicit_fields_win_over_the_context(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="common.runtime"), job_log_context({"run_id": 1}):
        log_event(logging.INFO, "x", {"run_id": 2})
    assert _lines(caplog)[0]["run_id"] == 2


# --- metrics -----------------------------------------------------------------------------------


def test_metrics_for_duration_queue_wait_and_outcome(
    schemas: Schemas, metrics: JobMetrics, caplog: pytest.LogCaptureFixture
) -> None:
    job_type = JobType.PART2_SOLVE
    worker, _ = _worker(schemas, job_type, lambda _c: DONE[job_type], FakeConnection())
    with caplog.at_level(logging.INFO, logger="common.runtime"):
        worker.process_message(raw(job_type))
        worker.process_message(raw(job_type))

    line = next(entry for entry in _lines(caplog) if entry["event"] == "job_metrics")
    assert line["status"] == "DONE"
    assert line["outcome"] == "SOLVED"
    assert isinstance(line["duration_ms"], int) and line["duration_ms"] >= 0
    assert isinstance(line["queue_wait_ms"], int)
    snapshot = metrics.snapshot()
    assert snapshot["outcomes"] == [
        {"job_type": "PART2_SOLVE", "status": "DONE", "result": "SOLVED", "count": 2}
    ]
    durations: Any = snapshot["duration_ms"]
    assert durations["PART2_SOLVE"]["count"] == 2


def test_a_lost_claim_is_counted_as_not_sent(schemas: Schemas, metrics: JobMetrics) -> None:
    connection = FakeConnection()
    connection.claimable = False
    worker, _ = _worker(
        schemas, JobType.YARD_PLACEMENT, lambda _c: DONE[JobType.YARD_PLACEMENT], connection
    )
    worker.process_message(raw(JobType.YARD_PLACEMENT))

    outcomes: Any = metrics.snapshot()["outcomes"]
    assert outcomes[0]["status"] == NOT_SENT


def test_a_failed_job_counts_its_error_category(schemas: Schemas, metrics: JobMetrics) -> None:
    def broken(_context: JobContext) -> JobResult:
        raise RuntimeError("boom")

    worker, _ = _worker(schemas, JobType.BAPLIE_PARSE, broken, FakeConnection())
    worker.process_message(raw(JobType.BAPLIE_PARSE))

    outcomes: Any = metrics.snapshot()["outcomes"]
    assert outcomes[0]["status"] == "FAILED"
    assert outcomes[0]["result"] == "INTERNAL_ERROR"


def test_a_metrics_failure_never_stops_the_worker(
    schemas: Schemas, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class Broken(JobMetrics):
        def observe(self, **_kwargs: Any) -> None:
            raise RuntimeError("metrics down")

    monkeypatch.setattr("common.runtime.worker.METRICS", Broken())
    job_type = JobType.PART2_SOLVE
    worker, redis = _worker(schemas, job_type, lambda _c: DONE[job_type], FakeConnection())
    with caplog.at_level(logging.INFO, logger="common.runtime"):
        worker.process_message(raw(job_type))

    assert len(redis.pushed) == 1
    assert "metrics_failed" in {line["event"] for line in _lines(caplog)}


@pytest.mark.parametrize(
    ("enqueued_at", "expected"),
    [
        ("2026-11-21T12:00:00Z", 1500),
        ("2026-11-21T12:00:02Z", -500),  # clock skew stays visible
        ("2026-11-21T12:00:00", None),  # no offset
        ("not a time", None),
        (None, None),
    ],
)
def test_queue_wait(enqueued_at: str | None, expected: int | None) -> None:
    started = datetime(2026, 11, 21, 12, 0, 1, 500000, tzinfo=UTC)
    assert queue_wait_ms(enqueued_at, started) == expected


def test_metrics_module_exports_one_shared_registry() -> None:
    assert isinstance(observability.METRICS, JobMetrics)


# --- redaction ---------------------------------------------------------------------------------


def test_redaction_of_manifest_fields_at_any_depth() -> None:
    fields = {
        "run_id": 7,
        "staged_payload": {"lines": [{"container_number": "MSCU1234566"}]},
        "detail": {"container_number": "MSCU1234566", "weight_kg": 24500, "count": 3},
        "lines": [1, 2],
    }
    assert redact(fields) == {
        "run_id": 7,
        "staged_payload": REDACTED,
        "detail": {"container_number": REDACTED, "weight_kg": REDACTED, "count": 3},
        "lines": REDACTED,
    }


def test_redaction_masks_container_numbers_in_text(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="common.runtime"):
        log_event(logging.INFO, "issue", {"message": "Container MSCU 123456 6 appears twice"})
        log_event(logging.INFO, "issue", {"message": "Size type 45G1 not found; IMO 9811000"})

    first, second = _lines(caplog)
    assert first["message"] == f"Container {REDACTED_CONTAINER} appears twice"
    assert "MSCU" not in json.dumps(first)
    assert second["message"] == "Size type 45G1 not found; IMO 9811000"  # not a container number
