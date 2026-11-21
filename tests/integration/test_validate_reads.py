"""B2 context loader and option read against MySQL (AI-060)."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from part2.context import read_constraint_types, read_vessel_type_ids
from part2.validation.job import read_option
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
                for table in (
                    "constraint_types",
                    "vessel_types",
                    "recommendation_option_tugs",
                    "recommendation_options",
                    "recommendations",
                ):
                    cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608
            conn.commit()
        finally:
            conn.close()


@pytest.fixture
def worker(port_db: PortDatabase, root: Any) -> Iterator[WorkerConnection]:
    settings = load_env_settings(port_db.worker_env(WorkerPart.VALIDATE), WorkerPart.VALIDATE)
    connection = connect_worker(settings)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_reference_reads(root: Any, worker: WorkerConnection) -> None:
    seed_row(
        root,
        "constraint_types",
        code="MAX_WIND_KN",
        category="ENVIRONMENTAL",
        unit="KNOTS",
        comparator="MAX_ALLOWED",
        is_hard_safety_limit=1,
    )
    vessel_type = seed_row(root, "vessel_types", code="CONTAINER", name="Container")
    types = read_constraint_types(worker)
    assert [(t.code, t.is_hard_safety_limit) for t in types] == [("MAX_WIND_KN", True)]
    assert read_vessel_type_ids(worker) == {"CONTAINER": vessel_type}


def test_option_read_with_tugs_and_status(root: Any, worker: WorkerConnection) -> None:
    rec = seed_row(root, "recommendations", berthing_request_id=77, status="PENDING_REVIEW")
    opt = seed_row(
        root,
        "recommendation_options",
        recommendation_id=rec,
        berth_id=11,
        planned_start=TRAINED,
        planned_end=TRAINED.replace(hour=4),
        pilot_user_id=31,
    )
    for tug in (42, 41):
        seed_row(root, "recommendation_option_tugs", option_id=opt, tugboat_id=tug)
    option, status = read_option(worker, opt)
    assert (option.request_id, option.berth_id, option.tug_ids, status) == (
        77,
        11,
        (41, 42),
        "PENDING_REVIEW",
    )
