"""Scope resolution and strictest wins (AI-044 criterion 2: "Strictest-wins tests with overlapping
scopes"), and active periods as half-open UTC intervals. SYNTHETIC limits only."""

from dataclasses import replace
from datetime import timedelta, timezone

import pytest

from part1.feasibility import SafetyConstraint, applies, resolve_limit
from tests.unit.part1.feasibility.builders import (
    BERTH,
    EQUIPMENT,
    OTHER_BERTH,
    OTHER_TERMINAL,
    OTHER_VESSEL_TYPE,
    SCOPE,
    SYN_MIN_VISIBILITY,
    T0,
    TERMINAL,
    VESSEL_TYPE,
    WIND,
    limit,
)

SCOPE_WITH_BERTH = replace(SCOPE, berth_id=BERTH, imdg_classes=frozenset({"3"}))
SCOPE_WITH_IMDG = replace(SCOPE, imdg_classes=frozenset({"3"}))


def _value(rows: list[SafetyConstraint], scope: object = SCOPE, ctype: object = WIND) -> str | None:
    row = resolve_limit(rows, ctype, scope, T0)  # type: ignore[arg-type]
    return None if row is None else str(row.value)


# (rows, scope, expected strictest value). WIND is MAX_ALLOWED: the lowest applicable value wins.
MAX_CASES = [
    ([limit(WIND, "30"), limit(WIND, "25", terminal_id=TERMINAL)], SCOPE, "25"),
    ([limit(WIND, "25"), limit(WIND, "30", terminal_id=TERMINAL)], SCOPE, "25"),
    ([limit(WIND, "30"), limit(WIND, "20", vessel_type_id=VESSEL_TYPE)], SCOPE, "20"),
    ([limit(WIND, "30"), limit(WIND, "20", vessel_type_id=OTHER_VESSEL_TYPE)], SCOPE, "30"),
    ([limit(WIND, "30"), limit(WIND, "15", terminal_id=OTHER_TERMINAL)], SCOPE, "30"),
    ([limit(WIND, "30"), limit(WIND, "18", imdg_class="3")], SCOPE_WITH_IMDG, "18"),
    ([limit(WIND, "30"), limit(WIND, "18", imdg_class="3")], SCOPE, "30"),
    (
        [
            limit(WIND, "30"),
            limit(WIND, "28", terminal_id=TERMINAL),
            limit(WIND, "26", terminal_id=TERMINAL, berth_id=BERTH),
            limit(WIND, "24", vessel_type_id=VESSEL_TYPE),
            limit(WIND, "22", imdg_class="3"),
        ],
        SCOPE_WITH_BERTH,
        "22",
    ),
    ([], SCOPE, None),
]


@pytest.mark.parametrize(("rows", "scope", "expected"), MAX_CASES)
def test_strictest_wins_for_max_allowed(
    rows: list[SafetyConstraint], scope: object, expected: str | None
) -> None:
    assert _value(rows, scope) == expected


# SYN_MIN_VISIBILITY is MIN_REQUIRED: the highest applicable value wins.
MIN_CASES = [
    ([limit(SYN_MIN_VISIBILITY, "1"), limit(SYN_MIN_VISIBILITY, "2", terminal_id=TERMINAL)], "2"),
    ([limit(SYN_MIN_VISIBILITY, "2"), limit(SYN_MIN_VISIBILITY, "1", terminal_id=TERMINAL)], "2"),
    (
        [
            limit(SYN_MIN_VISIBILITY, "1"),
            limit(SYN_MIN_VISIBILITY, "3", terminal_id=OTHER_TERMINAL),
        ],
        "1",
    ),
]


@pytest.mark.parametrize(("rows", "expected"), MIN_CASES)
def test_strictest_wins_for_min_required(rows: list[SafetyConstraint], expected: str) -> None:
    assert _value(rows, ctype=SYN_MIN_VISIBILITY) == expected


def test_a_tie_resolves_to_the_lowest_row_id() -> None:
    rows = [limit(WIND, "25", row_id=9), limit(WIND, "25", terminal_id=TERMINAL, row_id=3)]
    row = resolve_limit(rows, WIND, SCOPE, T0)
    assert row is not None and row.id == 3


def test_rows_of_another_constraint_type_are_ignored() -> None:
    assert _value([limit(SYN_MIN_VISIBILITY, "1")]) is None


def test_without_a_berth_every_berth_limit_of_the_terminal_applies() -> None:
    rows = [
        limit(WIND, "30"),
        limit(WIND, "22", terminal_id=TERMINAL, berth_id=BERTH),
        limit(WIND, "20", terminal_id=TERMINAL, berth_id=OTHER_BERTH),
        limit(WIND, "10", terminal_id=OTHER_TERMINAL, berth_id=99),
    ]
    assert _value(rows) == "20"


def test_with_a_berth_only_that_berths_limits_apply() -> None:
    rows = [
        limit(WIND, "30"),
        limit(WIND, "22", terminal_id=TERMINAL, berth_id=BERTH),
        limit(WIND, "20", terminal_id=TERMINAL, berth_id=OTHER_BERTH),
    ]
    assert _value(rows, replace(SCOPE, berth_id=BERTH)) == "22"
    assert _value(rows, replace(SCOPE, berth_id=OTHER_BERTH)) == "20"


# IMDG codes are classes ("2") or divisions ("2.1"). A class row covers its divisions; a division
# row covers only that division (review finding, user ruling 2026-11-20).
@pytest.mark.parametrize(
    ("row_class", "cargo", "expected"),
    [
        ("3", {"3"}, True),
        ("2", {"2.1"}, True),
        ("2", {"2.3", "9"}, True),
        ("1", {"1.4"}, True),
        ("2.1", {"2.1"}, True),
        ("2.1", {"2.2"}, False),
        ("2.1", {"2"}, False),
        ("2", {"3"}, False),
        ("1", {"1"}, True),
        ("1", set(), False),
    ],
)
def test_an_imdg_class_row_covers_its_divisions(
    row_class: str, cargo: set[str], expected: bool
) -> None:
    scope = replace(SCOPE, imdg_classes=frozenset(cargo))
    assert applies(limit(WIND, "25", imdg_class=row_class), scope, T0) is expected


def test_a_class_limit_is_the_strictest_for_division_cargo() -> None:
    rows = [limit(WIND, "30"), limit(WIND, "18", imdg_class="2")]
    assert _value(rows, replace(SCOPE, imdg_classes=frozenset({"2.1"}))) == "18"


def test_equipment_limits_never_apply_in_a4() -> None:
    rows = [limit(WIND, "30"), limit(WIND, "5", equipment_category_id=EQUIPMENT)]
    assert _value(rows) == "30"
    assert _value(rows, SCOPE_WITH_BERTH) == "30"


# Active periods are half-open [active_from, active_to) in UTC.
@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (timedelta(microseconds=-1), False),  # just before active_from
        (timedelta(0), True),  # at active_from
        (timedelta(hours=1, microseconds=-1), True),  # just before active_to
        (timedelta(hours=1), False),  # at active_to
    ],
)
def test_active_period_is_half_open(offset: timedelta, expected: bool) -> None:
    row = limit(WIND, "25", active_from=T0, active_to=T0 + timedelta(hours=1))
    assert applies(row, SCOPE, T0 + offset) is expected


def test_an_open_ended_row_applies_from_active_from_on() -> None:
    row = limit(WIND, "25", active_from=T0, active_to=None)
    assert applies(row, SCOPE, T0)
    assert applies(row, SCOPE, T0 + timedelta(days=3650))
    assert not applies(row, SCOPE, T0 - timedelta(microseconds=1))


@pytest.mark.parametrize(
    "moment",
    [T0.replace(tzinfo=None), T0.astimezone(timezone(timedelta(hours=2)))],
    ids=["naive", "utc+2"],
)
def test_the_moment_must_be_utc(moment: object) -> None:
    with pytest.raises(ValueError, match="UTC"):
        applies(limit(WIND, "25"), SCOPE, moment)  # type: ignore[arg-type]
