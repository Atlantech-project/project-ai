"""UTC and port-local time, in one place (AI-014).

Every database datetime is UTC; port local time follows `port_profile.timezone` and
`port_shift` times are local (Architecture §13.1). Zones come only from `zoneinfo` backed by
the `tzdata` package, never from the operating system. A local time that falls in a
daylight-saving gap or overlap raises instead of being guessed.

This module shares its name with the stdlib `time` module. That is safe with absolute imports
(`common.time`); never run a script from inside `common/`.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class UnknownTimeZoneError(ValueError):
    """The name is not a zone in the tzdata database."""


class LocalTimeError(ValueError):
    """A local wall time that has no single UTC instant."""

    def __init__(self, local: datetime, zone: str, reason: str) -> None:
        super().__init__(f"local time {local.isoformat()} in {zone} {reason}")
        self.local = local
        self.zone = zone
        self.reason = reason


class NonExistentLocalTimeError(LocalTimeError):
    """The local time falls in a spring-forward gap."""


class AmbiguousLocalTimeError(LocalTimeError):
    """The local time falls in a fall-back overlap."""


def load_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise UnknownTimeZoneError(f"unknown time zone {name!r}") from exc


def _zone(zone: ZoneInfo | str) -> ZoneInfo:
    return zone if isinstance(zone, ZoneInfo) else load_zone(zone)


def to_local(utc_dt: datetime, zone: ZoneInfo | str) -> datetime:
    """Convert an aware UTC datetime to the zone's local time."""
    offset = utc_dt.utcoffset()
    if offset is None:
        raise ValueError(f"expected an aware UTC datetime, got naive {utc_dt.isoformat()}")
    if offset != timedelta(0):
        raise ValueError(f"expected a UTC datetime, got offset {offset} in {utc_dt.isoformat()}")
    return utc_dt.astimezone(_zone(zone))


def to_utc(local_dt: datetime, zone: ZoneInfo | str) -> datetime:
    """Convert a naive local wall time in `zone` to an aware UTC datetime."""
    if local_dt.tzinfo is not None:
        raise ValueError(f"expected a naive local datetime, got {local_dt.isoformat()}")
    tz = _zone(zone)
    wall = local_dt.replace(fold=0)
    first = wall.replace(tzinfo=tz)
    second = wall.replace(tzinfo=tz, fold=1)
    if first.utcoffset() != second.utcoffset():
        # A gap time does not survive the round trip through UTC; an overlap time does.
        if first.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != wall:
            raise NonExistentLocalTimeError(wall, tz.key, "does not exist (clocks skip it)")
        raise AmbiguousLocalTimeError(wall, tz.key, "is ambiguous (clocks repeat it)")
    return first.astimezone(UTC)


def shift_interval_utc(
    shift_date: date, start_time: time, end_time: time, zone: ZoneInfo | str
) -> tuple[datetime, datetime]:
    """Return the UTC start and end of a `port_shift` on a local date.

    An end time earlier than the start time means the shift ends on the next local day.
    """
    if end_time == start_time:
        raise ValueError(f"shift end {end_time} must differ from start {start_time}")
    end_date = shift_date + timedelta(days=1) if end_time < start_time else shift_date
    return (
        to_utc(datetime.combine(shift_date, start_time), zone),
        to_utc(datetime.combine(end_date, end_time), zone),
    )
