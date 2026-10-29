"""Unit conversions shared by every worker (AI-014).

The units are the values of the PortSync enums `SpeedUnit`, `VisibilityUnit` and
`ConstraintUnit`. Conversions use exact definitions (1 nautical mile = 1852 m, 1 knot =
1852 m/h) and work in `float`; callers holding DB `decimal` values convert at the boundary.
An unknown unit or a conversion across dimensions raises: nothing is guessed.
"""

from enum import StrEnum


class Unit(StrEnum):
    KNOTS = "KNOTS"
    METRES_PER_SECOND = "METRES_PER_SECOND"
    KM_PER_HOUR = "KM_PER_HOUR"
    NAUTICAL_MILES = "NAUTICAL_MILES"
    KILOMETRES = "KILOMETRES"
    METRES = "METRES"
    PERCENT = "PERCENT"
    DEGREES = "DEGREES"
    MINUTES = "MINUTES"
    TONNES = "TONNES"


class Dimension(StrEnum):
    SPEED = "SPEED"
    DISTANCE = "DISTANCE"
    RATIO = "RATIO"
    ANGLE = "ANGLE"
    DURATION = "DURATION"
    MASS = "MASS"


class UnitError(ValueError):
    """Base class for unit errors."""


class UnknownUnitError(UnitError):
    """The text is not a PortSync unit value."""


class IncompatibleUnitsError(UnitError):
    """The two units measure different dimensions."""


# Dimension and factor to the dimension's base unit (speed: metres per second; distance: metres).
_UNITS: dict[Unit, tuple[Dimension, float]] = {
    Unit.KNOTS: (Dimension.SPEED, 1852 / 3600),
    Unit.METRES_PER_SECOND: (Dimension.SPEED, 1.0),
    Unit.KM_PER_HOUR: (Dimension.SPEED, 1000 / 3600),
    Unit.NAUTICAL_MILES: (Dimension.DISTANCE, 1852.0),
    Unit.KILOMETRES: (Dimension.DISTANCE, 1000.0),
    Unit.METRES: (Dimension.DISTANCE, 1.0),
    Unit.PERCENT: (Dimension.RATIO, 1.0),
    Unit.DEGREES: (Dimension.ANGLE, 1.0),
    Unit.MINUTES: (Dimension.DURATION, 1.0),
    Unit.TONNES: (Dimension.MASS, 1.0),
}


def parse_unit(text: str) -> Unit:
    """Return the unit for an exact PortSync enum value."""
    try:
        return Unit(text)
    except ValueError:
        raise UnknownUnitError(f"unknown unit {text!r}") from None


def dimension_of(unit: Unit | str) -> Dimension:
    return _UNITS[parse_unit(unit)][0]


def convert(value: float, from_unit: Unit | str, to_unit: Unit | str) -> float:
    """Convert `value` between two units of the same dimension."""
    source = parse_unit(from_unit)
    target = parse_unit(to_unit)
    if source is target:
        return value
    source_dimension, source_factor = _UNITS[source]
    target_dimension, target_factor = _UNITS[target]
    if source_dimension is not target_dimension:
        raise IncompatibleUnitsError(
            f"cannot convert {source.value} ({source_dimension.value}) "
            f"to {target.value} ({target_dimension.value})"
        )
    return value * source_factor / target_factor
