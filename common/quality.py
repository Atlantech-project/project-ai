"""Data-quality checks shared by Parts 1 to 3 (AI-025).

Each check returns a `QualityResult` with structured reasons (`QualityIssue`) that can go into a
run outcome or a log line as they are; none raises on bad data. A check never fills a threshold
the caller did not give: limits come from the schema, from CT-18 `port_settings` or from the
caller (for example the gap tolerance, which is AI-048's, DEC-24).
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

from common.datum import DatumError, check_datum_consistency

# Reason codes.
OUT_OF_RANGE: Final = "OUT_OF_RANGE"
MISSING_VALUE: Final = "MISSING_VALUE"
STALE: Final = "STALE"
FUTURE_TIMESTAMP: Final = "FUTURE_TIMESTAMP"
NO_DATA: Final = "NO_DATA"
STARTS_LATE: Final = "STARTS_LATE"
ENDS_EARLY: Final = "ENDS_EARLY"
GAP: Final = "GAP"
DATUM_MISMATCH: Final = "DATUM_MISMATCH"
UNTRUSTED: Final = "UNTRUSTED"

# `chk_efp_direction` and `chk_efp_values` (environment_forecast_points).
EFP_DIRECTION_FIELDS: Final = ("wind_direction_deg", "wave_direction_deg")
EFP_NON_NEGATIVE_FIELDS: Final = (
    "wind_speed",
    "wind_gust",
    "visibility",
    "wave_height",
    "wave_period",
    "current_speed",
)
# Architecture I-13: Part 3 uses trusted rows only.
TRUST_FLAG: Final = "clock_skew_suspect"


@dataclass(frozen=True)
class QualityIssue:
    code: str
    field: str | None
    detail: str

    def as_json(self) -> dict[str, str | None]:
        return {"code": self.code, "field": self.field, "detail": self.detail}


@dataclass(frozen=True)
class QualityResult:
    issues: tuple[QualityIssue, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.issues

    def __add__(self, other: QualityResult) -> QualityResult:
        return QualityResult(self.issues + other.issues)


OK: Final = QualityResult()


def _fail(code: str, field: str | None, detail: str) -> QualityResult:
    return QualityResult((QualityIssue(code, field, detail),))


def _require_aware(value: datetime, name: str) -> None:
    if value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware: {value.isoformat()}")


# --- ranges and completeness ------------------------------------------------------------------


def check_range(
    field: str,
    value: Decimal | int | None,
    *,
    minimum: Decimal | int | None = None,
    maximum: Decimal | int | None = None,
    max_exclusive: bool = False,
) -> QualityResult:
    """`minimum <= value <= maximum` (or `< maximum`). A missing value is not a range failure:
    completeness is `check_completeness`'s job."""
    if value is None:
        return OK
    if minimum is not None and value < minimum:
        return _fail(OUT_OF_RANGE, field, f"{field} = {value} is below {minimum}")
    if maximum is not None and (value >= maximum if max_exclusive else value > maximum):
        bound = f"{maximum} (exclusive)" if max_exclusive else f"{maximum}"
        return _fail(OUT_OF_RANGE, field, f"{field} = {value} is above {bound}")
    return OK


def check_completeness(row: Mapping[str, object], required: Iterable[str]) -> QualityResult:
    """Every required field is present and not None (an empty or blank string counts as missing)."""
    issues = []
    for field in required:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(QualityIssue(MISSING_VALUE, field, f"{field} is missing"))
    return QualityResult(tuple(issues))


def check_forecast_point(point: Mapping[str, Decimal | None]) -> QualityResult:
    """The schema checks of one `environment_forecast_points` row, before it is written."""
    result = OK
    for field in EFP_DIRECTION_FIELDS:
        result += check_range(field, point.get(field), minimum=0, maximum=360, max_exclusive=True)
    for field in EFP_NON_NEGATIVE_FIELDS:
        result += check_range(field, point.get(field), minimum=0)
    return result


# --- freshness and coverage ---------------------------------------------------------------------


def check_freshness(measured_at: datetime, now: datetime, max_age: timedelta) -> QualityResult:
    """Usable when measured within `max_age` of `now`, the boundary included (UML 2.10: "within
    48 h", CT-18 `part1_stored_data_max_age_hours`). A time after `now` is not usable either."""
    _require_aware(measured_at, "measured_at")
    _require_aware(now, "now")
    if max_age <= timedelta(0):
        raise ValueError(f"max_age must be positive: {max_age}")
    if measured_at > now:
        detail = f"measured at {measured_at.isoformat()}, after now ({now.isoformat()})"
        return _fail(FUTURE_TIMESTAMP, None, detail)
    age = now - measured_at
    if age > max_age:
        return _fail(STALE, None, f"measured {age} ago; the limit is {max_age}")
    return OK


def max_age_from_hours(hours: int) -> timedelta:
    """`part1_stored_data_max_age_hours` as a `timedelta` (CT-18: INT, 1 to 168)."""
    if not 1 <= hours <= 168:
        raise ValueError(f"part1_stored_data_max_age_hours must be 1 to 168: {hours}")
    return timedelta(hours=hours)


def check_coverage(
    times: Iterable[datetime],
    start: datetime,
    end: datetime,
    *,
    max_gap: timedelta | None = None,
) -> QualityResult:
    """The points cover `[start, end]`: one at or before `start`, one at or after `end`, and, when
    the caller gives `max_gap`, no two consecutive points inside the horizon further apart."""
    _require_aware(start, "start")
    _require_aware(end, "end")
    if end <= start:
        raise ValueError(f"the horizon must end after it starts: {start} to {end}")
    if max_gap is not None and max_gap <= timedelta(0):
        raise ValueError(f"max_gap must be positive: {max_gap}")
    ordered = sorted(times)
    for value in ordered:
        _require_aware(value, "point time")
    if not ordered:
        return _fail(NO_DATA, None, "no points")
    issues = []
    if ordered[0] > start:
        detail = f"first point {ordered[0].isoformat()} is after the start {start.isoformat()}"
        issues.append(QualityIssue(STARTS_LATE, None, detail))
    if ordered[-1] < end:
        detail = f"last point {ordered[-1].isoformat()} is before the end {end.isoformat()}"
        issues.append(QualityIssue(ENDS_EARLY, None, detail))
    if max_gap is not None:
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if later <= start or earlier >= end:
                continue
            if later - earlier > max_gap:
                detail = f"{later - earlier} between {earlier.isoformat()} and {later.isoformat()}"
                issues.append(QualityIssue(GAP, None, detail))
    return QualityResult(tuple(issues))


# --- datum and trusted rows ------------------------------------------------------------------


def check_datum(
    tide_set_datum: str | None, channel_datum: str | None, berth_datum: str | None
) -> QualityResult:
    """`common.datum.check_datum_consistency` as a structured result (no second implementation)."""
    try:
        check_datum_consistency(tide_set_datum, channel_datum, berth_datum)
    except DatumError as error:
        return _fail(DATUM_MISMATCH, None, str(error))
    return OK


@dataclass(frozen=True)
class TrustedRows[R]:
    kept: tuple[R, ...]
    excluded: tuple[R, ...]

    @property
    def result(self) -> QualityResult:
        if not self.excluded:
            return OK
        detail = f"{len(self.excluded)} row(s) excluded: {TRUST_FLAG} is not 0"
        return _fail(UNTRUSTED, TRUST_FLAG, detail)


def trusted_rows[R](rows: Iterable[R], flag: Callable[[R], object] | None = None) -> TrustedRows[R]:
    """Architecture I-13: keep only rows with `clock_skew_suspect = 0`.

    `flag` reads the flag from a row; by default the row is a mapping with that key. Anything
    other than 0 or False (1, True, a missing or NULL flag) is excluded: trust is never assumed.
    """
    read = flag if flag is not None else _mapping_flag
    kept: list[R] = []
    excluded: list[R] = []
    for row in rows:
        value = read(row)
        (kept if value is not None and value == 0 else excluded).append(row)
    return TrustedRows(tuple(kept), tuple(excluded))


def _mapping_flag(row: object) -> object:
    if not isinstance(row, Mapping):
        raise TypeError("pass `flag` for rows that are not mappings")
    return row.get(TRUST_FLAG)


def combine(results: Sequence[QualityResult]) -> QualityResult:
    """All issues of several checks, in order."""
    return QualityResult(tuple(issue for result in results for issue in result.issues))
