from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest

from common.config import ConfigurationError, PortSettings
from common.runtime.envelope import JobType, Schemas, load_schemas
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.logs import JsonFormatter
from common.runtime.runs import RUN_TABLES, read_completion_field
from common.runtime.worker import (
    AI_RESULTS_QUEUE,
    JobContext,
    JobResult,
    Worker,
    WorkerDefinition,
    part1_retries_allowed,
)
from tests.support.runtime_messages import envelope, raw

SCHEMA_DIR = Path(__file__).resolve().parents[4] / "docs" / "ref" / "ai-payloads"
RUN_JOBS = [job for job in JobType if job is not JobType.VALIDATION]
DONE: dict[JobType, JobResult] = {
    JobType.PART1_RUN: JobResult(
        "WINDOWS_FOUND",
        run_columns={"entry_window_proposal_id": 4},
        completion_fields={"entry_window_proposal_id": 4},
    ),
    JobType.PART2_SOLVE: JobResult("SOLVED", run_columns={"status": "OPTIMAL"}),
    JobType.YARD_PLACEMENT: JobResult(
        "YARD_REC_GENERATED", completion_fields={"terminal_recommendation_id": 11}
    ),
    JobType.BAPLIE_PARSE: JobResult(
        "PARSED", run_columns={"container_count": 3}, completion_fields={"baplie_file_id": 21}
    ),
    JobType.VALIDATION: JobResult(
        "VALID",
        completion_fields={
            "validation_result": {
                "validation_type": "OVERRIDE",
                "subject_id": 5,
                "valid": True,
                "violations": [],
            }
        },
    ),
}


class FakeCursor:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.rowcount = 0
        self._rows: list[tuple[Any, ...]] = []

    def execute(self, query: str, args: object = None) -> int:
        self.connection.log.append((" ".join(query.split()), args))
        error = self.connection.fail_on(query)
        if error is not None:
            raise error
        if query.startswith("SELECT setting_key"):
            self._rows = list(self.connection.settings)
        elif query.startswith("SELECT status"):
            self._rows = [("RUNNING" if self.connection.running else "FAILED",)]
        elif query.startswith("SELECT"):
            self._rows = [(self.connection.extra_id,)]
        elif "status = 'QUEUED'" in query:
            self.rowcount = 1 if self.connection.claimable else 0
        elif "lifecycle_status = 'YARD_REC_REQUESTED'" in query:
            self.rowcount = 1 if self.connection.yard_requested else 0
        else:
            self.rowcount = 1 if self.connection.running else 0
        return self.rowcount

    def fetchall(self) -> Sequence[Sequence[Any]]:
        return self._rows

    def fetchone(self) -> Sequence[Any] | None:
        return self._rows[0] if self._rows else None

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(self) -> None:
        self.log: list[tuple[str, object]] = []
        self.events: list[str] = []
        self.settings: list[tuple[str, str, str]] = [("part1_max_retries", "2", "INT")]
        self.extra_id = 77
        self.claimable = True
        self.running = True
        self.yard_requested = True
        self.fail_on: Callable[[str], Exception | None] = lambda _query: None
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")

    def close(self) -> None:
        self.closed = True

    def updates(self, table: str) -> list[tuple[str, object]]:
        return [(q, a) for q, a in self.log if q.startswith(f"UPDATE {table}")]


class FakeRedis:
    def __init__(self, connection: FakeConnection | None = None) -> None:
        self.pushed: list[tuple[str, dict[str, Any]]] = []
        self.connection = connection
        self.fail = False

    def ping(self) -> bool:
        return True

    def blpop(self, keys: Any, timeout: Any = 0) -> Any:
        return None

    def rpush(self, name: str, *values: Any) -> int:
        if self.fail:
            raise OSError("redis down")
        if self.connection is not None:
            self.connection.events.append("push")
        self.pushed.extend((name, json.loads(value)) for value in values)
        return len(values)


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return load_schemas(SCHEMA_DIR)


def _worker(
    schemas: Schemas,
    job_type: JobType,
    handler: Callable[[JobContext], JobResult],
    connection: FakeConnection,
) -> tuple[Worker, FakeRedis]:
    redis = FakeRedis(connection)
    definition = WorkerDefinition(job_type, handler, ("part1_max_retries",), "0.1.0")
    return Worker(definition, lambda: connection, redis, schemas), redis


def _done(job_type: JobType) -> Callable[[JobContext], JobResult]:
    return lambda _context: DONE[job_type]


def _raises(error: Exception, counter: list[int] | None = None) -> Callable[[JobContext], Any]:
    def handler(_context: JobContext) -> JobResult:
        if counter is not None:
            counter.append(1)
        raise error

    return handler


def _fields(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    return [
        getattr(record, "fields", {}) | {"level": record.levelname, "event": record.getMessage()}
        for record in caplog.records
    ]


# Duplicates and the happy path


@pytest.mark.parametrize("job_type", RUN_JOBS)
def test_done_commits_then_sends_one_valid_completion(schemas: Schemas, job_type: JobType) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, job_type, _done(job_type), connection)
    message = raw(job_type)
    worker.process_message(message)
    assert len(redis.pushed) == 1
    queue, body = redis.pushed[0]
    assert queue == AI_RESULTS_QUEUE == "queue:ai-results"
    assert body["status"] == "DONE"
    assert body["job_id"] == json.loads(message)["job_id"]
    assert connection.events[-2:] == ["commit", "push"]
    assert connection.closed


def test_lost_claim_runs_nothing_and_sends_nothing(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    connection = FakeConnection()
    connection.claimable = False
    calls: list[int] = []
    worker, redis = _worker(
        schemas, JobType.PART1_RUN, _raises(RuntimeError("no"), calls), connection
    )
    with caplog.at_level(logging.INFO):
        worker.process_message(raw(JobType.PART1_RUN))
    assert not calls
    assert not redis.pushed


def test_the_claim_is_the_contracts_conditional_update(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, _ = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    worker.process_message(raw(JobType.PART1_RUN, run_id=9))
    assert connection.updates("part1_runs")[0] == (
        "UPDATE part1_runs SET status = 'RUNNING', started_at = UTC_TIMESTAMP() "
        "WHERE id = %s AND status = 'QUEUED'",
        (9,),
    )


def test_settings_are_read_then_committed_before_the_handler(schemas: Schemas) -> None:
    connection = FakeConnection()
    seen: list[int] = []

    def handler(context: JobContext) -> JobResult:
        seen.append(context.settings.get_int("part1_max_retries"))
        connection.events.append("handler")
        return DONE[JobType.PART1_RUN]

    worker, _ = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert seen == [2]
    assert connection.events.index("handler") > 0
    assert connection.events[connection.events.index("handler") - 1] == "commit"


# Stale or replaced runs


@pytest.mark.parametrize("job_type", RUN_JOBS)
def test_guarded_update_losing_rolls_back_and_sends_nothing(
    schemas: Schemas, job_type: JobType
) -> None:
    connection = FakeConnection()

    def handler(_context: JobContext) -> JobResult:
        connection.running = False
        return DONE[job_type]

    worker, redis = _worker(schemas, job_type, handler, connection)
    worker.process_message(raw(job_type))
    assert connection.events[-1] == "rollback"
    assert not redis.pushed


def test_final_update_is_guarded_by_running(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, _ = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    worker.process_message(raw(JobType.PART1_RUN, run_id=9))
    query = connection.updates("part1_runs")[-1][0]
    assert query.endswith("WHERE id = %s AND status = 'RUNNING'")
    assert "finished_at = UTC_TIMESTAMP()" in query


# Retries


@pytest.mark.parametrize(
    ("job_type", "attempts"),
    [
        (JobType.PART1_RUN, 3),
        (JobType.PART2_SOLVE, 2),
        (JobType.YARD_PLACEMENT, 2),
        (JobType.BAPLIE_PARSE, 2),
        (JobType.VALIDATION, 1),
    ],
)
def test_retry_limits_follow_dec04(schemas: Schemas, job_type: JobType, attempts: int) -> None:
    connection = FakeConnection()
    calls: list[int] = []
    error = JobError(ErrorCategory.DATA_UNAVAILABLE, "provider down")
    worker, redis = _worker(schemas, job_type, _raises(error, calls), connection)
    worker.process_message(raw(job_type))
    assert len(calls) == attempts
    assert len(redis.pushed) == 1
    assert redis.pushed[0][1]["status"] == "FAILED"
    assert redis.pushed[0][1]["error_category"] == "DATA_UNAVAILABLE"


@pytest.mark.parametrize(
    "category",
    [
        ErrorCategory.PRECONDITION_FAILED,
        ErrorCategory.CONFIGURATION_ERROR,
        ErrorCategory.INVALID_ENVELOPE,
    ],
)
def test_other_categories_are_not_retried(schemas: Schemas, category: ErrorCategory) -> None:
    calls: list[int] = []
    connection = FakeConnection()
    error = JobError(category, "x")
    worker, _ = _worker(schemas, JobType.PART1_RUN, _raises(error, calls), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert len(calls) == 1


@pytest.mark.parametrize("category", [ErrorCategory.TIMEOUT, ErrorCategory.SOLVER_ERROR])
def test_part2_timeout_and_solver_error_are_not_retried(
    schemas: Schemas, category: ErrorCategory
) -> None:
    calls: list[int] = []
    connection = FakeConnection()
    error = JobError(category, "x")
    worker, redis = _worker(schemas, JobType.PART2_SOLVE, _raises(error, calls), connection)
    worker.process_message(raw(JobType.PART2_SOLVE))
    assert len(calls) == 1
    assert redis.pushed[0][1]["error_category"] == category.value


def test_timeout_is_retried_for_part1(schemas: Schemas) -> None:
    calls: list[int] = []
    error = JobError(ErrorCategory.TIMEOUT, "x")
    worker, _ = _worker(schemas, JobType.PART1_RUN, _raises(error, calls), FakeConnection())
    worker.process_message(raw(JobType.PART1_RUN))
    assert len(calls) == 3


def test_success_after_a_retry_sends_one_done(schemas: Schemas) -> None:
    connection = FakeConnection()
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        if len(calls) == 1:
            raise JobError(ErrorCategory.DATA_UNAVAILABLE, "x")
        return DONE[JobType.PART1_RUN]

    worker, redis = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert [body["status"] for _, body in redis.pushed] == ["DONE"]


@pytest.mark.parametrize(
    "job_type", [JobType.PART1_RUN, JobType.YARD_PLACEMENT, JobType.BAPLIE_PARSE]
)
def test_retry_count_is_incremented_guarded_where_granted(
    schemas: Schemas, job_type: JobType
) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.DATA_UNAVAILABLE, "x")
    worker, _ = _worker(schemas, job_type, _raises(error), connection)
    worker.process_message(raw(job_type))
    table = RUN_TABLES[job_type].table
    expected = (
        f"UPDATE {table} SET retry_count = retry_count + 1 "  # noqa: S608
        "WHERE id = %s AND status = 'RUNNING'"
    )
    assert expected in [query for query, _ in connection.log]


def test_solver_runs_have_no_retry_count(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.DATA_UNAVAILABLE, "x")
    worker, _ = _worker(schemas, JobType.PART2_SOLVE, _raises(error), connection)
    worker.process_message(raw(JobType.PART2_SOLVE))
    assert not any("retry_count" in query for query, _ in connection.log)


def test_a_failed_attempt_rolls_back_before_the_retry(schemas: Schemas) -> None:
    connection = FakeConnection()

    def handler(_context: JobContext) -> JobResult:
        connection.events.append("handler")
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, "x")

    worker, _ = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    after_first = connection.events[connection.events.index("handler") + 1]
    assert after_first == "rollback"


def test_a_run_lost_before_the_failed_update_sends_nothing(schemas: Schemas) -> None:
    connection = FakeConnection()

    def handler(_context: JobContext) -> JobResult:
        connection.running = False
        raise JobError(ErrorCategory.PRECONDITION_FAILED, "x")

    worker, redis = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert connection.events[-1] == "rollback"
    assert not redis.pushed


def test_a_lost_retry_update_stops_and_sends_nothing(schemas: Schemas) -> None:
    connection = FakeConnection()
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        connection.running = False
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, "x")

    worker, redis = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert len(calls) == 1
    assert not redis.pushed


@pytest.mark.parametrize(
    ("value", "valid"), [("0", True), ("3", True), ("4", False), ("10", False), ("-1", False)]
)
def test_part1_max_retries_outside_the_check_is_a_configuration_error(
    schemas: Schemas, value: str, valid: bool
) -> None:
    connection = FakeConnection()
    connection.settings = [("part1_max_retries", value, "INT")]
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        return DONE[JobType.PART1_RUN]

    worker, redis = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    body = redis.pushed[0][1]
    if valid:
        assert body["status"] == "DONE"
    else:
        assert not calls
        assert body["error_category"] == "CONFIGURATION_ERROR"


def test_part1_max_retries_message_is_clear() -> None:
    settings = PortSettings([("part1_max_retries", "10", "INT")])
    with pytest.raises(ConfigurationError, match=r"part1_max_retries.*chk_p1r_retry"):
        part1_retries_allowed(settings)


# Errors


@pytest.mark.parametrize(
    ("error", "category", "attempts"),
    [
        (ConfigurationError("bad"), "CONFIGURATION_ERROR", 1),
        (RuntimeError("boom"), "INTERNAL_ERROR", 3),
        (OSError(3819, "Check constraint violated"), "CONFIGURATION_ERROR", 1),
    ],
)
def test_errors_map_to_contract_categories(
    schemas: Schemas, error: Exception, category: str, attempts: int
) -> None:
    connection = FakeConnection()
    calls: list[int] = []
    worker, redis = _worker(schemas, JobType.PART1_RUN, _raises(error, calls), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert len(calls) == attempts
    assert redis.pushed[0][1]["error_category"] == category


def test_a_category_not_allowed_for_the_job_becomes_internal(schemas: Schemas) -> None:
    error = JobError(ErrorCategory.INFEASIBLE, "x")
    worker, redis = _worker(schemas, JobType.PART1_RUN, _raises(error), FakeConnection())
    worker.process_message(raw(JobType.PART1_RUN))
    assert redis.pushed[0][1]["error_category"] == "INTERNAL_ERROR"


def test_a_bad_result_fails_before_commit(schemas: Schemas) -> None:
    connection = FakeConnection()
    bad = JobResult("NOT_AN_OUTCOME", completion_fields={"entry_window_proposal_id": 4})
    worker, redis = _worker(schemas, JobType.PART1_RUN, lambda _c: bad, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert all(body["status"] == "FAILED" for _, body in redis.pushed)
    assert redis.pushed[0][1]["error_category"] == "INTERNAL_ERROR"


def test_a_column_outside_the_grants_fails_the_job(schemas: Schemas) -> None:
    connection = FakeConnection()
    bad = JobResult(
        "WINDOWS_FOUND",
        run_columns={"result_handled_at": "now"},
        completion_fields={"entry_window_proposal_id": 4},
    )
    worker, redis = _worker(schemas, JobType.PART1_RUN, lambda _c: bad, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert redis.pushed[0][1]["status"] == "FAILED"
    assert not any("result_handled_at" in query for query, _ in connection.log)


def test_a_solver_result_without_a_status_fails_the_job(schemas: Schemas) -> None:
    bad = JobResult("SOLVED")
    worker, redis = _worker(schemas, JobType.PART2_SOLVE, lambda _c: bad, FakeConnection())
    worker.process_message(raw(JobType.PART2_SOLVE))
    assert redis.pushed[0][1]["status"] == "FAILED"


def test_a_missing_run_row_gives_no_related_id() -> None:
    class NoRowCursor(FakeCursor):
        def fetchone(self) -> None:
            return None

    class NoRowConnection(FakeConnection):
        def cursor(self) -> FakeCursor:
            return NoRowCursor(self)

    spec = RUN_TABLES[JobType.YARD_PLACEMENT]
    assert read_completion_field(NoRowConnection(), spec, 1) is None


def test_a_handler_crash_doesnt_stop_processing(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, JobType.PART1_RUN, _raises(RuntimeError("x")), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    worker.process_message(raw(JobType.PART1_RUN))
    assert len(redis.pushed) == 2


def test_a_database_failure_doesnt_raise(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    connection = FakeConnection()
    connection.fail_on = lambda _query: OSError("database down")
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    assert not redis.pushed
    assert connection.closed
    assert any(f["level"] == "ERROR" for f in _fields(caplog))


def test_a_lost_completion_is_logged_after_commit(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    redis.fail = True
    worker.process_message(raw(JobType.PART1_RUN))
    assert connection.events[-1] == "commit"
    assert any(f["event"] == "completion_not_sent" for f in _fields(caplog))


# Failed writes per table


def test_part1_failed_columns(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x")
    worker, redis = _worker(schemas, JobType.PART1_RUN, _raises(error), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    query, args = connection.updates("part1_runs")[-1]
    assert "error_category" not in query
    assert args == ("FAILED", 1)
    assert redis.pushed[0][1]["outcome"] is None
    assert redis.pushed[0][1]["entry_window_proposal_id"] is None


def test_solver_failed_is_error_with_failure_reason(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "no requests")
    worker, redis = _worker(schemas, JobType.PART2_SOLVE, _raises(error), connection)
    worker.process_message(raw(JobType.PART2_SOLVE))
    query, args = connection.updates("solver_runs")[-1]
    assert isinstance(args, tuple)
    assert "result_detail = %s" in query
    assert args[0] == "ERROR"
    assert json.loads(args[1]) == {
        "outcome": "GENERATION_FAILED",
        "failure_reason": {"error_category": "PRECONDITION_FAILED", "message": "no requests"},
        "requests": [],
    }
    assert redis.pushed[0][1]["outcome"] == "GENERATION_FAILED"


def test_yard_failed_writes_the_recommendation_and_reads_its_id(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x" * 600)
    worker, redis = _worker(schemas, JobType.YARD_PLACEMENT, _raises(error), connection)
    worker.process_message(raw(JobType.YARD_PLACEMENT))
    query, args = connection.updates("yard_runs")[-1]
    assert isinstance(args, tuple)
    assert args[:3] == ("FAILED", "GENERATION_FAILED", "PRECONDITION_FAILED")
    assert "worker_version = %s" in query
    query, args = connection.updates("terminal_recommendations")[-1]
    assert isinstance(args, tuple)
    assert "lifecycle_status = 'YARD_REC_REQUESTED'" in query
    assert args[0] == "GENERATION_FAILED"
    assert args[1].startswith("PRECONDITION_FAILED: ")
    assert len(args[1]) == 500
    assert args[2] == 77
    body = redis.pushed[0][1]
    assert body["terminal_recommendation_id"] == 77
    assert body["outcome"] == "GENERATION_FAILED"


def test_yard_failed_rolls_back_if_the_row_moved_on(schemas: Schemas) -> None:
    connection = FakeConnection()
    connection.yard_requested = False
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x")
    worker, redis = _worker(schemas, JobType.YARD_PLACEMENT, _raises(error), connection)
    worker.process_message(raw(JobType.YARD_PLACEMENT))
    assert connection.events[-1] == "rollback"
    assert not redis.pushed


def test_edi_failed_marks_the_file_and_reads_its_id(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x")
    worker, redis = _worker(schemas, JobType.BAPLIE_PARSE, _raises(error), connection)
    worker.process_message(raw(JobType.BAPLIE_PARSE))
    query, args = connection.updates("baplie_parse_runs")[-1]
    assert "outcome" not in query
    assert isinstance(args, tuple)
    assert args[:2] == ("FAILED", "PRECONDITION_FAILED")
    assert connection.updates("baplie_files")[-1] == (
        "UPDATE baplie_files SET parse_status = 'FAILED' WHERE id = %s",
        (77,),
    )
    assert redis.pushed[0][1]["baplie_file_id"] == 77


# Invalid messages


@pytest.mark.parametrize("job_type", RUN_JOBS)
def test_invalid_payload_claims_and_fails_the_run(schemas: Schemas, job_type: JobType) -> None:
    connection = FakeConnection()
    calls: list[int] = []
    worker, redis = _worker(schemas, job_type, _raises(RuntimeError("no"), calls), connection)
    worker.process_message(raw(job_type, run_id=9, payload={}))
    assert not calls
    assert connection.updates(RUN_TABLES[job_type].table)[0][1] == (9,)
    assert redis.pushed[0][1]["error_category"] == "INVALID_ENVELOPE"


def test_invalid_message_lost_claim_sends_nothing(schemas: Schemas) -> None:
    connection = FakeConnection()
    connection.claimable = False
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    worker.process_message(raw(JobType.PART1_RUN, payload={}))
    assert not redis.pushed


def test_invalid_message_without_a_job_id_finishes_the_run_silently(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    worker.process_message(raw(JobType.PART1_RUN, payload={}, job_id="nope"))
    assert connection.events[-1] == "commit"
    assert not redis.pushed


def test_wrong_queue_logs_at_error_and_never_claims(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    connected: list[int] = []

    def connect() -> FakeConnection:
        connected.append(1)
        return FakeConnection()

    redis = FakeRedis()
    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    worker = Worker(definition, connect, redis, schemas)
    worker.process_message(raw(JobType.PART2_SOLVE, run_id=9))
    assert not connected
    assert not redis.pushed
    entry = next(f for f in _fields(caplog) if f["event"] == "wrong_queue_dropped")
    assert entry["level"] == "ERROR"
    assert entry["job_type"] == "PART2_SOLVE"
    assert entry["run_id"] == 9
    assert entry["queue"] == "queue:part1"


def test_unreadable_is_logged_capped_and_dropped(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), FakeConnection())
    worker.process_message(b"x" * 100_000)
    assert not redis.pushed
    entry = next(f for f in _fields(caplog) if f["event"] == "invalid_message_dropped")
    assert len(entry["raw"]) <= 4096


# Validation jobs


def test_validation_has_no_claim_and_writes_nothing(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, JobType.VALIDATION, _done(JobType.VALIDATION), connection)
    worker.process_message(raw(JobType.VALIDATION))
    assert not [query for query, _ in connection.log if query.startswith("UPDATE")]
    assert "commit" in connection.events
    assert connection.events[-2:] == ["rollback", "push"]
    assert redis.pushed[0][1]["outcome"] == "VALID"


def test_invalid_validation_sends_failed(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, JobType.VALIDATION, _done(JobType.VALIDATION), connection)
    worker.process_message(raw(JobType.VALIDATION, payload={}))
    body = redis.pushed[0][1]
    assert body["status"] == "FAILED"
    assert body["run_id"] is None
    assert body["error_category"] == "INVALID_ENVELOPE"


# Logs


@pytest.mark.parametrize("job_type", RUN_JOBS)
def test_job_logs_carry_run_id_and_contract_version(
    schemas: Schemas, job_type: JobType, caplog: pytest.LogCaptureFixture
) -> None:
    worker, _ = _worker(schemas, job_type, _done(job_type), FakeConnection())
    with caplog.at_level(logging.INFO):
        worker.process_message(raw(job_type, run_id=9, contract_version="1.3"))
    entries = _fields(caplog)
    assert entries
    assert all(f.get("run_id") == 9 for f in entries)
    assert all(f.get("contract_version") == "1.3" for f in entries)


def test_failed_job_logs_carry_run_id_and_contract_version(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    error = JobError(ErrorCategory.DATA_UNAVAILABLE, "x")
    worker, _ = _worker(schemas, JobType.PART1_RUN, _raises(error), FakeConnection())
    with caplog.at_level(logging.INFO):
        worker.process_message(raw(JobType.PART1_RUN, run_id=9))
    assert len(_fields(caplog)) > 1
    assert all(f.get("run_id") == 9 and f.get("contract_version") for f in _fields(caplog))


def test_formatter_writes_json_lines() -> None:
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "job_claimed", None, None)
    record.fields = {"run_id": 9, "contract_version": "1.0"}
    line = json.loads(JsonFormatter().format(record))
    assert line["event"] == "job_claimed"
    assert line["level"] == "INFO"
    assert line["run_id"] == 9
    assert line["contract_version"] == "1.0"
    assert line["timestamp"].endswith("Z")


# The loop


def test_stop_ends_the_loop_after_the_current_message(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    messages = [raw(JobType.PART1_RUN), raw(JobType.PART1_RUN)]

    def blpop(keys: Any, timeout: Any = 0) -> Any:
        assert keys == ["queue:part1"]
        worker.stop()
        return (b"queue:part1", messages.pop(0))

    redis.blpop = blpop  # type: ignore[method-assign]
    worker.run()
    assert len(redis.pushed) == 1
    assert len(messages) == 1


def test_a_redis_failure_doesnt_end_the_loop(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    worker, redis = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), FakeConnection())
    calls: list[int] = []

    def blpop(keys: Any, timeout: Any = 0) -> Any:
        calls.append(1)
        if len(calls) == 1:
            raise OSError("redis down")
        worker.stop()
        return None

    redis.blpop = blpop  # type: ignore[method-assign]
    worker.run()
    assert len(calls) == 2
    assert any(f["event"] == "queue_read_failed" for f in _fields(caplog))


def test_envelope_helper_is_valid_for_part1() -> None:
    assert envelope(JobType.PART1_RUN)["job_type"] == "PART1_RUN"
