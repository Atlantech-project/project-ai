"""Model registry against MySQL (AI-070): the one-champion rule and the champion read."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from common.registry import ModelKey, read_champion
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
                cursor.execute("DELETE FROM `ml_model_versions`")
                cursor.execute("DELETE FROM `ml_models`")
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


def _version(root: Any, model_id: int, version_no: int, status: str) -> int:
    return seed_row(
        root,
        "ml_model_versions",
        ml_model_id=model_id,
        version_no=version_no,
        status=status,
        artifact_path=f"M2_SERVICE_TIME/v{version_no}/model.bin",
        trained_at=TRAINED,
        deployed_at=TRAINED if status == "CHAMPION" else None,
    )


def test_the_schema_allows_one_champion_per_model(root: Any) -> None:
    model = seed_row(root, "ml_models", model_key="M2_SERVICE_TIME", algorithm_family="LightGBM")
    _version(root, model, 1, "CHAMPION")
    with pytest.raises(pymysql.err.IntegrityError):
        _version(root, model, 2, "CHAMPION")
    root.rollback()


def test_worker_reads_the_champion_or_none(root: Any, worker: WorkerConnection) -> None:
    model = seed_row(root, "ml_models", model_key="M2_SERVICE_TIME", algorithm_family="LightGBM")
    _version(root, model, 1, "CHALLENGER")
    assert read_champion(worker, ModelKey.M2_SERVICE_TIME) is None
    worker.rollback()

    champion = _version(root, model, 2, "CHAMPION")
    found = read_champion(worker, ModelKey.M2_SERVICE_TIME)
    assert found is not None
    assert (found.id, found.version_no, found.status) == (champion, 2, "CHAMPION")
    assert read_champion(worker, ModelKey.M4_DELAY_RISK) is None
