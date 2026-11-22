"""Part 2 validation suite and baseline harness (AI-062). Every port value is SYNTHETIC.

Property tests run CP-SAT and the FIFO baseline on seeded random instances through the harness
(`tools/evaluate/harness.py`), with a guard so no property can pass on an empty plan. Regression
tests pin a hand-computed indicator table.
"""

import random
from dataclasses import replace
from decimal import Decimal

import pytest

from part2.filter import Option
from part2.outcomes import PlannedOption, RequestOutcome, RequestResult, RunOutcome, SolveOutcome
from part2.state.model import ConfirmedHold, Identified, ResourceKind
from tests.unit.part2.filter.builders import BERTH, HOUR, OTHER_REQUEST, REQUEST, T0, context
from tests.unit.part2.solver.test_cpsat import (
    FOUR_HOURS,
    SETTINGS,
    random_instance,
    requirements,
    two_requests,
)
from tools.evaluate.harness import NOT_DEFINED, Comparison, compare, indicators, plan_of

SEEDS = range(10)


def random_comparison(seed: int) -> tuple[Comparison, object]:
    rng = random.Random(seed)  # noqa: S311 (seeded test data)
    port, ids, times = random_instance(rng, requests=8, berths=2, tugs=4, pilots=2)
    ctx = context(tug_requirements=requirements(port, ids))
    comparison = compare(port, ids, ctx, times, SETTINGS)
    assert comparison.cpsat.placed and comparison.fifo.placed, "the instance must place something"
    return comparison, port


# --- the property suite (backlog criterion 1: "Property suite in CI") -------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_neither_plan_double_books_or_breaks_a_hard_constraint(seed: int) -> None:
    comparison, _ = random_comparison(seed)
    for plan in (comparison.cpsat, comparison.fifo):
        assert (plan.conflicts, plan.violations, plan.feasibility) == (0, 0, Decimal(1))


@pytest.mark.parametrize("seed", SEEDS)
def test_an_optimal_solve_places_at_least_as_many_requests_as_fifo(seed: int) -> None:
    """The objective puts the number of scheduled requests first (AI-055), and FIFO keeps to the
    same hard rules, so an OPTIMAL solve never places fewer."""
    comparison, _ = random_comparison(seed)
    if comparison.cpsat_outcome.solver_status == "OPTIMAL":
        assert comparison.cpsat.placed >= comparison.fifo.placed


@pytest.mark.parametrize("seed", SEEDS)
def test_indicator_ranges_hold(seed: int) -> None:
    comparison, _ = random_comparison(seed)
    for plan in (comparison.cpsat, comparison.fifo):
        assert plan.placed + plan.unplaced == plan.requests == 8
        assert plan.waiting_total_minutes >= 0 and (plan.waiting_max_minutes or 0) >= 0
        assert all(Decimal(0) <= share <= Decimal(1) for share in plan.utilisation.values())
        assert (
            plan.waiting_max_minutes is None
            or plan.waiting_max_minutes * plan.placed >= plan.waiting_total_minutes
        )


def test_the_harness_is_deterministic() -> None:
    first, _ = random_comparison(3)
    again, _ = random_comparison(3)
    assert first.rows() == again.rows()


# --- the indicator table (backlog criterion 2) ---------------------------------------------


def test_hand_computed_table_for_two_requests_sharing_three_tugs() -> None:
    """Two 4 h calls, each needing 2 of the 3 tugs: one starts at T0, the other at T0 + 4 h.
    Horizon 8 days = 11 520 min. Berths 480 / (2 × 11 520), pilots the same, tugs 960 / (3 ×
    11 520)."""
    comparison = compare(two_requests(), [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)
    expected = [
        ("Requests placed", "2 of 2", "2 of 2"),
        ("Conflicts (resource overlaps)", "0", "0"),
        ("Hard-constraint violations (B2)", "0", "0"),
        ("Waiting, total (min)", "240", "240"),
        ("Waiting, mean (min)", "120.0000", "120.0000"),
        ("Waiting, max (min)", "240", "240"),
        ("Utilisation, berths", "0.0208", "0.0208"),
        ("Utilisation, pilots", "0.0208", "0.0208"),
        ("Utilisation, tugs", "0.0278", "0.0278"),
        ("Feasibility (B2)", "1.0000", "1.0000"),
        ("Estimated operational cost", NOT_DEFINED, NOT_DEFINED),
        ("Downstream re-handling", NOT_DEFINED, NOT_DEFINED),
    ]
    assert comparison.rows() == expected
    table = comparison.markdown()
    assert (
        table.startswith("| Indicator | CP-SAT | FIFO |") and table.count("\n") == len(expected) + 2
    )


def test_cost_and_rehandling_are_never_estimated() -> None:
    comparison, _ = random_comparison(0)
    rows = {name: (a, b) for name, a, b in comparison.rows()}
    assert rows["Estimated operational cost"] == (NOT_DEFINED, NOT_DEFINED)
    assert rows["Downstream re-handling"] == (NOT_DEFINED, NOT_DEFINED)


def test_an_unplaceable_run_reports_no_means() -> None:
    port = two_requests(berths=())
    comparison = compare(port, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)
    assert (
        comparison.cpsat.placed,
        comparison.cpsat.waiting_mean_minutes,
        comparison.cpsat.feasibility,
    ) == (0, None, None)
    assert dict((n, a) for n, a, _ in comparison.rows())["Waiting, mean (min)"] == "n/a"


# --- the counters really count (a broken plan is caught) ------------------------------------


def test_a_double_booked_berth_and_a_clash_with_a_fixed_hold_are_counted() -> None:
    port = two_requests()
    comparison = compare(port, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)
    outcome = comparison.cpsat_outcome
    first, second = plan_of(outcome)
    clash = replace(
        second,
        start=first.start,
        end=first.end,
        berth_id=first.berth_id,
        pilot_user_id=first.pilot_user_id,
        tug_ids=(),
    )
    requests = tuple(
        replace(r, options=(replace(r.options[0], option=clash),))
        if r.request_id == second.request_id
        else r
        for r in outcome.requests
    )
    broken = replace(outcome, requests=requests)
    hold = ConfirmedHold(
        ResourceKind.BERTH, first.berth_id, T0, T0 + HOUR, 99, 1, 1, Identified.COMPONENT
    )

    counted = indicators(replace(port, confirmed_holds=(hold,)), broken, context())
    # Berth and pilot shared by the two options (2), and the fixed hold on that berth overlapping
    # both of them (2).
    assert counted.conflicts == 4
    assert counted.violations >= 1 and counted.feasibility is not None and counted.feasibility < 1


def test_utilisation_counts_each_tug_of_an_option() -> None:
    port = two_requests()
    one = Option(REQUEST, BERTH, T0, T0 + 2 * HOUR, None, (41, 42, 43))
    outcome = SolveOutcome(
        RunOutcome.SOLVED,
        "OPTIMAL",
        "AI",
        None,
        None,
        (
            RequestOutcome(
                REQUEST, RequestResult.SOLVED, "INITIAL", (PlannedOption(1, one, None, ()),), ()
            ),
        ),
        None,
        0,
        "test",
        (),
    )
    share = indicators(port, outcome, context()).utilisation
    assert share["TUG"] == (Decimal(3 * 120) / (3 * 11520)).quantize(Decimal("0.0001"))
    assert share["PILOT"] == Decimal(0)  # no pilot on the option
