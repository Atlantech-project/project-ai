"""B2 on emitted options, AI and FIFO (AI-051 criteria 1 and 2). SYNTHETIC data only."""

from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal

import pytest

from part2.filter import Option, OptionCheck, check_option, check_plan
from part2.state.model import ConfirmedHold, Identified, PendingHold, ResourceKind
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
    option,
    pilot,
    request,
    requirement,
    state,
    tug,
    window,
)

# Request 1: window [T0, T0 + 6 h), option [T0 + 1 h, T0 + 13 h). Request 2: window [T0 + 12 h,
# T0 + 18 h), so a FIFO option can follow request 1 back to back or overlap it.
TWO_REQUESTS = state(
    requests=(request(), request(request_id=OTHER_REQUEST, vessel_id=OTHER_REQUEST)),
    confirmed_windows=(window(), window(OTHER_REQUEST, T0 + 12 * HOUR, T0 + 18 * HOUR)),
)
OVERLAP = {"start": T0 + 12 * HOUR, "end": T0 + 16 * HOUR}


def _codes(result: OptionCheck) -> list[str]:
    return [r.code for r in result.removals]


def _confirmed(kind: ResourceKind, resource: int, request_id: int = 9) -> ConfirmedHold:
    return ConfirmedHold(kind, resource, T0, T0 + 24 * HOUR, request_id, 1, 1, Identified.COMPONENT)


def _pending(kind: ResourceKind, resource: int, request_id: int = 9) -> PendingHold:
    return PendingHold(kind, resource, T0, T0 + 24 * HOUR, request_id, 1, "PENDING_REVIEW", 1, 1)


def test_a_valid_option_passes() -> None:
    result = check_option(state(), option(), context())
    assert result.passes
    assert result.removals == ()


# --- The pairing rules apply to the option's berth ---------------------------------------------


def test_the_option_berth_is_checked_with_the_pairing_rules() -> None:
    s = state(berths=(berth(BERTH, max_vessel_loa=Decimal("100")), berth(OTHER_BERTH)))
    assert _codes(check_option(s, option(), context())) == ["MAX_LOA"]
    assert check_option(s, option(berth_id=OTHER_BERTH), context()).passes


def test_a_berth_not_in_the_snapshot_is_unavailable() -> None:
    assert _codes(check_option(state(), option(berth_id=999), context())) == ["BERTH_UNAVAILABLE"]


# --- Entry window: half-open [start, end) in UTC ------------------------------------------------


@pytest.mark.parametrize(
    ("offset", "passes"),
    [
        (timedelta(microseconds=-1), False),
        (timedelta(0), True),
        (6 * HOUR - timedelta(microseconds=1), True),
        (6 * HOUR, False),
    ],
)
def test_the_option_starts_inside_the_window(offset: timedelta, passes: bool) -> None:
    start = T0 + offset
    result = check_option(state(), option(start=start, end=start + 12 * HOUR), context())
    assert _codes(result) == ([] if passes else ["ENTRY_WINDOW"])


@pytest.mark.parametrize(
    "start",
    [T0.replace(tzinfo=None), T0.astimezone(timezone(timedelta(hours=2)))],
    ids=["naive", "utc+2"],
)
def test_option_times_must_be_utc(start: object) -> None:
    with pytest.raises(ValueError, match="UTC"):
        check_option(state(), option(start=start), context())


def test_an_empty_option_interval_is_an_error() -> None:
    with pytest.raises(ValueError):
        check_option(state(), option(end=T0 + HOUR), context())


# --- Berth occupied -----------------------------------------------------------------------------


def test_a_berth_held_by_a_confirmed_plan_is_occupied() -> None:
    s = state(confirmed_holds=(_confirmed(ResourceKind.BERTH, BERTH),))
    assert _codes(check_option(s, option(), context())) == ["BERTH_OCCUPIED"]


def test_a_berth_held_by_a_pending_option_is_occupied() -> None:
    s = state(pending_holds=(_pending(ResourceKind.BERTH, BERTH),))
    assert _codes(check_option(s, option(), context())) == ["BERTH_OCCUPIED"]


def test_the_requests_own_holds_are_dropped() -> None:
    s = state(pending_holds=(_pending(ResourceKind.BERTH, BERTH, request_id=REQUEST),))
    assert check_option(s, option(), context()).passes


def test_holds_of_other_requests_in_the_run_are_dropped() -> None:
    s = state(pending_holds=(_pending(ResourceKind.BERTH, BERTH, request_id=OTHER_REQUEST),))
    assert not check_option(s, option(), context()).passes
    assert check_option(s, option(), context(), run_request_ids=(OTHER_REQUEST,)).passes


# --- Pilot --------------------------------------------------------------------------------------


def test_no_pilot_is_unavailable_with_its_own_detail() -> None:
    (removal,) = check_option(state(), option(pilot_user_id=None), context()).removals
    assert (removal.code, removal.detail) == ("PILOT_UNAVAILABLE", "no pilot assigned")


def test_a_busy_pilot_has_a_different_detail() -> None:
    s = state(confirmed_holds=(_confirmed(ResourceKind.PILOT, PILOT),))
    (removal,) = check_option(s, option(), context()).removals
    assert removal.code == "PILOT_UNAVAILABLE"
    assert removal.detail != "no pilot assigned"


@pytest.mark.parametrize(
    "s",
    [
        state(pilots=(pilot(PILOT, is_active=False), pilot(OTHER_PILOT))),
        state(pilot_shifts=()),
        state(confirmed_holds=(_confirmed(ResourceKind.PILOT, PILOT),)),
    ],
    ids=["inactive", "off-shift", "busy"],
)
def test_an_unavailable_pilot(s: object) -> None:
    assert _codes(check_option(s, option(), context())) == ["PILOT_UNAVAILABLE"]  # type: ignore[arg-type]


def test_an_under_ranked_pilot() -> None:
    s = state(pilots=(pilot(PILOT, rank="THIRD"), pilot(OTHER_PILOT)))  # THIRD: up to 150 m
    assert _codes(check_option(s, option(), context())) == ["PILOT_RANK_LIMIT"]
    assert check_option(s, option(pilot_user_id=OTHER_PILOT), context()).passes


# --- Tugs ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "s",
    [
        state(tugs=(tug(TUG_A, "MAINTENANCE"), tug(TUG_B), tug(TUG_C))),
        state(tug_master_shifts=()),
        state(pending_holds=(_pending(ResourceKind.TUG, TUG_A),)),
    ],
    ids=["out-of-service", "master-off-shift", "busy"],
)
def test_an_unavailable_tug(s: object) -> None:
    codes = _codes(check_option(s, option(), context()))  # type: ignore[arg-type]
    assert "TUG_UNAVAILABLE" in codes


@pytest.mark.parametrize(
    ("tugs", "eligible", "passes"),
    [
        ((TUG_A, TUG_B), (TUG_A, TUG_B, TUG_C), True),
        ((TUG_A,), (TUG_A, TUG_B, TUG_C), False),
        # Enough eligible tugs in the port (A, C), but the option uses ineligible B.
        ((TUG_A, TUG_B), (TUG_A, TUG_C), False),
    ],
)
def test_option_tug_count(tugs: tuple[int, ...], eligible: tuple[int, ...], passes: bool) -> None:
    ctx = context(tug_requirements={REQUEST: requirement(2, eligible)})
    result = check_option(state(), option(tug_ids=tugs), ctx)
    assert _codes(result) == ([] if passes else ["TUG_COUNT"])


def test_duplicate_tugs_are_an_error() -> None:
    with pytest.raises(ValueError, match="tug"):
        check_option(state(), option(tug_ids=(TUG_A, TUG_A)), context())


# --- FIFO output: the same filter, across the whole plan (criterion 2) --------------------------


def _fifo(**second: object) -> tuple[Option, Option]:
    """A FIFO plan by arrival order: request 1, then request 2."""
    first = option()
    other = option(
        request_id=OTHER_REQUEST,
        berth_id=OTHER_BERTH,
        pilot_user_id=OTHER_PILOT,
        tug_ids=(TUG_C, TUG_B),
        start=first.end,
        end=first.end + 4 * HOUR,
    )
    return first, replace(other, **second)  # type: ignore[arg-type]


def test_a_fifo_plan_with_separate_resources_passes_even_when_overlapping() -> None:
    # Request 2 overlaps request 1 in time but uses another berth, pilot and tug.
    plan = _fifo(tug_ids=(TUG_C,), **OVERLAP)
    ctx = context(tug_requirements={REQUEST: requirement(2), OTHER_REQUEST: requirement(1)})
    assert all(r.passes for r in check_plan(TWO_REQUESTS, plan, ctx))


@pytest.mark.parametrize(
    ("second", "code"),
    [
        ({"berth_id": BERTH, **OVERLAP}, "BERTH_OCCUPIED"),
        ({"pilot_user_id": PILOT, **OVERLAP}, "PILOT_UNAVAILABLE"),
        ({"tug_ids": (TUG_A, TUG_C), **OVERLAP}, "TUG_UNAVAILABLE"),
    ],
    ids=["berth", "pilot", "tug"],
)
def test_a_fifo_plan_that_double_books_fails(second: dict[str, object], code: str) -> None:
    first, other = _fifo(**second)
    results = check_plan(TWO_REQUESTS, (first, other), context())
    assert code in _codes(results[0]) and code in _codes(results[1])


def test_back_to_back_is_not_a_double_booking() -> None:
    first, other = _fifo(berth_id=BERTH, pilot_user_id=PILOT, tug_ids=(TUG_A, TUG_B))
    assert other.start == first.end
    assert all(r.passes for r in check_plan(TWO_REQUESTS, (first, other), context()))


def test_check_plan_drops_the_holds_of_every_request_in_the_plan() -> None:
    s = replace(
        TWO_REQUESTS,
        pending_holds=(_pending(ResourceKind.BERTH, OTHER_BERTH, request_id=OTHER_REQUEST),),
    )
    first, other = _fifo()
    assert all(r.passes for r in check_plan(s, (first, other), context()))
