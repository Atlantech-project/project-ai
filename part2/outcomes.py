"""Solver outcome handling (AI-056): the CT-10 outcomes of a PART2_SOLVE.

Architecture §8.9 and CT-10:

- CP-SAT solved (OPTIMAL or FEASIBLE): `SOLVED` or `PARTIALLY_SOLVED`, `source = AI`. A request
  without an option is `NO_FEASIBLE_PLAN` with its binding constraints.
- No request placed: `NO_FEASIBLE_PLAN`, `solver_runs.status = INFEASIBLE`, no recommendation.
  FIFO never runs on infeasibility.
- Technical failure (time limit before any solution, or a solver defect): `FIFO_FALLBACK`,
  `solver_runs.status = ERROR`, plans by arrival order that pass the same hard filter (B2),
  the reason in `result_detail.failure_reason`.

The module reads nothing and writes nothing; AI-058 persists what it returns.
"""

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Final

from part2.filter import (
    BindingConstraint,
    Code,
    FilterContext,
    Kind,
    Option,
    binding_constraints,
    check_plan,
    filter_candidates,
)
from part2.filter.pairing import confirmed_window, rank_allows, truncate, tug_requirement
from part2.solver import (
    RankedOption,
    RequestSolution,
    SolveResult,
    SolverInvariantError,
    SolverSettings,
    SolveStatus,
    TermValue,
    Unscheduled,
    solve,
)
from part2.state.availability import (
    is_berth_available,
    is_pilot_available,
    is_tug_available,
    overlaps,
    without_requests,
)
from part2.state.model import ConfirmedHold, PendingHold, PortState
from part2.tugs import TugRequirement

MINUTE: Final = timedelta(minutes=1)
SOURCE_AI: Final = "AI"
SOURCE_FIFO: Final = "FIFO"
PURPOSE_INITIAL: Final = "INITIAL"
PURPOSE_DELAY_REPLAN: Final = "DELAY_REPLAN"
# CT-08 / CT-10 error categories that lead to FIFO.
TIMEOUT: Final = "TIMEOUT"
SOLVER_ERROR: Final = "SOLVER_ERROR"
MESSAGE_LIMIT: Final = 1000  # CT-10 `failure_reason.message`


class RunOutcome(StrEnum):
    SOLVED = "SOLVED"
    PARTIALLY_SOLVED = "PARTIALLY_SOLVED"
    NO_FEASIBLE_PLAN = "NO_FEASIBLE_PLAN"
    FIFO_FALLBACK = "FIFO_FALLBACK"


class RequestResult(StrEnum):
    SOLVED = "SOLVED"
    FIFO_FALLBACK = "FIFO_FALLBACK"
    NO_FEASIBLE_PLAN = "NO_FEASIBLE_PLAN"


@dataclass(frozen=True)
class PlannedOption:
    """An option to persist. FIFO options have no objective score (`objective_score` NULL)."""

    rank: int
    option: Option
    objective_score: Decimal | None
    terms: tuple[TermValue, ...]


@dataclass(frozen=True)
class RequestOutcome:
    request_id: int
    outcome: RequestResult
    purpose: str
    options: tuple[PlannedOption, ...]
    binding_constraints: tuple[BindingConstraint, ...]  # non-empty only for NO_FEASIBLE_PLAN


@dataclass(frozen=True)
class SolveOutcome:
    outcome: RunOutcome
    solver_status: str  # `solver_runs.status`: OPTIMAL · FEASIBLE · INFEASIBLE · ERROR
    source: str  # `recommendations.source` for the written options
    error_category: str | None  # only with FIFO_FALLBACK
    failure_message: str | None
    requests: tuple[RequestOutcome, ...]
    objective_value: Decimal | None
    solve_time_ms: int
    solver_version: str
    flags: tuple[str, ...]

    def result_detail(self) -> dict[str, object]:
        """`solver_runs.result_detail` (CT-10). `recommendation_id` is filled by AI-058."""
        failure = (
            None
            if self.error_category is None
            else {"error_category": self.error_category, "message": self.failure_message or ""}
        )
        return {
            "outcome": self.outcome.value,
            "failure_reason": failure,
            "requests": [
                {
                    "request_id": r.request_id,
                    "outcome": r.outcome.value,
                    "purpose": r.purpose,
                    "recommendation_id": None,
                    "options_count": len(r.options),
                    "binding_constraints": [
                        {
                            "kind": b.kind.value,
                            "constraint_type_code": b.constraint_type_code,
                            "detail": b.detail,
                        }
                        for b in r.binding_constraints
                    ],
                }
                for r in self.requests
            ],
        }


SolveFn = Callable[..., SolveResult]


def handle_solve(
    state: PortState,
    request_ids: Iterable[int],
    context: FilterContext,
    service_times: Mapping[int, timedelta],
    settings: SolverSettings,
    *,
    replan_request_ids: Iterable[int] = (),
    solve_fn: SolveFn = solve,
    clock: Callable[[], float] = time.monotonic,
) -> SolveOutcome:
    """Run B5 and turn its result into the CT-10 outcome, with FIFO on a technical failure."""
    began = clock()
    run = tuple(sorted(set(request_ids)))
    replan = frozenset(replan_request_ids)
    try:
        result = solve_fn(state, run, context, service_times, settings, clock=clock)
    except SolverInvariantError as error:
        return _fifo(
            state, run, context, service_times, replan, SOLVER_ERROR, str(error), began, clock
        )
    if result.status is SolveStatus.TIMEOUT:
        message = (
            f"CP-SAT reached solver_time_limit_seconds ({settings.time_limit_seconds}) "
            "without a feasible solution"
        )
        return _fifo(state, run, context, service_times, replan, TIMEOUT, message, began, clock)
    return _from_solver(state, run, context, service_times, replan, result)


# --- solved runs ----------------------------------------------------------------------------


def _from_solver(
    state: PortState,
    run: tuple[int, ...],
    context: FilterContext,
    service_times: Mapping[int, timedelta],
    replan: frozenset[int],
    result: SolveResult,
) -> SolveOutcome:
    firsts = [s.options[0].option for s in result.requests if s.options]
    outcomes = []
    for solution in result.requests:
        purpose = _purpose(solution.request_id, replan)
        if solution.options:
            options = tuple(_planned(o) for o in solution.options)
            outcomes.append(
                RequestOutcome(solution.request_id, RequestResult.SOLVED, purpose, options, ())
            )
            continue
        reasons = _reasons(state, run, context, service_times, solution, firsts)
        outcomes.append(
            RequestOutcome(
                solution.request_id, RequestResult.NO_FEASIBLE_PLAN, purpose, (), reasons
            )
        )
    solved = sum(1 for o in outcomes if o.outcome is RequestResult.SOLVED)
    if solved == 0:
        outcome, status, value = RunOutcome.NO_FEASIBLE_PLAN, "INFEASIBLE", None
    else:
        outcome = RunOutcome.SOLVED if solved == len(outcomes) else RunOutcome.PARTIALLY_SOLVED
        status, value = result.status.value, result.objective_value
    return SolveOutcome(
        outcome=outcome,
        solver_status=status,
        source=SOURCE_AI,
        error_category=None,
        failure_message=None,
        requests=tuple(outcomes),
        objective_value=value,
        solve_time_ms=result.solve_time_ms,
        solver_version=result.solver_version,
        flags=result.flags,
    )


def _planned(ranked: RankedOption) -> PlannedOption:
    return PlannedOption(ranked.rank, ranked.option, ranked.objective_score, ranked.terms)


def _purpose(request_id: int, replan: frozenset[int]) -> str:
    return PURPOSE_DELAY_REPLAN if request_id in replan else PURPOSE_INITIAL


def _reasons(
    state: PortState,
    run: tuple[int, ...],
    context: FilterContext,
    service_times: Mapping[int, timedelta],
    solution: RequestSolution,
    firsts: Sequence[Option],
) -> tuple[BindingConstraint, ...]:
    """Why a request of a solved run got no option (CT-10 needs at least one reason)."""
    if solution.unscheduled is Unscheduled.FILTERED:
        return solution.binding_constraints
    request_id = solution.request_id
    if solution.unscheduled is Unscheduled.NO_START:
        detail = "The confirmed entry window holds no whole minute to start in"
        return (BindingConstraint(Kind.STRUCTURAL, Code.ENTRY_WINDOW, detail),)
    search = _Search.build(state, run, context, request_id, service_times[request_id], firsts)
    return search.missing_resources()


# --- FIFO fallback ----------------------------------------------------------------------------


def _fifo(
    state: PortState,
    run: tuple[int, ...],
    context: FilterContext,
    service_times: Mapping[int, timedelta],
    replan: frozenset[int],
    category: str,
    message: str,
    began: float,
    clock: Callable[[], float],
) -> SolveOutcome:
    """FIFO by arrival (`requested_eta`, then request id): each request takes the earliest berth,
    pilot and tugs that are free, after the requests before it. Every plan passes B2."""
    by_id = {r.request_id: r for r in state.requests}
    order = sorted(run, key=lambda r: (by_id[r].requested_eta, r))
    planned: list[Option] = []
    reasons: dict[int, tuple[BindingConstraint, ...]] = {}
    for request_id in order:
        candidates = filter_candidates(state, request_id, context)
        if not candidates.feasible:
            reasons[request_id] = binding_constraints(candidates)
            continue
        if request_id not in service_times:
            detail = "No service time (B3) for this request"
            reasons[request_id] = (BindingConstraint(Kind.STRUCTURAL, Code.ENTRY_WINDOW, detail),)
            continue
        search = _Search.build(state, run, context, request_id, service_times[request_id], planned)
        option = search.first_fit()
        if option is None:
            reasons[request_id] = search.missing_resources()
        else:
            planned.append(option)

    checks = check_plan(state, planned, context) if planned else ()
    failed = [c for c in checks if not c.passes]
    if failed:  # the greedy uses B2's own functions, so this is a defect, never a plan to write
        codes = ", ".join(sorted({r.code for c in failed for r in c.removals}))
        raise SolverInvariantError(f"FIFO plan fails B2: {codes}")
    options = {o.request_id: o for o in planned}
    outcomes = []
    for request_id in run:
        purpose = _purpose(request_id, replan)
        if request_id in options:
            plan = (PlannedOption(1, options[request_id], None, ()),)
            outcomes.append(
                RequestOutcome(request_id, RequestResult.FIFO_FALLBACK, purpose, plan, ())
            )
        else:
            outcomes.append(
                RequestOutcome(
                    request_id, RequestResult.NO_FEASIBLE_PLAN, purpose, (), reasons[request_id]
                )
            )
    return SolveOutcome(
        outcome=RunOutcome.FIFO_FALLBACK,
        solver_status="ERROR",
        source=SOURCE_FIFO,
        error_category=category,
        failure_message=message[:MESSAGE_LIMIT],
        requests=tuple(outcomes),
        objective_value=None,
        solve_time_ms=round((clock() - began) * 1000),
        solver_version="FIFO",
        flags=(),
    )


@dataclass(frozen=True)
class _Search:
    """Earliest-fit search for one request against fixed holds and other options."""

    state: PortState
    request_id: int
    terminal_id: int
    berth_ids: tuple[int, ...]
    starts: tuple[datetime, ...]
    duration: timedelta
    requirement: TugRequirement
    confirmed: tuple[ConfirmedHold, ...]
    pending: tuple[PendingHold, ...]
    others: tuple[Option, ...]

    @classmethod
    def build(
        cls,
        state: PortState,
        run: tuple[int, ...],
        context: FilterContext,
        request_id: int,
        service: timedelta,
        others: Sequence[Option],
    ) -> _Search:
        window = confirmed_window(state, request_id)
        if window is None:  # B2 removes a request without a window; kept as a guard
            raise SolverInvariantError(f"request {request_id} has no confirmed window")
        request = next(r for r in state.requests if r.request_id == request_id)
        candidates = filter_candidates(state, request_id, context)
        duration = _ceil_minute_delta(service)
        confirmed = without_requests(state.confirmed_holds, run)
        pending = without_requests(state.pending_holds, run)
        events = {window.start}
        events.update(h.end for h in confirmed)
        events.update(h.end for h in pending)
        events.update(o.end for o in others)
        events.update(s.start for s in (*state.pilot_shifts, *state.tug_master_shifts))
        starts = sorted(
            {_ceil_minute(t) for t in events if window.start <= _ceil_minute(t) < window.end}
        )
        return cls(
            state,
            request_id,
            request.requested_terminal_id,
            candidates.feasible_berth_ids,
            tuple(starts),
            duration,
            tug_requirement(context, request_id),
            confirmed,
            pending,
            tuple(others),
        )

    def _busy_in_others(self, start: datetime, end: datetime) -> list[Option]:
        return [o for o in self.others if overlaps(start, end, o.start, o.end)]

    def berth(self, start: datetime) -> int | None:
        end = start + self.duration
        used = {o.berth_id for o in self._busy_in_others(start, end)}
        for berth_id in self.berth_ids:
            if berth_id not in used and is_berth_available(
                self.state,
                berth_id,
                self.terminal_id,
                start,
                end,
                confirmed_holds=self.confirmed,
                pending_holds=self.pending,
            ):
                return berth_id
        return None

    def pilot(self, start: datetime) -> int | None:
        end = start + self.duration
        used = {o.pilot_user_id for o in self._busy_in_others(start, end)}
        request = next(r for r in self.state.requests if r.request_id == self.request_id)
        for pilot in sorted(self.state.pilots, key=lambda p: p.user_id):
            if (
                pilot.user_id not in used
                and rank_allows(pilot, request.loa, self.state.pilot_rank_limits)
                and is_pilot_available(
                    self.state,
                    pilot.user_id,
                    start,
                    end,
                    confirmed_holds=self.confirmed,
                    pending_holds=self.pending,
                )
            ):
                return pilot.user_id
        return None

    def tugs(self, start: datetime) -> tuple[int, ...] | None:
        """Fewest tugs meeting DEC-20: strongest first, until `N_min` and `BP_req` are met."""
        end = start + self.duration
        used = {t for o in self._busy_in_others(start, end) for t in o.tug_ids}
        req = self.requirement
        free = sorted(
            (
                t
                for t in self.state.tugs
                if t.id in req.eligible_tugs
                and t.id not in used
                and is_tug_available(
                    self.state,
                    t.id,
                    start,
                    end,
                    confirmed_holds=self.confirmed,
                    pending_holds=self.pending,
                )
            ),
            key=lambda t: (-t.tug_power, t.id),
        )
        chosen: list[int] = []
        power = Decimal(0)
        for tug in free:
            if len(chosen) >= req.n_min and power >= req.bp_req:
                break
            chosen.append(tug.id)
            power += tug.tug_power
        if len(chosen) < req.n_min or power < req.bp_req or len(chosen) > req.n_cap:
            return None
        return tuple(sorted(chosen))

    def first_fit(self) -> Option | None:
        for start in self.starts:
            berth = self.berth(start)
            if berth is None:
                continue
            pilot = self.pilot(start)
            tugs = self.tugs(start)
            if pilot is not None and tugs is not None:
                return Option(self.request_id, berth, start, start + self.duration, pilot, tugs)
        return None

    def missing_resources(self) -> tuple[BindingConstraint, ...]:
        """The resource kinds never free inside the window; all three if each is free at some
        time but never together."""
        found = {
            Code.BERTH_OCCUPIED: any(self.berth(s) is not None for s in self.starts),
            Code.PILOT_UNAVAILABLE: any(self.pilot(s) is not None for s in self.starts),
            Code.TUG_UNAVAILABLE: any(self.tugs(s) is not None for s in self.starts),
        }
        names = {
            Code.BERTH_OCCUPIED: "candidate berth",
            Code.PILOT_UNAVAILABLE: "pilot",
            Code.TUG_UNAVAILABLE: "set of tugs meeting the requirement",
        }
        missing = sorted(code for code, ok in found.items() if not ok)
        if missing:
            return tuple(
                BindingConstraint(
                    Kind.STRUCTURAL, c, f"No {names[c]} is free for the service time in the window"
                )
                for c in missing
            )
        return tuple(
            BindingConstraint(
                Kind.STRUCTURAL,
                c,
                truncate(
                    f"A {names[c]} is free at some start in the window, but never together "
                    "with the berth, pilot and tugs it needs"
                ),
            )
            for c in sorted(found)
        )


def _ceil_minute(value: datetime) -> datetime:
    floored = value.replace(second=0, microsecond=0)
    return floored if floored == value else floored + MINUTE


def _ceil_minute_delta(value: timedelta) -> timedelta:
    minutes = -(-(value // timedelta(microseconds=1)) // 60_000_000)
    return minutes * MINUTE
