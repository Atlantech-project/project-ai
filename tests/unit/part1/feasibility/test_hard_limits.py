"""No rule can loosen a hard limit (AI-044 criterion 3; I-6, D12). SYNTHETIC limits only.

A looser row, however specific its scope, never relaxes a stricter row that also applies; a tighter
one always tightens. The table covers every combination of the four A4 scope columns.
"""

from dataclasses import replace
from itertools import product

import pytest

from part1.feasibility import ConstraintType, Reason, assess
from tests.unit.part1.feasibility.builders import (
    BERTH,
    KNOTS_UNITS,
    SCOPE,
    SYN_MIN_VISIBILITY,
    TERMINAL,
    VESSEL_TYPE,
    WIND,
    limit,
    run,
    step,
)

FULL_SCOPE = replace(SCOPE, berth_id=BERTH, imdg_classes=frozenset({"3"}))

# Every subset of the scope columns, each set to a value that matches FULL_SCOPE.
SCOPE_COMBINATIONS = [
    {
        k: v
        for k, v, on in zip(
            ("terminal_id", "berth_id", "vessel_type_id", "imdg_class"),
            (TERMINAL, BERTH, VESSEL_TYPE, "3"),
            flags,
            strict=True,
        )
        if on
    }
    for flags in product((False, True), repeat=4)
]
# A berth row always carries its terminal (schema: fk_sc_berth_terminal).
SCOPE_COMBINATIONS = [
    {**c, "terminal_id": TERMINAL} if "berth_id" in c else c for c in SCOPE_COMBINATIONS
]

# (constraint type, series, hard limit, looser limit, tighter limit, reading)
CASES = [
    (WIND, "wind_speed", "25", "40", "15", "20"),
    (SYN_MIN_VISIBILITY, "visibility", "1", "0.1", "3", "2"),
]


@pytest.mark.parametrize("scope_columns", SCOPE_COMBINATIONS)
@pytest.mark.parametrize(("ctype", "series", "hard", "looser", "_tighter", "_r"), CASES)
def test_a_looser_specific_row_never_loosens(
    ctype: ConstraintType,
    series: str,
    hard: str,
    looser: str,
    _tighter: str,
    _r: str,
    scope_columns: dict[str, object],
) -> None:
    # A reading that breaks the hard limit but would pass the looser one.
    breaking = "30" if ctype is WIND else "0.5"
    rows = [limit(ctype, hard), limit(ctype, looser, **scope_columns)]  # type: ignore[arg-type]
    (result,) = run([step(0, **{series: breaking})], rows, scope=FULL_SCOPE)
    (failure,) = result.failures
    assert failure.reason is Reason.LIMIT_EXCEEDED
    assert str(failure.limit) == hard


@pytest.mark.parametrize("scope_columns", SCOPE_COMBINATIONS)
@pytest.mark.parametrize(("ctype", "series", "hard", "_looser", "tighter", "reading"), CASES)
def test_a_tighter_specific_row_always_tightens(
    ctype: ConstraintType,
    series: str,
    hard: str,
    _looser: str,
    tighter: str,
    reading: str,
    scope_columns: dict[str, object],
) -> None:
    rows = [limit(ctype, hard), limit(ctype, tighter, **scope_columns)]  # type: ignore[arg-type]
    (result,) = run([step(0, **{series: reading})], rows, scope=FULL_SCOPE)
    (failure,) = result.failures
    assert str(failure.limit) == tighter


def test_a4_blocks_whatever_the_hard_flag_says() -> None:
    # is_hard_safety_limit is about retraining (D12), not feasibility: every Part 1 limit is hard
    # (D13).
    soft_wind = replace(WIND, is_hard_safety_limit=False)
    (result,) = assess(
        [step(0, wind_speed="30")], [soft_wind], [limit(soft_wind, "25")], SCOPE, KNOTS_UNITS
    )
    assert [f.constraint_type_code for f in result.failures] == [WIND.code]
