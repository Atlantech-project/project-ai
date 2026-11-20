"""SYNTHETIC builders for the A4 tests (AI-044, DEC-34).

Every limit and reading here is made up for the tests. None is a real operating limit, and none is a
proposal for the thresholds register (DEC-30, Open). Codes starting with `SYNTHETIC_` exist only in
these tests; they stand in for constraint types the seed doesn't have yet (AI-009 criterion 1).
"""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from typing import Final

from part1.feasibility import (
    DEFAULT_REGISTRY,
    AssessmentScope,
    Category,
    CodeRegistry,
    Comparator,
    ConstraintType,
    EnvironmentStep,
    SafetyConstraint,
    Series,
    SeriesUnits,
    StepResult,
    assess,
)

T0: Final = datetime(2026, 1, 5, tzinfo=UTC)
STEP: Final = timedelta(minutes=30)

TERMINAL: Final = 1
OTHER_TERMINAL: Final = 2
BERTH: Final = 11
OTHER_BERTH: Final = 12  # also in TERMINAL
VESSEL_TYPE: Final = 21
OTHER_VESSEL_TYPE: Final = 22
EQUIPMENT: Final = 31

KNOTS_UNITS: Final = SeriesUnits(
    wind_speed_unit="KNOTS", visibility_unit="NAUTICAL_MILES", current_speed_unit="KNOTS"
)

# The seeded codes (AI-009 seed spec).
WIND: Final = ConstraintType(
    1, "MAX_WIND_KN", Category.ENVIRONMENTAL, "KNOTS", Comparator.MAX_ALLOWED
)
WAVE: Final = ConstraintType(
    2, "MAX_WAVE_HEIGHT_M", Category.ENVIRONMENTAL, "METRES", Comparator.MAX_ALLOWED
)
UKC: Final = ConstraintType(3, "MIN_UKC_M", Category.UKC, "METRES", Comparator.MIN_REQUIRED)

# Test-only codes.
SYN_MIN_VISIBILITY: Final = ConstraintType(
    4,
    "SYNTHETIC_MIN_VISIBILITY_NM",
    Category.ENVIRONMENTAL,
    "NAUTICAL_MILES",
    Comparator.MIN_REQUIRED,
)
SYN_VESSEL_GUST: Final = ConstraintType(
    5, "SYNTHETIC_VESSEL_MAX_GUST_KN", Category.VESSEL_SAFETY, "KNOTS", Comparator.MAX_ALLOWED
)
SYN_UNOWNED: Final = ConstraintType(
    6, "SYNTHETIC_UNOWNED_KN", Category.ENVIRONMENTAL, "KNOTS", Comparator.MAX_ALLOWED
)

ALL_TYPES: Final = (WIND, WAVE, UKC, SYN_MIN_VISIBILITY, SYN_VESSEL_GUST, SYN_UNOWNED)

TEST_REGISTRY: Final = CodeRegistry(
    a4={
        **DEFAULT_REGISTRY.a4,
        SYN_MIN_VISIBILITY.code: Series.VISIBILITY,
        SYN_VESSEL_GUST.code: Series.WIND_GUST,
    },
    elsewhere=DEFAULT_REGISTRY.elsewhere,
)

SCOPE: Final = AssessmentScope(terminal_id=TERMINAL, vessel_type_id=VESSEL_TYPE)

_ids = count(100)


def limit(
    ctype: ConstraintType,
    value: str,
    *,
    terminal_id: int | None = None,
    berth_id: int | None = None,
    vessel_type_id: int | None = None,
    imdg_class: str | None = None,
    equipment_category_id: int | None = None,
    active_from: datetime = T0 - timedelta(days=1),
    active_to: datetime | None = None,
    row_id: int | None = None,
) -> SafetyConstraint:
    """A synthetic `safety_constraints` row; port-wide and open-ended unless told otherwise."""
    return SafetyConstraint(
        id=next(_ids) if row_id is None else row_id,
        constraint_type_id=ctype.id,
        value=Decimal(value),
        active_from=active_from,
        active_to=active_to,
        terminal_id=terminal_id,
        berth_id=berth_id,
        vessel_type_id=vessel_type_id,
        imdg_class=imdg_class,
        equipment_category_id=equipment_category_id,
    )


def at(i: int) -> datetime:
    return T0 + i * STEP


def make_step(valid_at: datetime, values: Mapping[str, str | None]) -> EnvironmentStep:
    """A step from series values given as decimal strings or None; unknown names raise."""
    unknown = set(values) - {s.value for s in Series}
    if unknown:
        raise KeyError(f"not A4 series: {sorted(unknown)}")

    def get(series: Series) -> Decimal | None:
        text = values.get(series.value)
        return None if text is None else Decimal(text)

    return EnvironmentStep(
        valid_at=valid_at,
        wind_speed=get(Series.WIND_SPEED),
        wind_gust=get(Series.WIND_GUST),
        visibility=get(Series.VISIBILITY),
        wave_height=get(Series.WAVE_HEIGHT),
        current_speed=get(Series.CURRENT_SPEED),
        sea_level=get(Series.SEA_LEVEL),
        tide_m=get(Series.TIDE),
        surge_m=get(Series.SURGE),
    )


def step(i: int, **values: str | None) -> EnvironmentStep:
    """Step `i` with the given series values (decimal strings or None)."""
    return make_step(at(i), values)


def run(
    steps: Iterable[EnvironmentStep],
    constraints: Iterable[SafetyConstraint],
    *,
    scope: AssessmentScope = SCOPE,
    units: SeriesUnits = KNOTS_UNITS,
    registry: CodeRegistry = TEST_REGISTRY,
) -> tuple[StepResult, ...]:
    return assess(steps, ALL_TYPES, constraints, scope, units, registry=registry)


def codes(result: StepResult) -> list[str]:
    return [f.constraint_type_code for f in result.failures]
