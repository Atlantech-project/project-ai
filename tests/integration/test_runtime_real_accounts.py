"""AI-013: the AI-011 runtime and AI-012 settings end to end under the real `w_*` accounts."""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pymysql
import pytest
import redis

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker
from common.db.repository import WorkerRepository
from common.runtime.envelope import QUEUES, JobType, Schemas, load_schemas
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.runs import RUN_TABLES
from common.runtime.worker import (
    AI_RESULTS_QUEUE,
    JobContext,
    JobResult,
    Worker,
    WorkerDefinition,
    run_worker,
)
from tests.support.port_db import REPO_ROOT, PortDatabase, seed_row
from tests.support.runtime_messages import raw

pytestmark = pytest.mark.integration

PARTS = {
    JobType.PART1_RUN: WorkerPart.PART1,
    JobType.PART2_SOLVE: WorkerPart.PART2,
    JobType.YARD_PLACEMENT: WorkerPart.YARD,
    JobType.BAPLIE_PARSE: WorkerPart.EDI,
    JobType.VALIDATION: WorkerPart.VALIDATE,
}
RUN_JOBS = [job for job in PARTS if job is not JobType.VALIDATION]
TABLES = [
    "part1_runs",
    "solver_runs",
    "yard_runs",
    "baplie_parse_runs",
    "terminal_recommendations",
    "baplie_files",
    "containers",
    "port_settings",
]
SETTING_KEYS = {JobType.PART1_RUN: ("part1_max_retries",)}
RECOMMENDATION_ID = 11
FILE_ID = 21


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return load_schemas(REPO_ROOT / "docs" / "ref" / "ai-payloads")


@pytest.fixture
def root(port_db: PortDatabase) -> Iterator[pymysql.connections.Connection[Any]]:
    conn = port_db.root()
    seed_row(
        conn, "port_settings", setting_key="part1_max_retries", setting_value="2", value_type="INT"
    )
    seed_row(
        conn,
        "terminal_recommendations",
        id=RECOMMENDATION_ID,
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    seed_row(conn, "baplie_files", id=FILE_ID, parse_status="PENDING")
    try:
        yield conn
    finally:
        try:
            with conn.cursor() as cursor:
                for table in TABLES:
                    cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608
            conn.commit()
        finally:
            conn.close()


@pytest.fixture
def queues(redis_client: redis.Redis) -> Iterator[redis.Redis]:
    keys = [*QUEUES.values(), AI_RESULTS_QUEUE]
    redis_client.delete(*keys)
    yield redis_client
    redis_client.delete(*keys)


def _seed_run(root: pymysql.connections.Connection[Any], job: JobType) -> int:
    table = RUN_TABLES[job].table
    extra: dict[str, object] = {}
    if job is JobType.YARD_PLACEMENT:
        extra["terminal_recommendation_id"] = RECOMMENDATION_ID
    if job is JobType.BAPLIE_PARSE:
        extra["baplie_file_id"] = FILE_ID
    return seed_row(root, table, status="QUEUED", **extra)


def _worker(
    job: JobType,
    handler: Callable[[JobContext], JobResult],
    port_db: PortDatabase,
    client: Any,
    schemas: Schemas,
) -> Worker:
    part = PARTS[job]
    settings = load_env_settings(port_db.worker_env(part), part)
    definition = WorkerDefinition(job, handler, SETTING_KEYS.get(job, ()), "0.1.0")
    return Worker(definition, lambda: connect_worker(settings), client, schemas)


def _one(root: pymysql.connections.Connection[Any], sql: str) -> Any:
    root.commit()
    with root.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    root.commit()
    assert row is not None
    return row


def _completions(client: redis.Redis) -> list[dict[str, Any]]:
    return [json.loads(item) for item in client.lrange(AI_RESULTS_QUEUE, 0, -1)]


def _done_result(job: JobType, context: JobContext) -> JobResult:
    """Write through the repository under the worker's own account, as a real handler will."""
    assert isinstance(context.connection, WorkerConnection)
    run_id = context.envelope.run_id
    if job is JobType.PART1_RUN:
        return JobResult("NO_FEASIBLE_WINDOW", completion_fields={"entry_window_proposal_id": None})
    if job is JobType.PART2_SOLVE:
        return JobResult(
            "SOLVED",
            run_columns={
                "status": "OPTIMAL",
                "solve_time_ms": 5,
                "result_detail": {"outcome": "SOLVED", "failure_reason": None, "requests": []},
            },
        )
    if job is JobType.YARD_PLACEMENT:
        repository = WorkerRepository(context.connection, WorkerPart.YARD, run_id)
        assert repository.lock_yard_result(RECOMMENDATION_ID)
        assert repository.update_terminal_recommendation(
            RECOMMENDATION_ID, {"lifecycle_status": "YARD_REC_GENERATED", "confidence": 1}
        )
        return JobResult(
            "YARD_REC_GENERATED",
            completion_fields={"terminal_recommendation_id": RECOMMENDATION_ID},
        )
    repository = WorkerRepository(context.connection, WorkerPart.EDI, run_id)
    assert repository.update_baplie_file(FILE_ID, {"parse_status": "PARSED"})
    return JobResult(
        "PARSED", run_columns={"container_count": 0}, completion_fields={"baplie_file_id": FILE_ID}
    )


@pytest.mark.parametrize("job", RUN_JOBS, ids=str)
def test_a_job_completes_under_its_own_account(
    job: JobType,
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    run = _seed_run(root, job)
    worker = _worker(job, lambda context: _done_result(job, context), port_db, queues, schemas)
    message = raw(job, run_id=run)
    worker.process_message(message)
    worker.process_message(message)
    table = RUN_TABLES[job].table
    status, started, finished = _one(
        root,
        f"SELECT status, started_at, finished_at FROM {table} WHERE id = {run}",  # noqa: S608
    )
    assert status in {"DONE", "OPTIMAL"}
    assert started is not None
    assert finished is not None
    completions = _completions(queues)
    assert [body["status"] for body in completions] == ["DONE"]
    assert completions[0]["run_id"] == run


@pytest.mark.parametrize("job", RUN_JOBS, ids=str)
def test_a_failed_job_records_it_under_its_own_account(
    job: JobType,
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    run = _seed_run(root, job)

    def handler(_context: JobContext) -> JobResult:
        raise JobError(ErrorCategory.CONFIGURATION_ERROR, "not retried")

    _worker(job, handler, port_db, queues, schemas).process_message(raw(job, run_id=run))
    spec = RUN_TABLES[job]
    table = spec.table
    assert _one(root, f"SELECT status FROM {table} WHERE id = {run}")[0] == spec.failed_status  # noqa: S608
    assert [body["status"] for body in _completions(queues)] == ["FAILED"]
    if job is JobType.YARD_PLACEMENT:
        assert (
            _one(
                root,
                "SELECT lifecycle_status FROM terminal_recommendations "  # noqa: S608
                f"WHERE id = {RECOMMENDATION_ID}",
            )[0]
            == "GENERATION_FAILED"
        )
    if job is JobType.BAPLIE_PARSE:
        assert (
            _one(root, f"SELECT parse_status FROM baplie_files WHERE id = {FILE_ID}")[0]  # noqa: S608
            == "FAILED"
        )


@pytest.mark.parametrize("job", RUN_JOBS, ids=str)
def test_a_retry_counts_under_its_own_account(
    job: JobType,
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    run = _seed_run(root, job)
    attempts: list[int] = []

    def handler(context: JobContext) -> JobResult:
        attempts.append(context.attempt)
        if len(attempts) == 1:
            raise JobError(ErrorCategory.DATA_UNAVAILABLE, "try again")
        return _done_result(job, context)

    _worker(job, handler, port_db, queues, schemas).process_message(raw(job, run_id=run))
    assert len(attempts) == 2
    assert [body["status"] for body in _completions(queues)] == ["DONE"]
    if RUN_TABLES[job].has_retry_count:
        table = RUN_TABLES[job].table
        assert _one(root, f"SELECT retry_count FROM {table} WHERE id = {run}")[0] == 1  # noqa: S608


def test_validation_runs_under_a_select_only_account(
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    def handler(context: JobContext) -> JobResult:
        cursor = context.connection.cursor()
        cursor.execute("SELECT CURRENT_USER()")
        assert cursor.fetchone() == ("w_validate@%",)
        cursor.close()
        return JobResult("VALID")

    worker = _worker(JobType.VALIDATION, handler, port_db, queues, schemas)
    worker.process_message(raw(JobType.VALIDATION))
    assert _one(root, "SELECT COUNT(*) FROM port_settings")[0] == 1


def test_a_check_violation_through_the_repository_fails_without_retry(
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    run = _seed_run(root, JobType.BAPLIE_PARSE)
    attempts: list[int] = []

    def handler(context: JobContext) -> JobResult:
        attempts.append(context.attempt)
        repository = WorkerRepository(context.connection, WorkerPart.EDI, run)
        repository.insert_new_containers([{"container_number": "lowercase", "size_type_id": 1}])
        return JobResult("PARSED")

    worker = _worker(JobType.BAPLIE_PARSE, handler, port_db, queues, schemas)
    worker.process_message(raw(JobType.BAPLIE_PARSE, run_id=run))
    assert len(attempts) == 1
    status, category = _one(
        root,
        f"SELECT status, error_category FROM baplie_parse_runs WHERE id = {run}",  # noqa: S608
    )
    assert (status, category) == ("FAILED", "CONFIGURATION_ERROR")
    assert _one(root, "SELECT COUNT(*) FROM containers")[0] == 0


def test_a_handler_failure_rolls_back_its_writes(
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    run = _seed_run(root, JobType.BAPLIE_PARSE)
    seen: list[str] = []

    def handler(context: JobContext) -> JobResult:
        repository = WorkerRepository(context.connection, WorkerPart.EDI, run)
        assert repository.update_baplie_file(FILE_ID, {"staged_payload": {"partial": True}})
        seen.append("wrote")
        raise JobError(ErrorCategory.CONFIGURATION_ERROR, "after a write")

    worker = _worker(JobType.BAPLIE_PARSE, handler, port_db, queues, schemas)
    worker.process_message(raw(JobType.BAPLIE_PARSE, run_id=run))
    assert seen == ["wrote"]
    assert (
        _one(root, f"SELECT staged_payload IS NULL FROM baplie_files WHERE id = {FILE_ID}")[0]  # noqa: S608
        == 1
    )


def test_settings_load_per_job_under_a_real_account(
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    first = _seed_run(root, JobType.PART1_RUN)
    second = _seed_run(root, JobType.PART1_RUN)
    seen: list[int] = []

    def handler(context: JobContext) -> JobResult:
        seen.append(context.settings.get_int("part1_max_retries"))
        return _done_result(JobType.PART1_RUN, context)

    worker = _worker(JobType.PART1_RUN, handler, port_db, queues, schemas)
    worker.process_message(raw(JobType.PART1_RUN, run_id=first))
    with root.cursor() as cursor:
        cursor.execute(
            "UPDATE port_settings SET setting_value = '3' WHERE setting_key = 'part1_max_retries'"
        )
    root.commit()
    worker.process_message(raw(JobType.PART1_RUN, run_id=second))
    assert seen == [2, 3]


def test_run_worker_starts_with_the_real_connection_layer(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any], queues: redis.Redis
) -> None:
    run = _seed_run(root, JobType.PART1_RUN)
    queues.rpush(QUEUES[JobType.PART1_RUN], raw(JobType.PART1_RUN, run_id=run))
    env = os.environ | port_db.worker_env(WorkerPart.PART1)
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "tests.integration.fake_worker"],
        cwd=Path(REPO_ROOT),
        env=env,
    )
    try:
        deadline = time.monotonic() + 30
        status = ""
        while time.monotonic() < deadline and status != "DONE":
            status = _one(root, f"SELECT status FROM part1_runs WHERE id = {run}")[0]  # noqa: S608
            time.sleep(0.1)
        assert status == "DONE"
        assert process.poll() is None
    finally:
        process.kill()
        process.wait(timeout=30)
    assert [body["status"] for body in _completions(queues)] == ["DONE"]


def test_startup_fails_on_a_wrong_password(port_db: PortDatabase) -> None:
    env = port_db.worker_env(WorkerPart.PART1) | {"AI_DB_PASSWORD_PART1": "wrong"}

    def handler(_context: JobContext) -> JobResult:
        raise AssertionError("no job may run")

    definition = WorkerDefinition(JobType.PART1_RUN, handler, (), "0.1.0")
    assert run_worker(definition, connect_worker, env=env, repo_root=REPO_ROOT) == 1


class _LosesItsNextCommit(WorkerConnection):
    """Dies just before the commit a handler armed it for, as a lost network would."""

    def __init__(
        self,
        connection: WorkerConnection,
        root: pymysql.connections.Connection[Any],
        armed: list[int],
    ) -> None:
        super().__init__(connection.core)
        self._root = root
        self._armed = armed

    def commit(self) -> None:
        if self._armed:
            self._armed.clear()
            cursor = self.cursor()
            cursor.execute("SELECT CONNECTION_ID()")
            session = int(cursor.fetchone()[0])
            cursor.close()
            with self._root.cursor() as admin:
                admin.execute(f"KILL {session}")
        super().commit()


def test_a_connection_lost_at_the_final_commit_retries_and_finishes(
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
    queues: redis.Redis,
    schemas: Schemas,
) -> None:
    run = _seed_run(root, JobType.PART1_RUN)
    attempts: list[int] = []
    armed: list[int] = []

    def handler(context: JobContext) -> JobResult:
        attempts.append(context.attempt)
        if len(attempts) == 1:
            armed.append(1)
        return _done_result(JobType.PART1_RUN, context)

    settings = load_env_settings(port_db.worker_env(WorkerPart.PART1), WorkerPart.PART1)
    definition = WorkerDefinition(JobType.PART1_RUN, handler, ("part1_max_retries",), "0.1.0")
    worker = Worker(
        definition,
        lambda: _LosesItsNextCommit(connect_worker(settings), root, armed),
        queues,
        schemas,
    )
    worker.process_message(raw(JobType.PART1_RUN, run_id=run))
    assert attempts == [0, 1]
    status, retries = _one(root, f"SELECT status, retry_count FROM part1_runs WHERE id = {run}")  # noqa: S608
    assert (status, retries) == ("DONE", 1)
    assert [body["status"] for body in _completions(queues)] == ["DONE"]
