import itertools
import math
from fractions import Fraction

import pytest

from common.units import (
    Dimension,
    IncompatibleUnitsError,
    Unit,
    UnknownUnitError,
    convert,
    dimension_of,
    parse_unit,
)

# Independent exact definitions: speeds in metres per hour, distances in metres.
SPEED_M_PER_H = {
    Unit.KNOTS: Fraction(1852),
    Unit.METRES_PER_SECOND: Fraction(3600),
    Unit.KM_PER_HOUR: Fraction(1000),
}
DISTANCE_M = {
    Unit.NAUTICAL_MILES: Fraction(1852),
    Unit.KILOMETRES: Fraction(1000),
    Unit.METRES: Fraction(1),
}
SINGLE_UNIT = [Unit.PERCENT, Unit.DEGREES, Unit.MINUTES, Unit.TONNES]

SPEED_PAIRS = list(itertools.product(SPEED_M_PER_H, repeat=2))
DISTANCE_PAIRS = list(itertools.product(DISTANCE_M, repeat=2))
SAME_DIMENSION_PAIRS = SPEED_PAIRS + DISTANCE_PAIRS
CROSS_DIMENSION_PAIRS = [
    (a, b) for a, b in itertools.product(Unit, repeat=2) if dimension_of(a) != dimension_of(b)
]


def _exact(value: Fraction, source: Unit, target: Unit) -> Fraction:
    table = SPEED_M_PER_H if source in SPEED_M_PER_H else DISTANCE_M
    return value * table[source] / table[target]


def test_unit_values_match_the_db_enums() -> None:
    # SpeedUnit, VisibilityUnit and ConstraintUnit (ClassDiagramContext.md).
    assert {u.value for u in Unit} == {
        "KNOTS",
        "METRES_PER_SECOND",
        "KM_PER_HOUR",
        "NAUTICAL_MILES",
        "KILOMETRES",
        "METRES",
        "PERCENT",
        "DEGREES",
        "MINUTES",
        "TONNES",
    }


def test_dimensions() -> None:
    assert {u for u in Unit if dimension_of(u) is Dimension.SPEED} == set(SPEED_M_PER_H)
    assert {u for u in Unit if dimension_of(u) is Dimension.DISTANCE} == set(DISTANCE_M)


@pytest.mark.parametrize(("source", "target"), SAME_DIMENSION_PAIRS)
@pytest.mark.parametrize("value", ["0", "1", "12.5", "-3.25"])
def test_conversion_matches_exact_definition(source: Unit, target: Unit, value: str) -> None:
    expected = _exact(Fraction(value), source, target)
    assert math.isclose(convert(float(value), source, target), float(expected), rel_tol=1e-12)


@pytest.mark.parametrize(("source", "target"), SAME_DIMENSION_PAIRS)
def test_round_trip_within_float_tolerance(source: Unit, target: Unit) -> None:
    value = 17.3
    assert math.isclose(
        convert(convert(value, source, target), target, source), value, rel_tol=1e-12
    )


@pytest.mark.parametrize(
    ("value", "source", "target", "expected"),
    [
        (1.0, Unit.KNOTS, Unit.METRES_PER_SECOND, 0.514444444444),
        (1.0, Unit.KNOTS, Unit.KM_PER_HOUR, 1.852),
        (1.0, Unit.NAUTICAL_MILES, Unit.METRES, 1852.0),
        (1.0, Unit.NAUTICAL_MILES, Unit.KILOMETRES, 1.852),
        (36.0, Unit.KM_PER_HOUR, Unit.METRES_PER_SECOND, 10.0),
    ],
)
def test_known_values(value: float, source: Unit, target: Unit, expected: float) -> None:
    assert math.isclose(convert(value, source, target), expected, rel_tol=1e-9)


@pytest.mark.parametrize("unit", list(Unit))
def test_same_unit_returns_value_unchanged(unit: Unit) -> None:
    assert convert(7.125, unit, unit) == 7.125


@pytest.mark.parametrize(("source", "target"), CROSS_DIMENSION_PAIRS)
def test_cross_dimension_raises(source: Unit, target: Unit) -> None:
    with pytest.raises(IncompatibleUnitsError, match=f"{source.value}.*{target.value}"):
        convert(1.0, source, target)


def test_single_unit_dimensions_convert_only_to_themselves() -> None:
    for unit in SINGLE_UNIT:
        assert [u for u in Unit if dimension_of(u) is dimension_of(unit)] == [unit]


def test_parse_unit_accepts_db_values() -> None:
    assert parse_unit("KNOTS") is Unit.KNOTS
    assert parse_unit("METRES") is Unit.METRES


@pytest.mark.parametrize("text", ["knots", "KT", "KNOT", " KNOTS", "", "MILES"])
def test_parse_unit_rejects_unknown(text: str) -> None:
    with pytest.raises(UnknownUnitError):
        parse_unit(text)


def test_dimension_of_accepts_db_strings_and_rejects_unknown() -> None:
    assert dimension_of("KNOTS") is Dimension.SPEED
    with pytest.raises(UnknownUnitError):
        dimension_of("knots")


def test_convert_accepts_db_strings_and_rejects_unknown() -> None:
    assert math.isclose(convert(1.0, "KNOTS", "KM_PER_HOUR"), 1.852, rel_tol=1e-12)
    with pytest.raises(UnknownUnitError):
        convert(1.0, "kn", Unit.METRES_PER_SECOND)
    with pytest.raises(UnknownUnitError):
        convert(1.0, Unit.KNOTS, "mph")
