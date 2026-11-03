"""The run tables: claim, retry count and guarded completion (CT-08 §6, CT-15, DEC-08).

Each table records a failure differently, so the rules live here, taken from `schema.sql`.
A connection is in manual-commit mode; the caller owns commit and rollback, except where a
function says otherwise.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

from common.runtime.envelope import JobType
from common.runtime.errors import ErrorCategory

_FAILURE_REASON_LENGTH: Final = 500
_FAILURE_MESSAGE_LENGTH: Final = 1000
_SOLVER_STATUSES: Final = frozenset({"OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"})


class Cursor(Protocol):
    rowcount: int

    def execute(self, query: str, args: Any = ...) -> object: ...

    def fetchone(self) -> Any: ...

    def fetchall(self) -> Iterable[Sequence[Any]]: ...

    def close(self) -> object: ...


class Connection(Protocol):
    """The part of a DB-API connection the runtime needs; AI-013 owns how it's created."""

    def cursor(self) -> Cursor: ...

    def commit(self) -> object: ...

    def rollback(self) -> object: ...

    def close(self) -> object: ...


@dataclass(frozen=True)
class RunTable:
    table: str
    failed_status: str
    # None: the handler sets the status, as `solver_runs` has several successful ones.
    done_status: str | None = "DONE"
    has_outcome: bool = True
    failed_outcome_column: str | None = None
    failed_completion_outcome: str | None = None
    has_error_category: bool = False
    has_retry_count: bool = True
    has_worker_version: bool = False
    failure_in_result_detail: bool = False
    # Column on the run row a failed C-06 needs, also when the payload was the invalid part.
    completion_field: str | None = None
    # The CT-15 columns a handler may set; the runtime owns the others.
    handler_columns: frozenset[str] = field(default_factory=frozenset)


RUN_TABLES: Final[Mapping[JobType, RunTable]] = {
    JobType.PART1_RUN: RunTable(
        table="part1_runs",
        failed_status="FAILED",
        handler_columns=frozenset({"entry_window_proposal_id"}),
    ),
    JobType.PART2_SOLVE: RunTable(
        table="solver_runs",
        failed_status="ERROR",
        done_status=None,
        has_outcome=False,
        failed_completion_outcome="GENERATION_FAILED",
        has_retry_count=False,
        failure_in_result_detail=True,
        handler_columns=frozenset(
            {"status", "objective_value", "solve_time_ms", "solver_version", "result_detail"}
        ),
    ),
    JobType.YARD_PLACEMENT: RunTable(
        table="yard_runs",
        failed_status="FAILED",
        failed_outcome_column="GENERATION_FAILED",
        failed_completion_outcome="GENERATION_FAILED",
        has_error_category=True,
        has_worker_version=True,
        failure_in_result_detail=True,
        completion_field="terminal_recommendation_id",
        handler_columns=frozenset({"result_detail"}),
    ),
    JobType.BAPLIE_PARSE: RunTable(
        table="baplie_parse_runs",
        failed_status="FAILED",
        has_error_category=True,
        has_worker_version=True,
        failure_in_result_detail=True,
        completion_field="baplie_file_id",
        handler_columns=frozenset({"container_count", "result_detail"}),
    ),
}


def _execute(connection: Connection, query: str, args: Sequence[object]) -> int:
    cursor = connection.cursor()
    try:
        cursor.execute(query, tuple(args))
        return cursor.rowcount
    finally:
        cursor.close()


def _guarded_update(
    connection: Connection, spec: RunTable, run_id: int, columns: Mapping[str, object]
) -> bool:
    assignments = "".join(f"{name} = %s, " for name in columns)
    query = (
        f"UPDATE {spec.table} SET {assignments}finished_at = UTC_TIMESTAMP() "  # noqa: S608
        "WHERE id = %s AND status = 'RUNNING'"
    )
    return _execute(connection, query, [*columns.values(), run_id]) == 1


def claim(connection: Connection, spec: RunTable, run_id: int) -> bool:
    """The CT-08 §6 step 4 claim, committed. False: a duplicate or replaced delivery."""
    query = (
        f"UPDATE {spec.table} SET status = 'RUNNING', started_at = UTC_TIMESTAMP() "  # noqa: S608
        "WHERE id = %s AND status = 'QUEUED'"
    )
    claimed = _execute(connection, query, [run_id]) == 1
    connection.commit()
    return claimed


def count_retry(connection: Connection, spec: RunTable, run_id: int) -> bool:
    """Count a retry where the column exists, committed. False: the run is no longer RUNNING."""
    if spec.has_retry_count:
        query = (
            f"UPDATE {spec.table} SET retry_count = retry_count + 1 "  # noqa: S608
            "WHERE id = %s AND status = 'RUNNING'"
        )
        running = _execute(connection, query, [run_id]) == 1
    else:
        cursor = connection.cursor()
        try:
            cursor.execute(f"SELECT status FROM {spec.table} WHERE id = %s", (run_id,))  # noqa: S608
            row = cursor.fetchone()
        finally:
            cursor.close()
        running = row is not None and row[0] == "RUNNING"
    connection.commit()
    return running


def write_done(
    connection: Connection,
    spec: RunTable,
    run_id: int,
    outcome: str,
    run_columns: Mapping[str, object],
    worker_version: str,
) -> bool:
    """The guarded final update for a DONE job. False: roll back everything, send nothing."""
    unknown = set(run_columns) - spec.handler_columns
    if unknown:
        raise ValueError(f"not writable on {spec.table}: {', '.join(sorted(unknown))}")
    columns: dict[str, object] = {}
    if spec.done_status is not None:
        columns["status"] = spec.done_status
    elif run_columns.get("status") not in _SOLVER_STATUSES:
        raise ValueError(f"a handler must set a final status on {spec.table}")
    if spec.has_outcome:
        columns["outcome"] = outcome
    columns.update(
        (name, json.dumps(value) if isinstance(value, Mapping) else value)
        for name, value in run_columns.items()
    )
    if spec.has_worker_version:
        columns["worker_version"] = worker_version
    return _guarded_update(connection, spec, run_id, columns)


def read_completion_field(connection: Connection, spec: RunTable, run_id: int) -> object:
    """The id a failed C-06 needs, from the run row (`None` if this job type needs none)."""
    if spec.completion_field is None:
        return None
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT {spec.completion_field} FROM {spec.table} WHERE id = %s",  # noqa: S608
            (run_id,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    return None if row is None else row[0]


def write_failed(
    connection: Connection,
    spec: RunTable,
    run_id: int,
    category: ErrorCategory,
    message: str,
    worker_version: str,
    related_id: object,
) -> bool:
    """The guarded final update for a FAILED job. False: roll back everything, send nothing."""
    columns: dict[str, object] = {"status": spec.failed_status}
    if spec.failed_outcome_column is not None:
        columns["outcome"] = spec.failed_outcome_column
    if spec.has_error_category:
        columns["error_category"] = category.value
    if spec.failure_in_result_detail:
        detail: dict[str, object] = {
            "failure_reason": {
                "error_category": category.value,
                "message": message[:_FAILURE_MESSAGE_LENGTH],
            }
        }
        if spec.table == "solver_runs":
            detail |= {"outcome": spec.failed_completion_outcome, "requests": []}
        columns["result_detail"] = json.dumps(detail)
    if spec.has_worker_version:
        columns["worker_version"] = worker_version
    if not _guarded_update(connection, spec, run_id, columns):
        return False
    if spec.table == "yard_runs":
        return _fail_terminal_recommendation(connection, category, message, related_id)
    if spec.table == "baplie_parse_runs":
        _execute(
            connection,
            "UPDATE baplie_files SET parse_status = 'FAILED' WHERE id = %s",
            [related_id],
        )
    return True


def _fail_terminal_recommendation(
    connection: Connection, category: ErrorCategory, message: str, recommendation_id: object
) -> bool:
    # CT-11: re-check the row is still YARD_REC_REQUESTED, otherwise roll back and send nothing.
    reason = f"{category.value}: {message}"[:_FAILURE_REASON_LENGTH]
    query = (
        "UPDATE terminal_recommendations "
        "SET lifecycle_status = %s, failure_reason = %s, confidence = NULL "
        "WHERE id = %s AND lifecycle_status = 'YARD_REC_REQUESTED'"
    )
    return _execute(connection, query, ["GENERATION_FAILED", reason, recommendation_id]) == 1
