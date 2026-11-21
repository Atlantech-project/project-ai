"""Data-quality checks (AI-025): each check passes and fails at least once."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from common.quality import (
    DATUM_MISMATCH,
    ENDS_EARLY,
    FUTURE_TIMESTAMP,
    GAP,
    MISSING_VALUE,
    NO_DATA,
    OUT_OF_RANGE,
    STALE,
    STARTS_LATE,
    UNTRUSTED,
    QualityResult,
    check_completeness,
    check_coverage,
    check_datum,
    check_forecast_point,
    check_freshness,
    check_range,
    combine,
    max_age_from_hours,
    trusted_rows,
)

NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)
H48 = max_age_from_hours(48)  # CT-18 default of `part1_stored_data_max_age_hours`
HOUR = timedelta(hours=1)


def codes(result: QualityResult) -> list[str]:
    return [i.code for i in result.issues]


# --- ranges ------------------------------------------------------------------------------------


def test_range_passes_inside_and_on_inclusive_bounds() -> None:
    assert check_range("x", Decimal(5), minimum=0, maximum=10).passed
    assert check_range("x", 0, minimum=0, maximum=10).passed
    assert check_range("x", 10, minimum=0, maximum=10).passed
    assert check_range("x", None, minimum=0).passed  # missing is completeness, not range


def test_range_fails_outside_and_on_exclusive_bound() -> None:
    below = check_range("x", Decimal("-0.01"), minimum=0)
    assert codes(below) == [OUT_OF_RANGE]
    assert below.issues[0].field == "x"
    assert codes(check_range("x", 11, maximum=10)) == [OUT_OF_RANGE]
    assert codes(check_range("deg", 360, minimum=0, maximum=360, max_exclusive=True)) == [
        OUT_OF_RANGE
    ]


def test_forecast_point_schema_checks() -> None:
    good = {"wind_direction_deg": Decimal("359.9"), "wind_speed": Decimal(0), "sea_level": None}
    assert check_forecast_point(good).passed

    bad = {
        "wind_direction_deg": Decimal(360),
        "wave_direction_deg": Decimal(-1),
        "wave_height": Decimal("-0.5"),
    }
    result = check_forecast_point(bad)
    assert codes(result) == [OUT_OF_RANGE] * 3
    assert {i.field for i in result.issues} == {
        "wind_direction_deg",
        "wave_direction_deg",
        "wave_height",
    }


# --- completeness -----------------------------------------------------------------------------


def test_completeness_passes_when_all_present() -> None:
    assert check_completeness({"a": 1, "b": "x", "c": 0}, ["a", "b", "c"]).passed


def test_completeness_reports_each_missing_field() -> None:
    result = check_completeness({"a": None, "b": "  ", "c": 1}, ["a", "b", "c", "d"])
    assert codes(result) == [MISSING_VALUE] * 3
    assert [i.field for i in result.issues] == ["a", "b", "d"]


# --- freshness: the 48 h boundary --------------------------------------------------------------


def test_freshness_exactly_48_hours_is_usable() -> None:
    assert check_freshness(NOW - 48 * HOUR, NOW, H48).passed


def test_freshness_just_over_48_hours_is_stale() -> None:
    result = check_freshness(NOW - 48 * HOUR - timedelta(microseconds=1), NOW, H48)
    assert codes(result) == [STALE]


def test_freshness_recent_and_future() -> None:
    assert check_freshness(NOW, NOW, H48).passed
    assert check_freshness(NOW - HOUR, NOW, H48).passed
    assert codes(check_freshness(NOW + timedelta(seconds=1), NOW, H48)) == [FUTURE_TIMESTAMP]


def test_freshness_rejects_naive_times_and_bad_limits() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        check_freshness(datetime(2026, 11, 21), NOW, H48)  # noqa: DTZ001
    with pytest.raises(ValueError, match="positive"):
        check_freshness(NOW, NOW, timedelta(0))
    for hours in (0, 169):
        with pytest.raises(ValueError):
            max_age_from_hours(hours)


# --- horizon coverage --------------------------------------------------------------------------


def test_coverage_passes_when_points_span_the_horizon() -> None:
    times = [NOW + i * HOUR for i in range(7)]
    assert check_coverage(times, NOW, NOW + 6 * HOUR).passed
    assert check_coverage(times, NOW, NOW + 6 * HOUR, max_gap=HOUR).passed


def test_coverage_fails_late_start_early_end_and_no_data() -> None:
    times = [NOW + HOUR, NOW + 2 * HOUR]
    assert codes(check_coverage(times, NOW, NOW + 3 * HOUR)) == [STARTS_LATE, ENDS_EARLY]
    assert codes(check_coverage([], NOW, NOW + HOUR)) == [NO_DATA]


def test_coverage_gap_only_when_the_caller_gives_one() -> None:
    times = [NOW, NOW + HOUR, NOW + 4 * HOUR, NOW + 5 * HOUR]
    assert check_coverage(times, NOW, NOW + 5 * HOUR).passed  # no tolerance given: no gap check
    result = check_coverage(times, NOW, NOW + 5 * HOUR, max_gap=HOUR)
    assert codes(result) == [GAP]


def test_coverage_ignores_gaps_outside_the_horizon() -> None:
    times = [NOW - 10 * HOUR, NOW, NOW + HOUR, NOW + 20 * HOUR]
    assert check_coverage(times, NOW, NOW + HOUR, max_gap=HOUR).passed


def test_coverage_rejects_an_empty_horizon() -> None:
    with pytest.raises(ValueError, match="end after"):
        check_coverage([NOW], NOW, NOW)


# --- datum equality ----------------------------------------------------------------------------


def test_datum_equal_passes() -> None:
    assert check_datum("LAT", "LAT", "LAT").passed


@pytest.mark.parametrize(
    "values", [("LAT", "MSL", "LAT"), ("LAT", None, "LAT"), ("LAT", "", "LAT")]
)
def test_datum_mismatch_or_missing_fails(values: tuple[str | None, str | None, str | None]) -> None:
    assert codes(check_datum(*values)) == [DATUM_MISMATCH]


# --- trusted rows ----------------------------------------------------------------------------


def test_trusted_rows_keep_only_flag_zero() -> None:
    rows: list[dict[str, int | bool | None]] = [
        {"id": 1, "clock_skew_suspect": 0},
        {"id": 2, "clock_skew_suspect": 1},
        {"id": 3, "clock_skew_suspect": False},
        {"id": 4, "clock_skew_suspect": None},
        {"id": 5},
    ]
    split = trusted_rows(rows)
    assert [r["id"] for r in split.kept] == [1, 3]
    assert [r["id"] for r in split.excluded] == [2, 4, 5]
    assert codes(split.result) == [UNTRUSTED]


def test_trusted_rows_all_trusted_and_custom_reader() -> None:
    split = trusted_rows([(1, 0), (2, 0)], flag=lambda row: row[1])
    assert split.kept == ((1, 0), (2, 0))
    assert split.result.passed
    with pytest.raises(TypeError):
        trusted_rows([(1, 0)])


def test_issues_are_structured_for_outcomes_and_logs() -> None:
    result = combine([check_range("x", 11, maximum=10), check_completeness({}, ["y"])])
    assert [i.as_json() for i in result.issues] == [
        {"code": OUT_OF_RANGE, "field": "x", "detail": "x = 11 is above 10"},
        {"code": MISSING_VALUE, "field": "y", "detail": "y is missing"},
    ]
    assert not result.passed
