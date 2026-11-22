"""Part 2 baseline-comparison harness (AI-062): the same run through CP-SAT and through FIFO,
with an indicator table for each.

The harness takes what every scenario becomes before a solve: the AI-050 snapshot, the B2
context and B3's service times. It reuses AI-056's `handle_solve` for both plans (FIFO is the
path a solver timeout takes), B2's `check_plan`, and `overlaps` from the availability rules, so
it measures the engine as the worker runs it. It reads and writes nothing.

Indicators (Master_Context "Evaluation"; the backlog names conflicts, waiting and utilisation):

- **Placed / unplaced requests.**
- **Conflicts:** pairs of intervals on the same berth, pilot or tug that overlap, among the
  plan's options and against the snapshot's fixed holds (confirmed plans, other requests'
  pending option 1). **Hard-constraint violations:** options of the plan that B2 rejects.
- **Waiting:** whole minutes from the confirmed window's start to the option's start, the minutes
  AI-055's `WAITING_TIME` term counts; total, mean and maximum over placed requests.
- **Utilisation:** per resource kind, the minutes the plan books ÷ (resources of that kind in the
  snapshot × the run horizon in minutes).
- **Feasibility:** share of placed requests whose option passes B2.
- **Estimated operational cost** and **downstream re-handling:** no formula exists in any source
  here (R16), so they are reported as not defined, never estimated.

The plan of a run is option 1 of each request: the option that holds resources (DEC-32 rule 3).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from typing import Any, Final

from part2.filter import FilterContext, Option, check_plan
from part2.filter.pairing import confirmed_window
from part2.outcomes import SolveOutcome, handle_solve
from part2.solver import SolveResult, SolverSettings, SolveStatus
from part2.state.availability import overlaps, without_requests
from part2.state.model import ConfirmedHold, PendingHold, PortState, ResourceKind

MINUTE: Final = timedelta(minutes=1)
QUANTUM: Final = Decimal("0.0001")
NOT_DEFINED: Final = "not defined (R16)"


@dataclass(frozen=True)
class Indicators:
    """One plan's indicators."""

    requests: int
    placed: int
    conflicts: int
    violations: int
    waiting_total_minutes: int
    waiting_mean_minutes: Decimal | None  # None when nothing is placed
    waiting_max_minutes: int | None
    utilisation: Mapping[str, Decimal]  # ResourceKind value → share in [0, 1]
    feasibility: Decimal | None  # placed options passing B2 ÷ placed; None when nothing is placed

    @property
    def unplaced(self) -> int:
        return self.requests - self.placed


@dataclass(frozen=True)
class Comparison:
    cpsat: Indicators
    fifo: Indicators
    cpsat_outcome: SolveOutcome
    fifo_outcome: SolveOutcome

    def rows(self) -> list[tuple[str, str, str]]:
        """The indicator table: (indicator, CP-SAT, FIFO)."""
        a, b = self.cpsat, self.fifo
        rows = [
            ("Requests placed", f"{a.placed} of {a.requests}", f"{b.placed} of {b.requests}"),
            ("Conflicts (resource overlaps)", str(a.conflicts), str(b.conflicts)),
            ("Hard-constraint violations (B2)", str(a.violations), str(b.violations)),
            ("Waiting, total (min)", str(a.waiting_total_minutes), str(b.waiting_total_minutes)),
            ("Waiting, mean (min)", _show(a.waiting_mean_minutes), _show(b.waiting_mean_minutes)),
            ("Waiting, max (min)", _show(a.waiting_max_minutes), _show(b.waiting_max_minutes)),
        ]
        for kind in ResourceKind:
            rows.append(
                (
                    f"Utilisation, {kind.value.lower()}s",
                    _show(a.utilisation[kind.value]),
                    _show(b.utilisation[kind.value]),
                )
            )
        rows += [
            ("Feasibility (B2)", _show(a.feasibility), _show(b.feasibility)),
            ("Estimated operational cost", NOT_DEFINED, NOT_DEFINED),
            ("Downstream re-handling", NOT_DEFINED, NOT_DEFINED),
        ]
        return rows

    def markdown(self) -> str:
        lines = ["| Indicator | CP-SAT | FIFO |", "| --- | --- | --- |"]
        lines += [f"| {name} | {cpsat} | {fifo} |" for name, cpsat, fifo in self.rows()]
        return "\n".join(lines) + "\n"


def _as_timeout(*_args: Any, **_kwargs: Any) -> SolveResult:
    """The solver result that makes AI-056 take its FIFO path (a timeout before any solution)."""
    return SolveResult(SolveStatus.TIMEOUT, (), None, 0, "baseline", ())


def compare(
    state: PortState,
    request_ids: Sequence[int],
    context: FilterContext,
    service_times: Mapping[int, timedelta],
    settings: SolverSettings,
) -> Comparison:
    """CP-SAT and the FIFO baseline on the same run, with their indicators."""
    cpsat = handle_solve(state, request_ids, context, service_times, settings)
    fifo = handle_solve(state, request_ids, context, service_times, settings, solve_fn=_as_timeout)
    return Comparison(
        indicators(state, cpsat, context), indicators(state, fifo, context), cpsat, fifo
    )


def plan_of(outcome: SolveOutcome) -> list[Option]:
    """Option 1 of each placed request: the option that holds resources (DEC-32 rule 3)."""
    return [r.options[0].option for r in outcome.requests if r.options]


def indicators(state: PortState, outcome: SolveOutcome, context: FilterContext) -> Indicators:
    plan = plan_of(outcome)
    run = [r.request_id for r in outcome.requests]
    waits = [_waiting_minutes(state, o) for o in plan]
    checks = check_plan(state, plan, context) if plan else ()
    passing = sum(1 for c in checks if c.passes)
    return Indicators(
        requests=len(outcome.requests),
        placed=len(plan),
        conflicts=_conflicts(state, plan, run),
        violations=len(plan) - passing,
        waiting_total_minutes=sum(waits),
        waiting_mean_minutes=_ratio(Decimal(sum(waits)), len(waits)),
        waiting_max_minutes=max(waits) if waits else None,
        utilisation=_utilisation(state, plan),
        feasibility=_ratio(Decimal(passing), len(plan)),
    )


def _intervals(option: Option) -> list[tuple[ResourceKind, int]]:
    parts = [(ResourceKind.BERTH, option.berth_id)]
    if option.pilot_user_id is not None:
        parts.append((ResourceKind.PILOT, option.pilot_user_id))
    parts += [(ResourceKind.TUG, t) for t in option.tug_ids]
    return parts


def _conflicts(state: PortState, plan: Sequence[Option], run: Sequence[int]) -> int:
    count = 0
    for a, b in combinations(plan, 2):
        if overlaps(a.start, a.end, b.start, b.end):
            count += len(set(_intervals(a)) & set(_intervals(b)))
    fixed: list[ConfirmedHold | PendingHold] = [
        *without_requests(state.confirmed_holds, run),
        *without_requests(state.pending_holds, run),
    ]
    for option in plan:
        used = set(_intervals(option))
        count += sum(
            1
            for hold in fixed
            if (hold.kind, hold.resource_id) in used
            and overlaps(option.start, option.end, hold.start, hold.end)
        )
    return count


def _waiting_minutes(state: PortState, option: Option) -> int:
    window = confirmed_window(state, option.request_id)
    if window is None:  # every emitted option passed B2, which needs a window
        raise ValueError(f"option of request {option.request_id} has no confirmed window")
    return (option.start - window.start) // MINUTE


def _utilisation(state: PortState, plan: Sequence[Option]) -> dict[str, Decimal]:
    horizon = Decimal((state.horizon_end - state.horizon_start) // MINUTE)
    sizes = {
        ResourceKind.BERTH: len(state.berths),
        ResourceKind.PILOT: len(state.pilots),
        ResourceKind.TUG: len(state.tugs),
    }
    booked = dict.fromkeys(ResourceKind, 0)
    for option in plan:
        minutes = (option.end - option.start) // MINUTE
        for kind, _resource in _intervals(option):
            booked[kind] += minutes
    return {
        kind.value: (
            Decimal(0)
            if not sizes[kind] or not horizon
            else (Decimal(booked[kind]) / (sizes[kind] * horizon)).quantize(QUANTUM, ROUND_HALF_UP)
        )
        for kind in ResourceKind
    }


def _ratio(numerator: Decimal, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return (numerator / denominator).quantize(QUANTUM, ROUND_HALF_UP)


def _show(value: object) -> str:
    return "n/a" if value is None else str(value)
