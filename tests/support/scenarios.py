"""Read a SYNTHETIC scenario file and load it into a port database (AI-015).

The loader turns foreign key checks ON for its session, so a scenario that loads has real parent
rows for every child row. It runs in one transaction: a failure rolls everything back.
"""

import json
import re
from pathlib import Path
from typing import Any, Final

import pymysql

from tools.scenario_generator.model import SYNTHETIC_PREFIX, TABLE_ORDER, Scenario

LOAD_ORDER: Final = TABLE_ORDER
_IDENTIFIER: Final = re.compile(r"[a-z][a-z0-9_]*")


class ScenarioNotSyntheticError(ValueError):
    """A scenario that isn't labelled SYNTHETIC in its file name and metadata."""


def _require_synthetic(scenario: Scenario) -> None:
    label = scenario.metadata.get("label")
    if scenario.metadata.get("synthetic") is not True:
        raise ScenarioNotSyntheticError("metadata doesn't say synthetic: true")
    if not isinstance(label, str) or not label.startswith(SYNTHETIC_PREFIX):
        raise ScenarioNotSyntheticError("metadata has no label starting with SYNTHETIC")


def read_scenario(path: Path) -> Scenario:
    if not path.name.startswith(f"{SYNTHETIC_PREFIX}_"):
        raise ScenarioNotSyntheticError(f"{path.name} doesn't start with {SYNTHETIC_PREFIX}_")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not {"metadata", "tables"} <= document.keys():
        raise ScenarioNotSyntheticError(f"{path.name} has no metadata and tables")
    scenario = Scenario(metadata=document["metadata"], tables=document["tables"])
    _require_synthetic(scenario)
    return scenario


def _identifier(name: str) -> str:
    if _IDENTIFIER.fullmatch(name) is None:
        raise ValueError(f"not a table or column name: {name!r}")
    return f"`{name}`"


def load_scenario(conn: pymysql.connections.Connection[Any], scenario: Scenario) -> dict[str, int]:
    """Insert every table in `LOAD_ORDER` and commit. Returns the rows inserted per table."""
    _require_synthetic(scenario)
    unknown = set(scenario.tables) - set(LOAD_ORDER)
    if unknown:
        raise ValueError(f"tables the loader doesn't know: {sorted(unknown)}")
    inserted: dict[str, int] = {}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET foreign_key_checks = 1")
            for table in LOAD_ORDER:
                rows = scenario.tables.get(table, [])
                for row in rows:
                    names = ", ".join(_identifier(column) for column in row)
                    marks = ", ".join(["%s"] * len(row))
                    sql = f"INSERT INTO {_identifier(table)} ({names}) VALUES ({marks})"  # noqa: S608
                    cursor.execute(sql, tuple(row.values()))
                inserted[table] = len(rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted
