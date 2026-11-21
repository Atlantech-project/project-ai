"""Drift measurements against MySQL (AI-072): the stored is_drifted matches the code."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from common.db.repository import WorkerRepository
from part3.drift import Thresholds, measure, write_measurements
from tests.support.port_db import PortDatabase, seed_row

pytestmark = pytest.mark.integration

TRAINED = datetime(2026, 11, 1)  # noqa: DTZ001 - MySQL DATETIME holds UTC without an offset


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
                cursor.execute("DELETE FROM `drift_measurements`")
                cursor.execute("DELETE FROM `ml_model_versions`")
                cursor.execute("DELETE FROM `ml_models`")
            conn.commit()
        finally:
            conn.close()


@pytest.fixture
def worker(port_db: PortDatabase, root: Any) -> Iterator[WorkerConnection]:
    settings = load_env_settings(port_db.worker_env(WorkerPart.PART3), WorkerPart.PART3)
    connection = connect_worker(settings)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_stored_is_drifted_matches(root: Any, worker: WorkerConnection) -> None:
    model = seed_row(root, "ml_models", model_key="M2_SERVICE_TIME", algorithm_family="LightGBM")
    version = seed_row(
        root,
        "ml_model_versions",
        ml_model_id=model,
        version_no=1,
        status="CHALLENGER",
        artifact_path="M2_SERVICE_TIME/v1/model.bin",
        trained_at=TRAINED,
    )
    thresholds = Thresholds(Decimal("0.2"), Decimal("1.5"))  # test values only
    now = datetime(2026, 11, 21, tzinfo=UTC)
    ref = [float(i) for i in range(100)]
    rows = measure(
        version, {"moves": (ref, [v + 60 for v in ref])}, ([1.0], [1.0]), thresholds, now
    )
    write_measurements(WorkerRepository(worker, WorkerPart.PART3), rows)
    worker.commit()
    root.commit()
    with root.cursor() as cursor:
        cursor.execute("SELECT metric_type, is_drifted FROM drift_measurements ORDER BY id")
        stored = [(r[0], bool(r[1])) for r in cursor.fetchall()]
    assert (
        stored
        == [(m.metric_type, m.is_drifted) for m in rows]
        == [("PSI", True), ("ROLLING_MAE", False)]
    )
