"""Evaluation rows against MySQL (AI-071): the code's scope rules match the schema's checks."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from common.db.repository import WorkerRepository
from part3.evaluation import DatasetType, EvaluationMetric, MetricName, mae_metric, write_metrics
from tests.support.port_db import PortDatabase, seed_row

pytestmark = pytest.mark.integration

TRAINED = datetime(2026, 11, 1)  # noqa: DTZ001 - MySQL DATETIME holds UTC without an offset
START = datetime(2026, 11, 1, tzinfo=UTC)
END = START + timedelta(days=7)


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
                cursor.execute("DELETE FROM `evaluation_metrics`")
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


def test_rows_are_stored_with_their_scope(root: Any, worker: WorkerConnection) -> None:
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
    root.commit()
    now = END + timedelta(hours=1)
    mae = mae_metric(version, [10.0, 8.0], [12.0, 7.0], DatasetType.ROLLING, (START, END), now)
    assert mae is not None
    # A system-level row of a metric whose definition is still open (R9): shape only, test value.
    system = EvaluationMetric(
        MetricName.WAIT_TIME, DatasetType.PRODUCTION, Decimal("12.5"), START, END, now
    )
    write_metrics(WorkerRepository(worker, WorkerPart.PART3), [mae, system])
    worker.commit()

    with root.cursor() as cursor:
        cursor.execute(
            "SELECT metric_name, model_version_id, metric_value FROM evaluation_metrics ORDER BY id"
        )
        assert cursor.fetchall() == (
            ("MAE", version, Decimal("1.50000")),
            ("WAIT_TIME", None, Decimal("12.50000")),
        )


def test_the_schema_refuses_what_the_code_refuses(root: Any) -> None:
    """chk_em_scope in MySQL: an MAE row without a model version is refused."""
    with root.cursor() as cursor:
        with pytest.raises(pymysql.err.OperationalError, match="chk_em_scope"):
            cursor.execute(
                "INSERT INTO evaluation_metrics (metric_name, dataset_type, metric_value,"
                " period_start, period_end, computed_at) VALUES ('MAE', 'ROLLING', 1,"
                " '2026-11-01', '2026-11-08', '2026-11-08')"
            )
    root.rollback()
