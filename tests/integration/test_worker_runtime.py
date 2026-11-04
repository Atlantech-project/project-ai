"""AI-011 against real MySQL and Redis: the acceptance criteria and every table's constraints."""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pymysql
import pytest
import redis

from common.config import EnvSettings
from common.db.connection import connect_worker
from common.runtime import worker as worker_module
from common.runtime.envelope import QUEUES, JobType, Schemas, load_schemas
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.runs import RUN_TABLES
from common.runtime.worker import (
    _BLPOP_TIMEOUT_SECONDS as BLPOP_TIMEOUT_SECONDS,
)
from common.runtime.worker import (
    AI_RESULTS_QUEUE,
    JobContext,
    JobResult,
    Worker,
    WorkerDefinition,
    connect_redis,
)
from tests.support.runtime_messages import raw
from tests.support.services import ServiceSettings

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "docs" / "ref" / "ai-payloads"
TABLES_SQL = REPO_ROOT / "tests" / "support" / "run_tables.sql"
TABLES = [
    "part1_runs",
    "solver_runs",
    "yard_runs",
    "baplie_parse_runs",
    "terminal_recommendations",
    "baplie_files",
    "port_settings",
]
PORT_SETTINGS = """
CREATE TABLE port_settings (
  id bigint unsigned NOT NULL AUTO_INCREMENT,
  setting_key varchar(80) NOT NULL,
  setting_value varchar(255) NOT NULL,
  value_type enum('INT','DECIMAL','BOOL','STRING','JSON') NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY setting_key (setting_key)
)
"""
DONE: dict[JobType, JobResult] = {
    JobType.PART1_RUN: JobResult(
        "WINDOWS_FOUND",
        run_columns={"entry_window_proposal_id": 4},
        completion_fields={"entry_window_proposal_id": 4},
    ),
    JobType.PART2_SOLVE: JobResult(
        "SOLVED",
        run_columns={
            "status": "OPTIMAL",
            "solve_time_ms": 5,
            "result_detail": {"outcome": "SOLVED", "failure_reason": None, "requests": []},
        },
    ),
    JobType.YARD_PLACEMENT: JobResult(
        "YARD_REC_GENERATED", completion_fields={"terminal_recommendation_id": 1}
    ),
    JobType.BAPLIE_PARSE: JobResult(
        "PARSED", run_columns={"container_count": 3}, completion_fields={"baplie_file_id": 1}
    ),
}
RUN_JOBS = list(DONE)
NEW_ROWS = {
    JobType.PART1_RUN: "INSERT INTO part1_runs (berthing_request_id) VALUES (1)",
    JobType.PART2_SOLVE: (
        "INSERT INTO solver_runs (trigger_type, horizon_start, horizon_end, solver_version, "
        "queued_at) VALUES ('NEW_REQUEST', '2026-11-03', '2026-11-04', '1', '2026-11-03')"
    ),
    JobType.YARD_PLACEMENT: "INSERT INTO yard_runs (terminal_recommendation_id) VALUES (1)",
    JobType.BAPLIE_PARSE: "INSERT INTO baplie_parse_runs (baplie_file_id) VALUES (1)",
}


def _execute(conn: pymysql.connections.Connection, sql: str, args: Any = None) -> None:
    with conn.cursor() as cursor:
        cursor.execute(sql, args)
    conn.commit()


def _one_on(conn: Any, sql: str) -> Any:
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
    finally:
        cursor.close()
    return row[0]


def _one(conn: pymysql.connections.Connection, sql: str) -> Any:
    with conn.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    conn.commit()
    assert row is not None
    return row


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return load_schemas(SCHEMA_DIR)


@pytest.fixture
def db(mysql_conn: pymysql.connections.Connection) -> Iterator[pymysql.connections.Connection]:
    def drop() -> None:
        for table in TABLES:
            _execute(mysql_conn, f"DROP TABLE IF EXISTS {table}")

    drop()
    for statement in TABLES_SQL.read_text(encoding="utf-8").split(";\n"):
        if "CREATE TABLE" in statement:
            _execute(mysql_conn, statement)
    _execute(mysql_conn, PORT_SETTINGS)
    _execute(
        mysql_conn,
        "INSERT INTO port_settings (setting_key, setting_value, value_type) "
        "VALUES ('part1_max_retries', '2', 'INT')",
    )
    _execute(
        mysql_conn,
        "INSERT INTO terminal_recommendations (rec_type, lifecycle_status) "
        "VALUES ('YARD_PLACEMENT', 'YARD_REC_REQUESTED')",
    )
    _execute(mysql_conn, "INSERT INTO baplie_files (parse_status) VALUES ('PENDING')")
    yield mysql_conn
    drop()


@pytest.fixture
def queues(redis_client: redis.Redis) -> Iterator[redis.Redis]:
    keys = [*QUEUES.values(), AI_RESULTS_QUEUE]
    redis_client.delete(*keys)
    yield redis_client
    redis_client.delete(*keys)


def _worker(
    job: JobType,
    handler: Callable[[JobContext], JobResult],
    settings: ServiceSettings,
    client: Any,
    schemas: Schemas,
) -> Worker:
    definition = WorkerDefinition(job, handler, ("part1_max_retries",), "0.1.0")
    env = EnvSettings(
        settings.mysql_host,
        settings.mysql_port,
        settings.mysql_database,
        settings.mysql_user,
        settings.mysql_password,
        settings.redis_url,
    )
    return Worker(definition, lambda: connect_worker(env), client, schemas)


def _completions(client: redis.Redis) -> list[dict[str, Any]]:
    return [json.loads(item) for item in client.lrange(AI_RESULTS_QUEUE, 0, -1)]


# Criterion: "Duplicate delivery of a job executes once (test)"


@pytest.mark.parametrize("job", RUN_JOBS)
def test_duplicate_delivery_runs_once_and_sends_one_completion(
    job: JobType,
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[job])
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        return DONE[job]

    worker = _worker(job, handler, service_settings, queues, schemas)
    message = raw(job, run_id=1)
    worker.process_message(message)
    worker.process_message(message)
    assert len(calls) == 1
    assert len(_completions(queues)) == 1
    table = RUN_TABLES[job].table
    status, finished = _one(db, f"SELECT status, finished_at FROM {table} WHERE id = 1")  # noqa: S608
    assert status in {"DONE", "OPTIMAL"}
    assert finished is not None


def test_two_workers_racing_on_one_message_run_it_once(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    calls: list[int] = []
    lock = threading.Lock()

    def handler(_context: JobContext) -> JobResult:
        with lock:
            calls.append(1)
        return DONE[JobType.PART1_RUN]

    message = raw(JobType.PART1_RUN, run_id=1)
    workers = [
        _worker(JobType.PART1_RUN, handler, service_settings, queues, schemas) for _ in range(4)
    ]
    threads = [threading.Thread(target=w.process_message, args=(message,)) for w in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1
    assert len(_completions(queues)) == 1


# Criterion: "Invalid envelope is rejected and logged without crashing the worker"


def test_invalid_messages_are_logged_and_the_next_job_still_runs(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_module, "_BLPOP_TIMEOUT_SECONDS", 1)
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    worker = _worker(
        JobType.PART1_RUN, lambda _c: DONE[JobType.PART1_RUN], service_settings, queues, schemas
    )
    queue = QUEUES[JobType.PART1_RUN]
    queues.rpush(queue, b"not json", raw(JobType.PART1_RUN, run_id=1, payload={}))
    queues.rpush(queue, raw(JobType.PART2_SOLVE, run_id=1))
    queues.rpush(queue, raw(JobType.PART1_RUN, run_id=2))
    thread = threading.Thread(target=worker.run)
    thread.start()
    deadline = time.monotonic() + 20
    while queues.llen(AI_RESULTS_QUEUE) < 2 and time.monotonic() < deadline:
        time.sleep(0.05)
    worker.stop()
    thread.join(timeout=10)
    assert not thread.is_alive()

    bodies = _completions(queues)
    assert [(b["run_id"], b["status"]) for b in bodies] == [(1, "FAILED"), (2, "DONE")]
    assert bodies[0]["error_category"] == "INVALID_ENVELOPE"
    events = {record.getMessage(): record for record in caplog.records}
    assert "invalid_message_dropped" in events
    assert events["wrong_queue_dropped"].levelno == logging.ERROR
    assert _one(db, "SELECT status FROM part1_runs WHERE id = 1")[0] == "FAILED"


def test_wrong_queue_never_touches_a_run_with_the_same_id(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    worker = _worker(
        JobType.PART1_RUN, lambda _c: DONE[JobType.PART1_RUN], service_settings, queues, schemas
    )
    worker.process_message(raw(JobType.PART2_SOLVE, run_id=1))
    assert _one(db, "SELECT status FROM part1_runs WHERE id = 1")[0] == "QUEUED"
    assert not _completions(queues)


# Criterion: "Stale RUNNING run is swept per contract" (CT-08 §6: the Backend sweeps)


@pytest.mark.parametrize(
    ("job", "column"),
    [
        (JobType.PART1_RUN, "status = 'FAILED', finished_at = UTC_TIMESTAMP()"),
        (JobType.PART1_RUN, "status = 'REPLACED'"),
        (JobType.PART2_SOLVE, "status = 'ERROR', finished_at = UTC_TIMESTAMP()"),
        (
            JobType.YARD_PLACEMENT,
            "status = 'FAILED', outcome = 'GENERATION_FAILED', error_category = 'TIMEOUT', "
            "finished_at = UTC_TIMESTAMP()",
        ),
        (
            JobType.BAPLIE_PARSE,
            "status = 'FAILED', error_category = 'TIMEOUT', finished_at = UTC_TIMESTAMP()",
        ),
    ],
)
def test_a_run_swept_during_the_job_rolls_back_and_sends_nothing(
    job: JobType,
    column: str,
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[job])
    table = RUN_TABLES[job].table

    def handler(context: JobContext) -> JobResult:
        # A result row written by the job, then the Backend's sweeper acts on the run.
        with context.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute("INSERT INTO baplie_files (parse_status) VALUES ('PARSED')")
        _execute(db, f"UPDATE {table} SET {column} WHERE id = 1")  # noqa: S608
        return DONE[job]

    worker = _worker(job, handler, service_settings, queues, schemas)
    worker.process_message(raw(job, run_id=1))
    assert not _completions(queues)
    assert _one(db, "SELECT COUNT(*) FROM baplie_files")[0] == 1


def test_a_run_no_longer_queued_is_not_claimed(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    _execute(db, "UPDATE part1_runs SET status = 'REPLACED' WHERE id = 1")
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        return DONE[JobType.PART1_RUN]

    worker = _worker(JobType.PART1_RUN, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert not calls
    assert not _completions(queues)


# Commit before C-06, retries and every table's constraints


def test_completion_is_sent_only_after_the_commit(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    seen: list[str] = []

    class Spy:
        def ping(self) -> bool:
            return True

        def blpop(self, keys: Any, timeout: Any = 0) -> None:
            return None

        def rpush(self, name: Any, *values: Any) -> int:
            # A separate connection: it sees only what's committed.
            seen.append(_one(db, "SELECT status FROM part1_runs WHERE id = 1")[0])
            return int(queues.rpush(name, *values))

    worker = _worker(
        JobType.PART1_RUN, lambda _c: DONE[JobType.PART1_RUN], service_settings, Spy(), schemas
    )
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert seen == ["DONE"]


@pytest.mark.parametrize(
    ("job", "attempts", "counted"),
    [
        (JobType.PART1_RUN, 3, 2),
        (JobType.YARD_PLACEMENT, 2, 1),
        (JobType.BAPLIE_PARSE, 2, 1),
    ],
)
def test_retries_are_counted_and_one_completion_follows_the_last_attempt(
    job: JobType,
    attempts: int,
    counted: int,
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[job])
    calls: list[int] = []

    def handler(_context: JobContext) -> JobResult:
        calls.append(1)
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, "provider down")

    worker = _worker(job, handler, service_settings, queues, schemas)
    worker.process_message(raw(job, run_id=1))
    assert len(calls) == attempts
    table = RUN_TABLES[job].table
    assert _one(db, f"SELECT retry_count FROM {table} WHERE id = 1")[0] == counted  # noqa: S608
    assert [b["status"] for b in _completions(queues)] == ["FAILED"]


@pytest.mark.parametrize("job", RUN_JOBS)
def test_the_constraints_accept_every_failed_row(
    job: JobType,
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[job])
    worker = _worker(job, lambda _c: DONE[job], service_settings, queues, schemas)
    worker.process_message(raw(job, run_id=1, payload={}))
    bodies = _completions(queues)
    assert len(bodies) == 1
    assert bodies[0]["status"] == "FAILED"
    table = RUN_TABLES[job].table
    assert _one(db, f"SELECT finished_at FROM {table} WHERE id = 1")[0] is not None  # noqa: S608


def test_yard_failure_writes_the_recommendation(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.YARD_PLACEMENT])

    def handler(_context: JobContext) -> JobResult:
        raise JobError(ErrorCategory.INFEASIBLE, "no slots")

    worker = _worker(JobType.YARD_PLACEMENT, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.YARD_PLACEMENT, run_id=1))
    status, reason = _one(
        db, "SELECT lifecycle_status, failure_reason FROM terminal_recommendations WHERE id = 1"
    )
    assert status == "GENERATION_FAILED"
    assert reason == "INFEASIBLE: no slots"
    body = _completions(queues)[0]
    assert body["terminal_recommendation_id"] == 1
    assert body["outcome"] == "GENERATION_FAILED"


def test_edi_failure_marks_the_file(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.BAPLIE_PARSE])

    def handler(_context: JobContext) -> JobResult:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, "no file")

    worker = _worker(JobType.BAPLIE_PARSE, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.BAPLIE_PARSE, run_id=1))
    assert _one(db, "SELECT parse_status FROM baplie_files WHERE id = 1")[0] == "FAILED"
    assert _completions(queues)[0]["baplie_file_id"] == 1


def test_a_real_check_violation_is_a_configuration_error_without_retry(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    calls: list[int] = []

    def handler(context: JobContext) -> JobResult:
        calls.append(1)
        with context.connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute("UPDATE part1_runs SET retry_count = 9 WHERE id = 1")
        return DONE[JobType.PART1_RUN]

    worker = _worker(JobType.PART1_RUN, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert len(calls) == 1
    assert _completions(queues)[0]["error_category"] == "CONFIGURATION_ERROR"


def test_a_setting_above_the_check_fails_the_job_clearly(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    _execute(db, "UPDATE port_settings SET setting_value = '10'")
    worker = _worker(
        JobType.PART1_RUN, lambda _c: DONE[JobType.PART1_RUN], service_settings, queues, schemas
    )
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert _completions(queues)[0]["error_category"] == "CONFIGURATION_ERROR"
    assert _one(db, "SELECT status FROM part1_runs WHERE id = 1")[0] == "FAILED"
    assert "chk_p1r_retry" in caplog.text


def test_a_changed_setting_applies_to_the_next_job(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    seen: list[int] = []

    def handler(context: JobContext) -> JobResult:
        seen.append(context.settings.get_int("part1_max_retries"))
        return DONE[JobType.PART1_RUN]

    worker = _worker(JobType.PART1_RUN, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    _execute(db, "UPDATE port_settings SET setting_value = '3'")
    worker.process_message(raw(JobType.PART1_RUN, run_id=2))
    assert seen == [2, 3]


def test_validation_writes_nothing_and_a_duplicate_sends_again(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    result = JobResult(
        "VALID",
        completion_fields={
            "validation_result": {
                "validation_type": "OVERRIDE",
                "subject_id": 5,
                "valid": True,
                "violations": [],
            }
        },
    )
    worker = _worker(JobType.VALIDATION, lambda _c: result, service_settings, queues, schemas)
    message = raw(JobType.VALIDATION)
    worker.process_message(message)
    worker.process_message(message)
    assert [b["outcome"] for b in _completions(queues)] == ["VALID", "VALID"]


# Found by the independent review: only real services show these.


def test_an_idle_worker_with_the_real_client_logs_no_read_errors(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    client = connect_redis(service_settings.redis_url)
    worker = _worker(
        JobType.PART1_RUN, lambda _c: DONE[JobType.PART1_RUN], service_settings, client, schemas
    )
    thread = threading.Thread(target=worker.run)
    thread.start()
    time.sleep(BLPOP_TIMEOUT_SECONDS * 2 + 1)
    queues.rpush(QUEUES[JobType.PART1_RUN], raw(JobType.PART1_RUN, run_id=1))
    deadline = time.monotonic() + 15
    while not queues.llen(AI_RESULTS_QUEUE) and time.monotonic() < deadline:
        time.sleep(0.05)
    worker.stop()
    thread.join(timeout=BLPOP_TIMEOUT_SECONDS + 5)
    assert not thread.is_alive()
    assert [b["status"] for b in _completions(queues)] == ["DONE"]
    assert "queue_read_failed" not in [record.getMessage() for record in caplog.records]


def test_a_killed_connection_reconnects_and_the_retry_succeeds(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    attempts: list[int] = []

    def handler(context: JobContext) -> JobResult:
        attempts.append(context.attempt)
        if context.attempt == 0:
            own = _one_on(context.connection, "SELECT CONNECTION_ID()")
            _execute(db, f"KILL {own}")
            _one_on(context.connection, "SELECT 1")
        return DONE[JobType.PART1_RUN]

    worker = _worker(JobType.PART1_RUN, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert attempts == [0, 1]
    status, count = _one(db, "SELECT status, retry_count FROM part1_runs WHERE id = 1")
    assert status == "DONE"
    assert count == 1
    assert [b["status"] for b in _completions(queues)] == ["DONE"]


def test_a_retry_count_at_the_check_limit_fails_the_run_not_leaves_it_running(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    _execute(db, "UPDATE part1_runs SET retry_count = 3 WHERE id = 1")

    def handler(_context: JobContext) -> JobResult:
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, "x")

    worker = _worker(JobType.PART1_RUN, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=1))
    assert _one(db, "SELECT status FROM part1_runs WHERE id = 1")[0] == "FAILED"
    assert _completions(queues)[0]["error_category"] == "CONFIGURATION_ERROR"


def test_a_database_outage_leaves_the_message_on_the_real_queue(
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    def connect() -> Any:
        worker.stop()
        raise OSError("database down")

    definition = WorkerDefinition(
        JobType.PART1_RUN, lambda _c: DONE[JobType.PART1_RUN], (), "0.1.0"
    )
    worker = Worker(definition, connect, queues, schemas)
    queues.rpush(QUEUES[JobType.PART1_RUN], raw(JobType.PART1_RUN, run_id=1))
    worker.run()
    assert queues.llen(QUEUES[JobType.PART1_RUN]) == 1


def test_a_technical_edi_failure_stores_the_reason(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
    schemas: Schemas,
) -> None:
    _execute(db, NEW_ROWS[JobType.BAPLIE_PARSE])

    def handler(_context: JobContext) -> JobResult:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, "no file")

    worker = _worker(JobType.BAPLIE_PARSE, handler, service_settings, queues, schemas)
    worker.process_message(raw(JobType.BAPLIE_PARSE, run_id=1))
    detail = _one(db, "SELECT result_detail FROM baplie_parse_runs WHERE id = 1")[0]
    assert json.loads(detail)["failure_reason"]["message"] == "no file"


# A real process


@pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM can't be delivered on Windows")
def test_sigterm_finishes_the_current_job_then_exits_zero(
    db: pymysql.connections.Connection,
    queues: redis.Redis,
    service_settings: ServiceSettings,
) -> None:
    _execute(db, NEW_ROWS[JobType.PART1_RUN])
    queues.rpush(QUEUES[JobType.PART1_RUN], raw(JobType.PART1_RUN, run_id=1))
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "tests.integration.fake_worker"],
        cwd=REPO_ROOT,
        env=os.environ,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if _one(db, "SELECT status FROM part1_runs WHERE id = 1")[0] == "RUNNING":
                break
            time.sleep(0.05)
        process.send_signal(signal.SIGTERM)
        assert process.wait(timeout=30) == 0
    finally:
        process.kill()
    assert _one(db, "SELECT status FROM part1_runs WHERE id = 1")[0] == "DONE"
    assert [b["status"] for b in _completions(queues)] == ["DONE"]
