"""Trusted-data selection against MySQL (AI-074): suspect rows never come back."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from part3.trusted import trusted_status_updates
from tests.support.port_db import PortDatabase, seed_row

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 1, 6)  # noqa: DTZ001 - MySQL DATETIME holds UTC without an offset


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
                cursor.execute("DELETE FROM `actual_status_updates`")
            conn.commit()
        finally:
            conn.close()


@pytest.fixture
def worker(port_db: PortDatabase, root: Any) -> Iterator[WorkerConnection]:
    settings = load_env_settings(port_db.worker_env(WorkerPart.PART2), WorkerPart.PART2)
    connection = connect_worker(settings)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _event(root: Any, n: int, suspect: int) -> int:
    return seed_row(
        root,
        "actual_status_updates",
        client_event_id=f"00000000-0000-0000-0000-{n:012d}",
        plan_component_id=7,
        component_type="BERTH",
        status="STARTED",
        reported_at=T0 + timedelta(minutes=n),
        received_at=T0 + timedelta(minutes=n),
        clock_skew_suspect=suspect,
    )


def test_suspect_rows_are_excluded(root: Any, worker: WorkerConnection) -> None:
    trusted = _event(root, 1, 0)
    _event(root, 2, 1)
    start = T0.replace(tzinfo=UTC)
    rows = trusted_status_updates(
        worker, reported_from=start, reported_to=start + timedelta(hours=1)
    )
    assert [r.id for r in rows] == [trusted]
