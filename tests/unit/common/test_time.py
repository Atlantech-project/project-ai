from datetime import UTC, date, datetime, time, timedelta, timezone

import pytest

from common.time import (
    AmbiguousLocalTimeError,
    LocalTimeError,
    NonExistentLocalTimeError,
    UnknownTimeZoneError,
    load_zone,
    shift_interval_utc,
    to_local,
    to_utc,
)

# Reference port (Damietta) zone. Transitions read from tzdata 2026.6: clocks go 00:00 -> 01:00
# on 2026-04-24 (UTC+2 -> UTC+3) and 24:00 -> 23:00 on 2026-10-29 (UTC+3 -> UTC+2).
CAIRO = "Africa/Cairo"
GAP_LOCAL = datetime(2026, 4, 24, 0, 30)
OVERLAP_LOCAL = datetime(2026, 10, 29, 23, 30)


def test_load_zone() -> None:
    assert load_zone(CAIRO).key == CAIRO


@pytest.mark.parametrize("name", ["Africa/Atlantis", "", "cairo", "../etc/passwd"])
def test_unknown_zone_raises(name: str) -> None:
    with pytest.raises(UnknownTimeZoneError):
        load_zone(name)


def test_normal_day_control() -> None:
    # Winter, UTC+2.
    assert to_utc(datetime(2026, 1, 15, 9, 0), CAIRO) == datetime(2026, 1, 15, 7, 0, tzinfo=UTC)
    # Summer, UTC+3.
    assert to_utc(datetime(2026, 7, 15, 9, 0), CAIRO) == datetime(2026, 7, 15, 6, 0, tzinfo=UTC)


def test_to_local() -> None:
    local = to_local(datetime(2026, 1, 15, 7, 0, tzinfo=UTC), CAIRO)
    assert local.replace(tzinfo=None) == datetime(2026, 1, 15, 9, 0)
    assert local.utcoffset() == timedelta(hours=2)


def test_to_local_accepts_zone_object() -> None:
    zone = load_zone(CAIRO)
    assert to_local(datetime(2026, 7, 15, 6, 0, tzinfo=UTC), zone).hour == 9


def test_utc_round_trip_across_a_year() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    while instant < datetime(2027, 1, 1, tzinfo=UTC):
        local = to_local(instant, CAIRO)
        if local.fold == 0 and to_local(instant + timedelta(hours=1), CAIRO).fold == 0:
            assert to_utc(local.replace(tzinfo=None), CAIRO) == instant
        instant += timedelta(minutes=30)


def test_to_local_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        to_local(datetime(2026, 1, 15, 7, 0), CAIRO)


def test_to_local_rejects_non_utc_aware() -> None:
    with pytest.raises(ValueError, match="UTC"):
        to_local(datetime(2026, 1, 15, 7, 0, tzinfo=timezone(timedelta(hours=2))), CAIRO)


def test_to_utc_rejects_aware() -> None:
    with pytest.raises(ValueError, match="naive"):
        to_utc(datetime(2026, 1, 15, 9, 0, tzinfo=UTC), CAIRO)


def test_gap_raises_non_existent() -> None:
    with pytest.raises(NonExistentLocalTimeError) as info:
        to_utc(GAP_LOCAL, CAIRO)
    assert isinstance(info.value, LocalTimeError)
    message = str(info.value)
    assert "2026-04-24T00:30:00" in message
    assert CAIRO in message
    assert "does not exist" in message


def test_overlap_raises_ambiguous() -> None:
    with pytest.raises(AmbiguousLocalTimeError) as info:
        to_utc(OVERLAP_LOCAL, CAIRO)
    assert isinstance(info.value, LocalTimeError)
    message = str(info.value)
    assert "2026-10-29T23:30:00" in message
    assert CAIRO in message
    assert "ambiguous" in message


def test_overlap_raises_even_with_fold_set() -> None:
    with pytest.raises(AmbiguousLocalTimeError):
        to_utc(OVERLAP_LOCAL.replace(fold=1), CAIRO)


def test_edges_of_transitions_resolve() -> None:
    assert to_utc(datetime(2026, 4, 23, 23, 59), CAIRO) == datetime(2026, 4, 23, 21, 59, tzinfo=UTC)
    assert to_utc(datetime(2026, 4, 24, 1, 0), CAIRO) == datetime(2026, 4, 23, 22, 0, tzinfo=UTC)
    assert to_utc(datetime(2026, 10, 29, 22, 59), CAIRO) == datetime(
        2026, 10, 29, 19, 59, tzinfo=UTC
    )
    assert to_utc(datetime(2026, 10, 30, 0, 0), CAIRO) == datetime(2026, 10, 29, 22, 0, tzinfo=UTC)


def test_day_shift() -> None:
    assert shift_interval_utc(date(2026, 1, 15), time(6, 0), time(14, 0), CAIRO) == (
        datetime(2026, 1, 15, 4, 0, tzinfo=UTC),
        datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    )


def test_shift_spanning_midnight_ends_next_local_day() -> None:
    start, end = shift_interval_utc(date(2026, 1, 15), time(22, 0), time(6, 0), CAIRO)
    assert start == datetime(2026, 1, 15, 20, 0, tzinfo=UTC)
    assert end == datetime(2026, 1, 16, 4, 0, tzinfo=UTC)
    assert end - start == timedelta(hours=8)


def test_shift_spanning_midnight_on_spring_forward_night_is_one_hour_shorter() -> None:
    start, end = shift_interval_utc(date(2026, 4, 23), time(22, 0), time(6, 0), CAIRO)
    assert start == datetime(2026, 4, 23, 20, 0, tzinfo=UTC)
    assert end == datetime(2026, 4, 24, 3, 0, tzinfo=UTC)
    assert end - start == timedelta(hours=7)


def test_shift_spanning_midnight_on_fall_back_night_is_one_hour_longer() -> None:
    start, end = shift_interval_utc(date(2026, 10, 29), time(22, 0), time(6, 0), CAIRO)
    assert start == datetime(2026, 10, 29, 19, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 30, 4, 0, tzinfo=UTC)
    assert end - start == timedelta(hours=9)


def test_shift_boundary_in_overlap_raises() -> None:
    with pytest.raises(AmbiguousLocalTimeError):
        shift_interval_utc(date(2026, 10, 29), time(23, 30), time(6, 0), CAIRO)


def test_shift_boundary_in_gap_raises() -> None:
    with pytest.raises(NonExistentLocalTimeError):
        shift_interval_utc(date(2026, 4, 23), time(18, 0), time(0, 30), CAIRO)


def test_shift_with_equal_start_and_end_raises() -> None:
    with pytest.raises(ValueError, match="end"):
        shift_interval_utc(date(2026, 1, 15), time(6, 0), time(6, 0), CAIRO)
