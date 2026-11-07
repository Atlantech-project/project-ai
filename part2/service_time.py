"""B3 service time, Phase 1 formula (AI-052, DEC-28).

`hours = moves / productivity_rate + fixed_overhead_minutes / 60`, for one request at one candidate
terminal. A pure function: the caller reads the profiles, the BAPLIE and the port code and passes
plain values, so nothing here touches the database, the clock or the solver.

Nothing is guessed. A missing input excludes the candidate with a reason, and the result never
carries a P90 (`chk_ro_p90`: only method ML has one). P50 is rounded up to 0.01 h, so service time
errs long, as in DEC-28 and DEC-20. Vessels other than container vessels have no agreed basis
(DEC-28 open item 4) and are excluded with `BASIS_UNDEFINED`.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Context, Decimal
from typing import Final

from common.config import ConfigurationError

CONTAINER_VESSEL_TYPE: Final = "CONTAINER"  # `vessel_types.code` (DEC-28 rule)
METHOD_FORMULA: Final = "FORMULA"
_MOVES_UNIT: Final = "MOVES_PER_HOUR"  # the only unit a container terminal may carry (chk_tpp_unit)
_MINUTES_PER_HOUR: Final = Decimal(60)
_HOURS_STEP: Final = Decimal(
    "0.01"
)  # recommendation_options.service_time_p50_hours is decimal(6,2)
_CONTEXT: Final = Context(prec=28, rounding=ROUND_HALF_EVEN)

FLAG_LOADING_ESTIMATED: Final = "loading_estimated"

REASON_MISSING_MOVES: Final = "MISSING_MOVES"
REASON_NO_VALID_PROFILE: Final = "NO_VALID_PROFILE"
REASON_AMBIGUOUS_PROFILE: Final = "AMBIGUOUS_PROFILE"
REASON_BASIS_UNDEFINED: Final = "BASIS_UNDEFINED"
REASON_UNIT_MISMATCH: Final = "PROFILE_UNIT_MISMATCH"
REASON_NON_POSITIVE: Final = "NON_POSITIVE_SERVICE_TIME"


@dataclass(frozen=True)
class Moves:
    """Crane moves of one call (DEC-28 rule 7: recorded with each result)."""

    discharge: int
    loading: int
    loading_estimated: bool

    @property
    def total(self) -> int:
        return self.discharge + self.loading


@dataclass(frozen=True)
class ProductivityProfile:
    """A `terminal_productivity_profiles` row. `vessel_type_id` None is the terminal default."""

    id: int
    terminal_id: int
    vessel_type_id: int | None
    productivity_rate: Decimal
    rate_unit: str
    fixed_overhead_minutes: int
    valid_from: date
    valid_to: date | None

    def __post_init__(self) -> None:
        """Reject what the schema forbids (`chk_tpp_values`, `chk_tpp_period`); never guess."""
        if not self.productivity_rate > 0:
            raise ValueError("productivity_rate must be greater than 0")
        if self.fixed_overhead_minutes < 0:
            raise ValueError("fixed_overhead_minutes must not be negative")
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be before valid_from")


@dataclass(frozen=True)
class ServiceTimeResult:
    p50_hours: Decimal | None
    p90_hours: None  # always None: Phase 1 is FORMULA (chk_ro_p90)
    method: str
    excluded_reason: str | None
    flags: tuple[str, ...]
    inputs: Mapping[str, object]


def count_moves(
    *,
    has_active_baplie: bool,
    discharge_ports: Iterable[str | None],
    port_code: str | None,
    loading_count: int | None,
) -> Moves | None:
    """Moves of a container vessel (DEC-28 rules 1 to 5). None means unknown, never zero.

    `discharge_ports` is `port_of_discharge` of each manifest row of the request's ACTIVE BAPLIE.
    Without an ACTIVE BAPLIE the moves are unknown, and the caller leaves the request out with
    `MISSING_MOVES`. An unset port code is a configuration error, never discharge zero.
    """
    if not has_active_baplie:
        return None
    if port_code is None or not port_code.strip():
        raise ConfigurationError(
            "port_profiles.port_code is not set; discharge cannot be counted (DEC-28)",
            ["port_profiles.port_code"],
        )
    if loading_count is not None and loading_count < 0:
        raise ValueError("loading_count must not be negative")
    discharge = sum(1 for port in discharge_ports if port == port_code)
    if loading_count is None:
        return Moves(discharge=discharge, loading=discharge, loading_estimated=True)
    return Moves(discharge=discharge, loading=loading_count, loading_estimated=False)


def resolve_profile(
    profiles: Iterable[ProductivityProfile],
    *,
    terminal_id: int,
    vessel_type_id: int,
    on_date: date,
) -> tuple[ProductivityProfile | None, str | None]:
    """The profile valid on `on_date` for the terminal: the vessel's type first, then the default.

    Returns `(profile, None)`, or `(None, reason)` when there is none or more than one at the same
    level of detail (the Backend rejects overlaps, so that means bad data; no row is picked).
    """
    valid = [
        p
        for p in profiles
        if p.terminal_id == terminal_id
        and p.valid_from <= on_date
        and (p.valid_to is None or on_date <= p.valid_to)
    ]
    exact = [p for p in valid if p.vessel_type_id == vessel_type_id]
    candidates = exact or [p for p in valid if p.vessel_type_id is None]
    if not candidates:
        return None, REASON_NO_VALID_PROFILE
    if len(candidates) > 1:
        return None, REASON_AMBIGUOUS_PROFILE
    return candidates[0], None


def _excluded(reason: str, inputs: Mapping[str, object] | None = None) -> ServiceTimeResult:
    return ServiceTimeResult(
        p50_hours=None,
        p90_hours=None,
        method=METHOD_FORMULA,
        excluded_reason=reason,
        flags=(),
        inputs=inputs or {},
    )


def compute_service_time(
    *,
    vessel_type_code: str,
    vessel_type_id: int,
    terminal_id: int,
    moves: Moves | None,
    profiles: Iterable[ProductivityProfile],
    on_date: date,
) -> ServiceTimeResult:
    """Service time of one request at one terminal, or the reason it cannot be timed.

    `on_date` is the port-local date of the start of the request's earliest confirmed window
    (AI-052 ruling 1). The order of the checks puts the vessel type first, so a vessel without a
    basis is not reported as `MISSING_MOVES`.
    """
    if vessel_type_code != CONTAINER_VESSEL_TYPE:
        return _excluded(REASON_BASIS_UNDEFINED)
    if moves is None:
        return _excluded(REASON_MISSING_MOVES)
    profile, reason = resolve_profile(
        profiles, terminal_id=terminal_id, vessel_type_id=vessel_type_id, on_date=on_date
    )
    if profile is None:
        return _excluded(reason or REASON_NO_VALID_PROFILE)
    if profile.rate_unit != _MOVES_UNIT:
        return _excluded(REASON_UNIT_MISMATCH)

    inputs: dict[str, object] = {
        "discharge": moves.discharge,
        "loading": moves.loading,
        "loading_estimated": moves.loading_estimated,
        "moves": moves.total,
        "profile_id": profile.id,
        "productivity_rate": profile.productivity_rate,
        "rate_unit": profile.rate_unit,
        "fixed_overhead_minutes": profile.fixed_overhead_minutes,
        "on_date": on_date,
    }
    working = _CONTEXT.divide(Decimal(moves.total), profile.productivity_rate)
    overhead = _CONTEXT.divide(Decimal(profile.fixed_overhead_minutes), _MINUTES_PER_HOUR)
    hours = _CONTEXT.add(working, overhead).quantize(_HOURS_STEP, rounding=ROUND_CEILING)
    if hours <= 0:
        return _excluded(REASON_NON_POSITIVE, inputs)
    flags = (FLAG_LOADING_ESTIMATED,) if moves.loading_estimated else ()
    return ServiceTimeResult(
        p50_hours=hours,
        p90_hours=None,
        method=METHOD_FORMULA,
        excluded_reason=None,
        flags=flags,
        inputs=inputs,
    )
