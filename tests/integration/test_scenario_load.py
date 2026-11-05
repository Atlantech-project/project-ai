"""Both scenario sizes load into the real schema, with foreign key checks on (AI-015)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Final

import pymysql
import pytest

from tests.support.port_db import PortDatabase
from tests.support.scenarios import LOAD_ORDER, load_scenario, read_scenario
from tools.scenario_generator.model import Scenario

pytestmark = pytest.mark.integration

FIXTURES: Final = Path(__file__).resolve().parents[1] / "fixtures"
MINIMUM: Final = FIXTURES / "SYNTHETIC_minimum_seed1.json"
REFERENCE: Final = FIXTURES / "SYNTHETIC_reference_seed1.json"


def _empty_the_scenario_tables(database: PortDatabase) -> None:
    conn = database.root()  # its session starts with foreign key checks off
    try:
        with conn.cursor() as cursor:
            for table in reversed(LOAD_ORDER):
                cursor.execute(f"TRUNCATE TABLE `{table}`")  # noqa: S608
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def database(port_db: PortDatabase) -> Iterator[PortDatabase]:
    """The shared port database with the scenario tables empty before and after each test.

    Dropping a database of our own would drop the shared worker users and roles with it, so the
    other integration tests would lose their accounts.
    """
    _empty_the_scenario_tables(port_db)
    try:
        yield port_db
    finally:
        _empty_the_scenario_tables(port_db)


def _counts(conn: pymysql.connections.Connection[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cursor:
        for table in LOAD_ORDER:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")  # noqa: S608
            counts[table] = int(cursor.fetchone()[0])
    return counts


@pytest.mark.parametrize(
    ("path", "terminals", "berths"),
    [(MINIMUM, 1, 5), (REFERENCE, 8, 36)],
    ids=["minimum", "reference"],
)
def test_scenario_loads_into_the_real_schema(
    database: PortDatabase, path: Path, terminals: int, berths: int
) -> None:
    scenario = read_scenario(path)
    conn = database.root()
    try:
        inserted = load_scenario(conn, scenario)
        counts = _counts(conn)
    finally:
        conn.close()
    assert inserted == scenario.metadata["counts"]
    assert counts == scenario.metadata["counts"]
    assert (counts["terminals"], counts["berths"]) == (terminals, berths)


def test_loaded_rows_satisfy_foreign_keys(database: PortDatabase) -> None:
    conn = database.root()
    try:
        load_scenario(conn, read_scenario(REFERENCE))
        with conn.cursor() as cursor:
            cursor.execute("SET foreign_key_checks = 1")
            cursor.execute(
                "SELECT COUNT(*) FROM berthing_requests r "
                "LEFT JOIN vessels v ON v.id = r.vessel_id "
                "LEFT JOIN terminals t ON t.id = r.requested_terminal_id "
                "WHERE v.id IS NULL OR t.id IS NULL"
            )
            assert cursor.fetchone()[0] == 0
            cursor.execute(
                "SELECT COUNT(*) FROM berths b LEFT JOIN berth_terminals bt ON bt.berth_id = b.id "
                "WHERE bt.terminal_id IS NULL"
            )
            assert cursor.fetchone()[0] == 0
    finally:
        conn.close()


def test_foreign_keys_are_enforced_during_the_load(database: PortDatabase) -> None:
    scenario = read_scenario(MINIMUM)
    orphan = {**scenario.tables["berthing_requests"][0], "vessel_id": 999_999}
    broken = Scenario(scenario.metadata, {**scenario.tables, "berthing_requests": [orphan]})
    conn = database.root()  # its session starts with foreign key checks off
    try:
        with pytest.raises(pymysql.err.IntegrityError):
            load_scenario(conn, broken)
        assert set(_counts(conn).values()) == {0}
    finally:
        conn.close()


def test_a_failed_load_leaves_nothing_behind(database: PortDatabase) -> None:
    scenario = read_scenario(MINIMUM)
    vessel = dict(scenario.tables["vessels"][-1])
    vessel["beam"] = vessel["loa"]  # chk_vessel_dims needs beam < loa
    broken = Scenario(
        scenario.metadata,
        {**scenario.tables, "vessels": [*scenario.tables["vessels"][:-1], vessel]},
    )
    conn = database.root()
    try:
        # MySQL reports a CHECK violation (3819) as an OperationalError.
        with pytest.raises(pymysql.err.OperationalError, match="chk_vessel_dims"):
            load_scenario(conn, broken)
        assert set(_counts(conn).values()) == {0}
    finally:
        conn.close()


def test_loading_the_same_scenario_twice_is_refused(database: PortDatabase) -> None:
    scenario = read_scenario(MINIMUM)
    conn = database.root()
    try:
        load_scenario(conn, scenario)
        with pytest.raises(pymysql.err.IntegrityError):
            load_scenario(conn, scenario)
        assert _counts(conn) == scenario.metadata["counts"]
    finally:
        conn.close()
