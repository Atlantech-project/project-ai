"""Failure paths found by the independent AI-011 review. Each test failed before its fix."""

import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any

import pytest

from common.config import EnvSettings
from common.runtime.envelope import JobType, Schemas, load_schemas
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.logs import JsonFormatter, log_event
from common.runtime.runs import RUN_TABLES
from common.runtime.worker import (
    _BLPOP_TIMEOUT_SECONDS,
    _SOCKET_TIMEOUT_SECONDS,
    JobContext,
    JobResult,
    Worker,
    WorkerDefinition,
    connect_redis,
    run_worker,
)
from tests.support.runtime_messages import raw
from tests.unit.common.runtime.test_startup import ENV, GOOD_ROWS, _connect, _Connection, _Redis
from tests.unit.common.runtime.test_worker import (
    DONE,
    FakeConnection,
    FakeRedis,
    _done,
    _fields,
    _raises,
    _worker,
)

SCHEMA_DIR = Path(__file__).resolve().parents[4] / "docs" / "ref" / "ai-payloads"
SECRET = "SUPERSECRET123"


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return load_schemas(SCHEMA_DIR)


# C1: the client must outlast BLPOP, or a popped message can be lost.


def test_the_client_outlasts_blpop() -> None:
    assert _SOCKET_TIMEOUT_SECONDS > _BLPOP_TIMEOUT_SECONDS
    client = connect_redis("redis://127.0.0.1:1/0")
    kwargs = client.connection_pool.connection_kwargs
    assert kwargs["socket_timeout"] == _SOCKET_TIMEOUT_SECONDS


# I1: failure paths that used to leave a run RUNNING.


class _DeadOnRollback(FakeConnection):
    def rollback(self) -> None:
        raise OSError(2013, "Lost connection")


def test_a_lost_connection_reconnects_and_retries(schemas: Schemas) -> None:
    dead = _DeadOnRollback()
    fresh = FakeConnection()
    connections = [dead, fresh]
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        if len(calls) == 1:
            raise OSError(2013, "Lost connection")
        return DONE[JobType.PART1_RUN]

    redis = FakeRedis()
    definition = WorkerDefinition(JobType.PART1_RUN, handler, ("part1_max_retries",), "0.1.0")
    worker = Worker(definition, lambda: connections.pop(0), redis, schemas)
    worker.process_message(raw(JobType.PART1_RUN))
    assert len(calls) == 2
    assert [body["status"] for _, body in redis.pushed] == ["DONE"]
    assert fresh.closed


def test_a_retry_count_rejected_by_the_check_fails_the_run(schemas: Schemas) -> None:
    connection = FakeConnection()
    connection.fail_on = lambda q: (
        OSError(3819, "Check violated") if "retry_count = retry_count + 1" in q else None
    )
    error = JobError(ErrorCategory.DATA_UNAVAILABLE, "x")
    worker, redis = _worker(schemas, JobType.PART1_RUN, _raises(error), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    body = redis.pushed[0][1]
    assert body["status"] == "FAILED"
    assert body["error_category"] == "CONFIGURATION_ERROR"


def test_a_failed_completion_that_cant_be_built_still_finishes_the_run(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    connection = FakeConnection()
    definition = WorkerDefinition(
        JobType.PART1_RUN, _raises(JobError(ErrorCategory.PRECONDITION_FAILED, "x")), (), "v" * 41
    )
    worker = Worker(definition, lambda: connection, FakeRedis(connection), schemas)
    connection.settings = [("part1_max_retries", "1", "INT")]
    worker.process_message(raw(JobType.PART1_RUN))
    assert "commit" in connection.events
    assert any(query.startswith("UPDATE part1_runs SET status = %s") for query, _ in connection.log)
    assert any(f["event"] == "completion_not_possible" for f in _fields(caplog))


@pytest.mark.parametrize("version", ["", "v" * 41])
def test_a_bad_worker_version_stops_startup(version: str) -> None:
    definition = WorkerDefinition(JobType.PART1_RUN, _raises(RuntimeError()), (), version)
    assert run_worker(definition, _connect(GOOD_ROWS), lambda _url: _Redis(), ENV) == 1


def test_a_handler_calling_exit_fails_the_job_not_the_worker(schemas: Schemas) -> None:
    def handler(_context: JobContext) -> JobResult:
        sys.exit(3)

    worker, redis = _worker(schemas, JobType.PART1_RUN, handler, FakeConnection())
    worker.process_message(raw(JobType.PART1_RUN))
    assert redis.pushed[0][1]["error_category"] == "INTERNAL_ERROR"


# I2: a database outage must not drain the queue.


def test_a_database_outage_leaves_messages_in_the_queue(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    attempts: list[int] = []
    pops: list[int] = []

    class Queue(FakeRedis):
        def blpop(self, keys: Any, timeout: Any = 0) -> Any:
            pops.append(1)
            return None

    def connect() -> FakeConnection:
        attempts.append(1)
        if len(attempts) == 2:
            worker.stop()
        raise OSError("database down")

    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    worker = Worker(definition, connect, Queue(), schemas)
    worker.run()
    assert not pops
    assert any(f["event"] == "database_unavailable" for f in _fields(caplog))


def test_the_loop_gives_the_held_connection_to_the_job(schemas: Schemas) -> None:
    connection = FakeConnection()
    made: list[int] = []

    def connect() -> FakeConnection:
        made.append(1)
        return connection

    class Queue(FakeRedis):
        def blpop(self, keys: Any, timeout: Any = 0) -> Any:
            worker.stop()
            return (b"queue:part1", raw(JobType.PART1_RUN))

    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    connection.settings = [("part1_max_retries", "1", "INT")]
    worker = Worker(definition, connect, Queue(connection), schemas)
    worker.run()
    assert len(made) == 1
    assert connection.closed
    assert "commit" in connection.events


def test_an_idle_poll_closes_its_connection(schemas: Schemas) -> None:
    connection = FakeConnection()

    class Queue(FakeRedis):
        def blpop(self, keys: Any, timeout: Any = 0) -> Any:
            worker.stop()
            return None

    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    worker = Worker(definition, lambda: connection, Queue(), schemas)
    worker.run()
    assert connection.closed


def test_a_dropped_message_closes_the_held_connection(schemas: Schemas) -> None:
    connection = FakeConnection()
    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    worker = Worker(definition, lambda: connection, FakeRedis(), schemas)
    worker.process_message(b"not json", connection)
    assert connection.closed


# I4: the one log line for a failed job must say which job.


def test_job_handling_failed_names_the_job(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    def connect() -> FakeConnection:
        raise OSError("database down")

    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    worker = Worker(definition, connect, FakeRedis(), schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=9, contract_version="1.3"))
    entry = next(f for f in _fields(caplog) if f["event"] == "job_handling_failed")
    assert entry["run_id"] == 9
    assert entry["contract_version"] == "1.3"
    assert entry["job_id"]
    assert entry["job_type"] == "PART1_RUN"


def test_a_failed_job_logs_why(schemas: Schemas, caplog: pytest.LogCaptureFixture) -> None:
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "no plan")
    worker, _ = _worker(schemas, JobType.PART1_RUN, _raises(error), FakeConnection())
    worker.process_message(raw(JobType.PART1_RUN))
    entry = next(f for f in _fields(caplog) if f["event"] == "job_failed")
    assert entry["reason"] == "no plan"


# I5 and M7: result_detail on a failed run.


@pytest.mark.parametrize(
    ("job", "position"), [(JobType.BAPLIE_PARSE, 2), (JobType.YARD_PLACEMENT, 3)]
)
def test_technical_failures_store_failure_reason(
    schemas: Schemas, job: JobType, position: int
) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "why")
    worker, _ = _worker(schemas, job, _raises(error), connection)
    worker.process_message(raw(job))
    query, args = connection.updates(RUN_TABLES[job].table)[-1]
    assert isinstance(args, tuple)
    assert "result_detail = %s" in query
    assert json.loads(args[position]) == {
        "failure_reason": {"error_category": "PRECONDITION_FAILED", "message": "why"}
    }


def test_the_edi_failed_row_records_the_worker_version(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x")
    worker, _ = _worker(schemas, JobType.BAPLIE_PARSE, _raises(error), connection)
    worker.process_message(raw(JobType.BAPLIE_PARSE))
    query, args = connection.updates("baplie_parse_runs")[-1]
    assert "worker_version = %s" in query
    assert isinstance(args, tuple)
    assert "0.1.0" in args


def test_the_failure_message_is_capped_at_the_contract_limit(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x" * 5000)
    worker, _ = _worker(schemas, JobType.PART2_SOLVE, _raises(error), connection)
    worker.process_message(raw(JobType.PART2_SOLVE))
    _, args = connection.updates("solver_runs")[-1]
    assert isinstance(args, tuple)
    assert len(json.loads(args[1])["failure_reason"]["message"]) == 1000


def test_a_yard_failure_clears_confidence(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x")
    worker, _ = _worker(schemas, JobType.YARD_PLACEMENT, _raises(error), connection)
    worker.process_message(raw(JobType.YARD_PLACEMENT))
    query, _ = connection.updates("terminal_recommendations")[-1]
    assert "confidence = NULL" in query


# I6: exception text can hold secrets from a provider or driver.


def _format_with_exception(error: Exception) -> str:
    try:
        raise error
    except type(error):
        record = logging.LogRecord(
            "x", logging.ERROR, __file__, 1, "job_attempt_failed", None, sys.exc_info()
        )
    return JsonFormatter().format(record)


def test_exception_text_is_not_logged() -> None:
    line = _format_with_exception(RuntimeError(f"401 for url https://api/x?apikey={SECRET}"))
    entry = json.loads(line)
    assert SECRET not in line
    assert entry["exception"] == "RuntimeError"
    assert "test_failure_paths" in entry["traceback"]


def test_a_chained_cause_is_not_logged() -> None:
    try:
        try:
            raise ValueError(SECRET)
        except ValueError as cause:
            raise RuntimeError("outer") from cause
    except RuntimeError:
        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "e", None, sys.exc_info())
    assert SECRET not in JsonFormatter().format(record)


def test_a_failed_job_doesnt_log_unexpected_exception_text(
    schemas: Schemas, capsys: pytest.CaptureFixture[str]
) -> None:
    from common.runtime.logs import LOGGER, configure_logging

    state = (list(LOGGER.handlers), LOGGER.propagate, LOGGER.level)
    configure_logging()
    try:
        error = RuntimeError(f"apikey={SECRET}")
        worker, _ = _worker(schemas, JobType.PART1_RUN, _raises(error), FakeConnection())
        worker.process_message(raw(JobType.PART1_RUN))
    finally:
        LOGGER.handlers[:], LOGGER.propagate, LOGGER.level = state[0], state[1], state[2]
    assert SECRET not in capsys.readouterr().out


def test_log_event_passes_the_exception_to_the_record(caplog: pytest.LogCaptureFixture) -> None:
    try:
        raise ValueError("x")
    except ValueError:
        log_event(logging.ERROR, "e", {}, exc_info=True)
    assert caplog.records[-1].exc_info


# I7: anything wrong with Redis at startup.


def test_a_bad_redis_url_fails_startup_without_echoing_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    env = {**ENV, "AI_REDIS_URL": f"redis://:{SECRET}/x@h:6379/0"}

    def redis_for(url: str) -> _Redis:
        raise ValueError(f"Port could not be cast: {url}")

    assert run_worker(_definition(), _connect(GOOD_ROWS), redis_for, env) == 1
    output = capsys.readouterr()
    assert "startup_failed" in output.out
    assert SECRET not in output.out + output.err


def test_an_unreachable_redis_fails_startup() -> None:
    class Down(_Redis):
        def ping(self) -> bool:
            raise OSError("no route")

    assert run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: Down(), ENV) == 1


def _definition() -> WorkerDefinition:
    return WorkerDefinition(
        JobType.PART1_RUN, _raises(RuntimeError()), ("part1_max_retries",), "0.1.0"
    )


# I8: a transient failure before the settings are known.


@pytest.mark.parametrize("job", [JobType.PART1_RUN, JobType.PART2_SOLVE])
def test_a_transient_settings_failure_is_retried(schemas: Schemas, job: JobType) -> None:
    connection = FakeConnection()
    failures = [OSError("blip")]
    connection.fail_on = lambda q: (
        failures.pop() if failures and q.startswith("SELECT setting_key") else None
    )
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        return DONE[job]

    worker, redis = _worker(schemas, job, handler, connection)
    worker.process_message(raw(job))
    assert calls == [1]
    assert [body["status"] for _, body in redis.pushed] == ["DONE"]


# M1, M3, M4, M5, M8, M10: smaller rules.


def test_uncapped_values_dont_reach_the_logs(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    worker, _ = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), FakeConnection())
    worker.process_message(raw(JobType.PART1_RUN, job_type="X" * 5000, contract_version="1" * 5000))
    entry = next(f for f in _fields(caplog) if f["event"] == "wrong_queue_dropped")
    assert len(entry["job_type"]) <= 80
    assert len(entry["contract_version"]) <= 80


def test_a_handler_cant_override_the_core_completion_fields(schemas: Schemas) -> None:
    bad = JobResult(
        "WINDOWS_FOUND", completion_fields={"entry_window_proposal_id": 4, "run_id": 999}
    )
    worker, redis = _worker(schemas, JobType.PART1_RUN, lambda _c: bad, FakeConnection())
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert redis.pushed[0][1]["status"] == "FAILED"
    assert redis.pushed[0][1]["run_id"] == 1


@pytest.mark.parametrize("status", ["QUEUED", "RUNNING", "DONE"])
def test_a_solver_handler_cant_set_a_status_outside_the_contract(
    schemas: Schemas, status: str
) -> None:
    bad = JobResult("SOLVED", run_columns={"status": status})
    worker, redis = _worker(schemas, JobType.PART2_SOLVE, lambda _c: bad, FakeConnection())
    worker.process_message(raw(JobType.PART2_SOLVE))
    assert redis.pushed[0][1]["status"] == "FAILED"


def test_a_swept_solver_run_isnt_retried(schemas: Schemas) -> None:
    connection = FakeConnection()
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        connection.running = False
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, "x")

    worker, redis = _worker(schemas, JobType.PART2_SOLVE, handler, connection)
    worker.process_message(raw(JobType.PART2_SOLVE))
    assert calls == [1]
    assert not redis.pushed


def test_the_log_says_when_the_recommendation_moved_on(
    schemas: Schemas, caplog: pytest.LogCaptureFixture
) -> None:
    connection = FakeConnection()
    connection.yard_requested = False
    error = JobError(ErrorCategory.PRECONDITION_FAILED, "x")
    worker, _ = _worker(schemas, JobType.YARD_PLACEMENT, _raises(error), connection)
    worker.process_message(raw(JobType.YARD_PLACEMENT))
    assert any(f["event"] == "job_state_changed" for f in _fields(caplog))


def test_validation_survives_a_failing_rollback(schemas: Schemas) -> None:
    connection = _DeadOnRollback()
    worker, redis = _worker(schemas, JobType.VALIDATION, _done(JobType.VALIDATION), connection)
    worker.process_message(raw(JobType.VALIDATION))
    assert redis.pushed[0][1]["status"] == "DONE"


def test_validation_sends_failed_when_the_database_is_down(schemas: Schemas) -> None:
    def connect() -> _Connection:
        raise OSError("database down")

    redis = FakeRedis()
    definition = WorkerDefinition(JobType.VALIDATION, _done(JobType.VALIDATION), (), "0.1.0")
    worker = Worker(definition, connect, redis, schemas)
    worker.process_message(raw(JobType.VALIDATION))
    assert redis.pushed[0][1]["status"] == "FAILED"
    assert redis.pushed[0][1]["error_category"] == "INTERNAL_ERROR"


# Gaps the review's surviving mutations showed.


def test_yard_cant_report_solver_error(schemas: Schemas) -> None:
    error = JobError(ErrorCategory.SOLVER_ERROR, "x")
    worker, redis = _worker(schemas, JobType.YARD_PLACEMENT, _raises(error), FakeConnection())
    worker.process_message(raw(JobType.YARD_PLACEMENT))
    assert redis.pushed[0][1]["error_category"] == "INTERNAL_ERROR"


def test_validation_cant_report_infeasible(schemas: Schemas) -> None:
    error = JobError(ErrorCategory.INFEASIBLE, "x")
    worker, redis = _worker(schemas, JobType.VALIDATION, _raises(error), FakeConnection())
    worker.process_message(raw(JobType.VALIDATION))
    assert redis.pushed[0][1]["error_category"] == "INTERNAL_ERROR"


def test_each_job_checks_cross_field_settings(schemas: Schemas) -> None:
    connection = FakeConnection()
    connection.settings = [
        ("validation_result_ttl_seconds", "1", "INT"),
        ("validation_timeout_seconds", "9", "INT"),
        ("part1_max_retries", "1", "INT"),
    ]
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        return DONE[JobType.PART1_RUN]

    keys = ("validation_result_ttl_seconds", "validation_timeout_seconds", "part1_max_retries")
    redis = FakeRedis()
    definition = WorkerDefinition(JobType.PART1_RUN, handler, keys, "0.1.0")
    Worker(definition, lambda: connection, redis, schemas).process_message(raw(JobType.PART1_RUN))
    assert not calls
    assert redis.pushed[0][1]["error_category"] == "CONFIGURATION_ERROR"


def test_settings_are_read_once_per_job_not_per_attempt(schemas: Schemas) -> None:
    connection = FakeConnection()
    error = JobError(ErrorCategory.DATA_UNAVAILABLE, "x")
    worker, _ = _worker(schemas, JobType.PART1_RUN, _raises(error), connection)
    worker.process_message(raw(JobType.PART1_RUN))
    reads = [query for query, _ in connection.log if query.startswith("SELECT setting_key")]
    assert len(reads) == 1


def test_the_claim_is_committed_before_the_handler(schemas: Schemas) -> None:
    connection = FakeConnection()

    def handler(_context: JobContext) -> JobResult:
        connection.events.append("handler")
        return DONE[JobType.PART1_RUN]

    worker, _ = _worker(schemas, JobType.PART1_RUN, handler, connection)
    worker.process_message(raw(JobType.PART1_RUN))
    before = connection.events[: connection.events.index("handler")]
    assert before.count("commit") == 2


def test_invalid_message_connections_are_closed(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, _ = _worker(schemas, JobType.PART1_RUN, _done(JobType.PART1_RUN), connection)
    worker.process_message(raw(JobType.PART1_RUN, payload={}))
    assert connection.closed


def test_validation_connections_are_closed(schemas: Schemas) -> None:
    connection = FakeConnection()
    worker, _ = _worker(schemas, JobType.VALIDATION, _done(JobType.VALIDATION), connection)
    worker.process_message(raw(JobType.VALIDATION))
    assert connection.closed


def test_the_startup_connection_is_closed() -> None:
    closed: list[int] = []

    class Tracked(_Connection):
        def close(self) -> None:
            closed.append(1)

    def connect(_settings: EnvSettings) -> Tracked:
        return Tracked(GOOD_ROWS)

    definition = _definition()
    assert run_worker(definition, connect, lambda _url: _Redis(), ENV) == 0
    assert closed


def test_sigint_also_stops_the_worker() -> None:
    class Interrupt(_Redis):
        def blpop(self, keys: Any, timeout: Any = 0) -> None:
            signal.raise_signal(signal.SIGINT)

    assert run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: Interrupt(), ENV) == 0


def test_the_queue_read_retry_waits(schemas: Schemas, monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []
    monkeypatch.setattr("common.runtime.worker.time.sleep", waits.append)

    class Queue(FakeRedis):
        def blpop(self, keys: Any, timeout: Any = 0) -> Any:
            worker.stop()
            raise OSError("redis down")

    definition = WorkerDefinition(JobType.PART1_RUN, _done(JobType.PART1_RUN), (), "0.1.0")
    worker = Worker(definition, FakeConnection, Queue(), schemas)
    worker.run()
    assert waits
