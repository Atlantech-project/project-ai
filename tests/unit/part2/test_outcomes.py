"""Solver outcome handling (AI-056). Every port value is SYNTHETIC (B2 builders)."""

import random
import time
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest

from part2.filter import Code, check_plan
from part2.outcomes import (
    SOLVER_ERROR,
    TIMEOUT,
    RequestResult,
    RunOutcome,
    SolveOutcome,
    handle_solve,
)
from part2.solver import SolveResult, SolverInvariantError, SolveStatus
from part2.state.model import Shift
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_REQUEST,
    REQUEST,
    T0,
    berth,
    context,
    request,
    shift,
    state,
    tug,
    window,
)
from tests.unit.part2.solver.test_cpsat import (
    FOUR_HOURS,
    SETTINGS,
    random_instance,
    requirements,
    two_requests,
)


def by_id(outcome: SolveOutcome, request_id: int = REQUEST) -> Any:
    return next(r for r in outcome.requests if r.request_id == request_id)


def timed_out(*_args: Any, **_kwargs: Any) -> SolveResult:
    return SolveResult(SolveStatus.TIMEOUT, (), None, 10_000, "ortools test", ())


def broken(*_args: Any, **_kwargs: Any) -> SolveResult:
    raise SolverInvariantError("option for request 1 fails B2: BERTH_OCCUPIED")


def codes(outcome: SolveOutcome, request_id: int = REQUEST) -> list[str]:
    return [b.constraint_type_code for b in by_id(outcome, request_id).binding_constraints]


# --- CP-SAT solved ----------------------------------------------------------------------------


def test_solved_run_is_ai_with_ranked_options() -> None:
    outcome = handle_solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert outcome.outcome is RunOutcome.SOLVED
    assert (outcome.solver_status, outcome.source, outcome.error_category) == (
        "OPTIMAL",
        "AI",
        None,
    )
    result = by_id(outcome)
    assert result.outcome is RequestResult.SOLVED
    assert [o.rank for o in result.options] == [1, 2]
    assert result.options[0].objective_score == Decimal("666.6667")
    detail = outcome.result_detail()
    assert detail["outcome"] == "SOLVED" and detail["failure_reason"] is None
    assert detail["requests"] == [
        {
            "request_id": REQUEST,
            "outcome": "SOLVED",
            "purpose": "INITIAL",
            "recommendation_id": None,
            "options_count": 2,
            "binding_constraints": [],
        }
    ]


def test_partially_solved_names_the_busy_berth() -> None:
    narrow = (window(REQUEST, T0, T0 + HOUR), window(OTHER_REQUEST, T0, T0 + HOUR))
    port = two_requests(berths=(berth(BERTH),), confirmed_windows=narrow)
    outcome = handle_solve(port, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert outcome.outcome is RunOutcome.PARTIALLY_SOLVED
    left = next(r for r in outcome.requests if r.outcome is RequestResult.NO_FEASIBLE_PLAN)
    # The other request holds the only berth and two of the three tugs (this one needs two).
    reasons = [b.constraint_type_code for b in left.binding_constraints]
    assert reasons == [Code.BERTH_OCCUPIED, Code.TUG_UNAVAILABLE]
    assert left.options == ()


def test_infeasible_run_has_binding_constraints_and_never_fifo() -> None:
    calls: list[int] = []

    def counted(*args: Any, **kwargs: Any) -> SolveResult:
        from part2.solver import solve

        calls.append(1)
        return solve(*args, **kwargs)

    port = state(requests=(request(loa=Decimal("400.00")),))
    outcome = handle_solve(port, [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=counted)

    assert outcome.outcome is RunOutcome.NO_FEASIBLE_PLAN
    assert outcome.solver_status == "INFEASIBLE"
    assert outcome.source == "AI"  # FIFO did not run
    assert outcome.objective_value is None
    assert by_id(outcome).options == ()
    assert Code.MAX_LOA in codes(outcome)
    assert calls == [1]


def test_window_without_a_start_minute_is_entry_window() -> None:
    tiny = window(start=T0 + timedelta(seconds=10), end=T0 + timedelta(seconds=50))
    outcome = handle_solve(
        state(confirmed_windows=(tiny,)), [REQUEST], context(), FOUR_HOURS, SETTINGS
    )

    assert codes(outcome) == [Code.ENTRY_WINDOW]


def test_resources_free_only_at_different_times_name_all_three() -> None:
    from part2.state.model import ConfirmedHold, Identified, ResourceKind

    # The pilot works only [T0, T0+5h); the berths are held until T0+2h: a 4 h job never fits.
    pilots = (Shift(31, 1, T0, T0 + 5 * HOUR, True), Shift(32, 2, T0, T0 + 5 * HOUR, True))
    holds = tuple(
        ConfirmedHold(
            ResourceKind.BERTH, b, T0 - HOUR, T0 + 2 * HOUR, 99, 1, 1, Identified.COMPONENT
        )
        for b in (11, 12)
    )
    port = state(pilot_shifts=pilots, confirmed_holds=holds)
    outcome = handle_solve(port, [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert outcome.outcome is RunOutcome.NO_FEASIBLE_PLAN
    assert codes(outcome) == sorted(
        [Code.BERTH_OCCUPIED, Code.PILOT_UNAVAILABLE, Code.TUG_UNAVAILABLE]
    )


def test_replan_requests_get_delay_replan_purpose() -> None:
    outcome = handle_solve(
        state(), [REQUEST], context(), FOUR_HOURS, SETTINGS, replan_request_ids=[REQUEST]
    )
    assert by_id(outcome).purpose == "DELAY_REPLAN"


# --- technical failure: FIFO -------------------------------------------------------------------


def test_forced_timeout_yields_fifo_with_reason() -> None:
    outcome = handle_solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out)

    assert outcome.outcome is RunOutcome.FIFO_FALLBACK
    assert (outcome.solver_status, outcome.source, outcome.error_category) == (
        "ERROR",
        "FIFO",
        TIMEOUT,
    )
    detail = outcome.result_detail()
    assert detail["failure_reason"] == {
        "error_category": "TIMEOUT",
        "message": "CP-SAT reached solver_time_limit_seconds (10) without a feasible solution",
    }
    result = by_id(outcome)
    assert result.outcome is RequestResult.FIFO_FALLBACK
    assert len(result.options) == 1 and result.options[0].objective_score is None
    assert result.options[0].option.start == T0


def test_solver_defect_yields_fifo_with_solver_error() -> None:
    outcome = handle_solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=broken)

    assert outcome.error_category == SOLVER_ERROR
    assert "fails B2" in (outcome.failure_message or "")


def test_fifo_follows_arrival_order() -> None:
    late = request(requested_eta=T0 + HOUR)
    early = request(request_id=OTHER_REQUEST, vessel_id=OTHER_REQUEST, requested_eta=T0)
    port = two_requests(requests=(late, early), berths=(berth(BERTH),))
    outcome = handle_solve(
        port, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out
    )

    assert by_id(outcome, OTHER_REQUEST).options[0].option.start == T0
    assert by_id(outcome, REQUEST).options[0].option.start == T0 + 4 * HOUR


def test_fifo_takes_the_fewest_tugs_meeting_bollard_pull() -> None:
    port = state(tugs=(tug(41), replace(tug(42), tug_power=Decimal("90.00")), tug(43)))
    need = replace(context().tug_requirements[REQUEST], n_min=1, n_cap=2, bp_req=80)
    ctx = context(tug_requirements={REQUEST: need})
    outcome = handle_solve(port, [REQUEST], ctx, FOUR_HOURS, SETTINGS, solve_fn=timed_out)

    assert by_id(outcome).options[0].option.tug_ids == (42,)


def test_fifo_request_that_fits_nowhere_gets_reasons() -> None:
    port = state(pilot_shifts=(shift(99),))  # no pilot has a shift
    outcome = handle_solve(port, [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out)

    assert by_id(outcome).outcome is RequestResult.NO_FEASIBLE_PLAN
    assert codes(outcome) == [Code.PILOT_UNAVAILABLE]


def test_fifo_filtered_request_keeps_b2_reasons() -> None:
    port = state(requests=(request(loa=Decimal("400.00")),))
    outcome = handle_solve(port, [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out)

    assert Code.MAX_LOA in codes(outcome)


@pytest.mark.parametrize("seed", range(6))
def test_fifo_output_passes_the_filter(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 (seeded test data)
    port, ids, times = random_instance(rng, requests=8, berths=2, tugs=4, pilots=2)
    ctx = context(tug_requirements=requirements(ids))
    outcome = handle_solve(port, ids, ctx, times, SETTINGS, solve_fn=timed_out)

    plan = [o.options[0].option for o in outcome.requests if o.options]
    assert all(check.passes for check in check_plan(port, plan, ctx))
    assert all(o.binding_constraints for o in outcome.requests if not o.options)


def test_total_time_stays_under_twelve_seconds() -> None:
    rng = random.Random(3)  # noqa: S311 (seeded test data)
    port, ids, times = random_instance(rng, requests=40, berths=4, tugs=8, pilots=4)
    ctx = context(tug_requirements=requirements(ids))
    settings = replace(SETTINGS, time_limit_seconds=10)
    began = time.monotonic()
    handle_solve(port, ids, ctx, times, settings)
    handle_solve(port, ids, ctx, times, settings, solve_fn=timed_out)

    assert time.monotonic() - began < 12
