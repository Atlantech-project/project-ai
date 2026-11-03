"""The worker loop: CT-08 §6 from BLPOP to C-06.

`BLPOP` removes a message on receipt, so there is nothing to acknowledge. C-06 is sent only after
the result transaction commits. The database connection is opened before `BLPOP`, so an outage
doesn't drain the queue. After a crash the Backend covers the run: the stale sweep for a claimed
run (DEC-04) and the P3-I2 sweeper for one still QUEUED (DEC-11). If the Backend sweeps a run
during a job, the guarded final update finds no RUNNING row and everything rolls back.
Handlers must not commit: the runtime owns commit and rollback.
"""

import json
import logging
import os
import signal
import socket
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any, Final, Protocol

import redis

from common.config import (
    ConfigurationError,
    EnvSettings,
    OptionalEnvVar,
    PortSettings,
    WorkerPart,
    check_consistency,
    check_startup_settings,
    load_env_settings,
    read_port_settings,
)
from common.runtime.envelope import (
    QUEUES,
    Envelope,
    JobType,
    Rejection,
    RejectionKind,
    Schemas,
    load_schemas,
    parse_message,
    resolve_schema_dir,
)
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.logs import configure_logging, log_event
from common.runtime.runs import (
    RUN_TABLES,
    Connection,
    claim,
    count_retry,
    read_completion_field,
    write_done,
    write_failed,
)

AI_RESULTS_QUEUE: Final = "queue:ai-results"
_COMPLETION_VERSION: Final = "1.0"
_PART1_RETRIES_KEY: Final = "part1_max_retries"
# `chk_p1r_retry` on part1_runs. CT-18 allows up to 10: to be raised with the Backend (AI-011).
_PART1_RETRY_CHECK_MAX: Final = 3
_RETRIES_BY_JOB: Final[Mapping[JobType, int]] = {
    JobType.PART2_SOLVE: 1,
    JobType.YARD_PLACEMENT: 1,
    JobType.BAPLIE_PARSE: 1,
}
# Before the settings are read, Part 1's limit isn't known; a failed read gets the one retry
# every other job has (DEC-04).
_RETRIES_BEFORE_SETTINGS: Final = 1
_RETRIED: Final = frozenset(
    {ErrorCategory.DATA_UNAVAILABLE, ErrorCategory.TIMEOUT, ErrorCategory.INTERNAL_ERROR}
)
_NOT_ALLOWED: Final[Mapping[JobType, frozenset[ErrorCategory]]] = {
    JobType.PART1_RUN: frozenset({ErrorCategory.INFEASIBLE, ErrorCategory.SOLVER_ERROR}),
    JobType.PART2_SOLVE: frozenset({ErrorCategory.INFEASIBLE}),
    JobType.YARD_PLACEMENT: frozenset({ErrorCategory.SOLVER_ERROR}),
    JobType.BAPLIE_PARSE: frozenset({ErrorCategory.INFEASIBLE, ErrorCategory.SOLVER_ERROR}),
    JobType.VALIDATION: frozenset({ErrorCategory.INFEASIBLE, ErrorCategory.SOLVER_ERROR}),
}
_PARTS: Final[Mapping[JobType, WorkerPart]] = {
    JobType.PART1_RUN: WorkerPart.PART1,
    JobType.PART2_SOLVE: WorkerPart.PART2,
    JobType.YARD_PLACEMENT: WorkerPart.YARD,
    JobType.BAPLIE_PARSE: WorkerPart.EDI,
    JobType.VALIDATION: WorkerPart.VALIDATE,
}
_CORE_COMPLETION_FIELDS: Final = frozenset(
    {
        "contract_version",
        "job_type",
        "job_id",
        "run_id",
        "status",
        "outcome",
        "error_category",
        "finished_at",
        "worker_version",
    }
)
_MYSQL_CHECK_VIOLATED: Final = 3819
_RAW_LOG_LIMIT: Final = 4096
_LOG_VALUE_LIMIT: Final = 80
_WORKER_VERSION_LIMIT: Final = 40
_BLPOP_TIMEOUT_SECONDS: Final = 5
# Must outlast BLPOP: a client giving up at the same moment can lose a message the server popped.
_SOCKET_TIMEOUT_SECONDS: Final = 15
_OUTAGE_RETRY_SECONDS: Final = 1.0
_SHUTDOWN_SIGNALS: Final = (signal.SIGTERM, signal.SIGINT)


class RedisClient(Protocol):
    def ping(self) -> Any: ...

    def blpop(self, keys: Any, timeout: Any = ...) -> Any: ...

    def rpush(self, name: Any, *values: Any) -> Any: ...


def connect_redis(url: str) -> redis.Redis:
    """A client safe for the worker loop. Use this: redis-py's default timeout equals BLPOP's."""
    client: redis.Redis = redis.Redis.from_url(
        url,
        socket_timeout=_SOCKET_TIMEOUT_SECONDS,
        socket_connect_timeout=_SOCKET_TIMEOUT_SECONDS,
    )
    return client


@dataclass(frozen=True)
class JobContext:
    envelope: Envelope
    settings: PortSettings
    connection: Connection
    attempt: int


@dataclass(frozen=True)
class JobResult:
    """What a handler returns for a DONE job (CT-14).

    `completion_fields` are the job type's extra C-06 fields. `error_category` is only for
    `FIFO_FALLBACK`.
    """

    outcome: str
    run_columns: Mapping[str, object] = field(default_factory=dict)
    completion_fields: Mapping[str, object] = field(default_factory=dict)
    error_category: ErrorCategory | None = None


@dataclass(frozen=True)
class WorkerDefinition:
    job_type: JobType
    handler: Callable[[JobContext], JobResult]
    # Every port_settings key the worker uses; the startup check picks the approved ones.
    used_setting_keys: tuple[str, ...]
    worker_version: str


def part1_retries_allowed(settings: PortSettings) -> int:
    """`part1_max_retries`, refusing a value the `part1_runs` CHECK couldn't record."""
    retries = settings.get_int(_PART1_RETRIES_KEY)
    if not 0 <= retries <= _PART1_RETRY_CHECK_MAX:
        raise ConfigurationError(
            f"{_PART1_RETRIES_KEY} must be 0 to {_PART1_RETRY_CHECK_MAX}: chk_p1r_retry on "
            "part1_runs can't record more retries",
            [_PART1_RETRIES_KEY],
        )
    return retries


def _is_check_violation(error: BaseException) -> bool:
    return bool(error.args) and error.args[0] == _MYSQL_CHECK_VIOLATED


def _classify(error: BaseException, job_type: JobType) -> tuple[ErrorCategory, str]:
    if isinstance(error, JobError):
        category, message = error.category, error.message
    elif isinstance(error, ConfigurationError):
        category, message = ErrorCategory.CONFIGURATION_ERROR, str(error)
    elif _is_check_violation(error):
        category, message = ErrorCategory.CONFIGURATION_ERROR, "a CHECK constraint rejected a write"
    else:
        category, message = ErrorCategory.INTERNAL_ERROR, f"unexpected {type(error).__name__}"
    if category in _NOT_ALLOWED[job_type]:
        return ErrorCategory.INTERNAL_ERROR, f"{category} isn't allowed for {job_type}"
    return category, message


def _can_retry(job_type: JobType, category: ErrorCategory) -> bool:
    if job_type is JobType.PART2_SOLVE and category is ErrorCategory.TIMEOUT:
        return False
    return category in _RETRIED


def _capped(value: str | None) -> str | None:
    return None if value is None else value[:_LOG_VALUE_LIMIT]


def _close_quietly(connection: Connection) -> None:
    try:
        connection.close()
    except Exception:  # noqa: S110
        pass  # Already closed or lost; there's nothing more to do with it.


class Worker:
    """Handles one queue. A problem with a job never ends the loop."""

    def __init__(
        self,
        definition: WorkerDefinition,
        connect: Callable[[], Connection],
        redis_client: RedisClient,
        schemas: Schemas,
    ) -> None:
        self._definition = definition
        self._job_type = definition.job_type
        self._queue = QUEUES[definition.job_type]
        self._connect = connect
        self._redis = redis_client
        self._schemas = schemas
        # A plain flag: `threading.Event` takes a lock, which a signal handler could deadlock on.
        self._stopping = False

    def stop(self) -> None:
        """Finish the current job and take no new one. Safe to call from a signal handler."""
        self._stopping = True

    def run(self) -> None:
        while not self._stopping:
            try:
                connection = self._connect()
            except Exception:
                log_event(
                    logging.ERROR, "database_unavailable", {"queue": self._queue}, exc_info=True
                )
                time.sleep(_OUTAGE_RETRY_SECONDS)
                continue
            try:
                item = self._redis.blpop([self._queue], timeout=_BLPOP_TIMEOUT_SECONDS)
            except Exception:
                _close_quietly(connection)
                log_event(logging.ERROR, "queue_read_failed", {"queue": self._queue}, exc_info=True)
                time.sleep(_OUTAGE_RETRY_SECONDS)
                continue
            if item is None:
                _close_quietly(connection)
            else:
                self.process_message(item[1], connection)

    def process_message(self, raw: bytes | str, connection: Connection | None = None) -> None:
        """Handle one message, on `connection` if given, which is closed afterwards."""
        connect = self._connect if connection is None else (lambda: connection)
        fields: dict[str, object] = {"queue": self._queue}
        try:
            parsed = parse_message(raw, self._job_type, self._schemas)
            fields = self._fields(parsed.run_id, parsed.job_id, parsed.contract_version)
            if isinstance(parsed, Rejection):
                self._reject(parsed, raw, connect, fields)
            elif parsed.job_type is JobType.VALIDATION:
                self._run_validation(parsed, connect, fields)
            else:
                self._run_job(parsed, connect, fields)
        except Exception:
            log_event(logging.ERROR, "job_handling_failed", fields, exc_info=True)
        finally:
            if connection is not None:
                _close_quietly(connection)

    def _fields(
        self, run_id: int | None, job_id: str | None, contract_version: str | None
    ) -> dict[str, object]:
        return {
            "queue": self._queue,
            "job_type": self._job_type.value,
            "job_id": job_id,
            "run_id": run_id,
            "contract_version": _capped(contract_version),
        }

    def _reject(
        self,
        rejection: Rejection,
        raw: bytes | str,
        connect: Callable[[], Connection],
        fields: dict[str, object],
    ) -> None:
        fields = fields | {"reason": rejection.reason}
        if rejection.kind is RejectionKind.WRONG_QUEUE:
            log_event(
                logging.ERROR,
                "wrong_queue_dropped",
                fields | {"job_type": _capped(rejection.job_type)},
            )
        elif rejection.kind is RejectionKind.UNREADABLE:
            text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            log_event(
                logging.ERROR, "invalid_message_dropped", fields | {"raw": text[:_RAW_LOG_LIMIT]}
            )
        elif self._job_type is JobType.VALIDATION:
            log_event(logging.ERROR, "invalid_message_failed", fields)
            self._send(
                self._completion(
                    job_id=rejection.job_id,
                    run_id=None,
                    status="FAILED",
                    outcome=None,
                    category=ErrorCategory.INVALID_ENVELOPE,
                ),
                fields,
            )
        else:
            self._finish_invalid(rejection, connect, fields)

    def _finish_invalid(
        self,
        rejection: Rejection,
        connect: Callable[[], Connection],
        fields: dict[str, object],
    ) -> None:
        run_id = rejection.run_id
        assert run_id is not None  # noqa: S101
        spec = RUN_TABLES[self._job_type]
        connection = connect()
        try:
            if not claim(connection, spec, run_id):
                log_event(logging.INFO, "invalid_message_not_claimed", fields)
                return
            log_event(logging.ERROR, "invalid_message_failed", fields)
            self._finish_failed(
                connection,
                run_id,
                rejection.job_id,
                ErrorCategory.INVALID_ENVELOPE,
                rejection.reason,
                fields,
            )
        finally:
            _close_quietly(connection)

    def _recover(self, connection: Connection, fields: dict[str, object]) -> Connection:
        """Roll back. If the connection is gone, close it and open another."""
        try:
            connection.rollback()
        except Exception:
            log_event(logging.WARNING, "connection_lost", fields, exc_info=True)
            _close_quietly(connection)
            return self._connect()
        return connection

    def _run_job(
        self, envelope: Envelope, connect: Callable[[], Connection], fields: dict[str, object]
    ) -> None:
        run_id = envelope.run_id
        assert run_id is not None  # noqa: S101
        spec = RUN_TABLES[self._job_type]
        connection = connect()
        try:
            if not claim(connection, spec, run_id):
                log_event(logging.INFO, "job_not_claimed", fields)
                return
            log_event(logging.INFO, "job_claimed", fields)
            attempt = 0
            retries = _RETRIES_BEFORE_SETTINGS
            settings: PortSettings | None = None
            while True:
                try:
                    if settings is None:
                        new_settings = self._read_settings(connection)
                        retries = self._retries(new_settings)
                        settings = new_settings
                    result = self._definition.handler(
                        JobContext(envelope, settings, connection, attempt)
                    )
                    message = self._completion(
                        job_id=envelope.job_id,
                        run_id=run_id,
                        status="DONE",
                        outcome=result.outcome,
                        category=result.error_category,
                        extra=result.completion_fields,
                    )
                    written = write_done(
                        connection,
                        spec,
                        run_id,
                        result.outcome,
                        result.run_columns,
                        self._definition.worker_version,
                    )
                    if not written:
                        connection.rollback()
                        log_event(logging.WARNING, "job_lost_to_backend", fields)
                        return
                    connection.commit()
                    log_event(logging.INFO, "job_done", fields | {"outcome": result.outcome})
                    self._send(message, fields)
                    return
                except (Exception, SystemExit) as error:
                    connection = self._recover(connection, fields)
                    category, reason = _classify(error, self._job_type)
                    log_event(
                        logging.WARNING,
                        "job_attempt_failed",
                        fields | {"attempt": attempt, "error_category": category.value},
                        exc_info=True,
                    )
                if _can_retry(self._job_type, category) and attempt < retries:
                    try:
                        still_running = count_retry(connection, spec, run_id)
                    except Exception as error:
                        connection = self._recover(connection, fields)
                        category, reason = _classify(error, self._job_type)
                    else:
                        if not still_running:
                            log_event(logging.WARNING, "job_lost_to_backend", fields)
                            return
                        attempt += 1
                        continue
                self._finish_failed(connection, run_id, envelope.job_id, category, reason, fields)
                return
        finally:
            _close_quietly(connection)

    def _run_validation(
        self, envelope: Envelope, connect: Callable[[], Connection], fields: dict[str, object]
    ) -> None:
        connection: Connection | None = None
        try:
            connection = connect()
            settings = self._read_settings(connection)
            result = self._definition.handler(JobContext(envelope, settings, connection, 0))
            message = self._completion(
                job_id=envelope.job_id,
                run_id=None,
                status="DONE",
                outcome=result.outcome,
                category=None,
                extra=result.completion_fields,
            )
        except (Exception, SystemExit) as error:
            category, _ = _classify(error, self._job_type)
            log_event(
                logging.WARNING,
                "job_attempt_failed",
                fields | {"error_category": category.value},
                exc_info=True,
            )
            message = self._completion(
                job_id=envelope.job_id,
                run_id=None,
                status="FAILED",
                outcome=None,
                category=category,
            )
        if connection is not None:
            # VALIDATION writes nothing, so a failure here can't affect the result.
            try:
                connection.rollback()
            except Exception:
                log_event(logging.WARNING, "connection_lost", fields, exc_info=True)
            _close_quietly(connection)
        self._send(message, fields)

    def _read_settings(self, connection: Connection) -> PortSettings:
        # Committed at once: a transaction left open would freeze later reads (AI-012).
        settings = read_port_settings(connection)
        connection.commit()
        check_consistency(settings, self._definition.used_setting_keys)
        return settings

    def _retries(self, settings: PortSettings) -> int:
        if self._job_type is JobType.PART1_RUN:
            return part1_retries_allowed(settings)
        return _RETRIES_BY_JOB[self._job_type]

    def _failed_completion(
        self,
        run_id: int,
        job_id: str,
        category: ErrorCategory,
        related_id: object,
        fields: dict[str, object],
    ) -> dict[str, object] | None:
        spec = RUN_TABLES[self._job_type]
        extra: dict[str, object] = {}
        if self._job_type is JobType.PART1_RUN:
            extra["entry_window_proposal_id"] = None
        if spec.completion_field is not None:
            extra[spec.completion_field] = related_id
        try:
            return self._completion(
                job_id=job_id,
                run_id=run_id,
                status="FAILED",
                outcome=spec.failed_completion_outcome,
                category=category,
                extra=extra,
            )
        except Exception:
            # The run must still end FAILED; the Backend's poller picks it up (CT-14).
            log_event(logging.ERROR, "completion_invalid", fields, exc_info=True)
            return None

    def _finish_failed(
        self,
        connection: Connection,
        run_id: int,
        job_id: str | None,
        category: ErrorCategory,
        reason: str,
        fields: dict[str, object],
    ) -> None:
        spec = RUN_TABLES[self._job_type]
        related_id = read_completion_field(connection, spec, run_id)
        message = None
        if job_id is not None:
            message = self._failed_completion(run_id, job_id, category, related_id, fields)
        written = write_failed(
            connection,
            spec,
            run_id,
            category,
            reason,
            self._definition.worker_version,
            related_id,
        )
        if not written:
            connection.rollback()
            log_event(logging.WARNING, "job_state_changed", fields)
            return
        connection.commit()
        log_event(
            logging.ERROR,
            "job_failed",
            fields | {"error_category": category.value, "reason": reason},
        )
        if message is None:
            # No valid C-06 can be sent; the Backend's poller picks up the run (CT-14).
            log_event(logging.ERROR, "completion_not_possible", fields)
        else:
            self._send(message, fields)

    def _completion(
        self,
        *,
        job_id: str | None,
        run_id: int | None,
        status: str,
        outcome: str | None,
        category: ErrorCategory | None,
        extra: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Build C-06 and check it against its schema, before anything is committed."""
        extra = extra or {}
        overridden = _CORE_COMPLETION_FIELDS & set(extra)
        if overridden:
            raise ValueError(f"can't override C-06 fields: {', '.join(sorted(overridden))}")
        message: dict[str, object] = {
            "contract_version": _COMPLETION_VERSION,
            "job_type": self._job_type.value,
            "job_id": job_id,
            "run_id": run_id,
            "status": status,
            "outcome": outcome,
            "error_category": None if category is None else category.value,
            "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "worker_version": self._definition.worker_version,
            **extra,
        }
        self._schemas.completion.validate(message)
        return message

    def _send(self, message: Mapping[str, object], fields: dict[str, object]) -> None:
        try:
            self._redis.rpush(AI_RESULTS_QUEUE, json.dumps(message))
        except Exception:
            # Committed already. The Backend's poller covers run jobs (CT-14).
            log_event(logging.ERROR, "completion_not_sent", fields, exc_info=True)


def _startup_checks(
    definition: WorkerDefinition,
    env: Mapping[str, str],
    connect_with: Callable[[EnvSettings], Connection],
    redis_for: Callable[[str], RedisClient],
    repo_root: Path | None,
) -> tuple[EnvSettings, RedisClient, Schemas]:
    if not 1 <= len(definition.worker_version) <= _WORKER_VERSION_LIMIT:
        raise ConfigurationError(
            f"worker_version must be 1 to {_WORKER_VERSION_LIMIT} characters (CT-14)"
        )
    env_settings = load_env_settings(env, _PARTS[definition.job_type])
    arguments = () if repo_root is None else (repo_root,)
    schema_dir = resolve_schema_dir(env, *arguments)
    if not env.get(OptionalEnvVar.SCHEMA_DIR, "").strip():
        log_event(logging.WARNING, "schema_dir_defaulted", {"schema_dir": str(schema_dir)})
    schemas = load_schemas(schema_dir)
    connection = connect_with(env_settings)
    try:
        settings = read_port_settings(connection)
        connection.commit()
    finally:
        connection.close()
    check_startup_settings(settings, definition.used_setting_keys)
    redis_client = redis_for(env_settings.redis_url)
    redis_client.ping()
    return env_settings, redis_client, schemas


def run_worker(
    definition: WorkerDefinition,
    connect_with: Callable[[EnvSettings], Connection],
    redis_for: Callable[[str], RedisClient] = connect_redis,
    env: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
) -> int:
    """Run a worker process and return its exit code: non-zero if startup checks fail."""
    environment = os.environ if env is None else env
    configure_logging()
    fields = {"queue": QUEUES[definition.job_type], "host": socket.gethostname()}
    try:
        env_settings, redis_client, schemas = _startup_checks(
            definition, environment, connect_with, redis_for, repo_root
        )
    except ConfigurationError as error:
        log_event(logging.CRITICAL, "startup_failed", fields | {"reason": str(error)})
        return 1
    except Exception as error:
        reason = f"unexpected {type(error).__name__}"
        log_event(logging.CRITICAL, "startup_failed", fields | {"reason": reason}, exc_info=True)
        return 1
    worker = Worker(definition, lambda: connect_with(env_settings), redis_client, schemas)

    def _stop(_signal: int, _frame: FrameType | None) -> None:
        worker.stop()

    for name in _SHUTDOWN_SIGNALS:
        signal.signal(name, _stop)
    log_event(logging.INFO, "worker_started", fields)
    worker.run()
    log_event(logging.INFO, "worker_stopped", fields)
    return 0
