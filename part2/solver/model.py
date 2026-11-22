"""B5 data: what the CP-SAT solve takes and returns (AI-055).

Every datetime is timezone-aware UTC. Scores are on the CT-18 §5 scale: each term normalised to
[0, 1] per request, multiplied by its weight, summed and scaled by 1000.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Final

from common.config import PortSettings
from part2.filter import BindingConstraint, Option

# CT-18 §4 keys (DEC-23).
KEY_TIME_LIMIT: Final = "solver_time_limit_seconds"
KEY_OPTIONS: Final = "solver_options_per_request"
KEY_EQUIVALENCE: Final = "solver_option_equivalence_pct"
KEY_WEIGHT_WAITING: Final = "objective_weight_waiting_time"
KEY_WEIGHT_RESOURCE: Final = "objective_weight_resource"

# `objective_terms.code` values (CT-18 §2, DEC-23).
TERM_WAITING_TIME: Final = "WAITING_TIME"
TERM_RESOURCE_COST: Final = "RESOURCE_COST"

SCORE_SCALE: Final = Decimal(1000)


class SolveStatus(StrEnum):
    """The CP-SAT result of the joint solve. AI-056 maps it to the CT-10 outcomes."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"  # the time limit stopped the search after a solution was found
    TIMEOUT = "TIMEOUT"  # the time limit stopped the search before any solution


class Unscheduled(StrEnum):
    """Why a request of the run got no option."""

    FILTERED = "FILTERED"  # B2 left no candidate berth; `binding_constraints` say why
    NO_START = "NO_START"  # the confirmed window holds no whole minute to start in
    NOT_PLACED = "NOT_PLACED"  # candidates exist, but no assignment fits the shared resources
    SOLVER_TIMEOUT = "SOLVER_TIMEOUT"  # the time limit hit before any solution (AI-056: FIFO)


@dataclass(frozen=True)
class SolverSettings:
    """The CT-18 keys B5 reads, plus the search seed and worker count (deterministic search)."""

    time_limit_seconds: int
    options_per_request: int
    equivalence_pct: Decimal
    weight_waiting_time: Decimal
    weight_resource: Decimal
    random_seed: int = 0
    num_workers: int = 1

    def __post_init__(self) -> None:
        """Reject values outside the CT-18 §4 ranges; never clamp."""
        if not 1 <= self.time_limit_seconds <= 120:
            raise ValueError(f"{KEY_TIME_LIMIT} must be 1 to 120: {self.time_limit_seconds}")
        if not 1 <= self.options_per_request <= 3:
            raise ValueError(f"{KEY_OPTIONS} must be 1 to 3: {self.options_per_request}")
        if not Decimal(0) <= self.equivalence_pct <= Decimal(50):
            raise ValueError(f"{KEY_EQUIVALENCE} must be 0 to 50: {self.equivalence_pct}")
        for key, weight in (
            (KEY_WEIGHT_WAITING, self.weight_waiting_time),
            (KEY_WEIGHT_RESOURCE, self.weight_resource),
        ):
            if not Decimal(0) <= weight <= Decimal(10):
                raise ValueError(f"{key} must be 0 to 10: {weight}")
        if self.num_workers < 1:
            raise ValueError(f"num_workers must be at least 1: {self.num_workers}")

    @classmethod
    def from_port_settings(cls, settings: PortSettings) -> SolverSettings:
        return cls(
            time_limit_seconds=settings.get_int(KEY_TIME_LIMIT),
            options_per_request=settings.get_int(KEY_OPTIONS),
            equivalence_pct=settings.get_decimal(KEY_EQUIVALENCE),
            weight_waiting_time=settings.get_decimal(KEY_WEIGHT_WAITING),
            weight_resource=settings.get_decimal(KEY_WEIGHT_RESOURCE),
        )


@dataclass(frozen=True)
class TermValue:
    """One objective term of an option: the normalised value in [0, 1] and its weight."""

    code: str
    normalised: Decimal
    weight: Decimal


@dataclass(frozen=True)
class RankedOption:
    """An option of one request. `rank` 1 is the joint solution and the one that holds resources
    (DEC-32 rule 3); ranks 2 and 3 are alternatives within the equivalence percentage."""

    rank: int
    option: Option
    objective_score: Decimal  # CT-18 §5 scale, 4 decimals (`recommendation_options`)
    terms: tuple[TermValue, ...]


@dataclass(frozen=True)
class RequestSolution:
    request_id: int
    options: tuple[RankedOption, ...]  # by rank; empty when unscheduled
    unscheduled: Unscheduled | None
    binding_constraints: tuple[BindingConstraint, ...]  # B2's reasons, for FILTERED only


@dataclass(frozen=True)
class SolveResult:
    status: SolveStatus
    requests: tuple[RequestSolution, ...]  # by request id
    objective_value: Decimal | None  # sum of the option-1 scores; None on TIMEOUT
    solve_time_ms: int
    solver_version: str
    flags: tuple[str, ...]


@dataclass(frozen=True)
class Pin:
    """What a REPLAN request's new option must keep, because it has started (AI-059).

    Architecture §8.13: a delay re-plan re-solves "with `STARTED` components fixed". A started
    component keeps its resource and its interval; an option has one interval for its berth, pilot
    and tugs (DEC-32 rule 4), so the option's start and end are the started components' interval.
    `None` (or an empty set) leaves that part free.
    """

    start: datetime
    end: datetime
    berth_id: int | None = None
    pilot_user_id: int | None = None
    tug_ids: frozenset[int] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for name, value in (("start", self.start), ("end", self.end)):
            if value.utcoffset() is None:
                raise ValueError(f"pin {name} must be timezone-aware")
            if value.second or value.microsecond:
                raise ValueError(f"pin {name} must be a whole minute (the solve grid): {value}")
        if self.end <= self.start:
            raise ValueError("pin end must be after its start")

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def honoured_by(self, option: Option) -> bool:
        return (
            option.start == self.start
            and option.end == self.end
            and (self.berth_id is None or option.berth_id == self.berth_id)
            and (self.pilot_user_id is None or option.pilot_user_id == self.pilot_user_id)
            and self.tug_ids <= set(option.tug_ids)
        )
