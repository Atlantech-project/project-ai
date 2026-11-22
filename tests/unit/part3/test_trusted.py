"""Trusted-data selection (AI-074): suspect field events never reach Part 3."""

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.dialects import mysql

from common.db.tables import ACTUAL_STATUS_UPDATES
from part3 import trusted
from part3.trusted import filter_trusted, trusted_select, trusted_status_updates

PART3 = Path(__file__).resolve().parents[3] / "part3"
T0 = datetime(2026, 11, 1, tzinfo=UTC)
NO_DB: Any = object()


def _sql(statement: Any) -> str:
    return str(statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))


class _Capture:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> _Capture:
        self.statements.append(statement)
        return self

    def mappings(self) -> list[dict[str, Any]]:
        return [
            {
                "id": 1,
                "plan_component_id": 7,
                "component_type": "BERTH",
                "status": "COMPLETED",
                "reported_at": T0,
                "received_at": T0,
            }
        ]


def test_trusted_select_always_filters_suspect_rows() -> None:
    assert "clock_skew_suspect = 0" in _sql(trusted_select(ACTUAL_STATUS_UPDATES.c.id))


@pytest.mark.parametrize("ids", [None, [7, 8]])
def test_the_read_carries_the_filter(
    monkeypatch: pytest.MonkeyPatch, ids: list[int] | None
) -> None:
    capture = _Capture()
    monkeypatch.setattr(trusted, "core_of", lambda _c: capture)
    rows = trusted_status_updates(
        NO_DB, reported_from=T0, reported_to=T0 + timedelta(days=1), plan_component_ids=ids
    )

    sql = _sql(capture.statements[0])
    assert "clock_skew_suspect = 0" in sql
    assert rows[0].plan_component_id == 7


def test_an_empty_component_list_reads_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture()
    monkeypatch.setattr(trusted, "core_of", lambda _c: capture)
    assert (
        trusted_status_updates(
            NO_DB, reported_from=T0, reported_to=T0 + timedelta(hours=1), plan_component_ids=[]
        )
        == []
    )
    assert capture.statements == []


def test_bad_periods_are_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        trusted_status_updates(NO_DB, reported_from=T0.replace(tzinfo=None), reported_to=T0)
    with pytest.raises(ValueError, match="end after"):
        trusted_status_updates(NO_DB, reported_from=T0, reported_to=T0)


def test_no_option_includes_suspect_rows() -> None:
    """Human review never makes a record trusted: the API has no way to ask for suspect rows."""
    import inspect

    parameters = inspect.signature(trusted_status_updates).parameters
    assert not any("suspect" in name or "include" in name for name in parameters)


def test_dataset_filter_keeps_only_trusted_rows() -> None:
    rows = [{"id": 1, "clock_skew_suspect": 0}, {"id": 2, "clock_skew_suspect": 1}]
    split = filter_trusted(rows)
    assert [r["id"] for r in split.kept] == [1]
    assert not split.result.passed


def test_every_part3_query_goes_through_the_trusted_select() -> None:
    """Every Part 3 module that names `actual_status_updates` does it in `part3/trusted.py`."""
    offenders = []
    for path in PART3.rglob("*.py"):
        if path.name == "trusted.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        text = path.read_text(encoding="utf-8")
        if "ACTUAL_STATUS_UPDATES" in names or "actual_status_updates" in text:
            offenders.append(path.name)
    assert offenders == []
