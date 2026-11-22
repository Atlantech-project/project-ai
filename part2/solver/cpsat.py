"""B5: port-wide joint CP-SAT allocation of berth, pilot and tugs, with ranked options (AI-055).

Architecture §8.8 and the AI-055 task decision. Per request of the run:

- one candidate berth from B2 (AI-051), an optional fixed-size interval per berth, `NoOverlap` per
  berth;
- one pilot whose rank may take the LOA, and between `N_min` and `N_cap` eligible tugs whose
  bollard pull sums to at least `BP_req` (DEC-20 CP-SAT interface); each pilot and tug works the
  whole option interval inside one active shift (its own, or its tug master's), with `NoOverlap`
  per person and per tug (DEC-32 rules 1 to 4, interim interval = option window);
- start inside the confirmed entry window, half-open `[start, end)`, on a whole-minute grid.

Confirmed plans and every other pending recommendation's option 1 are fixed intervals (DEC-06,
DEC-32 rule 3); the run's own holds are dropped (DEC-32 rule 5). A request that cannot be placed
is left unscheduled, never forced: the model first maximises the number of scheduled requests, then
minimises the DEC-23 objective. Every emitted option is checked again by B2 (Architecture §8.4).
"""

import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from importlib.metadata import version
from typing import Final

from ortools.sat.python import cp_model

from part2.filter import (
    FilterContext,
    Option,
    binding_constraints,
    check_option,
    filter_candidates,
)
from part2.filter.pairing import confirmed_window, rank_allows, tug_requirement
from part2.solver.model import (
    SCORE_SCALE,
    TERM_RESOURCE_COST,
    TERM_WAITING_TIME,
    Pin,
    RankedOption,
    RequestSolution,
    SolveResult,
    SolverSettings,
    SolveStatus,
    TermValue,
    Unscheduled,
)
from part2.state.availability import TUG_OUT_OF_SERVICE, without_requests
from part2.state.model import (
    ConfirmedHold,
    ConfirmedWindow,
    PendingHold,
    PortState,
    ResourceKind,
    Shift,
)

MINUTE: Final = timedelta(minutes=1)
_MICROS_PER_MINUTE: Final = 60_000_000
# Solver units per unit of weighted, normalised score. The reported score is recomputed exactly.
RESOLUTION: Final = 1_000_000
# Tug bollard pull is compared in hundredths of a tonne; a rating is floored (conservative).
BP_SCALE: Final = 100
SCORE_QUANTUM: Final = Decimal("0.0001")

FLAG_ALTERNATIVES_TIME_LIMIT: Final = "ALTERNATIVES_TIME_LIMIT"

_Resource = tuple[ResourceKind, int]
_Range = tuple[int, int]


class SolverInvariantError(RuntimeError):
    """The model produced something B2 rejects, or CP-SAT reported an impossible status."""


@dataclass(frozen=True)
class _Grid:
    """Whole minutes from `origin`. Starts round up, ends round down: never outside a bound."""

    origin: datetime

    def _micros(self, value: datetime) -> int:
        return (value - self.origin) // timedelta(microseconds=1)

    def ceil(self, value: datetime) -> int:
        return -(-self._micros(value) // _MICROS_PER_MINUTE)

    def floor(self, value: datetime) -> int:
        return self._micros(value) // _MICROS_PER_MINUTE

    def at(self, minute: int) -> datetime:
        return self.origin + minute * MINUTE


@dataclass(frozen=True)
class _Worker:
    """A pilot or a tug that may serve the request, with the start ranges its shifts allow."""

    resource_id: int
    ranges: tuple[_Range, ...]
    bollard_pull: int = 0  # tugs only, in BP_SCALE units


@dataclass(frozen=True)
class _Request:
    request_id: int
    berth_ids: tuple[int, ...]
    lo: int  # first allowed start minute
    hi: int  # last allowed start minute
    duration: int  # minutes
    pilots: tuple[_Worker, ...]
    tugs: tuple[_Worker, ...]
    n_min: int
    n_cap: int
    bp_req: int  # BP_SCALE units
    fixed_start: int | None = None  # AI-059: a started component fixes the start minute
    required_tugs: frozenset[int] = frozenset()  # AI-059: started tug components

    @property
    def span(self) -> int:
        return self.hi - self.lo


@dataclass(frozen=True)
class _Placed:
    berth_id: int
    start: int
    pilot_id: int
    tug_ids: tuple[int, ...]


# start, assigned, berth literals, pilot literals, tug literals
_Vars = tuple[
    cp_model.IntVar,
    cp_model.IntVar,
    dict[int, cp_model.IntVar],
    dict[int, cp_model.IntVar],
    dict[int, cp_model.IntVar],
]


@dataclass(frozen=True)
class _Outcome:
    status: cp_model.CpSolverStatus
    placed: Mapping[int, _Placed]


def solve(
    state: PortState,
    request_ids: Iterable[int],
    context: FilterContext,
    service_times: Mapping[int, timedelta],
    settings: SolverSettings,
    *,
    clock: Callable[[], float] = time.monotonic,
    pins: Mapping[int, Pin] | None = None,
) -> SolveResult:
    """Solve the run's requests jointly and rank up to `options_per_request` options each.

    `service_times`: B3's P50 duration per request (AI-052); a request B3 excluded is not passed in.
    The time limit covers the joint solve and the alternatives together. `pins`: the started parts
    of REPLAN requests (AI-059); every option of a pinned request keeps them.
    """
    pins = dict(pins or {})
    started = clock()
    deadline = started + settings.time_limit_seconds
    run = tuple(sorted(set(request_ids)))
    if not run:
        raise ValueError("a solve needs at least one request")
    missing = [r for r in run if r not in service_times]
    if missing:
        raise ValueError(f"no service time for requests {missing}")
    strays = sorted(set(pins) - set(run))
    if strays:
        raise ValueError(f"pins for requests outside the run: {strays}")

    solutions: dict[int, RequestSolution] = {}
    windows: dict[int, tuple[ConfirmedWindow, tuple[int, ...]]] = {}
    for request_id in run:
        candidates = filter_candidates(state, request_id, context)
        if not candidates.feasible:
            solutions[request_id] = RequestSolution(
                request_id, (), Unscheduled.FILTERED, binding_constraints(candidates)
            )
            continue
        window = confirmed_window(state, request_id)
        if window is None:  # B2 removes such a request; kept as a guard
            raise SolverInvariantError(f"request {request_id} passed B2 without a window")
        windows[request_id] = (window, candidates.feasible_berth_ids)

    earliest = min((w.start for w, _ in windows.values()), default=state.horizon_start)
    grid = _Grid(_floor_minute(earliest))
    confirmed = without_requests(state.confirmed_holds, run)
    pending = without_requests(state.pending_holds, run)
    busy = _busy_intervals(grid, confirmed, pending)

    requests: list[_Request] = []
    for request_id, (window, berth_ids) in windows.items():
        prepared = _prepare(
            state, context, grid, request_id, window, berth_ids, service_times, pins.get(request_id)
        )
        if prepared is None:
            solutions[request_id] = RequestSolution(request_id, (), Unscheduled.NO_START, ())
        else:
            requests.append(prepared)

    flags: list[str] = []
    if not requests:
        status = SolveStatus.OPTIMAL
        placed: Mapping[int, _Placed] = {}
    else:
        outcome = _run(requests, busy, settings, deadline - clock())
        if outcome.status == cp_model.UNKNOWN:
            for request in requests:
                solutions[request.request_id] = RequestSolution(
                    request.request_id, (), Unscheduled.SOLVER_TIMEOUT, ()
                )
            return _result(SolveStatus.TIMEOUT, solutions, None, started, clock, flags)
        status = SolveStatus.OPTIMAL if outcome.status == cp_model.OPTIMAL else SolveStatus.FEASIBLE
        placed = outcome.placed

    by_id = {r.request_id: r for r in requests}
    firsts = {
        request_id: _option(grid, request_id, p, by_id[request_id])
        for request_id, p in placed.items()
    }
    _verify(state, context, run, list(firsts.values()))

    for request in requests:
        request_id = request.request_id
        if request_id not in placed:
            solutions[request_id] = RequestSolution(request_id, (), Unscheduled.NOT_PLACED, ())
            continue
        first = _ranked(1, firsts[request_id], placed[request_id], request, settings)
        options = [first]
        others = [o for r, o in firsts.items() if r != request_id]
        bound = first.objective_score * (1 + settings.equivalence_pct / 100)
        used = {placed[request_id].berth_id}
        while len(options) < settings.options_per_request:
            remaining = deadline - clock()
            if remaining <= 0:
                flags.append(FLAG_ALTERNATIVES_TIME_LIMIT)
                break
            narrowed = _without_berths(request, used)
            if not narrowed.berth_ids:
                break
            alt = _run([narrowed], _with_options(busy, grid, others), settings, remaining)
            if request_id not in alt.placed:
                break
            candidate = alt.placed[request_id]
            option = _option(grid, request_id, candidate, request)
            ranked = _ranked(len(options) + 1, option, candidate, request, settings)
            if ranked.objective_score > bound:
                break
            _verify(state, context, run, [option], plan=others)
            options.append(ranked)
            used.add(candidate.berth_id)
        solutions[request_id] = RequestSolution(request_id, tuple(options), None, ())

    for request_id, pin in pins.items():
        kept = solutions.get(request_id)
        if kept is not None and not all(pin.honoured_by(o.option) for o in kept.options):
            raise SolverInvariantError(f"an option of request {request_id} moves a started part")
    total = sum((s.options[0].objective_score for s in solutions.values() if s.options), Decimal(0))
    return _result(status, solutions, total, started, clock, sorted(set(flags)))


def _floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _busy_intervals(
    grid: _Grid, confirmed: Iterable[ConfirmedHold], pending: Iterable[PendingHold]
) -> dict[_Resource, list[_Range]]:
    """Fixed intervals per resource, widened to whole minutes (conservative)."""
    busy: dict[_Resource, list[_Range]] = defaultdict(list)
    holds: list[ConfirmedHold | PendingHold] = [*confirmed, *pending]
    for hold in holds:
        start, end = grid.floor(hold.start), grid.ceil(hold.end)
        if end > start:
            busy[(hold.kind, hold.resource_id)].append((start, end))
    return busy


def _with_options(
    busy: Mapping[_Resource, list[_Range]], grid: _Grid, options: Iterable[Option]
) -> dict[_Resource, list[_Range]]:
    """`busy` plus the berth, pilot and tugs of each option over its interval."""
    merged: dict[_Resource, list[_Range]] = defaultdict(list)
    for key, ranges in busy.items():
        merged[key].extend(ranges)
    for option in options:
        interval = (grid.floor(option.start), grid.ceil(option.end))
        merged[(ResourceKind.BERTH, option.berth_id)].append(interval)
        if option.pilot_user_id is not None:
            merged[(ResourceKind.PILOT, option.pilot_user_id)].append(interval)
        for tug_id in option.tug_ids:
            merged[(ResourceKind.TUG, tug_id)].append(interval)
    return merged


def _start_ranges(
    grid: _Grid, shifts: Iterable[Shift], person_id: int, lo: int, hi: int, duration: int
) -> tuple[_Range, ...]:
    """Start minutes at which one active shift of the person covers the whole interval."""
    ranges = set()
    for shift in shifts:
        if shift.person_id != person_id or not shift.shift_is_active:
            continue
        first = max(lo, grid.ceil(shift.start))
        last = min(hi, grid.floor(shift.end) - duration)
        if first <= last:
            ranges.add((first, last))
    return tuple(sorted(ranges))


def _prepare(
    state: PortState,
    context: FilterContext,
    grid: _Grid,
    request_id: int,
    window: ConfirmedWindow,
    berth_ids: tuple[int, ...],
    service_times: Mapping[int, timedelta],
    pin: Pin | None = None,
) -> _Request | None:
    """The request's variables' domains, or None when the window holds no whole start minute.

    A pin (AI-059) fixes the start minute and the duration to the started interval, and keeps only
    the pinned berth, pilot and tugs; the confirmed window still bounds the start.
    """
    service = service_times[request_id]
    if service <= timedelta(0):
        raise ValueError(f"service time of request {request_id} must be positive: {service}")
    duration = -(-(service // timedelta(microseconds=1)) // _MICROS_PER_MINUTE)
    lo = grid.ceil(window.start)
    hi = grid.ceil(window.end) - 1  # half-open window: the start is before its end
    if lo > hi:
        return None
    fixed_start = None
    if pin is not None:
        duration = pin.duration // MINUTE
        fixed_start = grid.ceil(pin.start)
        if grid.at(fixed_start) != pin.start or not lo <= fixed_start <= hi:
            return None
        if pin.berth_id is not None:
            berth_ids = tuple(b for b in berth_ids if b == pin.berth_id)

    request = next(r for r in state.requests if r.request_id == request_id)
    pilots = tuple(
        _Worker(p.user_id, ranges)
        for p in sorted(state.pilots, key=lambda p: p.user_id)
        if p.is_active
        and p.has_active_pilot_role
        and rank_allows(p, request.loa, state.pilot_rank_limits)
        and (pin is None or pin.pilot_user_id in (None, p.user_id))
        and (ranges := _start_ranges(grid, state.pilot_shifts, p.user_id, lo, hi, duration))
    )
    requirement = tug_requirement(context, request_id)
    tugs = []
    for tug in sorted(state.tugs, key=lambda t: t.id):
        if tug.id not in requirement.eligible_tugs or tug.status in TUG_OUT_OF_SERVICE:
            continue
        master = next((m for m in state.tug_masters if m.tugboat_id == tug.id), None)
        if master is None or not (master.is_active and master.has_active_tug_master_role):
            continue
        ranges = _start_ranges(grid, state.tug_master_shifts, master.user_id, lo, hi, duration)
        if ranges:
            bollard = int((tug.tug_power * BP_SCALE).to_integral_value(rounding=ROUND_FLOOR))
            tugs.append(_Worker(tug.id, ranges, bollard))
    return _Request(
        request_id=request_id,
        berth_ids=berth_ids,
        lo=lo,
        hi=hi,
        duration=duration,
        pilots=pilots,
        tugs=tuple(tugs),
        n_min=requirement.n_min,
        n_cap=requirement.n_cap,
        bp_req=requirement.bp_req * BP_SCALE,
        fixed_start=fixed_start,
        required_tugs=frozenset() if pin is None else pin.tug_ids,
    )


def _without_berths(request: _Request, used: set[int]) -> _Request:
    """The request without the berths its better options use: alternatives differ by berth."""
    return replace(request, berth_ids=tuple(b for b in request.berth_ids if b not in used))


def _coefficients(request: _Request, settings: SolverSettings) -> tuple[int, int]:
    """Per minute of waiting and per tug, in solver units."""
    wait = round(RESOLUTION * settings.weight_waiting_time / request.span) if request.span else 0
    tug = round(RESOLUTION * settings.weight_resource / request.n_cap) if request.n_cap else 0
    return wait, tug


def _run(
    requests: Sequence[_Request],
    busy: Mapping[_Resource, list[_Range]],
    settings: SolverSettings,
    seconds: float,
) -> _Outcome:
    model = cp_model.CpModel()
    intervals: dict[_Resource, list[cp_model.IntervalVar]] = defaultdict(list)
    for (kind, resource_id), ranges in sorted(busy.items()):
        for first, last in ranges:
            intervals[(kind, resource_id)].append(
                model.new_fixed_size_interval_var(first, last - first, f"busy_{kind}_{resource_id}")
            )

    cost_terms: list[cp_model.LinearExprT] = []
    unscheduled: list[cp_model.LinearExprT] = []
    worst = 0
    variables: dict[int, _Vars] = {}
    for request in requests:
        r = request.request_id
        start = model.new_int_var(request.lo, request.hi, f"start_{r}")
        if request.fixed_start is not None:
            model.add(start == request.fixed_start)
        assigned = model.new_bool_var(f"assigned_{r}")
        berths = {b: model.new_bool_var(f"berth_{r}_{b}") for b in request.berth_ids}
        model.add(cp_model.LinearExpr.sum(list(berths.values())) == assigned)
        for berth_id, present in berths.items():
            intervals[(ResourceKind.BERTH, berth_id)].append(
                model.new_optional_fixed_size_interval_var(
                    start, request.duration, present, f"berth_iv_{r}_{berth_id}"
                )
            )
        pilots = _workers(model, request, request.pilots, start, ResourceKind.PILOT, intervals)
        model.add(cp_model.LinearExpr.sum(list(pilots.values())) == assigned)
        tugs = _workers(model, request, request.tugs, start, ResourceKind.TUG, intervals)
        for tug_id in sorted(request.required_tugs):  # a started tug stays on the option
            if tug_id in tugs:
                model.add(tugs[tug_id] == 1).only_enforce_if(assigned)
            else:
                model.add(assigned == 0)
        tug_count = cp_model.LinearExpr.sum(list(tugs.values()))
        bollard = cp_model.LinearExpr.weighted_sum(
            list(tugs.values()), [w.bollard_pull for w in request.tugs]
        )
        # DEC-20 CP-SAT interface: never relaxed; a request that can't meet it stays unscheduled.
        model.add(tug_count >= request.n_min).only_enforce_if(assigned)
        model.add(tug_count <= request.n_cap).only_enforce_if(assigned)
        model.add(bollard >= request.bp_req).only_enforce_if(assigned)
        model.add(tug_count == 0).only_enforce_if(~assigned)

        wait, per_tug = _coefficients(request, settings)
        cost_terms.append(wait * (start - request.lo) + per_tug * tug_count)
        worst += wait * request.span + per_tug * request.n_cap
        unscheduled.append(1 - assigned)
        variables[r] = (start, assigned, berths, pilots, tugs)

    for key in sorted(intervals):
        if len(intervals[key]) > 1:
            model.add_no_overlap(intervals[key])
    # Scheduling one more request always beats any change in cost (lexicographic by weight).
    model.minimize(
        (worst + 1) * cp_model.LinearExpr.sum(unscheduled) + cp_model.LinearExpr.sum(cost_terms)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(seconds, 0.001)
    solver.parameters.num_workers = settings.num_workers
    solver.parameters.random_seed = settings.random_seed
    status = solver.solve(model)
    if status in (cp_model.INFEASIBLE, cp_model.MODEL_INVALID):
        raise SolverInvariantError(f"CP-SAT status {solver.status_name(status)}")
    if status == cp_model.UNKNOWN:
        return _Outcome(status, {})

    placed: dict[int, _Placed] = {}
    for r, (start, assigned, berths, pilots, tugs) in variables.items():
        if not solver.boolean_value(assigned):
            continue
        berth = next(b for b, v in berths.items() if solver.boolean_value(v))
        pilot = next(p for p, v in pilots.items() if solver.boolean_value(v))
        chosen = tuple(sorted(t for t, v in tugs.items() if solver.boolean_value(v)))
        placed[r] = _Placed(berth, solver.value(start), pilot, chosen)
    return _Outcome(status, placed)


def _workers(
    model: cp_model.CpModel,
    request: _Request,
    workers: Sequence[_Worker],
    start: cp_model.IntVar,
    kind: ResourceKind,
    intervals: dict[_Resource, list[cp_model.IntervalVar]],
) -> dict[int, cp_model.IntVar]:
    """One literal per worker; when true the start lies in one of its shift ranges."""
    chosen = {}
    r = request.request_id
    for worker in workers:
        name = f"{kind}_{r}_{worker.resource_id}"
        literal = model.new_bool_var(name)
        in_range = []
        for index, (first, last) in enumerate(worker.ranges):
            fits = model.new_bool_var(f"{name}_shift{index}")
            model.add(start >= first).only_enforce_if(fits)
            model.add(start <= last).only_enforce_if(fits)
            in_range.append(fits)
        model.add(cp_model.LinearExpr.sum(in_range) == literal)
        intervals[(kind, worker.resource_id)].append(
            model.new_optional_fixed_size_interval_var(
                start, request.duration, literal, f"{name}_iv"
            )
        )
        chosen[worker.resource_id] = literal
    return chosen


def _option(grid: _Grid, request_id: int, placed: _Placed, request: _Request) -> Option:
    return Option(
        request_id=request_id,
        berth_id=placed.berth_id,
        start=grid.at(placed.start),
        end=grid.at(placed.start + request.duration),
        pilot_user_id=placed.pilot_id,
        tug_ids=placed.tug_ids,
    )


def _ranked(
    rank: int, option: Option, placed: _Placed, request: _Request, settings: SolverSettings
) -> RankedOption:
    """The exact CT-18 §5 score of an option (the solver works on a rounded copy)."""
    waiting = Decimal(placed.start - request.lo) / request.span if request.span else Decimal(0)
    resource = Decimal(len(placed.tug_ids)) / request.n_cap if request.n_cap else Decimal(0)
    terms = (
        TermValue(TERM_WAITING_TIME, waiting, settings.weight_waiting_time),
        TermValue(TERM_RESOURCE_COST, resource, settings.weight_resource),
    )
    score = SCORE_SCALE * sum((t.normalised * t.weight for t in terms), Decimal(0))
    return RankedOption(rank, option, score.quantize(SCORE_QUANTUM, ROUND_HALF_UP), terms)


def _verify(
    state: PortState,
    context: FilterContext,
    run: Sequence[int],
    options: Sequence[Option],
    *,
    plan: Sequence[Option] | None = None,
) -> None:
    """B2 again on every emitted option (Architecture §8.4); a failure is a model defect."""
    for option in options:
        others = options if plan is None else plan
        check = check_option(state, option, context, run_request_ids=run, plan=others)
        if not check.passes:
            codes = ", ".join(r.code for r in check.removals)
            raise SolverInvariantError(f"option for request {option.request_id} fails B2: {codes}")


def _result(
    status: SolveStatus,
    solutions: Mapping[int, RequestSolution],
    total: Decimal | None,
    started: float,
    clock: Callable[[], float],
    flags: Sequence[str],
) -> SolveResult:
    return SolveResult(
        status=status,
        requests=tuple(solutions[r] for r in sorted(solutions)),
        objective_value=total,
        solve_time_ms=round((clock() - started) * 1000),
        solver_version=f"ortools {version('ortools')}",
        flags=tuple(flags),
    )
