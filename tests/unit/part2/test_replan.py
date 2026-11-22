"""B7 re-planning inputs and STARTED components fixed in the solve (AI-059).

Every port value is SYNTHETIC (B2 builders). A pin is what a delay re-plan keeps (Architecture
§8.13): the started components' resources and interval.
"""

import random
from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from common.runtime.errors import ErrorCategory, JobError
from part2.filter import Code, check_plan
from part2.outcomes import RequestResult, SolveOutcome, handle_solve
from part2.replan import pins_for, scope_from_payload
from part2.solver import Pin, solve
from part2.state.model import PortState, ResourceKind, StartedComponent
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_BERTH,
    OTHER_PILOT,
    OTHER_REQUEST,
    REQUEST,
    T0,
    TUG_A,
    TUG_B,
    TUG_C,
    context,
    requirement,
    tug,
)
from tests.unit.part2.solver.test_cpsat import (
    FOUR_HOURS,
    SETTINGS,
    random_instance,
    two_requests,
)
from tests.unit.part2.test_outcomes import timed_out

LATE = T0 + 2 * HOUR  # the solver's own choice is T0; a pin at T0 + 2 h shows it is kept


def eligible(port: PortState, ids: list[int]) -> dict[int, Any]:
    """Tug requirements whose eligible tugs are the instance's own (`random_instance` tugs)."""
    tugs = frozenset(t.id for t in port.tugs)
    return {r: replace(requirement(n_min=1), n_cap=2, bp_req=50, eligible_tugs=tugs) for r in ids}


def started(
    kind: ResourceKind,
    resource_id: int,
    start: Any = LATE,
    end: Any = LATE + 4 * HOUR,
    request_id: int = REQUEST,
    status: str = "STARTED",
) -> StartedComponent:
    return StartedComponent(kind, resource_id, start, end, request_id, 300, resource_id, status)


def replan(
    pins: dict[int, Pin],
    port: PortState | None = None,
    **kwargs: Any,
) -> SolveOutcome:
    port = port or two_requests()
    return handle_solve(
        port,
        [REQUEST, OTHER_REQUEST],
        context(),
        FOUR_HOURS,
        SETTINGS,
        replan_request_ids=list(pins) or [REQUEST],
        pins=pins,
        **kwargs,
    )


def options_of(outcome: SolveOutcome, request_id: int = REQUEST) -> Any:
    return next(r for r in outcome.requests if r.request_id == request_id).options


# --- scope from the CT-10 triggers ----------------------------------------------------------


def test_scope_follows_the_ct10_example() -> None:
    payload = {
        "trigger_type": "REPLAN",
        "triggers": [
            {"trigger_type": "NEW_REQUEST", "berthing_request_ids": [1560, 1561]},
            {
                "trigger_type": "RESOURCE_CHANGE",
                "berthing_request_ids": [1550, 1553],
                "changed_resources": [{"type": "TUG", "id": 7}],
            },
            {"trigger_type": "MANUAL", "berthing_request_ids": [1548], "requested_by_user_id": 41},
            {"trigger_type": "REPLAN", "berthing_request_ids": [1540], "operational_plan_id": 311},
        ],
    }
    scope = scope_from_payload(payload)

    assert scope.request_ids == (1540, 1548, 1550, 1553, 1560, 1561)
    assert scope.replan_request_ids == {1540}
    assert scope.trigger_of[1548] == "MANUAL" and scope.trigger_of[1553] == "RESOURCE_CHANGE"


@pytest.mark.parametrize(
    ("triggers", "message"),
    [
        (
            [
                {"trigger_type": "NEW_REQUEST", "berthing_request_ids": [1]},
                {"trigger_type": "MANUAL", "berthing_request_ids": [1]},
            ],
            "more than one trigger entry",
        ),
        ([{"trigger_type": "REPLAN", "berthing_request_ids": [1, 2]}], "exactly one request"),
        ([{"trigger_type": "LATER", "berthing_request_ids": [1]}], "unknown trigger_type"),
        ([], "names no request"),
    ],
)
def test_scope_rules_that_the_schema_cannot_check(triggers: list[Any], message: str) -> None:
    with pytest.raises(JobError, match=message) as caught:
        scope_from_payload({"triggers": triggers})
    assert caught.value.category is ErrorCategory.INVALID_ENVELOPE


# --- pins from started components -----------------------------------------------------------


def test_a_pin_keeps_every_started_part_and_only_replan_requests_get_one() -> None:
    port = replace(
        two_requests(),
        started_components=(
            started(ResourceKind.BERTH, OTHER_BERTH),
            started(ResourceKind.PILOT, OTHER_PILOT, status="DONE"),
            started(ResourceKind.TUG, TUG_C),
            started(ResourceKind.TUG, TUG_A, request_id=OTHER_REQUEST),
        ),
    )
    assert pins_for(port, [REQUEST]) == {
        REQUEST: Pin(LATE, LATE + 4 * HOUR, OTHER_BERTH, OTHER_PILOT, frozenset({TUG_C}))
    }
    assert pins_for(port, []) == {}


@pytest.mark.parametrize(
    ("parts", "message"),
    [
        (
            (
                started(ResourceKind.BERTH, BERTH),
                started(ResourceKind.TUG, TUG_C, end=LATE + 5 * HOUR),
            ),
            "different intervals",
        ),
        (
            (started(ResourceKind.BERTH, BERTH), started(ResourceKind.BERTH, OTHER_BERTH)),
            "more than one begun berth",
        ),
        ((started(ResourceKind.BERTH, BERTH, start=LATE + timedelta(seconds=30)),), "whole minute"),
    ],
)
def test_begun_parts_that_one_option_cannot_hold_fail_the_run(
    parts: tuple[StartedComponent, ...], message: str
) -> None:
    port = replace(two_requests(), started_components=parts)
    with pytest.raises(JobError, match=message) as caught:
        pins_for(port, [REQUEST])
    assert caught.value.category is ErrorCategory.PRECONDITION_FAILED


# --- STARTED components unchanged in the DELAY_REPLAN output (backlog criterion 3) ----------


def test_without_a_pin_the_solver_would_move_the_request() -> None:
    first = options_of(replan({}))[0].option
    assert first.start == T0  # so the pinned tests below show the pin, not the solver's choice


def test_a_started_berth_pilot_and_tug_stay_unchanged() -> None:
    pin = Pin(LATE, LATE + 4 * HOUR, OTHER_BERTH, OTHER_PILOT, frozenset({TUG_C}))
    outcome = replan({REQUEST: pin})

    request = next(r for r in outcome.requests if r.request_id == REQUEST)
    assert request.outcome is RequestResult.SOLVED and request.purpose == "DELAY_REPLAN"
    assert [pin.honoured_by(o.option) for o in request.options] == [True]  # one berth: one option
    first = request.options[0].option
    assert (first.start, first.end, first.berth_id, first.pilot_user_id) == (
        LATE,
        LATE + 4 * HOUR,
        OTHER_BERTH,
        OTHER_PILOT,
    )
    assert TUG_C in first.tug_ids and len(first.tug_ids) >= 2  # the rest is re-planned
    assert all(c.passes for c in check_plan(two_requests(), [first], context()))


def test_the_started_interval_wins_over_the_b3_estimate() -> None:
    pin = Pin(LATE, LATE + 3 * HOUR + 30 * timedelta(minutes=1), tug_ids=frozenset({TUG_A}))
    first = options_of(replan({REQUEST: pin}))[0].option
    assert (first.start, first.end) == (pin.start, pin.end)


def test_alternatives_keep_the_pin_when_the_berth_is_free() -> None:
    pin = Pin(LATE, LATE + 4 * HOUR, pilot_user_id=OTHER_PILOT)
    options = options_of(replan({REQUEST: pin}))
    assert len(options) == 2  # both berths, the same started interval and pilot
    assert all(pin.honoured_by(o.option) for o in options)
    assert {o.option.berth_id for o in options} == {BERTH, OTHER_BERTH}


def test_a_started_tug_that_is_now_out_of_service_is_never_swapped() -> None:
    port = two_requests(tugs=(tug(TUG_A), tug(TUG_B), tug(TUG_C, status="MAINTENANCE")))
    pin = Pin(LATE, LATE + 4 * HOUR, tug_ids=frozenset({TUG_C}))
    outcome = replan({REQUEST: pin}, port)

    request = next(r for r in outcome.requests if r.request_id == REQUEST)
    assert request.outcome is RequestResult.NO_FEASIBLE_PLAN and request.options == ()
    assert request.binding_constraints  # CT-10: a reason is always given


def test_a_started_interval_outside_the_confirmed_window_gives_no_option() -> None:
    pin = Pin(T0 + 7 * HOUR, T0 + 11 * HOUR)  # the builders' window ends at T0 + 6 h
    outcome = replan({REQUEST: pin})
    request = next(r for r in outcome.requests if r.request_id == REQUEST)
    assert request.outcome is RequestResult.NO_FEASIBLE_PLAN
    assert [b.constraint_type_code for b in request.binding_constraints] == [Code.ENTRY_WINDOW]


def test_fifo_keeps_the_pin_too() -> None:
    pin = Pin(LATE, LATE + 4 * HOUR, OTHER_BERTH, OTHER_PILOT, frozenset({TUG_C}))
    outcome = replan({REQUEST: pin}, solve_fn=timed_out)

    assert outcome.source == "FIFO"
    [option] = options_of(outcome)
    assert pin.honoured_by(option.option)
    assert all(c.passes for c in check_plan(two_requests(), [option.option], context()))


def test_end_to_end_from_the_snapshot_started_components() -> None:
    port = replace(
        two_requests(),
        started_components=(
            started(ResourceKind.PILOT, OTHER_PILOT),
            started(ResourceKind.TUG, TUG_B),
        ),
    )
    pins = pins_for(port, [REQUEST])
    outcome = replan(pins, port)
    assert all(pins[REQUEST].honoured_by(o.option) for o in options_of(outcome))


@pytest.mark.parametrize("seed", range(8))
def test_re_solving_with_option_one_pinned_keeps_it_on_random_instances(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 (seeded test data)
    port, ids, times = random_instance(rng, requests=6, berths=2, tugs=4, pilots=2)
    ctx = context(tug_requirements=eligible(port, ids))
    first = handle_solve(port, ids, ctx, times, SETTINGS)
    placed = [r for r in first.requests if r.options]
    assert placed, "the instance must place something, or the test checks nothing"
    target = placed[0]
    o = target.options[0].option
    pin = Pin(o.start, o.end, o.berth_id, o.pilot_user_id, frozenset(o.tug_ids[:1]))

    again = handle_solve(
        port, ids, ctx, times, SETTINGS, replan_request_ids=[target.request_id],
        pins={target.request_id: pin},
    )  # fmt: skip
    kept = next(r for r in again.requests if r.request_id == target.request_id)
    assert kept.options and all(pin.honoured_by(x.option) for x in kept.options)
    plan = [r.options[0].option for r in again.requests if r.options]
    assert all(c.passes for c in check_plan(port, plan, ctx))


# --- guards ---------------------------------------------------------------------------------


def test_pins_are_only_for_replan_requests_of_the_run() -> None:
    pin = Pin(LATE, LATE + 4 * HOUR)
    with pytest.raises(ValueError, match="not REPLAN"):
        handle_solve(
            two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS, pins={REQUEST: pin}
        )
    with pytest.raises(ValueError, match="outside the run"):
        solve(two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS, pins={OTHER_REQUEST: pin})


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (LATE, LATE, "after its start"),
        (LATE.replace(tzinfo=None), LATE + HOUR, "timezone-aware"),
        (LATE + timedelta(seconds=1), LATE + HOUR, "whole minute"),
    ],
)
def test_pin_values(start: Any, end: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Pin(start, end)
