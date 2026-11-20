"""A4 threshold feasibility: each time step against every applicable limit (AI-044).

A pure function: the caller reads the rows and series and passes plain values, so nothing here
touches the database, the clock or the queue. Window formation, gap tolerance (DEC-24) and
persistence are AI-048's.

- Each A4-owned code is checked against the strictest applicable row (`scope.resolve_limit`).
- A reading is converted into the constraint type's unit with `common.units.convert`. A value equal
  to the limit passes. There is no tolerance and no margin (DEC-25): a converted value a hair above
  the limit blocks, because a tolerance would loosen a hard limit (I-6).
- A missing reading for a series with an applicable limit blocks the step with `MISSING_VALUE`.
- Codes owned elsewhere (UKC: A5) are skipped. A code in neither list, with a row that applies at
  some step, raises `ConfigurationError` (CT-08 `CONFIGURATION_ERROR`).
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from common.config import ConfigurationError
from common.units import UnitError, convert, dimension_of
from part1.feasibility.model import (
    AssessmentScope,
    BlockedPeriod,
    Comparator,
    ConstraintType,
    EnvironmentStep,
    Failure,
    Reason,
    SafetyConstraint,
    Series,
    SeriesUnits,
    StepResult,
)
from part1.feasibility.scope import applies, require_utc, resolve_limit
from part1.feasibility.series import DEFAULT_REGISTRY, CodeRegistry, series_unit


@dataclass(frozen=True)
class _Check:
    constraint_type: ConstraintType
    series: Series
    unit: str  # the unit the series arrives in
    rows: tuple[SafetyConstraint, ...]


def assess(
    steps: Iterable[EnvironmentStep],
    constraint_types: Iterable[ConstraintType],
    constraints: Iterable[SafetyConstraint],
    scope: AssessmentScope,
    units: SeriesUnits,
    *,
    registry: CodeRegistry = DEFAULT_REGISTRY,
) -> tuple[StepResult, ...]:
    """Assess every step; the result has one `StepResult` per step, in the same order."""
    ordered = tuple(steps)
    _require_increasing([s.valid_at for s in ordered], "steps")
    checks = _checks(ordered, constraint_types, constraints, scope, units, registry)
    return tuple(
        StepResult(s.valid_at, tuple(f for c in checks if (f := _check(c, s, scope)) is not None))
        for s in ordered
    )


def blocked_periods(
    results: Sequence[StepResult], step_length: timedelta
) -> tuple[BlockedPeriod, ...]:
    """Merge adjacent blocked steps into periods, one per (reason, constraint type).

    Steps are adjacent when their `valid_at` are exactly `step_length` apart. A period ends one
    step after its last step. Periods of different types or reasons may overlap.
    """
    if step_length <= timedelta(0):
        raise ValueError(f"the step length must be positive, got {step_length}")
    _require_increasing([r.valid_at for r in results], "results")
    periods: list[BlockedPeriod] = []
    open_: dict[tuple[Reason, int], tuple[datetime, datetime, Failure]] = {}
    previous: datetime | None = None
    for result in results:
        adjacent = previous is not None and result.valid_at - previous == step_length
        now = {(f.reason, f.constraint_type_id): f for f in result.failures}
        for key in list(open_):
            if key not in now or not adjacent:
                periods.append(_close(open_.pop(key), step_length))
        for key, failure in now.items():
            start = open_[key][0] if key in open_ else result.valid_at
            open_[key] = (start, result.valid_at, failure)
        previous = result.valid_at
    periods.extend(_close(entry, step_length) for entry in open_.values())
    return tuple(sorted(periods, key=lambda p: (p.start, p.reason, p.constraint_type_code)))


def _checks(
    steps: Sequence[EnvironmentStep],
    constraint_types: Iterable[ConstraintType],
    constraints: Iterable[SafetyConstraint],
    scope: AssessmentScope,
    units: SeriesUnits,
    registry: CodeRegistry,
) -> list[_Check]:
    types = {t.id: t for t in constraint_types}
    rows_by_type: dict[int, list[SafetyConstraint]] = defaultdict(list)
    for row in constraints:
        require_utc(row.active_from, f"safety constraint {row.id} active_from")
        if row.active_to is not None:
            require_utc(row.active_to, f"safety constraint {row.id} active_to")
        if row.constraint_type_id not in types:
            raise ConfigurationError(
                f"safety constraint {row.id} has unknown constraint type {row.constraint_type_id}"
            )
        rows_by_type[row.constraint_type_id].append(row)

    checks: list[_Check] = []
    for type_id, rows in rows_by_type.items():
        ctype = types[type_id]
        if not any(applies(row, scope, s.valid_at) for row in rows for s in steps):
            continue
        if ctype.code in registry.elsewhere:
            continue
        series = registry.a4.get(ctype.code)
        if series is None:
            raise ConfigurationError(
                f"constraint type {ctype.code} is neither checked by A4 nor owned by another "
                "component; add it to the A4 code lists",
                keys=(ctype.code,),
            )
        unit = series_unit(series, units)
        _require_same_dimension(ctype, series, unit)
        checks.append(_Check(ctype, series, unit, tuple(rows)))
    return sorted(checks, key=lambda c: c.constraint_type.code)


def _check(check: _Check, step: EnvironmentStep, scope: AssessmentScope) -> Failure | None:
    ctype = check.constraint_type
    row = resolve_limit(check.rows, ctype, scope, step.valid_at)
    if row is None:
        return None
    reading: Decimal | None = getattr(step, check.series.value)
    if reading is None:
        return _failure(Reason.MISSING_VALUE, check, row, None)
    if check.unit == ctype.unit:
        value: Decimal | float = reading
        limit: Decimal | float = row.value
    else:
        value = convert(float(reading), check.unit, ctype.unit)
        limit = float(row.value)
    passes = value <= limit if ctype.comparator is Comparator.MAX_ALLOWED else value >= limit
    return None if passes else _failure(Reason.LIMIT_EXCEEDED, check, row, float(value))


def _failure(reason: Reason, check: _Check, row: SafetyConstraint, value: float | None) -> Failure:
    return Failure(
        reason=reason,
        constraint_type_id=check.constraint_type.id,
        constraint_type_code=check.constraint_type.code,
        series=check.series,
        safety_constraint_id=row.id,
        limit=row.value,
        value=value,
    )


def _require_same_dimension(ctype: ConstraintType, series: Series, unit: str) -> None:
    try:
        limit_dimension = dimension_of(ctype.unit)
        series_dimension = dimension_of(unit)
    except UnitError as error:
        raise ConfigurationError(f"{ctype.code} / {series.value}: {error}") from error
    if limit_dimension is not series_dimension:
        raise ConfigurationError(
            f"{ctype.code} is in {ctype.unit} ({limit_dimension.value}) but {series.value} "
            f"arrives in {unit} ({series_dimension.value})",
            keys=(ctype.code,),
        )


def _require_increasing(moments: Sequence[datetime], what: str) -> None:
    for moment in moments:
        require_utc(moment, f"{what} valid_at")
    for earlier, later in zip(moments, moments[1:], strict=False):
        if later <= earlier:
            raise ValueError(f"{what} must be strictly increasing in time: {earlier} then {later}")


def _close(entry: tuple[datetime, datetime, Failure], step_length: timedelta) -> BlockedPeriod:
    start, last, failure = entry
    return BlockedPeriod(
        start=start,
        end=last + step_length,
        reason=failure.reason,
        constraint_type_id=failure.constraint_type_id,
        constraint_type_code=failure.constraint_type_code,
        series=failure.series,
    )
