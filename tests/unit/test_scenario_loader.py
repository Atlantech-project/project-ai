import json
from pathlib import Path
from typing import Any, Self

import pytest

from tests.support.scenarios import (
    LOAD_ORDER,
    ScenarioNotSyntheticError,
    load_scenario,
    read_scenario,
)
from tools.scenario_generator.generate import generate
from tools.scenario_generator.io import to_json, write_scenario
from tools.scenario_generator.model import Scenario, ScenarioSize


class _FakeCursor:
    def __init__(self, conn: _FakeConnection) -> None:
        self.conn = conn

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, args: tuple[object, ...] | None = None) -> None:
        self.conn.statements.append(sql)
        if self.conn.fail_on is not None and self.conn.fail_on in sql:
            raise RuntimeError("insert failed")


class _FakeConnection:
    def __init__(self, fail_on: str | None = None) -> None:
        self.statements: list[str] = []
        self.fail_on = fail_on
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def _scenario() -> Scenario:
    return generate(ScenarioSize.MINIMUM, 1, 1)


def _load(conn: _FakeConnection, scenario: Scenario) -> dict[str, int]:
    fake: Any = conn
    return load_scenario(fake, scenario)


def test_read_scenario_round_trips(tmp_path: Path) -> None:
    scenario = _scenario()
    assert read_scenario(write_scenario(scenario, tmp_path)) == scenario


def test_read_scenario_refuses_a_file_without_the_prefix(tmp_path: Path) -> None:
    path = tmp_path / "minimum_seed1.json"
    path.write_text(to_json(_scenario()), encoding="utf-8")
    with pytest.raises(ScenarioNotSyntheticError, match="SYNTHETIC_"):
        read_scenario(path)


@pytest.mark.parametrize("change", [{"synthetic": False}, {"label": "operational"}, {"label": 3}])
def test_read_scenario_refuses_wrong_metadata(tmp_path: Path, change: dict[str, object]) -> None:
    scenario = _scenario()
    document = {"metadata": scenario.metadata | change, "tables": scenario.tables}
    path = tmp_path / "SYNTHETIC_minimum_seed1.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ScenarioNotSyntheticError):
        read_scenario(path)


def test_read_scenario_refuses_missing_metadata_keys(tmp_path: Path) -> None:
    document: dict[str, object] = {"metadata": {}, "tables": {}}
    path = tmp_path / "SYNTHETIC_minimum_seed1.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ScenarioNotSyntheticError):
        read_scenario(path)


def test_load_scenario_refuses_an_unlabelled_scenario() -> None:
    scenario = Scenario(_scenario().metadata | {"synthetic": False}, _scenario().tables)
    conn = _FakeConnection()
    with pytest.raises(ScenarioNotSyntheticError):
        _load(conn, scenario)
    assert conn.statements == []


def test_foreign_key_checks_are_on_before_the_first_insert() -> None:
    conn = _FakeConnection()
    _load(conn, _scenario())
    assert conn.statements[0] == "SET foreign_key_checks = 1"
    assert conn.statements[1].startswith("INSERT")


def test_tables_are_inserted_in_load_order() -> None:
    conn = _FakeConnection()
    _load(conn, _scenario())
    seen: list[str] = []
    for statement in conn.statements[1:]:
        table = statement.split("`")[1]
        if not seen or seen[-1] != table:
            seen.append(table)
    assert seen == list(LOAD_ORDER)


def test_a_successful_load_commits_once_and_returns_counts() -> None:
    conn = _FakeConnection()
    counts = _load(conn, _scenario())
    assert (conn.commits, conn.rollbacks) == (1, 0)
    assert counts == _scenario().metadata["counts"]


def test_a_failed_insert_rolls_back_and_raises() -> None:
    conn = _FakeConnection(fail_on="`vessels`")
    with pytest.raises(RuntimeError, match="insert failed"):
        _load(conn, _scenario())
    assert (conn.commits, conn.rollbacks) == (0, 1)


def test_unknown_tables_are_refused() -> None:
    scenario = Scenario(_scenario().metadata, {**_scenario().tables, "users": [{"id": 1}]})
    with pytest.raises(ValueError, match="users"):
        _load(_FakeConnection(), scenario)


def test_bad_column_names_are_refused_before_sql_is_built() -> None:
    tables: dict[str, list[dict[str, object]]] = {
        **_scenario().tables,
        "terminals": [{"id; DROP TABLE x": 1}],
    }
    conn = _FakeConnection()
    with pytest.raises(ValueError, match="not a table or column name"):
        _load(conn, Scenario(_scenario().metadata, tables))
    assert conn.rollbacks == 1


@pytest.mark.parametrize("document", [[], {"metadata": {}}, {"tables": {}}])
def test_read_scenario_refuses_a_file_without_metadata_and_tables(
    tmp_path: Path, document: object
) -> None:
    path = tmp_path / "SYNTHETIC_minimum_seed1.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ScenarioNotSyntheticError, match="no metadata and tables"):
        read_scenario(path)
