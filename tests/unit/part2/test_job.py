"""PART2_SOLVE handler helpers (AI-059). Port values are SYNTHETIC (B2 builders)."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from common.runtime.errors import ErrorCategory, JobError
from part2.inputs import ServiceInputs, as_duration, service_times
from part2.job import with_unplanned
from part2.outcomes import RunOutcome, handle_solve
from part2.service_time import ProductivityProfile
from tests.unit.part2.filter.builders import OTHER_REQUEST, REQUEST, TERMINAL, context, window
from tests.unit.part2.solver.test_cpsat import FOUR_HOURS, SETTINGS, two_requests
from tests.unit.part2.test_outcomes import timed_out

PROFILE = ProductivityProfile(
    1, TERMINAL, None, Decimal(25), "MOVES_PER_HOUR", 60, date(2026, 1, 1), None
)


def test_an_untimed_request_turns_a_solved_run_into_a_partial_one() -> None:
    outcome = with_unplanned(
        handle_solve(two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS),
        {OTHER_REQUEST: "No service time (B3): MISSING_MOVES"},
        frozenset(),
    )

    assert outcome.outcome is RunOutcome.PARTIALLY_SOLVED
    left = next(r for r in outcome.requests if r.request_id == OTHER_REQUEST)
    [reason] = left.binding_constraints
    assert (reason.constraint_type_code, reason.detail) == (
        "ENTRY_WINDOW",
        "No service time (B3): MISSING_MOVES",
    )
    assert [r.request_id for r in outcome.requests] == [REQUEST, OTHER_REQUEST]


def test_a_fifo_run_stays_fifo_and_a_replan_request_keeps_its_purpose() -> None:
    fifo = handle_solve(
        two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out
    )
    outcome = with_unplanned(fifo, {OTHER_REQUEST: "MISSING_MOVES"}, frozenset({OTHER_REQUEST}))
    assert outcome.outcome is RunOutcome.FIFO_FALLBACK and outcome.solver_status == "ERROR"
    assert (
        next(r for r in outcome.requests if r.request_id == OTHER_REQUEST).purpose == "DELAY_REPLAN"
    )


def test_nothing_placed_is_no_feasible_plan() -> None:
    port = two_requests()
    empty = handle_solve(
        replace(port, confirmed_windows=(window(OTHER_REQUEST),)),
        [REQUEST],
        context(),
        FOUR_HOURS,
        SETTINGS,
    )
    assert empty.outcome is RunOutcome.NO_FEASIBLE_PLAN
    outcome = with_unplanned(empty, {OTHER_REQUEST: "MISSING_MOVES"}, frozenset())
    assert (outcome.outcome, outcome.solver_status, outcome.objective_value) == (
        RunOutcome.NO_FEASIBLE_PLAN,
        "INFEASIBLE",
        None,
    )


def test_no_timed_request_at_all_is_no_feasible_plan_without_a_solve() -> None:
    outcome = with_unplanned(None, {REQUEST: "BASIS_UNDEFINED"}, frozenset())
    assert (outcome.outcome, outcome.solver_status, outcome.source) == (
        RunOutcome.NO_FEASIBLE_PLAN,
        "INFEASIBLE",
        "AI",
    )
    assert outcome.solver_version.startswith("ortools ")


def test_nothing_to_add_returns_the_run_unchanged() -> None:
    run = handle_solve(two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS)
    assert with_unplanned(run, {}, frozenset()) is run


def test_b3_times_each_request_on_the_port_local_date_of_its_window() -> None:
    late = datetime(2026, 1, 5, 23, 30, tzinfo=UTC)  # already 6 January in Cairo (UTC+2)
    port = two_requests(
        confirmed_windows=(
            window(REQUEST, late, late.replace(day=6, hour=5)),
            window(OTHER_REQUEST),
        )
    )
    profiles = (replace(PROFILE, valid_from=date(2026, 1, 6)),)  # valid only from 6 January
    inputs = ServiceInputs("EGDAM", profiles, frozenset({REQUEST, OTHER_REQUEST}))
    results = service_times(port, inputs, {"CONTAINER": 21})

    assert results[REQUEST].p50_hours is not None  # local date 6 January: the profile applies
    assert results[OTHER_REQUEST].excluded_reason == "NO_VALID_PROFILE"  # 5 January
    assert results[REQUEST].p50_hours == Decimal(
        "1.00"
    )  # no loading count, no discharge: 0 moves + 60 min


def test_a_request_without_an_active_baplie_is_missing_moves() -> None:
    inputs = ServiceInputs("EGDAM", (PROFILE,), frozenset())
    assert (
        service_times(two_requests(), inputs, {"CONTAINER": 21})[REQUEST].excluded_reason
        == "MISSING_MOVES"
    )


def test_an_unknown_vessel_type_is_data_unavailable() -> None:
    with pytest.raises(JobError) as caught:
        service_times(two_requests(), ServiceInputs("EGDAM", (PROFILE,), frozenset()), {})
    assert caught.value.category is ErrorCategory.DATA_UNAVAILABLE


def test_hours_become_whole_seconds() -> None:
    assert as_duration(Decimal("1.40")).total_seconds() == 5040
