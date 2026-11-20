"""The SYNTHETIC A4 cases (AI-044, DEC-34), run with the production code lists."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import pytest

from part1.feasibility import (
    AssessmentScope,
    Category,
    Comparator,
    ConstraintType,
    EnvironmentStep,
    SafetyConstraint,
    SeriesUnits,
    assess,
    blocked_periods,
)
from tests.unit.part1.feasibility.builders import make_step

FIXTURE: Final = (
    Path(__file__).resolve().parents[3] / "fixtures" / "a4" / "SYNTHETIC_a4_threshold_cases.json"
)


def _load() -> dict[str, Any]:
    with FIXTURE.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


def _time(text: str | None) -> datetime | None:
    return None if text is None else datetime.fromisoformat(text)


def _types(data: dict[str, Any]) -> list[ConstraintType]:
    return [
        ConstraintType(
            id=t["id"],
            code=t["code"],
            category=Category(t["category"]),
            unit=t["unit"],
            comparator=Comparator(t["comparator"]),
            is_hard_safety_limit=t["is_hard_safety_limit"],
        )
        for t in data["constraint_types"]
    ]


def _constraint(row: dict[str, Any]) -> SafetyConstraint:
    active_from = _time(row["active_from"])
    assert active_from is not None
    return SafetyConstraint(
        id=row["id"],
        constraint_type_id=row["constraint_type_id"],
        value=Decimal(row["value"]),
        active_from=active_from,
        active_to=_time(row["active_to"]),
        terminal_id=row.get("terminal_id"),
        berth_id=row.get("berth_id"),
        vessel_type_id=row.get("vessel_type_id"),
        imdg_class=row.get("imdg_class"),
        equipment_category_id=row.get("equipment_category_id"),
    )


def _step(row: dict[str, Any]) -> EnvironmentStep:
    valid_at = _time(row["valid_at"])
    assert valid_at is not None
    return make_step(valid_at, {k: v for k, v in row.items() if k != "valid_at"})


def test_the_fixture_is_labelled_synthetic() -> None:
    metadata = _load()["metadata"]
    assert metadata["synthetic"] is True
    assert metadata["label"].startswith("SYNTHETIC")
    assert FIXTURE.name.startswith("SYNTHETIC_")


@pytest.mark.parametrize("case", _load()["cases"], ids=lambda c: str(c["name"]))
def test_synthetic_case(case: dict[str, Any]) -> None:
    data = _load()
    scope = case["scope"]
    results = assess(
        [_step(s) for s in case["steps"]],
        _types(data),
        [_constraint(c) for c in case["constraints"]],
        AssessmentScope(
            terminal_id=scope["terminal_id"],
            vessel_type_id=scope["vessel_type_id"],
            berth_id=scope["berth_id"],
            imdg_classes=frozenset(scope["imdg_classes"]),
        ),
        SeriesUnits(**case["units"]),
    )
    expected = case["expected"]
    assert [
        [[f.reason.value, f.constraint_type_code, str(f.limit)] for f in r.failures]
        for r in results
    ] == expected["failures"]
    periods = blocked_periods(results, timedelta(minutes=case["step_minutes"]))
    assert [
        {
            "start": p.start.isoformat().replace("+00:00", "Z"),
            "end": p.end.isoformat().replace("+00:00", "Z"),
            "reason": p.reason.value,
            "code": p.constraint_type_code,
        }
        for p in periods
    ] == expected["blocked_periods"]
