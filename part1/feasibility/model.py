"""A4 data: the rows and series the engine reads, and the results it returns (AI-044).

The input rows mirror `constraint_types`, `safety_constraints` and `environment_forecast_points`
(with the unit columns of `forecast_runs`), so the real feed connects later without changing the
rules (DEC-34). Values stay `Decimal`, as the database returns them; every datetime is
timezone-aware UTC.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class Comparator(StrEnum):
    """`constraint_types.comparator`."""

    MAX_ALLOWED = "MAX_ALLOWED"
    MIN_REQUIRED = "MIN_REQUIRED"


class Category(StrEnum):
    """`constraint_types.category`."""

    ENVIRONMENTAL = "ENVIRONMENTAL"
    UKC = "UKC"
    VESSEL_SAFETY = "VESSEL_SAFETY"


class Series(StrEnum):
    """An A4 input series. The value is the `EnvironmentStep` field that holds it."""

    WIND_SPEED = "wind_speed"
    WIND_GUST = "wind_gust"
    VISIBILITY = "visibility"
    WAVE_HEIGHT = "wave_height"
    CURRENT_SPEED = "current_speed"
    SEA_LEVEL = "sea_level"
    TIDE = "tide_m"
    SURGE = "surge_m"


class Reason(StrEnum):
    """Why a step is blocked for one constraint type."""

    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    MISSING_VALUE = "MISSING_VALUE"  # no reading for a series that has an applicable limit


@dataclass(frozen=True)
class ConstraintType:
    """A `constraint_types` row."""

    id: int
    code: str
    category: Category
    unit: str  # `constraint_types.unit`, a `common.units.Unit` value
    comparator: Comparator
    is_hard_safety_limit: bool = True  # D12 (retraining); A4 treats every limit as hard (D13)


@dataclass(frozen=True)
class SafetyConstraint:
    """A `safety_constraints` row. A NULL scope column means "any"."""

    id: int
    constraint_type_id: int
    value: Decimal  # in the constraint type's unit
    active_from: datetime  # UTC, inclusive
    active_to: datetime | None = None  # UTC, exclusive; None = open-ended
    terminal_id: int | None = None
    berth_id: int | None = None
    vessel_type_id: int | None = None
    imdg_class: str | None = None
    equipment_category_id: int | None = None  # never applied in A4; AI-051 applies these


@dataclass(frozen=True)
class AssessmentScope:
    """Who is being assessed. Part 1 normally has no berth; AI-051 passes one per candidate."""

    terminal_id: int
    vessel_type_id: int
    berth_id: int | None = None
    imdg_classes: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SeriesUnits:
    """The `forecast_runs` unit columns. Wave height, sea level, tide and surge are metres."""

    wind_speed_unit: str  # also the unit of wind_gust
    visibility_unit: str
    current_speed_unit: str


@dataclass(frozen=True)
class EnvironmentStep:
    """One time step: `environment_forecast_points` raw values plus tide and surge (A2, A3)."""

    valid_at: datetime
    wind_speed: Decimal | None = None
    wind_gust: Decimal | None = None
    visibility: Decimal | None = None
    wave_height: Decimal | None = None
    current_speed: Decimal | None = None
    sea_level: Decimal | None = None
    tide_m: Decimal | None = None  # metres on the active datum
    surge_m: Decimal | None = None  # metres; sea level minus tide (A3)


@dataclass(frozen=True)
class Failure:
    """One constraint type failing at one step: its strictest applicable row and the reading."""

    reason: Reason
    constraint_type_id: int
    constraint_type_code: str
    series: Series
    safety_constraint_id: int
    limit: Decimal  # in the constraint type's unit
    value: float | None  # the reading in the constraint type's unit; None for MISSING_VALUE

    def describe(self) -> str:
        if self.reason is Reason.MISSING_VALUE:
            return f"{self.constraint_type_code}: no {self.series.value} reading"
        return (
            f"{self.constraint_type_code}: {self.series.value} {self.value} vs limit {self.limit}"
        )


@dataclass(frozen=True)
class StepResult:
    valid_at: datetime
    failures: tuple[Failure, ...]  # ordered by constraint type code

    @property
    def feasible(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class BlockedPeriod:
    """Adjacent steps blocked for one constraint type and one reason, as `[start, end)`."""

    start: datetime
    end: datetime
    reason: Reason
    constraint_type_id: int
    constraint_type_code: str
    series: Series
