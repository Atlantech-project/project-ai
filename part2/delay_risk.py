"""B4 delay risk, Phase 1 (AI-053, DEC-21): a level from weather and congestion, or NULL.

The result is max(weather W, congestion C), so a missing input can only make the level too low,
never too high. A HIGH is always reliable; a LOW or MEDIUM computed with a gap is a lower bound.
NULL is limited to a forecast that is missing, older than the allowed age, or has no point in the
option's window (DEC-21 rule 5). Every other gap is flagged beside `rules_unvalidated`, and the
result names what was not assessed. Nothing is invented. The result also returns the inputs it used
(W maxima, C ratio, post-storm flag, coverage) for DEC-21 open item 6; storing them is AI-058's.

The caller (AI-055/056) reads the database and passes plain values; this module reads nothing, has
no clock and imports no solver. Every number lives in `delay_risk_rules.json` with its source.
The level codes are NOT probabilities: P-38 shows the level only (DEC-21 condition (a)).
Safety-limit headroom is not applied (DEC-30 TR-10 is not filled): the function takes no such input.
"""

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import IntEnum
from pathlib import Path
from typing import Any, Final

from common.time import to_local
from common.units import Unit, convert, parse_unit

RULES_PATH: Final = Path(__file__).with_name("delay_risk_rules.json")

STATUS_APPROVED: Final = "APPROVED"
_RULE_STATUSES: Final = frozenset({"PROPOSED", STATUS_APPROVED})

FLAG_RULES_UNVALIDATED: Final = "rules_unvalidated"
FLAG_CONGESTION_UNAVAILABLE: Final = "congestion_unavailable"
FLAG_STORM_HISTORY_UNKNOWN: Final = "storm_history_unknown"
FLAG_FORECAST_PARTIAL: Final = "forecast_partial"
FLAG_WEATHER_INCOMPLETE: Final = "weather_incomplete"

NOT_ASSESSED_CONGESTION: Final = "congestion"
NOT_ASSESSED_STORM_HISTORY: Final = "storm_history"

REASON_NO_FORECAST: Final = "forecast_missing"
REASON_FORECAST_STALE: Final = "forecast_stale"
REASON_NO_POINT_IN_WINDOW: Final = "no_forecast_point_in_window"

DRIVER_WEATHER: Final = "weather"
DRIVER_CONGESTION: Final = "congestion"
DRIVER_BACKLOG: Final = "backlog"

_KNOTS_PLACES: Final = 6  # float noise from a unit conversion must not decide a boundary


class Level(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


@dataclass(frozen=True)
class WeatherRules:
    gust_medium_min_kn: Decimal
    gust_high_above_kn: Decimal
    wind_high_above_kn: Decimal
    wave_medium_min_m: Decimal
    wave_high_above_m: Decimal


@dataclass(frozen=True)
class CongestionRules:
    medium_min_ratio: Decimal
    high_min_ratio: Decimal
    history_days: int


@dataclass(frozen=True)
class DelayRiskRules:
    status: str
    rule_version: str
    weather: WeatherRules
    congestion: CongestionRules
    backlog_min_days: int
    backlog_max_days: int
    codes: Mapping[Level, Decimal]


@dataclass(frozen=True)
class ForecastPoint:
    """One `environment_forecast_points` row; None is a value the provider did not send."""

    valid_at: datetime  # aware UTC
    wind_speed: Decimal | None
    wind_gust: Decimal | None
    wave_height: Decimal | None  # metres


@dataclass(frozen=True)
class Forecast:
    points: tuple[ForecastPoint, ...]
    wind_speed_unit: str  # `forecast_runs.wind_speed_unit`: KNOTS, METRES_PER_SECOND, KM_PER_HOUR
    step_minutes: int  # spacing of the points, to judge coverage
    age: timedelta  # how old the data is; the caller measures it


@dataclass(frozen=True)
class Congestion:
    """The caller's counts. DEC-21 does not say where arrivals come from (open question)."""

    expected_arrivals_24h: int | None
    median_daily_arrivals_28d: Decimal | None
    days_of_history: int | None


@dataclass(frozen=True)
class Coverage:
    points_used: int
    points_expected: int


@dataclass(frozen=True)
class WeatherMaxima:
    """Maxima over the window, wind in knots and waves in metres; None: no value at all."""

    wind_gust_kn: Decimal | None
    wind_speed_kn: Decimal | None
    wave_height_m: Decimal | None


@dataclass(frozen=True)
class DelayRiskInputs:
    """What the level was computed from, so M4 has its features from day one (DEC-21 item 6)."""

    weather: WeatherMaxima
    weather_level: Level
    congestion_ratio: Decimal | None  # None: unavailable
    congestion_level: Level | None  # before the post-storm raise
    post_storm_window: (
        bool | None
    )  # the window starts 1 to 3 port days after a HIGH day; None: unknown
    backlog_raised: bool  # the post-storm rule actually raised C


@dataclass(frozen=True)
class DelayRiskResult:
    """`code` is what the worker writes to `recommendation_options.delay_risk`; None is NULL."""

    code: Decimal | None
    level: Level | None
    reason: str | None  # why the result is NULL
    drivers: tuple[str, ...]
    flags: tuple[str, ...]
    not_assessed: tuple[str, ...]
    coverage: Coverage | None
    rule_version: str
    inputs: DelayRiskInputs | None = None  # None when the result is NULL

    @property
    def is_lower_bound(self) -> bool:
        """A gap was left out of the max(W, C): the true level can only be higher."""
        return self.level is not None and bool(self.not_assessed)


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    section: Mapping[str, Any] = data[name]
    if not section["source"] or not isinstance(section["interim"], bool):
        raise ValueError(f"{name} needs a source and an interim note")
    return section


def _decimal(value: Any) -> Decimal:
    # Strings only: a JSON float would already have lost exactness.
    if not isinstance(value, str):
        raise TypeError("a decimal value must be a string")
    return Decimal(value)


def _parse_rules(data: Mapping[str, Any]) -> DelayRiskRules:
    if data["status"] not in _RULE_STATUSES:
        raise ValueError("unknown status")
    weather = _section(data, "weather")
    congestion = _section(data, "congestion")
    backlog = _section(data, "backlog")
    codes = _section(data, "level_codes")
    parsed_codes = {level: _decimal(codes[level.name]) for level in Level}
    if not (parsed_codes[Level.LOW] < parsed_codes[Level.MEDIUM] < parsed_codes[Level.HIGH]):
        raise ValueError("level codes must rise from LOW to HIGH")
    if not all(Decimal(0) < code < Decimal(1) for code in parsed_codes.values()):
        raise ValueError("level codes must lie between 0 and 1")
    medium = _decimal(congestion["medium_min_ratio"])
    high = _decimal(congestion["high_min_ratio"])
    if not Decimal(0) < medium < high:
        raise ValueError("congestion cut-offs must rise")
    if not 1 <= int(backlog["min_days_after"]) <= int(backlog["max_days_after"]):
        raise ValueError("backlog days must run from 1 up")
    gust_medium = _decimal(weather["gust_medium_min_kn"])
    gust_high = _decimal(weather["gust_high_above_kn"])
    wave_medium = _decimal(weather["wave_medium_min_m"])
    wave_high = _decimal(weather["wave_high_above_m"])
    if not (gust_medium < gust_high and wave_medium < wave_high):
        raise ValueError("weather MEDIUM must start below HIGH")
    if not data["rule_version"]:
        raise ValueError("a rule version is needed")
    return DelayRiskRules(
        status=data["status"],
        rule_version=data["rule_version"],
        weather=WeatherRules(
            gust_medium, gust_high, _decimal(weather["wind_high_above_kn"]), wave_medium, wave_high
        ),
        congestion=CongestionRules(medium, high, int(congestion["history_days"])),
        backlog_min_days=int(backlog["min_days_after"]),
        backlog_max_days=int(backlog["max_days_after"]),
        codes=parsed_codes,
    )


def load_rules(path: Path = RULES_PATH) -> DelayRiskRules:
    with path.open(encoding="utf-8") as handle:
        return _parse_rules(json.load(handle))


def _knots(value: Decimal | None, unit: Unit) -> Decimal | None:
    if value is None:
        return None
    if unit is Unit.KNOTS:
        return value
    converted = convert(float(value), unit, Unit.KNOTS)
    return Decimal(repr(round(converted, _KNOTS_PLACES)))


def weather_maxima(points: Iterable[ForecastPoint], wind_speed_unit: str) -> WeatherMaxima:
    """The maxima over the points, wind converted to knots with `common.units` (AI-014).

    Raises on a wind unit that is not a speed (nothing is guessed).
    """
    unit = parse_unit(wind_speed_unit)
    rows = tuple(points)
    gusts = [g for p in rows if (g := _knots(p.wind_gust, unit)) is not None]
    winds = [w for p in rows if (w := _knots(p.wind_speed, unit)) is not None]
    waves = [p.wave_height for p in rows if p.wave_height is not None]
    return WeatherMaxima(
        max(gusts, default=None), max(winds, default=None), max(waves, default=None)
    )


def _weather_level_of(maxima: WeatherMaxima, rules: DelayRiskRules) -> Level | None:
    """W from the maxima; None when no metric has a value."""
    rule = rules.weather
    gust, wind, wave = maxima.wind_gust_kn, maxima.wind_speed_kn, maxima.wave_height_m
    if gust is None and wind is None and wave is None:
        return None
    if (
        (gust is not None and gust > rule.gust_high_above_kn)
        or (wind is not None and wind > rule.wind_high_above_kn)
        or (wave is not None and wave > rule.wave_high_above_m)
    ):
        return Level.HIGH
    if (gust is not None and gust >= rule.gust_medium_min_kn) or (
        wave is not None and wave >= rule.wave_medium_min_m
    ):
        return Level.MEDIUM
    return Level.LOW


def _missing_metrics(maxima: WeatherMaxima) -> tuple[str, ...]:
    return tuple(
        name
        for name, value in (
            ("wind_gust", maxima.wind_gust_kn),
            ("wind_speed", maxima.wind_speed_kn),
            ("wave_height", maxima.wave_height_m),
        )
        if value is None
    )


def weather_level(
    points: Iterable[ForecastPoint], wind_speed_unit: str, rules: DelayRiskRules
) -> tuple[Level | None, tuple[str, ...]]:
    """W over the given points, and the metrics with no value at all (not assessed).

    None: no metric has any value. Public so the caller can find the days on which W was HIGH.
    """
    maxima = weather_maxima(points, wind_speed_unit)
    return _weather_level_of(maxima, rules), _missing_metrics(maxima)


def _congestion_ratio(congestion: Congestion | None, rules: DelayRiskRules) -> Decimal | None:
    """expected arrivals / median daily arrivals, or None when unavailable: a missing input, a
    median of 0, or too little history."""
    if congestion is None:
        return None
    expected = congestion.expected_arrivals_24h
    median = congestion.median_daily_arrivals_28d
    history = congestion.days_of_history
    if expected is None or median is None or history is None:
        return None
    if median <= 0 or history < rules.congestion.history_days:
        return None
    return Decimal(expected) / median


def _congestion_level(ratio: Decimal | None, rules: DelayRiskRules) -> Level | None:
    if ratio is None:
        return None
    if ratio >= rules.congestion.high_min_ratio:
        return Level.HIGH
    if ratio >= rules.congestion.medium_min_ratio:
        return Level.MEDIUM
    return Level.LOW


def _raised(level: Level) -> Level:
    return Level(min(level + 1, Level.HIGH))


def _null(rules: DelayRiskRules, reason: str) -> DelayRiskResult:
    return DelayRiskResult(
        code=None,
        level=None,
        reason=reason,
        drivers=(),
        flags=(),
        not_assessed=(),
        coverage=None,
        rule_version=rules.rule_version,
    )


def assess_delay_risk(
    *,
    window_start: datetime,
    window_end: datetime,
    forecast: Forecast | None,
    max_forecast_age_hours: int,
    congestion: Congestion | None,
    storm_days: frozenset[date] | None,
    time_zone: str,
    rules: DelayRiskRules | None = None,
) -> DelayRiskResult:
    """B4 Phase 1 for one option over `[window_start, window_end)` (aware UTC).

    `max_forecast_age_hours` is `part1_stored_data_max_age_hours` from `port_settings` (48).
    `storm_days` are the port days (in `time_zone`) on which W was HIGH: an empty set means none,
    None means the history is unknown. Safety-limit headroom is not an input and is not applied.
    """
    if window_end <= window_start:
        raise ValueError(f"the window must end after it starts: {window_start} to {window_end}")
    rules = rules or load_rules()
    if forecast is None or not forecast.points:
        return _null(rules, REASON_NO_FORECAST)
    if forecast.age > timedelta(hours=max_forecast_age_hours):
        return _null(rules, REASON_FORECAST_STALE)
    if forecast.step_minutes <= 0:
        raise ValueError("the forecast step must be positive")

    in_window = tuple(p for p in forecast.points if window_start <= p.valid_at < window_end)
    if not in_window:
        return _null(rules, REASON_NO_POINT_IN_WINDOW)
    maxima = weather_maxima(in_window, forecast.wind_speed_unit)
    level_w = _weather_level_of(maxima, rules)
    if level_w is None:
        return _null(rules, REASON_NO_POINT_IN_WINDOW)
    missing_metrics = _missing_metrics(maxima)

    # Unvalidated until the rules file is APPROVED (as in AI-054); DEC-21 starts it PROPOSED.
    flags = [FLAG_RULES_UNVALIDATED] if rules.status != STATUS_APPROVED else []
    not_assessed = list(missing_metrics)
    if missing_metrics:
        flags.append(FLAG_WEATHER_INCOMPLETE)

    # At least this many points fall in any half-open window of this length, so a shortfall is a
    # real gap and never an artefact of where the window sits on the forecast grid.
    window_minutes = (window_end - window_start) / timedelta(minutes=1)
    expected = max(1, math.floor(window_minutes / forecast.step_minutes))
    coverage = Coverage(points_used=len(in_window), points_expected=expected)
    if coverage.points_used < coverage.points_expected:
        flags.append(FLAG_FORECAST_PARTIAL)

    ratio = _congestion_ratio(congestion, rules)
    level_c = _congestion_level(ratio, rules)
    congestion_level = level_c
    if level_c is None:
        flags.append(FLAG_CONGESTION_UNAVAILABLE)
        not_assessed.append(NOT_ASSESSED_CONGESTION)

    post_storm_window: bool | None = None
    backlog_applied = False
    if storm_days is None:
        flags.append(FLAG_STORM_HISTORY_UNKNOWN)
        not_assessed.append(NOT_ASSESSED_STORM_HISTORY)
    else:
        first_day = to_local(window_start, time_zone).date()
        days_after = range(rules.backlog_min_days, rules.backlog_max_days + 1)
        post_storm_window = any((first_day - day).days in days_after for day in storm_days)
        if post_storm_window and level_c is not None:
            raised = _raised(level_c)
            backlog_applied = raised != level_c
            level_c = raised

    candidates = [level_w] if level_c is None else [level_w, level_c]
    level = Level(max(candidates))
    drivers: list[str] = []
    if level_w == level:
        drivers.append(DRIVER_WEATHER)
    if level_c is not None and level_c == level:
        drivers.append(DRIVER_CONGESTION)
        if backlog_applied:
            drivers.append(DRIVER_BACKLOG)
    return DelayRiskResult(
        code=rules.codes[level],
        level=level,
        reason=None,
        drivers=tuple(drivers),
        flags=tuple(flags),
        not_assessed=tuple(not_assessed),
        coverage=coverage,
        rule_version=rules.rule_version,
        inputs=DelayRiskInputs(
            weather=maxima,
            weather_level=level_w,
            congestion_ratio=ratio,
            congestion_level=congestion_level,
            post_storm_window=post_storm_window,
            backlog_raised=backlog_applied,
        ),
    )
