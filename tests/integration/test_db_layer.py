"""AI-013: the connection, table definitions, repositories and read models on the real schema."""

import json
import logging
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pymysql
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from common.config import WorkerPart, load_env_settings, read_port_settings
from common.db.connection import (
    WorkerConnection,
    _engine,
    connect_worker,
    core_of,
    dispose_engines,
    transaction,
)
from common.db.read_models import read_request_with_vessel, read_run, read_tugboats
from common.db.repository import WorkerRepository, WriteRefused
from common.db.rights import WRITE_RIGHTS
from common.db.tables import KnownEnum, metadata
from tests.support.port_db import (
    ACCOUNTS,
    PortDatabase,
    is_generated_column,
    required_row,
    seed_row,
)

pytestmark = pytest.mark.integration

# Values the schema's CHECK constraints need, where a placeholder doesn't pass.
ROWS: dict[str, dict[str, object]] = {
    "forecast_runs": {
        "pull_type": "SCHEDULED",
        "berthing_request_id": None,
        "submitted_by": None,
    },
}
INSERT_CASES = [
    (part, table)
    for part, rights in WRITE_RIGHTS.items()
    for table in sorted(rights.insert)
    if table != "containers"
]
TOUCHED = sorted(metadata.tables)


@pytest.fixture(autouse=True)
def fresh_sessions() -> Iterator[None]:
    """A session setting a test makes, such as foreign key checks, ends with that test."""
    yield
    dispose_engines()


@pytest.fixture
def root(port_db: PortDatabase) -> Iterator[pymysql.connections.Connection[Any]]:
    conn = port_db.root()
    try:
        yield conn
    finally:
        try:
            with conn.cursor() as cursor:
                for table in [*TOUCHED, "port_settings"]:
                    cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608
            conn.commit()
        finally:
            conn.close()


def _open(port_db: PortDatabase, part: WorkerPart) -> WorkerConnection:
    return connect_worker(load_env_settings(port_db.worker_env(part), part))


@pytest.fixture
def worker(
    request: pytest.FixtureRequest,
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
) -> Iterator[WorkerConnection]:
    connection = _open(port_db, getattr(request, "param", WorkerPart.EDI))
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _one(root: pymysql.connections.Connection[Any], sql: str) -> Any:
    root.commit()
    with root.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    root.commit()
    assert row is not None
    return row


# Table definitions


def _expected_type(column: sa.Column[Any]) -> str:
    if isinstance(column.type, KnownEnum):
        return "enum(" + ",".join(f"'{value}'" for value in column.type.values) + ")"
    compiled = str(column.type.compile(dialect=mysql.dialect())).lower()
    return compiled.replace(", ", ",").replace("integer", "int")


@pytest.mark.parametrize("table_name", sorted(metadata.tables))
def test_each_definition_matches_the_real_table(table_name: str, port_db: PortDatabase) -> None:
    conn = port_db.root()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT column_name, column_type, is_nullable, column_key, extra "
                "FROM information_schema.columns WHERE table_schema = DATABASE() "
                "AND table_name = %s ORDER BY ordinal_position",
                (table_name,),
            )
            real = cursor.fetchall()
    finally:
        conn.close()
    table = metadata.tables[table_name]
    assert [row[0] for row in real] == list(table.c.keys())
    for name, column_type, nullable, key, extra in real:
        column = table.c[name]
        assert _expected_type(column) == column_type, name
        assert column.nullable == (nullable == "YES"), name
        assert column.primary_key == (key == "PRI"), name
        assert bool(column.info.get("generated")) == is_generated_column(extra), name
        if column_type == "json":
            # Otherwise SQLAlchemy stores None as JSON null, not SQL NULL.
            assert column.type.none_as_null, name


# Connections


def test_a_connection_is_in_utc_utf8mb4_and_manual_commit(worker: WorkerConnection) -> None:
    cursor = worker.cursor()
    cursor.execute("SELECT @@session.time_zone, @@character_set_client, @@autocommit")
    assert cursor.fetchone() == ("+00:00", "utf8mb4", 0)
    cursor.close()


def test_a_pooled_replacement_keeps_the_session_settings(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    first = _open(port_db, WorkerPart.EDI)
    cursor = first.cursor()
    cursor.execute("SELECT CONNECTION_ID()")
    session = cursor.fetchone()[0]
    cursor.close()
    first.rollback()
    first.close()
    with root.cursor() as admin:
        admin.execute(f"KILL {int(session)}")
    second = _open(port_db, WorkerPart.EDI)
    try:
        cursor = second.cursor()
        cursor.execute("SELECT CONNECTION_ID(), @@session.time_zone, CURRENT_USER()")
        new_session, time_zone, user = cursor.fetchone()
        cursor.close()
        assert new_session != session
        assert time_zone == "+00:00"
        assert user == "w_edi@%"
    finally:
        second.rollback()
        second.close()


def test_rollback_on_a_killed_connection_raises(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    connection = _open(port_db, WorkerPart.EDI)
    cursor = connection.cursor()
    cursor.execute("SELECT CONNECTION_ID()")
    session = cursor.fetchone()[0]
    cursor.close()
    with root.cursor() as admin:
        admin.execute(f"KILL {int(session)}")
    # The runtime replaces the connection when this raises (AI-011 `_recover`).
    with pytest.raises(sa.exc.DBAPIError):
        connection.rollback()
    connection.close()


def test_a_raw_cursor_write_commits_and_rolls_back_through_the_connection(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    sql = "UPDATE part1_runs SET retry_count = %s WHERE id = %s"
    try:
        cursor = connection.cursor()
        cursor.execute(sql, (1, run))
        cursor.close()
        connection.rollback()
        assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {run}")[0] == 0  # noqa: S608
        cursor = connection.cursor()
        cursor.execute(sql, (2, run))
        cursor.close()
        connection.commit()
        assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {run}")[0] == 2  # noqa: S608
    finally:
        connection.close()


def test_a_repository_and_a_raw_cursor_share_one_transaction(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        WorkerRepository(connection, WorkerPart.PART1, run).update_own_run({"retry_count": 1})
        cursor = connection.cursor()
        cursor.execute("SELECT retry_count FROM part1_runs WHERE id = %s", (run,))
        assert cursor.fetchone() == (1,)
        cursor.close()
        assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {run}")[0] == 0  # noqa: S608
        connection.rollback()
        assert read_run(connection, WorkerPart.PART1, run).retry_count == 0  # type: ignore[union-attr]
    finally:
        connection.rollback()
        connection.close()


def test_commit_and_rollback_with_nothing_open_do_nothing(worker: WorkerConnection) -> None:
    worker.commit()
    worker.rollback()
    assert not worker.core.in_transaction()


def test_a_settings_change_shows_on_the_next_read_after_commit(
    worker: WorkerConnection, root: pymysql.connections.Connection[Any]
) -> None:
    seed_row(root, "port_settings", setting_key="ai013_key", setting_value="1", value_type="INT")
    assert read_port_settings(worker).get_int("ai013_key") == 1
    worker.commit()
    with root.cursor() as cursor:
        cursor.execute(
            "UPDATE port_settings SET setting_value = '2' WHERE setting_key = 'ai013_key'"
        )
    root.commit()
    assert read_port_settings(worker).get_int("ai013_key") == 2


def test_core_of_refuses_another_connection_type(root: Any) -> None:
    with pytest.raises(TypeError, match="connect_worker"):
        core_of(root)


def test_transaction_commits_on_success(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    connection = _open(port_db, WorkerPart.PART3)
    row = required_row(root, "evaluation_metrics", {})
    try:
        with transaction(connection):
            _force_fk_off(connection)
            WorkerRepository(connection, WorkerPart.PART3).insert("evaluation_metrics", row)
    finally:
        connection.close()
    assert _one(root, "SELECT COUNT(*) FROM evaluation_metrics")[0] == 1


def test_transaction_rolls_back_on_error_and_reraises(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    connection = _open(port_db, WorkerPart.PART3)
    row = required_row(root, "evaluation_metrics", {})
    try:
        with pytest.raises(RuntimeError, match="boom"), transaction(connection):
            _force_fk_off(connection)
            WorkerRepository(connection, WorkerPart.PART3).insert("evaluation_metrics", row)
            raise RuntimeError("boom")
    finally:
        connection.close()
    assert _one(root, "SELECT COUNT(*) FROM evaluation_metrics")[0] == 0


# Real writes: every INSERT and UPDATE the matrix lists succeeds under the real account.


def _force_fk_off(connection: WorkerConnection) -> None:
    """Parent rows aren't under test here; the grants are. MySQL needs no privilege for this."""
    cursor = connection.cursor()
    cursor.execute("SET foreign_key_checks = 0")
    cursor.close()


@pytest.mark.parametrize(("part", "table"), INSERT_CASES, ids=str)
def test_every_listed_insert_succeeds(
    part: WorkerPart,
    table: str,
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
) -> None:
    row = required_row(root, table, ROWS.get(table, {}))
    connection = _open(port_db, part)
    try:
        _force_fk_off(connection)
        repository = WorkerRepository(connection, part)
        repository.insert(table, row)
        repository.insert_many(table, [])
        count = connection.core.execute(
            sa.select(sa.func.count()).select_from(metadata.tables[table])
        )
        assert count.scalar_one() == 1
    finally:
        connection.rollback()
        connection.close()


GOOD_VALUES: dict[str, object] = {
    "status": "RUNNING",
    "retry_count": 1,
    "outcome": None,
    "error_category": None,
    "entry_window_proposal_id": None,
    "objective_value": Decimal("1.5"),
    "solve_time_ms": 3,
    "solver_version": "1",
    "result_detail": {"a": 1},
    "worker_version": "1",
    "container_count": 1,
    "started_at": datetime(2026, 11, 3, 10),
    "finished_at": None,
    "parse_status": "PARSED",
    "staged_payload": {"a": 1},
    "confidence": None,
    "rationale_template_id": None,
    "rationale_params": {"a": 1},
    "failure_reason": "x",
    "lifecycle_status": "YARD_REC_GENERATED",
    "call_sign": "A",
    "flag_state": "EG",
}
UPDATE_CASES = [
    (part, table, column)
    for part, rights in WRITE_RIGHTS.items()
    for table, columns in rights.update.items()
    for column in sorted(columns)
]


@pytest.mark.parametrize(("part", "table", "column"), UPDATE_CASES, ids=str)
def test_every_listed_update_succeeds(
    part: WorkerPart,
    table: str,
    column: str,
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
) -> None:
    overrides: dict[str, object] = {}
    if table == WRITE_RIGHTS[part].run_table:
        overrides["status"] = "RUNNING"
    if table == "terminal_recommendations":
        overrides |= {"rec_type": "YARD_PLACEMENT", "lifecycle_status": "YARD_REC_REQUESTED"}
    row_id = seed_row(root, table, **overrides)
    connection = _open(port_db, part)
    values = {column: GOOD_VALUES[column]}
    try:
        repository = WorkerRepository(connection, part, row_id)
        if table == WRITE_RIGHTS[part].run_table:
            assert repository.update_own_run(values)
        elif table == "terminal_recommendations":
            assert repository.update_terminal_recommendation(row_id, values)
        elif table == "baplie_files":
            assert repository.update_baplie_file(row_id, values)
        else:
            assert repository.fill_vessel_nulls(row_id, values)
        connection.commit()
    finally:
        connection.rollback()
        connection.close()


# Refusals before any statement is sent


@pytest.mark.parametrize(
    ("part", "table", "row", "message"),
    [
        (WorkerPart.PART1, "yard_placement_items", {}, "may not insert"),
        (WorkerPart.VALIDATE, "evaluation_metrics", {}, "may not insert"),
        (WorkerPart.PART3, "drift_measurements", {"notified_at": None}, "isn't a worker's"),
        (WorkerPart.PART3, "drift_measurements", {"is_drifted": 1}, "isn't a worker's"),
        (WorkerPart.PART3, "drift_measurements", {"nope": 1}, "no column"),
        (WorkerPart.EDI, "containers", {"container_number": "x"}, "insert_new_containers"),
        (WorkerPart.PART1, "forecast_runs", {"pull_type": "MANUAL"}, "the Backend's"),
        (WorkerPart.PART1, "forecast_runs", {}, "the Backend's"),
    ],
    ids=str,
)
def test_a_refused_insert_raises(
    part: WorkerPart,
    table: str,
    row: dict[str, object],
    message: str,
    port_db: PortDatabase,
) -> None:
    connection = _open(port_db, part)
    try:
        with pytest.raises(WriteRefused, match=message):
            WorkerRepository(connection, part).insert(table, row)
        assert not connection.core.in_transaction()
    finally:
        connection.close()


def test_insert_many_applies_the_same_checks(worker: WorkerConnection) -> None:
    with pytest.raises(WriteRefused, match="may not insert"):
        WorkerRepository(worker, WorkerPart.EDI).insert_many("recommendations", [{}])


def test_insert_many_writes_every_row(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    row = required_row(root, "feasible_windows", {})
    connection = _open(port_db, WorkerPart.PART1)
    try:
        _force_fk_off(connection)
        repository = WorkerRepository(connection, WorkerPart.PART1)
        repository.insert_many("feasible_windows", [row, row, row])
        connection.commit()
    finally:
        connection.close()
    assert _one(root, "SELECT COUNT(*) FROM feasible_windows")[0] == 3


def test_a_worker_may_not_update_another_workers_table(worker: WorkerConnection) -> None:
    repository = WorkerRepository(worker, WorkerPart.EDI, 1)
    with pytest.raises(WriteRefused, match="may not update"):
        repository.update_terminal_recommendation(1, {"failure_reason": "x"})
    with pytest.raises(WriteRefused, match=r"may not update vessels\.name"):
        repository.fill_vessel_nulls(1, {"name": "x"})
    with pytest.raises(WriteRefused, match=r"baplie_parse_runs\.result_handled_at"):
        repository.update_own_run({"result_handled_at": None})
    with pytest.raises(WriteRefused, match="nothing to update"):
        repository.update_baplie_file(1, {})


def test_a_worker_without_a_run_id_has_no_run_to_update(worker: WorkerConnection) -> None:
    with pytest.raises(WriteRefused, match="no run"):
        WorkerRepository(worker, WorkerPart.EDI).update_own_run({"retry_count": 1})


def test_part3_has_no_run_table(port_db: PortDatabase) -> None:
    connection = _open(port_db, WorkerPart.PART3)
    try:
        with pytest.raises(WriteRefused, match="no run"):
            WorkerRepository(connection, WorkerPart.PART3, 1).update_own_run({"retry_count": 1})
        with pytest.raises(ValueError, match="no runs"):
            read_run(connection, WorkerPart.PART3, 1)
    finally:
        connection.close()


# The rules grants can't enforce


def test_own_run_only_and_only_while_running(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    mine = seed_row(root, "part1_runs", status="RUNNING")
    other = seed_row(root, "part1_runs", status="RUNNING")
    replaced = seed_row(root, "part1_runs", status="REPLACED")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        assert WorkerRepository(connection, WorkerPart.PART1, mine).update_own_run(
            {"retry_count": 2}
        )
        assert not WorkerRepository(connection, WorkerPart.PART1, replaced).update_own_run(
            {"retry_count": 2}
        )
        connection.commit()
    finally:
        connection.close()
    assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {other}")[0] == 0  # noqa: S608
    assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {replaced}")[0] == 0  # noqa: S608


def test_an_unchanged_value_still_counts_as_updated(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        assert WorkerRepository(connection, WorkerPart.PART1, run).update_own_run(
            {"retry_count": 0}
        )
    finally:
        connection.rollback()
        connection.close()


def test_vessel_columns_fill_only_where_null(
    worker: WorkerConnection, root: pymysql.connections.Connection[Any]
) -> None:
    vessel = seed_row(
        root,
        "vessels",
        call_sign="KEEP",
    )
    repository = WorkerRepository(worker, WorkerPart.EDI)
    assert repository.fill_vessel_nulls(vessel, {"call_sign": "NEW", "flag_state": "EG"})
    worker.commit()
    assert _one(root, f"SELECT call_sign, flag_state FROM vessels WHERE id = {vessel}") == (  # noqa: S608
        "KEEP",
        "EG",
    )
    assert repository.fill_vessel_nulls(vessel, {"flag_state": "XX"})
    worker.commit()
    assert _one(root, f"SELECT flag_state FROM vessels WHERE id = {vessel}")[0] == "EG"  # noqa: S608
    assert not repository.fill_vessel_nulls(vessel + 1000, {"flag_state": "XX"})


def test_on_demand_and_failed_forecast_runs_are_a_workers(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    row = required_row(root, "forecast_runs", ROWS["forecast_runs"]) | {
        "pull_type": "ON_DEMAND",
        "berthing_request_id": 1,
        "status": "FAILED",
    }
    connection = _open(port_db, WorkerPart.PART1)
    try:
        _force_fk_off(connection)
        assert WorkerRepository(connection, WorkerPart.PART1).insert("forecast_runs", row) > 0
    finally:
        connection.rollback()
        connection.close()


def test_only_new_container_numbers_are_inserted(
    worker: WorkerConnection, root: pymysql.connections.Connection[Any]
) -> None:
    existing = seed_row(root, "containers", container_number="ABCU1234567", size_type_id=1)
    _force_fk_off(worker)
    repository = WorkerRepository(worker, WorkerPart.EDI)
    ids = repository.insert_new_containers(
        [
            {"container_number": "ABCU1234567", "size_type_id": 9},
            {"container_number": "DEFU7654321", "size_type_id": 1},
        ]
    )
    worker.commit()
    assert ids["ABCU1234567"] == existing
    assert ids["DEFU7654321"] != existing
    assert _one(root, f"SELECT size_type_id FROM containers WHERE id = {existing}")[0] == 1  # noqa: S608
    assert _one(root, "SELECT COUNT(*) FROM containers")[0] == 2
    assert repository.insert_new_containers([{"container_number": "ABCU1234567"}]) == {
        "ABCU1234567": existing
    }
    assert repository.insert_new_containers([]) == {}


@pytest.mark.parametrize(
    "status", ["YARD_REC_REQUESTED", "YARD_REC_ACCEPTED", "YARD_REC_REJECTED", "GENERATED", None]
)
def test_a_worker_may_only_set_generation_statuses(status: str, port_db: PortDatabase) -> None:
    connection = _open(port_db, WorkerPart.YARD)
    try:
        with pytest.raises(WriteRefused, match="lifecycle_status"):
            WorkerRepository(connection, WorkerPart.YARD).update_terminal_recommendation(
                1, {"lifecycle_status": status}
            )
    finally:
        connection.close()


def test_a_reset_recommendation_is_not_overwritten(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    done = seed_row(
        root,
        "terminal_recommendations",
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_GENERATED",
    )
    connection = _open(port_db, WorkerPart.YARD)
    try:
        assert not WorkerRepository(connection, WorkerPart.YARD).update_terminal_recommendation(
            done, {"lifecycle_status": "GENERATION_FAILED"}
        )
    finally:
        connection.rollback()
        connection.close()


def test_the_yard_worker_can_take_the_ct17_locks(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    recommendation = seed_row(
        root,
        "terminal_recommendations",
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    run = seed_row(root, "yard_runs", status="RUNNING", terminal_recommendation_id=recommendation)
    stopped = seed_row(
        root, "yard_runs", status="REPLACED", terminal_recommendation_id=recommendation
    )
    connection = _open(port_db, WorkerPart.YARD)
    try:
        assert WorkerRepository(connection, WorkerPart.YARD, run).lock_yard_result(recommendation)
        connection.rollback()
        assert not WorkerRepository(connection, WorkerPart.YARD, stopped).lock_yard_result(
            recommendation
        )
        connection.rollback()
        assert not WorkerRepository(connection, WorkerPart.YARD, run).lock_yard_result(
            recommendation + 1000
        )
        with pytest.raises(WriteRefused, match="no yard run"):
            WorkerRepository(connection, WorkerPart.YARD).lock_yard_result(recommendation)
    finally:
        connection.rollback()
        connection.close()


def test_the_ct17_locks_really_hold_both_rows(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    recommendation = seed_row(
        root,
        "terminal_recommendations",
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    run = seed_row(root, "yard_runs", status="RUNNING", terminal_recommendation_id=recommendation)
    connection = _open(port_db, WorkerPart.YARD)
    try:
        assert WorkerRepository(connection, WorkerPart.YARD, run).lock_yard_result(recommendation)
        for table, row_id in (("terminal_recommendations", recommendation), ("yard_runs", run)):
            with root.cursor() as cursor, pytest.raises(pymysql.err.OperationalError) as refused:
                cursor.execute(
                    f"SELECT id FROM {table} WHERE id = {row_id} FOR UPDATE NOWAIT"  # noqa: S608
                )
            assert refused.value.args[0] == 3572
            root.rollback()
    finally:
        connection.rollback()
        connection.close()


def test_only_the_yard_worker_has_yard_locks(worker: WorkerConnection) -> None:
    with pytest.raises(WriteRefused, match="no yard run"):
        WorkerRepository(worker, WorkerPart.EDI, 1).lock_yard_result(1)


def test_a_json_none_is_sql_null_and_a_mapping_is_json(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "yard_runs", status="RUNNING", terminal_recommendation_id=1)
    connection = _open(port_db, WorkerPart.YARD)
    try:
        repository = WorkerRepository(connection, WorkerPart.YARD, run)
        repository.update_own_run({"result_detail": {"a": 1}})
        connection.commit()
        assert json.loads(
            _one(root, f"SELECT result_detail FROM yard_runs WHERE id = {run}")[0]  # noqa: S608
        ) == {"a": 1}
        repository.update_own_run({"result_detail": None})
        connection.commit()
        assert _one(root, f"SELECT result_detail IS NULL FROM yard_runs WHERE id = {run}")[0] == 1  # noqa: S608
    finally:
        connection.close()


# Read models


def _seed_request(root: pymysql.connections.Connection[Any]) -> tuple[int, int]:
    vessel_type = seed_row(root, "vessel_types", code="BULK_CARRIER", name="Bulk carrier")
    vessel = seed_row(
        root,
        "vessels",
        loa=Decimal("200.50"),
        beam=Decimal("32.25"),
        max_draft=Decimal("12.75"),
        imo_number="1234567",
        vessel_type_id=vessel_type,
        name="Nile",
    )
    request = seed_row(
        root,
        "berthing_requests",
        vessel_id=vessel,
        requested_terminal_id=3,
        source="MANUAL",
        submitted_by=1,
        requested_eta="2026-11-03 10:00:00",
        arrival_draft=Decimal("11.50"),
        block_coefficient=Decimal("0.810"),
        gross_tonnage=40000,
        deadweight_tonnes=70000,
        status="SUBMITTED",
    )
    return request, vessel


def test_a_request_reads_with_its_vessel_in_exact_types(
    worker: WorkerConnection, root: pymysql.connections.Connection[Any]
) -> None:
    request, vessel = _seed_request(root)
    model = read_request_with_vessel(worker, request)
    assert model is not None
    assert model.request_id == request
    assert model.vessel_id == vessel
    assert model.vessel_type_code == "BULK_CARRIER"
    assert model.arrival_draft == Decimal("11.50")
    assert isinstance(model.block_coefficient, Decimal)
    assert isinstance(model.loa, Decimal)
    assert model.requested_eta == datetime(2026, 11, 3, 10)
    assert model.gross_tonnage == 40000
    assert read_request_with_vessel(worker, request + 1000) is None


def test_tugboats_read_in_id_order(
    worker: WorkerConnection, root: pymysql.connections.Connection[Any]
) -> None:
    first = seed_row(root, "tugboats", name="A", tug_power=Decimal("25.50"), tug_power_unit="HP")
    second = seed_row(root, "tugboats", name="B", tug_power=Decimal("40.00"))
    tugs = read_tugboats(worker)
    assert [tug.id for tug in tugs] == [first, second]
    assert tugs[0].tug_power == Decimal("25.50")
    assert tugs[0].tug_power_unit == "HP"


@pytest.mark.parametrize(
    ("worker", "table", "has_outcome"),
    [
        (WorkerPart.PART1, "part1_runs", True),
        (WorkerPart.PART2, "solver_runs", False),
        (WorkerPart.YARD, "yard_runs", True),
        (WorkerPart.EDI, "baplie_parse_runs", True),
    ],
    indirect=["worker"],
    ids=str,
)
def test_a_run_row_reads_for_each_table(
    worker: WorkerConnection,
    table: str,
    has_outcome: bool,
    request: pytest.FixtureRequest,
    root: pymysql.connections.Connection[Any],
) -> None:
    part = request.node.callspec.params["worker"]
    run = seed_row(root, table, status="RUNNING", started_at="2026-11-03 10:00:00")
    model = read_run(worker, part, run)
    assert model is not None
    assert model.id == run
    assert model.status == "RUNNING"
    assert model.started_at == datetime(2026, 11, 3, 10)
    assert model.finished_at is None
    assert (model.retry_count == 0) is has_outcome
    assert read_run(worker, part, run + 1000) is None


def _widen_enum(
    root: pymysql.connections.Connection[Any], table: str, column: str, definition: str
) -> None:
    with root.cursor() as cursor:
        cursor.execute(f"ALTER TABLE `{table}` MODIFY `{column}` {definition}")
    root.commit()


def test_an_unknown_enum_value_is_skipped_with_a_warning(
    worker: WorkerConnection,
    root: pymysql.connections.Connection[Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = "enum('AVAILABLE','BUSY','MAINTENANCE','INACTIVE') NOT NULL DEFAULT 'AVAILABLE'"
    wider = (
        "enum('AVAILABLE','BUSY','MAINTENANCE','INACTIVE','NEW_ONE') NOT NULL DEFAULT 'AVAILABLE'"
    )
    _widen_enum(root, "tugboats", "status", wider)
    try:
        kept = seed_row(root, "tugboats", name="A", tug_power=1)
        seed_row(root, "tugboats", name="B", tug_power=1, status="NEW_ONE")
        with caplog.at_level(logging.WARNING):
            assert [tug.id for tug in read_tugboats(worker)] == [kept]
        assert "unknown_enum_value_skipped" in caplog.text
    finally:
        worker.rollback()
        with root.cursor() as cursor:
            cursor.execute("DELETE FROM tugboats")
        root.commit()
        _widen_enum(root, "tugboats", "status", original)


def test_a_run_or_request_with_an_unknown_enum_value_reads_as_none(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    request, _vessel = _seed_request(root)
    run = seed_row(root, "part1_runs", status="RUNNING")
    with root.cursor() as cursor:
        cursor.execute(
            "SELECT column_type FROM information_schema.columns WHERE table_schema = DATABASE() "
            "AND table_name = 'berthing_requests' AND column_name = 'status'"
        )
        request_type = cursor.fetchone()[0]
    original_run = "enum('QUEUED','RUNNING','DONE','FAILED','REPLACED') NOT NULL DEFAULT 'QUEUED'"
    _widen_enum(
        root,
        "part1_runs",
        "status",
        "enum('QUEUED','RUNNING','DONE','FAILED','REPLACED','NEW_ONE') NOT NULL DEFAULT 'QUEUED'",
    )
    _widen_enum(root, "berthing_requests", "status", request_type[:-1] + ",'NEW_ONE') NOT NULL")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        with root.cursor() as cursor:
            cursor.execute(f"UPDATE part1_runs SET status = 'NEW_ONE' WHERE id = {run}")  # noqa: S608
            cursor.execute(f"UPDATE berthing_requests SET status = 'NEW_ONE' WHERE id = {request}")  # noqa: S608
        root.commit()
        assert read_run(connection, WorkerPart.PART1, run) is None
        assert read_request_with_vessel(connection, request) is None
    finally:
        connection.rollback()
        connection.close()
        with root.cursor() as cursor:
            cursor.execute("DELETE FROM part1_runs")
            cursor.execute("DELETE FROM berthing_requests")
        root.commit()
        _widen_enum(root, "part1_runs", "status", original_run)
        _widen_enum(root, "berthing_requests", "status", request_type + " NOT NULL")


def test_rights_tables_exist_in_the_definitions() -> None:
    for rights in WRITE_RIGHTS.values():
        assert rights.insert <= set(metadata.tables)
        for table, columns in rights.update.items():
            assert columns <= set(metadata.tables[table].c.keys())


def test_accounts_cover_every_part() -> None:
    assert set(ACCOUNTS) == set(WorkerPart)


# Review findings (independent review, 2026-11-04)


def _session_id(connection: WorkerConnection) -> int:
    cursor = connection.cursor()
    cursor.execute("SELECT CONNECTION_ID()")
    session = int(cursor.fetchone()[0])
    cursor.close()
    return session


def test_after_a_failed_commit_rollback_makes_the_connection_usable_again(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    connection = _open(port_db, WorkerPart.PART1)
    session = _session_id(connection)
    with root.cursor() as admin:
        admin.execute(f"KILL {session}")
    try:
        with pytest.raises(sa.exc.DBAPIError):
            connection.commit()
        connection.rollback()
        assert _session_id(connection) != session
    finally:
        connection.rollback()
        connection.close()


def test_rollback_with_nothing_open_on_a_killed_connection_raises(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    connection = _open(port_db, WorkerPart.PART1)
    session = _session_id(connection)
    connection.commit()
    with root.cursor() as admin:
        admin.execute(f"KILL {session}")
    with pytest.raises(pymysql.err.Error):
        connection.rollback()
    connection.core.invalidate()
    connection.close()


def test_a_cursor_kept_across_a_commit_still_commits_and_rolls_back(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    sql = "UPDATE part1_runs SET retry_count = %s WHERE id = %s"
    try:
        cursor = connection.cursor()
        cursor.execute(sql, (1, run))
        connection.commit()
        cursor.execute(sql, (2, run))
        connection.commit()
        assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {run}")[0] == 2  # noqa: S608
        cursor.execute(sql, (3, run))
        connection.rollback()
        cursor.close()
        assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {run}")[0] == 2  # noqa: S608
    finally:
        connection.close()


def test_rows_with_different_columns_are_refused(worker: WorkerConnection) -> None:
    repository = WorkerRepository(worker, WorkerPart.EDI)
    plain = {"baplie_file_id": 1, "severity": "ERROR", "message": "x"}
    for rows in (
        [plain, plain | {"segment_ref": "KEEP"}],
        [plain | {"segment_ref": "KEEP"}, plain],
    ):
        with pytest.raises(WriteRefused, match="same columns"):
            repository.insert_many("baplie_parse_issues", rows)
    with pytest.raises(WriteRefused, match="same columns"):
        repository.insert_new_containers(
            [
                {"container_number": "ABCU1234567"},
                {"container_number": "DEFU7654321", "size_type_id": 1},
            ]
        )
    assert not worker.core.in_transaction()


def test_a_later_row_gets_the_same_checks(port_db: PortDatabase) -> None:
    connection = _open(port_db, WorkerPart.PART1)
    good = {"pull_type": "SCHEDULED"}
    try:
        repository = WorkerRepository(connection, WorkerPart.PART1)
        with pytest.raises(WriteRefused, match="the Backend's"):
            repository.insert_many("forecast_runs", [good, {"pull_type": "MANUAL"}])
        with pytest.raises(WriteRefused, match="starts as"):
            repository.insert_many(
                "entry_window_proposals", [{"status": "PROPOSED"}, {"status": "CONFIRMED"}]
            )
    finally:
        connection.close()


def test_duplicate_or_missing_container_numbers_are_refused(worker: WorkerConnection) -> None:
    repository = WorkerRepository(worker, WorkerPart.EDI)
    same = {"container_number": "ABCU1234567", "size_type_id": 1}
    with pytest.raises(WriteRefused, match="appears twice"):
        repository.insert_new_containers([same, same])
    with pytest.raises(WriteRefused, match="needs a container_number"):
        repository.insert_new_containers([{"size_type_id": 1}])


def test_another_worker_may_not_insert_containers(port_db: PortDatabase) -> None:
    connection = _open(port_db, WorkerPart.PART1)
    try:
        with pytest.raises(WriteRefused, match="may not insert"):
            WorkerRepository(connection, WorkerPart.PART1).insert_new_containers(
                [{"container_number": "ABCU1234567"}]
            )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "column",
    [
        "confirmed_window_id",
        "confirmed_by",
        "confirmed_at",
        "rejection_reason",
        "rejected_by",
        "rejected_at",
    ],
)
def test_a_new_proposal_may_not_set_the_backends_columns(
    column: str, port_db: PortDatabase
) -> None:
    connection = _open(port_db, WorkerPart.PART1)
    try:
        with pytest.raises(WriteRefused, match="isn't a worker's"):
            WorkerRepository(connection, WorkerPart.PART1).insert(
                "entry_window_proposals", {column: None}
            )
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("part", "table", "allowed", "refused"),
    [
        (
            WorkerPart.PART1,
            "entry_window_proposals",
            "PROPOSED",
            ["CONFIRMED", "REPLACED", "REJECTED", None],
        ),
        (
            WorkerPart.PART2,
            "recommendations",
            "PENDING_REVIEW",
            ["CONFIRMED", "REJECTED", "INVALIDATED", "REPLACED", "MODIFIED_BY_STAFF", None],
        ),
    ],
    ids=str,
)
def test_new_rows_start_only_in_the_workers_status(
    part: WorkerPart,
    table: str,
    allowed: str,
    refused: list[str | None],
    port_db: PortDatabase,
    root: pymysql.connections.Connection[Any],
) -> None:
    connection = _open(port_db, part)
    row = required_row(root, table, {})
    try:
        _force_fk_off(connection)
        repository = WorkerRepository(connection, part)
        for status in refused:
            with pytest.raises(WriteRefused, match="starts as"):
                repository.insert(table, row | {"status": status})
        assert repository.insert(table, row | {"status": allowed}) > 0
        connection.rollback()
        _force_fk_off(connection)
        assert repository.insert(table, row) > 0
        stored = metadata.tables[table]
        assert connection.core.execute(sa.select(stored.c.status)).scalar_one() == allowed
    finally:
        connection.rollback()
        connection.close()


def test_a_datetime_with_an_offset_is_stored_as_utc(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    cairo = datetime(2026, 11, 3, 12, tzinfo=timezone(timedelta(hours=2)))
    try:
        repository = WorkerRepository(connection, WorkerPart.PART1, run)
        repository.update_own_run({"started_at": cairo})
        connection.commit()
    finally:
        connection.close()
    assert _one(root, f"SELECT started_at FROM part1_runs WHERE id = {run}")[0] == datetime(  # noqa: S608
        2026, 11, 3, 10
    )


def test_a_datetime_without_an_offset_is_taken_as_utc(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        repository = WorkerRepository(connection, WorkerPart.PART1, run)
        repository.update_own_run({"started_at": datetime(2026, 11, 3, 12)})
        connection.commit()
        read_back = read_run(connection, WorkerPart.PART1, run)
        assert read_back is not None
        assert read_back.started_at == datetime(2026, 11, 3, 12)
        connection.rollback()
        repository.update_own_run({"started_at": read_back.started_at})
        connection.commit()
    finally:
        connection.close()
    assert _one(root, f"SELECT started_at FROM part1_runs WHERE id = {run}")[0] == datetime(  # noqa: S608
        2026, 11, 3, 12
    )


def test_now_in_utc_matches_the_servers_utc_clock(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    """On a machine set to Cairo time, a naive now() would land two or three hours off."""
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        repository = WorkerRepository(connection, WorkerPart.PART1, run)
        repository.update_own_run({"started_at": datetime.now(UTC)})
        connection.commit()
    finally:
        connection.close()
    difference = _one(
        root,
        "SELECT ABS(TIMESTAMPDIFF(SECOND, started_at, UTC_TIMESTAMP())) "  # noqa: S608
        f"FROM part1_runs WHERE id = {run}",
    )[0]
    assert difference < 60


def test_writes_touch_only_the_row_they_name(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    target = seed_row(root, "baplie_files", parse_status="PENDING")
    other = seed_row(root, "baplie_files", parse_status="PENDING", file_hash_sha256="1" * 64)
    connection = _open(port_db, WorkerPart.EDI)
    try:
        repository = WorkerRepository(connection, WorkerPart.EDI)
        assert repository.update_baplie_file(target, {"parse_status": "PARSED"})
        connection.commit()
    finally:
        connection.close()
    assert _one(root, f"SELECT parse_status FROM baplie_files WHERE id = {other}")[0] == "PENDING"  # noqa: S608
    assert _one(root, f"SELECT parse_status FROM baplie_files WHERE id = {target}")[0] == "PARSED"  # noqa: S608


def test_a_recommendation_update_touches_only_the_row_it_names(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    target = seed_row(
        root,
        "terminal_recommendations",
        recommendation_id=1,
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    other = seed_row(
        root,
        "terminal_recommendations",
        recommendation_id=2,
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    connection = _open(port_db, WorkerPart.YARD)
    try:
        assert WorkerRepository(connection, WorkerPart.YARD).update_terminal_recommendation(
            target, {"lifecycle_status": "GENERATION_FAILED"}
        )
        connection.commit()
    finally:
        connection.close()
    assert (
        _one(root, f"SELECT lifecycle_status FROM terminal_recommendations WHERE id = {other}")[0]  # noqa: S608
        == "YARD_REC_REQUESTED"
    )


def test_a_run_row_read_returns_only_that_run(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    first = seed_row(root, "part1_runs", status="QUEUED")
    second = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        model = read_run(connection, WorkerPart.PART1, first)
        assert model is not None
        assert (model.id, model.status) == (first, "QUEUED")
        later = read_run(connection, WorkerPart.PART1, second)
        assert later is not None
        assert (later.id, later.status) == (second, "RUNNING")
        assert read_run(connection, WorkerPart.PART1, first - 1) is None
    finally:
        connection.rollback()
        connection.close()


def _yard_pair(root: pymysql.connections.Connection[Any]) -> tuple[int, int, int]:
    mine = seed_row(
        root,
        "terminal_recommendations",
        recommendation_id=1,
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    other = seed_row(
        root,
        "terminal_recommendations",
        recommendation_id=2,
        rec_type="YARD_PLACEMENT",
        lifecycle_status="YARD_REC_REQUESTED",
    )
    run = seed_row(root, "yard_runs", status="RUNNING", terminal_recommendation_id=mine)
    return mine, other, run


def test_the_ct17_locks_are_taken_in_its_order(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    mine, _other, run = _yard_pair(root)
    connection = _open(port_db, WorkerPart.YARD)
    statements: list[str] = []

    def record(_conn: Any, _cursor: Any, statement: str, *_rest: Any) -> None:
        statements.append(statement)

    sa.event.listen(connection.core, "before_cursor_execute", record)
    try:
        assert WorkerRepository(connection, WorkerPart.YARD, run).lock_yard_result(mine)
    finally:
        connection.rollback()
        connection.close()
    locks = [s for s in statements if "FOR UPDATE" in s]
    assert len(locks) == 2
    assert "terminal_recommendations" in locks[0]
    assert "yard_runs" in locks[1]


def test_a_run_can_lock_only_its_own_recommendation(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    _mine, other, run = _yard_pair(root)
    connection = _open(port_db, WorkerPart.YARD)
    try:
        assert not WorkerRepository(connection, WorkerPart.YARD, run).lock_yard_result(other)
    finally:
        connection.rollback()
        connection.close()


def test_transaction_rolls_back_on_an_interrupt(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    run = seed_row(root, "part1_runs", status="RUNNING")
    connection = _open(port_db, WorkerPart.PART1)
    try:
        with pytest.raises(KeyboardInterrupt), transaction(connection):
            WorkerRepository(connection, WorkerPart.PART1, run).update_own_run({"retry_count": 2})
            raise KeyboardInterrupt
        # Checked before closing, because closing would roll back anyway.
        assert not connection.core.in_transaction()
    finally:
        connection.close()
    assert _one(root, f"SELECT retry_count FROM part1_runs WHERE id = {run}")[0] == 0  # noqa: S608


def test_one_engine_with_a_small_pool_serves_a_worker(port_db: PortDatabase) -> None:
    settings = load_env_settings(port_db.worker_env(WorkerPart.EDI), WorkerPart.EDI)
    engine = _engine(settings)
    assert _engine(settings) is engine
    connection = connect_worker(settings)
    assert engine.pool.status().startswith("Pool size: 1 ")
    assert engine.pool.checkedout() == 1  # type: ignore[attr-defined]
    replacement = connect_worker(settings)
    assert engine.pool.checkedout() == 2  # type: ignore[attr-defined]
    replacement.close()
    connection.close()
    assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]


def test_dispose_engines_closes_pooled_sessions(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    connection = _open(port_db, WorkerPart.EDI)
    session = _session_id(connection)
    connection.rollback()
    connection.close()
    dispose_engines()
    for _ in range(50):
        count = _one(
            root,
            f"SELECT COUNT(*) FROM information_schema.processlist WHERE id = {session}",  # noqa: S608
        )[0]
        if count == 0:
            break
        time.sleep(0.05)
    assert count == 0


def test_foreign_keys_are_enforced_on_a_worker_write(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> None:
    file_id = seed_row(root, "baplie_files", parse_status="PENDING")
    connection = _open(port_db, WorkerPart.EDI)
    row = {"severity": "ERROR", "message": "x"}
    try:
        repository = WorkerRepository(connection, WorkerPart.EDI)
        with pytest.raises(sa.exc.IntegrityError) as refused:
            repository.insert("baplie_parse_issues", row | {"baplie_file_id": file_id + 1000})
        assert isinstance(refused.value.orig, pymysql.err.IntegrityError)
        assert refused.value.orig.args[0] == 1452
        connection.rollback()
        assert repository.insert("baplie_parse_issues", row | {"baplie_file_id": file_id}) > 0
    finally:
        connection.rollback()
        connection.close()
