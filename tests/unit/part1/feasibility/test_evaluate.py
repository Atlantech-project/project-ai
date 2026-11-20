"""A4 assessment: units, missing values, blocked periods and input checks (AI-044).

SYNTHETIC limits and readings only.
"""

from dataclasses import replace
from datetime import timedelta, timezone

import pytest

from common.config import ConfigurationError
from part1.feasibility import (
    BlockedPeriod,
    ConstraintType,
    EnvironmentStep,
    Reason,
    Series,
    SeriesUnits,
    StepResult,
    assess,
    blocked_periods,
)
from part1.feasibility.series import series_unit
from tests.unit.part1.feasibility.builders import (
    KNOTS_UNITS,
    SCOPE,
    STEP,
    WAVE,
    WIND,
    at,
    codes,
    limit,
    run,
    step,
)

MS_UNITS = replace(KNOTS_UNITS, wind_speed_unit="METRES_PER_SECOND")
KMH_UNITS = replace(KNOTS_UNITS, wind_speed_unit="KM_PER_HOUR")


# --- Units -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("units", "reading", "feasible"),
    [
        (KNOTS_UNITS, "25", True),
        (KNOTS_UNITS, "25.01", False),
        (MS_UNITS, "12.8610", True),  # 24.99978 kn
        (MS_UNITS, "12.8612", False),  # 25.00017 kn: just above, and no tolerance (I-6)
        (KMH_UNITS, "46.29", True),  # 24.99460 kn
        (KMH_UNITS, "46.31", False),  # 25.00540 kn
    ],
)
def test_wind_is_converted_to_the_limit_unit(
    units: SeriesUnits, reading: str, feasible: bool
) -> None:
    (result,) = run([step(0, wind_speed=reading)], [limit(WIND, "25")], units=units)
    assert result.feasible is feasible


def test_a_converted_value_just_above_the_limit_blocks_and_reports_it_in_the_limit_unit() -> None:
    (result,) = run([step(0, wind_speed="12.8612")], [limit(WIND, "25")], units=MS_UNITS)
    (failure,) = result.failures
    assert failure.reason is Reason.LIMIT_EXCEEDED
    assert failure.value is not None
    assert 25 < failure.value < 25.001


@pytest.mark.parametrize(
    ("series", "expected"),
    [
        (Series.WIND_SPEED, "KM_PER_HOUR"),
        (Series.WIND_GUST, "KM_PER_HOUR"),
        (Series.VISIBILITY, "KILOMETRES"),
        (Series.CURRENT_SPEED, "METRES_PER_SECOND"),
        (Series.WAVE_HEIGHT, "METRES"),
        (Series.SEA_LEVEL, "METRES"),
        (Series.TIDE, "METRES"),
        (Series.SURGE, "METRES"),
    ],
)
def test_each_series_arrives_in_its_forecast_run_unit(series: Series, expected: str) -> None:
    units = SeriesUnits(
        wind_speed_unit="KM_PER_HOUR",
        visibility_unit="KILOMETRES",
        current_speed_unit="METRES_PER_SECOND",
    )
    assert series_unit(series, units) == expected


def test_an_exceeded_limit_describes_reading_and_limit() -> None:
    (result,) = run([step(0, wind_speed="30")], [limit(WIND, "25")])
    assert result.failures[0].describe() == "MAX_WIND_KN: wind_speed 30.0 vs limit 25"


def test_a_step_where_no_row_is_active_is_not_checked() -> None:
    row = limit(WIND, "25", active_from=at(0), active_to=at(1))
    results = run([step(0, wind_speed="30"), step(1, wind_speed="30")], [row])
    assert [r.feasible for r in results] == [False, True]


def test_wave_height_is_in_metres() -> None:
    (result,) = run([step(0, wave_height="2.6")], [limit(WAVE, "2.5")])
    assert codes(result) == [WAVE.code]


def test_a_limit_unit_of_the_wrong_dimension_is_a_configuration_error() -> None:
    wind_in_metres = ConstraintType(
        WIND.id, WIND.code, WIND.category, "METRES", WIND.comparator, WIND.is_hard_safety_limit
    )
    with pytest.raises(ConfigurationError, match="MAX_WIND_KN"):
        assess(
            [step(0, wind_speed="1")],
            [wind_in_metres],
            [limit(wind_in_metres, "25")],
            SCOPE,
            KNOTS_UNITS,
        )


def test_an_unknown_series_unit_is_a_configuration_error() -> None:
    units = replace(KNOTS_UNITS, wind_speed_unit="FURLONGS_PER_FORTNIGHT")
    with pytest.raises(ConfigurationError, match="FURLONGS_PER_FORTNIGHT"):
        run([step(0, wind_speed="1")], [limit(WIND, "25")], units=units)


# --- Missing values ----------------------------------------------------------------------------


def test_a_missing_value_with_a_limit_blocks_with_missing_value() -> None:
    (result,) = run([step(0, wind_speed=None)], [limit(WIND, "25")])
    (failure,) = result.failures
    assert failure.reason is Reason.MISSING_VALUE
    assert failure.series is Series.WIND_SPEED
    assert failure.value is None
    assert "wind_speed" in failure.describe()


def test_a_missing_value_without_a_limit_has_no_effect() -> None:
    (result,) = run([step(0, wind_speed="10", wave_height=None)], [limit(WIND, "25")])
    assert result.feasible


def test_missing_and_exceeded_are_reported_together() -> None:
    (result,) = run(
        [step(0, wind_speed="30", wave_height=None)], [limit(WIND, "25"), limit(WAVE, "2")]
    )
    assert [(f.reason, f.constraint_type_code) for f in result.failures] == [
        (Reason.MISSING_VALUE, WAVE.code),
        (Reason.LIMIT_EXCEEDED, WIND.code),
    ]


# --- Blocked periods ---------------------------------------------------------------------------


def _periods(results: tuple[StepResult, ...]) -> list[tuple[int, int, Reason, str]]:
    def index(moment: object) -> int:
        return int((moment - at(0)) / STEP)  # type: ignore[operator]

    return [
        (index(p.start), index(p.end), p.reason, p.constraint_type_code)
        for p in blocked_periods(results, STEP)
    ]


def test_adjacent_blocked_steps_merge_and_end_one_step_after_the_last() -> None:
    winds = ["10", "30", "31", "32", "10"]
    results = run([step(i, wind_speed=w) for i, w in enumerate(winds)], [limit(WIND, "25")])
    assert _periods(results) == [(1, 4, Reason.LIMIT_EXCEEDED, WIND.code)]


def test_a_feasible_step_splits_a_period() -> None:
    winds = ["30", "10", "30"]
    results = run([step(i, wind_speed=w) for i, w in enumerate(winds)], [limit(WIND, "25")])
    assert _periods(results) == [
        (0, 1, Reason.LIMIT_EXCEEDED, WIND.code),
        (2, 3, Reason.LIMIT_EXCEEDED, WIND.code),
    ]


def test_a_time_gap_splits_a_period() -> None:
    results = run([step(0, wind_speed="30"), step(2, wind_speed="30")], [limit(WIND, "25")])
    assert _periods(results) == [
        (0, 1, Reason.LIMIT_EXCEEDED, WIND.code),
        (2, 3, Reason.LIMIT_EXCEEDED, WIND.code),
    ]


def test_periods_of_different_types_overlap() -> None:
    steps = [
        step(0, wind_speed="30", wave_height="1"),
        step(1, wind_speed="30", wave_height="3"),
        step(2, wind_speed="10", wave_height="3"),
    ]
    results = run(steps, [limit(WIND, "25"), limit(WAVE, "2")])
    assert _periods(results) == [
        (0, 2, Reason.LIMIT_EXCEEDED, WIND.code),
        (1, 3, Reason.LIMIT_EXCEEDED, WAVE.code),
    ]


def test_missing_value_periods_stay_separate_from_exceeded_periods() -> None:
    steps = [step(0, wind_speed="30"), step(1, wind_speed=None), step(2, wind_speed="30")]
    results = run(steps, [limit(WIND, "25")])
    assert _periods(results) == [
        (0, 1, Reason.LIMIT_EXCEEDED, WIND.code),
        (1, 2, Reason.MISSING_VALUE, WIND.code),
        (2, 3, Reason.LIMIT_EXCEEDED, WIND.code),
    ]
    period = blocked_periods(results, STEP)[1]
    assert period == BlockedPeriod(
        start=at(1),
        end=at(2),
        reason=Reason.MISSING_VALUE,
        constraint_type_id=WIND.id,
        constraint_type_code=WIND.code,
        series=Series.WIND_SPEED,
    )


def test_no_failures_no_periods() -> None:
    results = run([step(0, wind_speed="1")], [limit(WIND, "25")])
    assert blocked_periods(results, STEP) == ()


@pytest.mark.parametrize("length", [timedelta(0), timedelta(minutes=-30)])
def test_the_step_length_must_be_positive(length: timedelta) -> None:
    with pytest.raises(ValueError, match="step length"):
        blocked_periods((), length)


# --- Input checks ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "steps",
    [
        [step(1), step(0)],
        [step(0), step(0)],
        [EnvironmentStep(valid_at=at(0).replace(tzinfo=None))],
        [EnvironmentStep(valid_at=at(0).astimezone(timezone(timedelta(hours=2))))],
    ],
    ids=["unsorted", "duplicate", "naive", "utc+2"],
)
def test_steps_must_be_utc_and_strictly_increasing(steps: list[EnvironmentStep]) -> None:
    with pytest.raises(ValueError, match=r"UTC|increasing"):
        run(steps, [limit(WIND, "25")])


def test_results_for_periods_must_be_strictly_increasing() -> None:
    results = (StepResult(at(1), ()), StepResult(at(0), ()))
    with pytest.raises(ValueError, match="increasing"):
        blocked_periods(results, STEP)


def test_a_row_of_an_unknown_constraint_type_is_a_configuration_error() -> None:
    orphan = replace(limit(WIND, "25"), constraint_type_id=999)
    with pytest.raises(ConfigurationError, match="999"):
        run([step(0)], [orphan])


def test_a_row_with_a_naive_active_from_is_rejected() -> None:
    row = limit(WIND, "25", active_from=at(0).replace(tzinfo=None))
    with pytest.raises(ValueError, match="UTC"):
        run([step(0, wind_speed="1")], [row])


def test_no_steps_no_results() -> None:
    assert run([], [limit(WIND, "25")]) == ()
