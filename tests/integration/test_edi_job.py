"""The EDI job against MySQL (AI-032): all-or-nothing writes and fill-empty vessel fields."""

import shutil
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymysql
import pytest

from common.config import PortSettings, WorkerPart, load_env_settings
from common.db import repository
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from common.runtime.envelope import Envelope, JobType
from common.runtime.worker import JobContext
from edi.job import make_handler
from tests.support.edi_corpus import CORPUS_ROOT
from tests.support.port_db import PortDatabase, seed_row

pytestmark = pytest.mark.integration

TABLES = (
    "baplie_parse_issues",
    "container_manifest_entries",
    "containers",
    "baplie_files",
    "container_size_types",
    "imdg_classes",
    "vessels",
    "port_profiles",
)


@pytest.fixture(autouse=True)
def fresh_sessions() -> Iterator[None]:
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
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table in TABLES:
                    cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
        finally:
            conn.close()


@pytest.fixture
def worker(port_db: PortDatabase, root: Any) -> Iterator[WorkerConnection]:
    connection = connect_worker(
        load_env_settings(port_db.worker_env(WorkerPart.EDI), WorkerPart.EDI)
    )
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _seed(root: Any, volume: Path, case: str) -> int:
    shutil.copy(CORPUS_ROOT / f"{case}.edi", volume / f"{case}.edi")
    vessel = seed_row(
        root, "vessels", imo_number="9811000", name="MSC ALEXANDRIA", call_sign="KEEP"
    )
    for code, length, group in (
        ("22G1", 20, "GENERAL"),
        ("45G1", 40, "GENERAL"),
        ("45R1", 40, "REEFER"),
    ):
        teu = Decimal(1) if length == 20 else Decimal(2)
        seed_row(
            root,
            "container_size_types",
            code=code,
            length_ft=length,
            type_group=group,
            teu_factor=teu,
        )
    seed_row(root, "imdg_classes", code="3", name="Flammable liquids")
    seed_row(root, "port_profiles", port_code="EGDAM")
    return seed_row(
        root,
        "baplie_files",
        vessel_id=vessel,
        storage_path=f"{case}.edi",
        parse_status="PENDING",
        status="STAGED",
    )


def _context(connection: WorkerConnection, file_id: int) -> JobContext:
    envelope = Envelope(
        "1.0",
        JobType.BAPLIE_PARSE,
        "job-1",
        1,
        "2026-11-21T12:00:00Z",
        None,
        {"baplie_file_id": file_id, "source": "FILE"},
    )
    return JobContext(envelope, PortSettings([]), connection, 0)


def _count(root: Any, sql: str) -> Any:
    root.commit()
    with root.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()[0]


def test_parsed_file_commits_and_keeps_vessel_fields(
    root: Any, worker: WorkerConnection, tmp_path: Path
) -> None:
    file_id = _seed(root, tmp_path, "01-valid-221")
    result = make_handler(tmp_path)(_context(worker, file_id))
    worker.commit()

    assert result.outcome == "PARSED"
    assert (
        _count(root, "SELECT COUNT(*) FROM container_manifest_entries")
        == result.run_columns["container_count"]
    )
    assert _count(root, f"SELECT parse_status FROM baplie_files WHERE id = {file_id}") == "PARSED"  # noqa: S608
    assert _count(root, f"SELECT status FROM baplie_files WHERE id = {file_id}") == "STAGED"  # noqa: S608
    assert _count(root, "SELECT call_sign FROM vessels") == "KEEP"


def test_a_failure_mid_write_leaves_nothing(
    root: Any, worker: WorkerConnection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_id = _seed(root, tmp_path, "03-valid-with-warnings")
    real = repository.WorkerRepository.insert_many

    def failing(self: Any, table: str, rows: Any) -> None:
        if table == "baplie_parse_issues":  # after containers and manifest entries are written
            raise RuntimeError("injected fault")
        real(self, table, rows)

    monkeypatch.setattr(repository.WorkerRepository, "insert_many", failing)
    with pytest.raises(RuntimeError, match="injected"):
        make_handler(tmp_path)(_context(worker, file_id))
    worker.rollback()  # what the runtime does on any handler error

    assert _count(root, "SELECT COUNT(*) FROM containers") == 0
    assert _count(root, "SELECT COUNT(*) FROM container_manifest_entries") == 0
    assert _count(root, f"SELECT parse_status FROM baplie_files WHERE id = {file_id}") == "PENDING"  # noqa: S608
