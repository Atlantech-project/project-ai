"""B4 delay risk Phase 1 (AI-053, DEC-21): the rule, its boundaries, its NULL path and its gaps."""

import inspect
import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import product
from typing import Any, Final

import pytest

from common.units import IncompatibleUnitsError, UnknownUnitError
from part2.delay_risk import (
    FLAG_CONGESTION_UNAVAILABLE,
    FLAG_FORECAST_PARTIAL,
    FLAG_RULES_UNVALIDATED,
    FLAG_STORM_HISTORY_UNKNOWN,
    FLAG_WEATHER_INCOMPLETE,
    RULES_PATH,
    Congestion,
    DelayRiskResult,
    DelayRiskRules,
    Forecast,
    ForecastPoint,
    Level,
    assess_delay_risk,
    load_rules,
    weather_level,
)

START: Final = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
END: Final = START + timedelta(hours=3)
ZONE: Final = "Africa/Cairo"
MAX_AGE: Final = 48
RULES: Final = load_rules()
GOOD_CONGESTION: Final = Congestion(7, Decimal(7), 28)  # ratio 1.0


def _points(
    *,
    gust: str | None = "10",
    wind: str | None = "10",
    wave: str | None = "0.5",
    count: int = 3,
    first: datetime = START,
) -> tuple[ForecastPoint, ...]:
    return tuple(
        ForecastPoint(
            first + timedelta(hours=hour),
            None if wind is None else Decimal(wind),
            None if gust is None else Decimal(gust),
            None if wave is None else Decimal(wave),
        )
        for hour in range(count)
    )


def _forecast(
    points: tuple[ForecastPoint, ...] | None = None,
    *,
    unit: str = "KNOTS",
    age: timedelta = timedelta(hours=1),
) -> Forecast:
    return Forecast(
        points=_points() if points is None else points,
        wind_speed_unit=unit,
        step_minutes=60,
        age=age,
    )


def _assess(**changes: Any) -> DelayRiskResult:
    arguments: dict[str, Any] = {
        "window_start": START,
        "window_end": END,
        "forecast": _forecast(),
        "max_forecast_age_hours": MAX_AGE,
        "congestion": GOOD_CONGESTION,
        "storm_days": frozenset(),
        "time_zone": ZONE,
    }
    return assess_delay_risk(**(arguments | changes))


def _level(**changes: Any) -> Level | None:
    return _assess(**changes).level


# Weather boundaries (ruling 2)


@pytest.mark.parametrize(
    ("gust", "expected"),
    [
        ("29.9", Level.LOW),
        ("30.0", Level.MEDIUM),
        ("35.0", Level.MEDIUM),
        ("35.1", Level.HIGH),
    ],
)
def test_gust_boundaries(gust: str, expected: Level) -> None:
    assert _level(forecast=_forecast(_points(gust=gust))) == expected


@pytest.mark.parametrize(
    ("wave", "expected"),
    [
        ("1.49", Level.LOW),
        ("1.5", Level.MEDIUM),
        ("2.0", Level.MEDIUM),
        ("2.01", Level.HIGH),
    ],
)
def test_wave_boundaries(wave: str, expected: Level) -> None:
    assert _level(forecast=_forecast(_points(wave=wave))) == expected


@pytest.mark.parametrize(("wind", "expected"), [("20.0", Level.LOW), ("20.1", Level.HIGH)])
def test_wind_has_no_medium_band(wind: str, expected: Level) -> None:
    assert _level(forecast=_forecast(_points(wind=wind))) == expected


def test_the_maximum_over_the_window_decides_not_the_mean() -> None:
    points = (
        *_points(gust="5", count=2),
        ForecastPoint(START + timedelta(hours=2), Decimal(5), Decimal("36"), Decimal(1)),
    )
    assert _level(forecast=_forecast(points)) is Level.HIGH


def test_only_points_inside_the_window_count() -> None:
    before = ForecastPoint(START - timedelta(hours=1), Decimal(40), Decimal(60), Decimal(5))
    at_end = ForecastPoint(END, Decimal(40), Decimal(60), Decimal(5))
    result = _assess(forecast=_forecast((before, *_points(), at_end)))
    assert result.level is Level.LOW


# Wind unit conversion


@pytest.mark.parametrize(
    ("unit", "gust", "expected"),
    [
        ("KM_PER_HOUR", "55.56", Level.MEDIUM),  # exactly 30.000 kn
        ("KM_PER_HOUR", "55.5", Level.LOW),
        ("KM_PER_HOUR", "64.82", Level.MEDIUM),  # exactly 35.000 kn is still MEDIUM
        ("KM_PER_HOUR", "64.83", Level.HIGH),  # 35.005 kn
        ("METRES_PER_SECOND", "15.5", Level.MEDIUM),  # 30.13 kn
        ("METRES_PER_SECOND", "15.4", Level.LOW),  # 29.9 kn
        ("METRES_PER_SECOND", "18.1", Level.HIGH),  # 35.18 kn
    ],
)
def test_gust_is_converted_to_knots(unit: str, gust: str, expected: Level) -> None:
    points = _points(gust=gust, wind="1")
    assert _level(forecast=_forecast(points, unit=unit)) == expected


@pytest.mark.parametrize("unit", ["FURLONGS", "METRES"])
def test_a_wind_unit_that_is_not_a_speed_raises(unit: str) -> None:
    with pytest.raises((UnknownUnitError, IncompatibleUnitsError)):
        _assess(forecast=_forecast(unit=unit))


# Congestion (ruling 1)


@pytest.mark.parametrize(
    ("expected_arrivals", "median", "level"),
    [
        (9, Decimal(7), Level.LOW),  # 1.2857
        (129, Decimal(100), Level.LOW),  # 1.29
        (13, Decimal(10), Level.MEDIUM),  # exactly 1.3
        (159, Decimal(100), Level.MEDIUM),  # 1.59
        (16, Decimal(10), Level.HIGH),  # exactly 1.6
        (11, Decimal(7), Level.MEDIUM),  # 1.571, below 1.6
    ],
)
def test_congestion_ratio_boundaries(expected_arrivals: int, median: Decimal, level: Level) -> None:
    result = _assess(congestion=Congestion(expected_arrivals, median, 28))
    assert result.level is level


@pytest.mark.parametrize(
    "congestion",
    [
        None,
        Congestion(None, Decimal(7), 28),
        Congestion(7, None, 28),
        Congestion(7, Decimal(7), None),
        Congestion(7, Decimal(0), 28),  # median 0: never a division by zero
        Congestion(7, Decimal(7), 27),  # fewer than 28 days of history
    ],
    ids=["none", "no-expected", "no-median", "no-history", "median-zero", "27-days"],
)
def test_unavailable_congestion_gives_weather_alone_with_a_flag(
    congestion: Congestion | None,
) -> None:
    result = _assess(congestion=congestion, forecast=_forecast(_points(gust="31")))
    assert result.level is Level.MEDIUM  # from W, not NULL
    assert FLAG_CONGESTION_UNAVAILABLE in result.flags
    assert "congestion" in result.not_assessed
    assert result.is_lower_bound


def test_exactly_28_days_of_history_is_available() -> None:
    result = _assess(congestion=Congestion(16, Decimal(10), 28))
    assert result.level is Level.HIGH
    assert FLAG_CONGESTION_UNAVAILABLE not in result.flags
    assert not result.is_lower_bound


# Post-storm backlog (ruling 4)


def _congestion_at_ratio_one_and_a_half() -> Congestion:
    return Congestion(15, Decimal(10), 28)  # MEDIUM


def test_a_high_day_one_to_three_port_days_before_raises_congestion_one_level() -> None:
    start_day = date(2026, 11, 10)  # the window starts 10:00 in Cairo
    medium = _congestion_at_ratio_one_and_a_half()
    assert _level(congestion=medium) is Level.MEDIUM
    for days_before in (1, 2, 3):
        result = _assess(
            congestion=medium, storm_days=frozenset({start_day - timedelta(days=days_before)})
        )
        assert result.level is Level.HIGH
        assert "backlog" in result.drivers
    for days_before in (0, 4, -1):
        result = _assess(
            congestion=medium, storm_days=frozenset({start_day - timedelta(days=days_before)})
        )
        assert result.level is Level.MEDIUM
        assert "backlog" not in result.drivers


def test_the_backlog_raises_low_to_medium_and_stops_at_high() -> None:
    day_before = frozenset({date(2026, 11, 9)})
    assert _level(storm_days=day_before) is Level.MEDIUM  # LOW to MEDIUM
    high = Congestion(16, Decimal(10), 28)
    assert _level(congestion=high, storm_days=day_before) is Level.HIGH  # capped


def test_the_backlog_counts_port_days_not_utc_days() -> None:
    """A window starting 22:30 UTC on the 10th is 00:30 on the 11th in Cairo (UTC+2).

    A HIGH day on the 10th is one port day before it. By UTC days the window starts on the 10th,
    so the same storm day would be day 0 and the backlog would not apply.
    """
    late = datetime(2026, 11, 10, 22, 30, tzinfo=UTC)
    window = {"window_start": late, "window_end": late + timedelta(hours=3)}
    forecast = _forecast(_points(first=late))
    with_storm = _assess(**window, forecast=forecast, storm_days=frozenset({date(2026, 11, 10)}))
    without = _assess(**window, forecast=forecast, storm_days=frozenset())
    assert without.level is Level.LOW
    assert (with_storm.level, with_storm.drivers) == (Level.MEDIUM, ("congestion", "backlog"))
    same_port_day = _assess(**window, forecast=forecast, storm_days=frozenset({date(2026, 11, 11)}))
    assert same_port_day.level is Level.LOW


def test_empty_history_means_none_and_missing_history_is_unknown() -> None:
    known = _assess(storm_days=frozenset())
    unknown = _assess(storm_days=None)
    assert FLAG_STORM_HISTORY_UNKNOWN not in known.flags
    assert FLAG_STORM_HISTORY_UNKNOWN in unknown.flags
    assert "storm_history" in unknown.not_assessed
    assert unknown.level is known.level  # unknown only ever lowers; here nothing was lost
    assert unknown.is_lower_bound
    assert not known.is_lower_bound


def test_weather_level_is_public_so_the_caller_can_find_high_days() -> None:
    level, missing = weather_level(_points(gust="40"), "KNOTS", RULES)
    assert (level, missing) == (Level.HIGH, ())


# max(W, C) and drivers


@pytest.mark.parametrize(
    ("gust", "ratio_count", "level", "drivers"),
    [
        ("10", 7, Level.LOW, ("weather", "congestion")),
        ("31", 7, Level.MEDIUM, ("weather",)),
        ("10", 15, Level.MEDIUM, ("congestion",)),
        ("31", 15, Level.MEDIUM, ("weather", "congestion")),
        ("40", 7, Level.HIGH, ("weather",)),
        ("10", 17, Level.HIGH, ("congestion",)),
        ("40", 17, Level.HIGH, ("weather", "congestion")),
    ],
)
def test_the_result_is_the_higher_of_weather_and_congestion(
    gust: str, ratio_count: int, level: Level, drivers: tuple[str, ...]
) -> None:
    result = _assess(
        forecast=_forecast(_points(gust=gust)), congestion=Congestion(ratio_count, Decimal(10), 28)
    )
    # ratio_count/10: 7 gives 0.7 (LOW), 15 gives 1.5 (MEDIUM), 17 gives 1.7 (HIGH)
    assert (result.level, result.drivers) == (level, drivers)


def test_a_high_found_despite_gaps_is_still_high() -> None:
    result = _assess(forecast=_forecast(_points(gust="40")), congestion=None, storm_days=None)
    assert result.level is Level.HIGH
    assert result.code == Decimal("0.900")


# NULL path (the only NULL cases)


def test_no_forecast_is_null() -> None:
    for forecast in (None, _forecast(())):
        result = _assess(forecast=forecast)
        assert (result.code, result.level, result.reason) == (None, None, "forecast_missing")
        assert result.flags == ()


def test_a_stale_forecast_is_null_at_48_hours_and_one_second() -> None:
    assert _assess(forecast=_forecast(age=timedelta(hours=48))).code is not None
    stale = _assess(forecast=_forecast(age=timedelta(hours=48, seconds=1)))
    assert (stale.code, stale.reason) == (None, "forecast_stale")


def test_the_allowed_age_is_the_one_the_caller_passes() -> None:
    assert (
        _assess(forecast=_forecast(age=timedelta(hours=30)), max_forecast_age_hours=24).code is None
    )


def test_no_point_in_the_window_is_null() -> None:
    far = _points(first=START + timedelta(days=2))
    result = _assess(forecast=_forecast(far))
    assert (result.code, result.reason) == (None, "no_forecast_point_in_window")


def test_points_with_no_value_at_all_are_null() -> None:
    empty = _points(gust=None, wind=None, wave=None)
    assert _assess(forecast=_forecast(empty)).code is None


def test_congestion_and_history_gaps_are_never_null() -> None:
    result = _assess(congestion=None, storm_days=None)
    assert result.code == Decimal("0.100")
    assert result.reason is None


# Partial coverage and incomplete weather (ruling 5)


def test_a_forecast_covering_the_whole_window_is_not_partial() -> None:
    result = _assess()
    assert FLAG_FORECAST_PARTIAL not in result.flags
    assert (result.coverage.points_used, result.coverage.points_expected) == (3, 3)  # type: ignore[union-attr]


def test_a_forecast_covering_part_of_the_window_is_computed_and_flagged() -> None:
    result = _assess(forecast=_forecast(_points(gust="31", count=1)))
    assert result.level is Level.MEDIUM
    assert FLAG_FORECAST_PARTIAL in result.flags
    assert (result.coverage.points_used, result.coverage.points_expected) == (1, 3)  # type: ignore[union-attr]


def test_a_window_off_the_forecast_grid_is_not_flagged_by_mistake() -> None:
    start = START + timedelta(minutes=30)
    result = _assess(
        window_start=start,
        window_end=start + timedelta(hours=2, minutes=30),
        forecast=_forecast(_points(count=4)),
    )
    assert FLAG_FORECAST_PARTIAL not in result.flags


def test_a_metric_with_no_value_is_not_assessed_and_flagged() -> None:
    result = _assess(forecast=_forecast(_points(wave=None, gust="31")))
    assert result.level is Level.MEDIUM
    assert FLAG_WEATHER_INCOMPLETE in result.flags
    assert "wave_height" in result.not_assessed
    assert result.is_lower_bound


# Codes, flags and the rules file


def test_codes_are_the_three_fixed_decimals() -> None:
    codes = {
        Level.LOW: _assess().code,
        Level.MEDIUM: _assess(forecast=_forecast(_points(gust="31"))).code,
        Level.HIGH: _assess(forecast=_forecast(_points(gust="40"))).code,
    }
    assert codes == {
        Level.LOW: Decimal("0.100"),
        Level.MEDIUM: Decimal("0.500"),
        Level.HIGH: Decimal("0.900"),
    }
    assert all(isinstance(code, Decimal) for code in codes.values())


def test_every_assessed_result_is_flagged_unvalidated_and_carries_the_rule_version() -> None:
    result = _assess()
    assert result.flags[0] == FLAG_RULES_UNVALIDATED
    assert result.rule_version == "DEC-21-phase1"


def test_no_result_is_a_number_off_the_three_codes() -> None:
    allowed = {Decimal("0.100"), Decimal("0.500"), Decimal("0.900"), None}
    histories: tuple[frozenset[date] | None, ...] = (
        frozenset(),
        None,
        frozenset({date(2026, 11, 9)}),
    )
    for gust, wave, count, storm in product(
        ("5", "30", "35", "36"), ("0.5", "1.5", "2.5"), (0, 7, 13, 16, 40), histories
    ):
        result = _assess(
            forecast=_forecast(_points(gust=gust, wave=wave)),
            congestion=Congestion(count, Decimal(10), 28),
            storm_days=storm,
        )
        assert result.code in allowed


def test_the_result_does_not_depend_on_safety_limits() -> None:
    """Headroom is not applied (DEC-30 TR-10 is not filled): there is no input to change it."""
    names = set(inspect.signature(assess_delay_risk).parameters)
    assert not {name for name in names if "safety" in name or "headroom" in name}
    with pytest.raises(TypeError):
        _assess(safety_constraints=[object()])


def test_the_window_must_end_after_it_starts() -> None:
    with pytest.raises(ValueError, match="end after"):
        _assess(window_end=START)


def test_the_rules_file_gives_every_value_a_source_and_an_interim_note() -> None:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    for name in ("weather", "congestion", "backlog", "level_codes"):
        assert data[name]["source"]
        assert isinstance(data[name]["interim"], bool)
    assert data["status"] == "PROPOSED"  # DEC-21 open item 2
    assert RULES.status == "PROPOSED"


def test_an_unknown_status_or_a_non_string_decimal_is_refused() -> None:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    from part2.delay_risk import _parse_rules  # noqa: PLC0415

    with pytest.raises(ValueError, match="unknown status"):
        _parse_rules({**data, "status": "DRAFT"})
    broken = {**data, "weather": {**data["weather"], "gust_high_above_kn": 35}}
    with pytest.raises(TypeError, match="string"):
        _parse_rules(broken)


def test_the_module_holds_no_thresholds() -> None:
    source = RULES_PATH.with_name("delay_risk.py").read_text(encoding="utf-8")
    for value in ("1.3", "1.6", "0.100", "0.500", "0.900", "35", "2.0", "1.5"):
        assert value not in source, value


def test_a_result_is_frozen() -> None:
    result = _assess()
    with pytest.raises(AttributeError):
        result.code = Decimal(0)  # type: ignore[misc]


# The rules_unvalidated flag follows the rules file (as in AI-054)


def test_rules_unvalidated_is_derived_from_the_rules_status() -> None:
    approved = replace(RULES, status="APPROVED")
    assert FLAG_RULES_UNVALIDATED in _assess().flags
    assert FLAG_RULES_UNVALIDATED not in _assess(rules=approved).flags


# The inputs are returned for DEC-21 open item 6


def _all_inputs(rules: DelayRiskRules | None = None) -> DelayRiskResult:
    points = (
        ForecastPoint(START, Decimal(12), Decimal(31), Decimal("1.6")),
        ForecastPoint(START + timedelta(hours=1), Decimal(14), Decimal(33), Decimal("1.2")),
        ForecastPoint(START + timedelta(hours=2), Decimal(9), Decimal(28), Decimal("0.4")),
    )
    return _assess(
        forecast=_forecast(points),
        congestion=Congestion(15, Decimal(10), 28),
        storm_days=frozenset({date(2026, 11, 9)}),
        rules=rules,
    )


def test_the_result_returns_the_inputs_it_used() -> None:
    result = _all_inputs()
    inputs = result.inputs
    assert inputs is not None
    assert (
        inputs.weather.wind_gust_kn,
        inputs.weather.wind_speed_kn,
        inputs.weather.wave_height_m,
    ) == (Decimal(33), Decimal(14), Decimal("1.6"))
    assert inputs.weather_level is Level.MEDIUM
    assert inputs.congestion_ratio == Decimal("1.5")
    assert inputs.congestion_level is Level.MEDIUM  # before the post-storm raise
    assert inputs.post_storm_window is True
    assert inputs.backlog_raised is True
    assert result.level is Level.HIGH  # MEDIUM raised one level by the backlog
    assert result.coverage is not None
    assert (result.coverage.points_used, result.coverage.points_expected) == (3, 3)


def test_unknown_and_unavailable_inputs_are_returned_as_none_not_as_zero() -> None:
    result = _assess(congestion=None, storm_days=None)
    assert result.inputs is not None
    assert result.inputs.congestion_ratio is None
    assert result.inputs.congestion_level is None
    assert result.inputs.post_storm_window is None  # unknown, not False
    assert result.inputs.backlog_raised is False
    assert _assess(storm_days=frozenset()).inputs.post_storm_window is False  # type: ignore[union-attr]


def test_a_null_result_has_no_inputs() -> None:
    assert _assess(forecast=None).inputs is None
