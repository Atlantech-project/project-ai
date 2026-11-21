"""B5 CP-SAT tests (AI-055). Every port value here is SYNTHETIC (see the B2 builders)."""

import random
import time
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from ortools.sat.python import cp_model

from common.config import PortSettings
from common.db.read_models import Tugboat
from part2.filter import Code, Option
from part2.solver import (
    FLAG_ALTERNATIVES_TIME_LIMIT,
    TERM_RESOURCE_COST,
    TERM_WAITING_TIME,
    SolveResult,
    SolverSettings,
    SolveStatus,
    Unscheduled,
    cpsat,
    solve,
)
from part2.state.availability import overlaps
from part2.state.model import (
    ConfirmedHold,
    Identified,
    PendingHold,
    PortState,
    ResourceKind,
    Shift,
)
from part2.tugs import TugRequirement
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_BERTH,
    OTHER_PILOT,
    OTHER_REQUEST,
    PILOT,
    REQUEST,
    T0,
    TUG_A,
    TUG_B,
    TUG_C,
    berth,
    context,
    master,
    request,
    requirement,
    shift,
    state,
    tug,
    window,
)

SETTINGS = SolverSettings(
    time_limit_seconds=10,
    options_per_request=3,
    equivalence_pct=Decimal(10),
    weight_waiting_time=Decimal("1.0"),
    weight_resource=Decimal("1.0"),
)
FOUR_HOURS = {REQUEST: 4 * HOUR, OTHER_REQUEST: 4 * HOUR}


def two_requests(**changes: object) -> PortState:
    base = state(
        requests=(request(), request(request_id=OTHER_REQUEST, vessel_id=OTHER_REQUEST)),
        confirmed_windows=(window(REQUEST), window(OTHER_REQUEST)),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def first(result: SolveResult, request_id: int = REQUEST) -> Option:
    solution = next(s for s in result.requests if s.request_id == request_id)
    assert solution.options, solution
    return solution.options[0].option


def berth_hold(
    berth_id: int, start: timedelta, end: timedelta, request_id: int = 99
) -> ConfirmedHold:
    return ConfirmedHold(
        ResourceKind.BERTH, berth_id, T0 + start, T0 + end, request_id, 1, 1, Identified.COMPONENT
    )


# --- single request -------------------------------------------------------------------------


def test_single_request_starts_at_window_start_with_fewest_tugs() -> None:
    result = solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert result.status is SolveStatus.OPTIMAL
    option = first(result)
    assert option.start == T0
    assert option.end == T0 + 4 * HOUR
    assert option.pilot_user_id in (PILOT, OTHER_PILOT)
    assert len(option.tug_ids) == 2  # N_min; RESOURCE_COST rises with each tug
    ranked = result.requests[0].options[0]
    assert ranked.rank == 1
    # 1000 × (1.0 × 0 waiting + 1.0 × 2/3 tugs)
    assert ranked.objective_score == Decimal("666.6667")
    assert {t.code for t in ranked.terms} == {TERM_WAITING_TIME, TERM_RESOURCE_COST}
    assert result.objective_value == Decimal("666.6667")
    assert result.solver_version.startswith("ortools ")


def test_confirmed_berth_hold_pushes_the_start() -> None:
    holds = (
        berth_hold(BERTH, timedelta(0), 3 * HOUR),
        berth_hold(OTHER_BERTH, timedelta(0), 3 * HOUR),
    )
    result = solve(state(confirmed_holds=holds), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert first(result).start == T0 + 3 * HOUR


def test_free_berth_beats_waiting() -> None:
    holds = (berth_hold(BERTH, timedelta(0), 3 * HOUR),)
    result = solve(state(confirmed_holds=holds), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    option = first(result)
    assert (option.berth_id, option.start) == (OTHER_BERTH, T0)


def test_own_pending_hold_is_dropped() -> None:
    """DEC-32 rule 5: the run's previous recommendation becomes REPLACED and holds nothing."""
    pending = tuple(
        PendingHold(ResourceKind.BERTH, b, T0, T0 + 6 * HOUR, REQUEST, 5, "PENDING_REVIEW", 7, 1)
        for b in (BERTH, OTHER_BERTH)
    )
    result = solve(state(pending_holds=pending), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert first(result).start == T0


def test_other_requests_pending_option_one_holds_its_pilot() -> None:
    pending = tuple(
        PendingHold(ResourceKind.PILOT, p, T0, T0 + 2 * HOUR, 77, 5, "PENDING_REVIEW", 7, 1)
        for p in (PILOT, OTHER_PILOT)
    )
    result = solve(state(pending_holds=pending), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert first(result).start == T0 + 2 * HOUR


def test_pilot_shift_must_cover_the_whole_interval() -> None:
    shifts = (
        Shift(PILOT, 1, T0, T0 + 3 * HOUR, True),  # too short for a 4-hour job
        Shift(OTHER_PILOT, 2, T0 + HOUR, T0 + 8 * HOUR, True),
    )
    result = solve(state(pilot_shifts=shifts), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    option = first(result)
    assert option.pilot_user_id == OTHER_PILOT
    assert option.start == T0 + HOUR


def test_inactive_shift_does_not_count() -> None:
    shifts = (Shift(PILOT, 1, T0, T0 + 8 * HOUR, False),)
    result = solve(state(pilot_shifts=shifts), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert result.requests[0].unscheduled is Unscheduled.NOT_PLACED
    assert result.requests[0].options == ()


def test_bollard_pull_forces_more_tugs_than_n_min() -> None:
    need = replace(requirement(n_min=1), n_cap=3, bp_req=90)  # 50 t tugs: two are needed
    ctx = context(tug_requirements={REQUEST: need})
    result = solve(state(), [REQUEST], ctx, FOUR_HOURS, SETTINGS)

    assert len(first(result).tug_ids) == 2


def test_bollard_pull_never_relaxed() -> None:
    need = replace(requirement(n_min=1), n_cap=2, bp_req=120)  # two 50 t tugs give only 100 t
    ctx = context(tug_requirements={REQUEST: need})
    result = solve(state(), [REQUEST], ctx, FOUR_HOURS, SETTINGS)

    assert result.requests[0].unscheduled is Unscheduled.NOT_PLACED


def test_tug_with_master_off_shift_is_not_used() -> None:
    shifts = (shift(51), Shift(52, 52, T0 + 10 * HOUR, T0 + 20 * HOUR, True), shift(53))
    result = solve(state(tug_master_shifts=shifts), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert TUG_B not in first(result).tug_ids


def test_out_of_service_tug_is_not_used() -> None:
    tugs = (tug(TUG_A), tug(TUG_B, status="MAINTENANCE"), tug(TUG_C))
    result = solve(state(tugs=tugs), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert set(first(result).tug_ids) == {TUG_A, TUG_C}


def test_tug_without_master_is_not_used() -> None:
    masters = (master(51, TUG_A), master(53, TUG_C))
    result = solve(state(tug_masters=masters), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert set(first(result).tug_ids) == {TUG_A, TUG_C}


def test_filtered_request_carries_b2_reasons() -> None:
    big = request(loa=Decimal("400.00"))
    result = solve(state(requests=(big,)), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    solution = result.requests[0]
    assert solution.unscheduled is Unscheduled.FILTERED
    assert Code.MAX_LOA in {b.constraint_type_code for b in solution.binding_constraints}
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective_value == Decimal(0)


def test_window_without_a_whole_start_minute() -> None:
    tiny = window(start=T0 + timedelta(seconds=10), end=T0 + timedelta(seconds=50))
    result = solve(state(confirmed_windows=(tiny,)), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert result.requests[0].unscheduled is Unscheduled.NO_START


def test_start_is_before_window_end_half_open() -> None:
    narrow = window(start=T0, end=T0 + timedelta(minutes=1))
    holds = (berth_hold(BERTH, -HOUR, timedelta(seconds=30)), berth_hold(OTHER_BERTH, -HOUR, HOUR))
    result = solve(
        state(confirmed_windows=(narrow,), confirmed_holds=holds),
        [REQUEST],
        context(),
        FOUR_HOURS,
        SETTINGS,
    )

    # The only start minute is T0, and the hold on BERTH ends at T0 + 30 s (widened to T0 + 1 min).
    assert result.requests[0].unscheduled is Unscheduled.NOT_PLACED


def test_service_time_rounds_up_to_whole_minutes() -> None:
    times = {REQUEST: timedelta(hours=1, seconds=1)}
    result = solve(state(), [REQUEST], context(), times, SETTINGS)

    option = first(result)
    assert option.end - option.start == timedelta(hours=1, minutes=1)


# --- joint solve: known optima ---------------------------------------------------------------


def test_known_optimum_shorter_job_first_on_one_berth() -> None:
    """One berth, both windows [T0, T0+6h): 2 h job first waits 0, 4 h job then waits 2 h."""
    one_berth = two_requests(berths=(berth(BERTH),))
    times = {REQUEST: 4 * HOUR, OTHER_REQUEST: 2 * HOUR}
    result = solve(one_berth, [REQUEST, OTHER_REQUEST], context(), times, SETTINGS)

    assert result.status is SolveStatus.OPTIMAL
    assert first(result, OTHER_REQUEST).start == T0
    assert first(result, REQUEST).start == T0 + 2 * HOUR


def test_joint_solve_shares_tugs() -> None:
    """Three tugs, each request needs two: they can't overlap, so one waits."""
    result = solve(two_requests(), [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)

    a, b = first(result, REQUEST), first(result, OTHER_REQUEST)
    assert not overlaps(a.start, a.end, b.start, b.end)
    assert {a.start, b.start} == {T0, T0 + 4 * HOUR}


def test_scheduling_more_requests_wins_over_cost() -> None:
    """OTHER must start in its first hour; scheduling both puts REQUEST after it."""
    one_berth = two_requests(
        berths=(berth(BERTH),),
        confirmed_windows=(window(REQUEST), window(OTHER_REQUEST, T0, T0 + HOUR)),
    )
    result = solve(one_berth, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert all(s.options for s in result.requests)
    assert first(result, REQUEST).start >= first(result, OTHER_REQUEST).end


def test_capacity_leaves_one_request_not_placed() -> None:
    narrow = (window(REQUEST, T0, T0 + HOUR), window(OTHER_REQUEST, T0, T0 + HOUR))
    one_berth = two_requests(berths=(berth(BERTH),), confirmed_windows=narrow)
    result = solve(one_berth, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)

    outcomes = sorted(str(s.unscheduled) for s in result.requests)
    assert outcomes == ["NOT_PLACED", "None"]
    assert result.status is SolveStatus.OPTIMAL


# --- ranking -----------------------------------------------------------------------------------


def test_alternative_on_another_berth_within_equivalence() -> None:
    result = solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    options = result.requests[0].options
    assert [o.rank for o in options] == [1, 2]  # two berths: at most two options
    assert options[0].option.berth_id != options[1].option.berth_id
    assert options[1].objective_score == options[0].objective_score


def test_alternative_beyond_equivalence_is_dropped() -> None:
    holds = (berth_hold(OTHER_BERTH, timedelta(0), 2 * HOUR),)
    result = solve(state(confirmed_holds=holds), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    # Option 1: BERTH at T0, 1000 × (0 + 2/3) = 666.6667; bound with 10 % = 733.3334.
    # Option 2 would wait 120 of 359 start minutes on OTHER_BERTH: 1000 × (120/359 + 2/3) > bound.
    options = result.requests[0].options
    assert len(options) == 1
    assert options[0].option.berth_id == BERTH


def test_alternative_at_the_equivalence_boundary_is_kept() -> None:
    # N_min 0: no tug, so both berths score 0 at T0. With 0 % the bound is option 1's score
    # itself, and an equal score is kept (the bound is inclusive).
    ctx = context(tug_requirements={REQUEST: replace(requirement(n_min=0), n_cap=1, bp_req=0)})
    settings = replace(SETTINGS, equivalence_pct=Decimal(0))
    result = solve(state(), [REQUEST], ctx, FOUR_HOURS, settings)

    scores = [o.objective_score for o in result.requests[0].options]
    assert scores == [Decimal("0.0000"), Decimal("0.0000")]


def test_alternatives_never_use_another_requests_option_one() -> None:
    result = solve(two_requests(), [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)

    for solution in result.requests:
        others = [first(result, r.request_id) for r in result.requests if r != solution]
        for ranked in solution.options[1:]:
            for other in others:
                if overlaps(ranked.option.start, ranked.option.end, other.start, other.end):
                    assert ranked.option.berth_id != other.berth_id
                    assert ranked.option.pilot_user_id != other.pilot_user_id
                    assert not set(ranked.option.tug_ids) & set(other.tug_ids)


def test_options_capped_by_setting() -> None:
    settings = replace(SETTINGS, options_per_request=1)
    result = solve(state(), [REQUEST], context(), FOUR_HOURS, settings)

    assert len(result.requests[0].options) == 1


# --- time limit and determinism -----------------------------------------------------------


def test_alternatives_skipped_when_the_time_limit_is_spent() -> None:
    ticks = iter([0.0, 0.0] + [100.0] * 20)
    result = solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS, clock=lambda: next(ticks))

    assert len(result.requests[0].options) == 1
    assert FLAG_ALTERNATIVES_TIME_LIMIT in result.flags


def test_timeout_before_any_solution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cpsat, "_run", lambda *a, **k: cpsat._Outcome(cp_model.UNKNOWN, {}))
    result = solve(state(), [REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert result.status is SolveStatus.TIMEOUT
    assert result.objective_value is None
    assert result.requests[0].unscheduled is Unscheduled.SOLVER_TIMEOUT


def test_respects_the_time_limit_on_a_large_instance() -> None:
    port, ids, times = random_instance(random.Random(7), requests=40, berths=4, tugs=8, pilots=4)  # noqa: S311 (seeded test data)
    settings = replace(SETTINGS, time_limit_seconds=1)
    began = time.monotonic()
    result = solve(port, ids, context(tug_requirements=requirements(ids)), times, settings)
    elapsed = time.monotonic() - began

    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE, SolveStatus.TIMEOUT)
    assert elapsed < 1 + 2  # the limit, plus model building and B2 re-checks


def test_same_input_same_result() -> None:
    port = two_requests()
    one = solve(port, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)
    two = solve(port, [REQUEST, OTHER_REQUEST], context(), FOUR_HOURS, SETTINGS)

    assert replace(one, solve_time_ms=0) == replace(two, solve_time_ms=0)


def test_empty_run_and_missing_service_time_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one request"):
        solve(state(), [], context(), FOUR_HOURS, SETTINGS)
    with pytest.raises(ValueError, match="no service time"):
        solve(state(), [REQUEST], context(), {}, SETTINGS)
    with pytest.raises(ValueError, match="must be positive"):
        solve(state(), [REQUEST], context(), {REQUEST: timedelta(0)}, SETTINGS)


# --- settings ---------------------------------------------------------------------------------


def test_settings_from_port_settings() -> None:
    rows = [
        ("solver_time_limit_seconds", "10", "INT"),
        ("solver_options_per_request", "3", "INT"),
        ("solver_option_equivalence_pct", "10", "DECIMAL"),
        ("objective_weight_waiting_time", "1.0", "DECIMAL"),
        ("objective_weight_resource", "1.0", "DECIMAL"),
    ]
    assert SolverSettings.from_port_settings(PortSettings(rows)) == replace(SETTINGS)


@pytest.mark.parametrize(
    "change",
    [
        {"time_limit_seconds": 0},
        {"time_limit_seconds": 121},
        {"options_per_request": 0},
        {"options_per_request": 4},
        {"equivalence_pct": Decimal("50.01")},
        {"weight_waiting_time": Decimal("-0.1")},
        {"weight_resource": Decimal("10.1")},
        {"num_workers": 0},
    ],
)
def test_settings_outside_ct18_ranges_are_rejected(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(SETTINGS, **change)  # type: ignore[arg-type]


# --- property test: zero hard-constraint violations -----------------------------------------


def requirements(ids: list[int]) -> dict[int, TugRequirement]:
    return {r: replace(requirement(n_min=1), n_cap=2, bp_req=50) for r in ids}


def random_instance(
    rng: random.Random, *, requests: int, berths: int, tugs: int, pilots: int
) -> tuple[PortState, list[int], dict[int, timedelta]]:
    """A SYNTHETIC port with random windows, holds and shifts."""
    ids = list(range(100, 100 + requests))
    berth_ids = list(range(200, 200 + berths))
    tug_ids = list(range(300, 300 + tugs))
    pilot_ids = list(range(400, 400 + pilots))
    windows = []
    for r in ids:
        start = T0 + rng.randrange(0, 48 * 60) * timedelta(minutes=1)
        windows.append(window(r, start, start + rng.randrange(60, 12 * 60) * timedelta(minutes=1)))
    holds = []
    for b in rng.sample(berth_ids, k=min(2, berths)):
        start = T0 + rng.randrange(0, 24) * HOUR
        holds.append(
            ConfirmedHold(
                ResourceKind.BERTH, b, start, start + 5 * HOUR, 9, 1, 1, Identified.COMPONENT
            )
        )
    shifts = []
    for person in [*pilot_ids, *(t + 1000 for t in tug_ids)]:
        for day in range(4):
            begin = T0 + day * 24 * HOUR + rng.randrange(0, 4) * HOUR
            shifts.append(Shift(person, day, begin, begin + 12 * HOUR, rng.random() > 0.1))
    port = state(
        requests=tuple(request(request_id=r, vessel_id=r) for r in ids),
        confirmed_windows=tuple(windows),
        berths=tuple(berth(b) for b in berth_ids),
        tugs=tuple(
            Tugboat(
                t, f"SYNTHETIC TUG {t}", Decimal(rng.choice([30, 50, 70])), "TONNES", "AVAILABLE"
            )
            for t in tug_ids
        ),
        tug_masters=tuple(master(t + 1000, t) for t in tug_ids),
        pilots=tuple(replace(state().pilots[0], user_id=p) for p in pilot_ids),
        pilot_shifts=tuple(s for s in shifts if s.person_id in pilot_ids),
        tug_master_shifts=tuple(s for s in shifts if s.person_id not in pilot_ids),
        confirmed_holds=tuple(holds),
    )
    times = {r: rng.randrange(60, 8 * 60) * timedelta(minutes=1) for r in ids}
    return port, ids, times


@pytest.mark.parametrize("seed", range(12))
def test_property_no_hard_constraint_violation(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 (seeded test data, never a secret)
    port, ids, times = random_instance(rng, requests=6, berths=2, tugs=4, pilots=2)
    ctx = context(tug_requirements=requirements(ids))
    result = solve(port, ids, ctx, times, SETTINGS)  # B2 re-checks every option inside

    firsts = [s.options[0].option for s in result.requests if s.options]
    windows = {w.berthing_request_id: w for w in port.confirmed_windows}
    bollard = {t.id: t.tug_power for t in port.tugs}
    for option in firsts:
        w = windows[option.request_id]
        assert w.start <= option.start < w.end
        assert option.end - option.start >= times[option.request_id]
        assert 1 <= len(option.tug_ids) <= 2
        assert sum(bollard[t] for t in option.tug_ids) >= 50
        for hold in port.confirmed_holds:
            if hold.resource_id == option.berth_id:
                assert not overlaps(option.start, option.end, hold.start, hold.end)
    for a in firsts:
        for b in firsts:
            if a is b or not overlaps(a.start, a.end, b.start, b.end):
                continue
            assert a.berth_id != b.berth_id
            assert a.pilot_user_id != b.pilot_user_id
            assert not set(a.tug_ids) & set(b.tug_ids)
