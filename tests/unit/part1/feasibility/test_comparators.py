"""A4 comparators and categories (AI-044 criterion 1: "Table-driven tests for every comparator and
category"). SYNTHETIC limits and readings only."""

import pytest

from common.config import ConfigurationError
from part1.feasibility import Category, Comparator, ConstraintType, Reason
from tests.unit.part1.feasibility.builders import (
    OTHER_TERMINAL,
    SYN_MIN_VISIBILITY,
    SYN_UNOWNED,
    SYN_VESSEL_GUST,
    UKC,
    WIND,
    codes,
    limit,
    run,
    step,
)

# (constraint type, limit, series, reading, feasible)
COMPARATOR_CASES = [
    (WIND, "25", "wind_speed", "24.99", True),  # MAX_ALLOWED below
    (WIND, "25", "wind_speed", "25", True),  # MAX_ALLOWED equal passes
    (WIND, "25", "wind_speed", "25.01", False),  # MAX_ALLOWED above
    (SYN_MIN_VISIBILITY, "1.0", "visibility", "1.01", True),  # MIN_REQUIRED above
    (SYN_MIN_VISIBILITY, "1.0", "visibility", "1.0", True),  # MIN_REQUIRED equal passes
    (SYN_MIN_VISIBILITY, "1.0", "visibility", "0.99", False),  # MIN_REQUIRED below
]


@pytest.mark.parametrize(("ctype", "value", "series", "reading", "feasible"), COMPARATOR_CASES)
def test_comparator_table(
    ctype: ConstraintType, value: str, series: str, reading: str, feasible: bool
) -> None:
    (result,) = run([step(0, **{series: reading})], [limit(ctype, value)])
    assert result.feasible is feasible
    if not feasible:
        (failure,) = result.failures
        assert failure.reason is Reason.LIMIT_EXCEEDED
        assert failure.constraint_type_code == ctype.code
        assert str(failure.limit) == value


def test_the_table_covers_both_comparators() -> None:
    assert {case[0].comparator for case in COMPARATOR_CASES} == set(Comparator)


# (constraint type, series, reading over the 10.0 limit or under it for MIN, evaluated by A4)
CATEGORY_CASES = [
    (WIND, "wind_speed", "30", True),  # ENVIRONMENTAL, A4-owned
    (SYN_VESSEL_GUST, "wind_gust", "30", True),  # VESSEL_SAFETY, A4-owned (test registry)
    (UKC, None, None, False),  # UKC, owned elsewhere (AI-045): skipped
]


@pytest.mark.parametrize(("ctype", "series", "reading", "evaluated"), CATEGORY_CASES)
def test_category_table(
    ctype: ConstraintType, series: str | None, reading: str | None, evaluated: bool
) -> None:
    values = {} if series is None else {series: reading}
    (result,) = run([step(0, **values)], [limit(ctype, "10")])
    assert codes(result) == ([ctype.code] if evaluated else [])


def test_the_table_covers_every_category() -> None:
    assert {case[0].category for case in CATEGORY_CASES} == set(Category)


def test_a_code_in_neither_list_fails_loudly() -> None:
    with pytest.raises(ConfigurationError, match="SYNTHETIC_UNOWNED_KN"):
        run([step(0, wind_speed="1")], [limit(SYN_UNOWNED, "10")])


def test_a_code_in_neither_list_is_ignored_when_none_of_its_rows_applies() -> None:
    (result,) = run([step(0)], [limit(SYN_UNOWNED, "10", terminal_id=OTHER_TERMINAL)])
    assert result.feasible
