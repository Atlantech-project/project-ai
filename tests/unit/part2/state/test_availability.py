"""DEC-32 rules 1 to 5 and the AI-050 berth rule, on plain values (no database)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Final

import pytest

from common.db.read_models import Tugboat
from part2.state.availability import (
    EmptyIntervalError,
    is_berth_available,
    is_busy,
    is_pilot_available,
    is_tug_available,
    overlaps,
    shift_covers,
    without_requests,
)
from part2.state.model import (
    Berth,
    ConfirmedHold,
    Identified,
    PendingHold,
    Pilot,
    PortState,
    ResourceKind,
    Shift,
    TugMaster,
)

T0: Final = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
T1: Final = T0 + timedelta(hours=2)
T2: Final = T0 + timedelta(hours=4)
T3: Final = T0 + timedelta(hours=6)
SHIFT_START: Final = T0 - timedelta(hours=1)
SHIFT_END: Final = T0 + timedelta(hours=11)

PILOT_ID: Final = 11
MASTER_ID: Final = 21
TUG_ID: Final = 31
BERTH_ID: Final = 41
TERMINAL_ID: Final = 51


def _state(**changes: Any) -> PortState:
    base = PortState(
        horizon_start=T0 - timedelta(days=1),
        horizon_end=T0 + timedelta(days=1),
        time_zone="Africa/Cairo",
        requests=(),
        confirmed_windows=(),
        berths=(
            Berth(
                id=BERTH_ID,
                code="B1",
                status="ACTIVE",
                length=Decimal(300),
                water_depth=Decimal(15),
                depth_datum="LAT",
                max_vessel_loa=Decimal(280),
                terminal_ids=frozenset({TERMINAL_ID}),
            ),
        ),
        tugs=(Tugboat(TUG_ID, "Tug 1", Decimal(60), "BOLLARD_PULL_TONNES", "AVAILABLE"),),
        pilots=(Pilot(PILOT_ID, "Pilot 1", "FIRST", True, True),),
        tug_masters=(TugMaster(MASTER_ID, "Master 1", TUG_ID, True, True),),
        pilot_rank_limits=(),
        pilot_shifts=(Shift(PILOT_ID, 1, SHIFT_START, SHIFT_END, True),),
        tug_master_shifts=(Shift(MASTER_ID, 1, SHIFT_START, SHIFT_END, True),),
        confirmed_holds=(),
        pending_holds=(),
        safety_constraints=(),
        manifest_entries=(),
        inconsistencies=(),
    )
    return replace(base, **changes)


def _confirmed(
    kind: ResourceKind, resource_id: int, start: datetime, end: datetime, request_id: int = 900
) -> ConfirmedHold:
    return ConfirmedHold(
        kind=kind,
        resource_id=resource_id,
        start=start,
        end=end,
        berthing_request_id=request_id,
        operational_plan_id=700,
        plan_component_id=800,
        identified=Identified.COMPONENT,
    )


def _pending(
    kind: ResourceKind, resource_id: int, start: datetime, end: datetime, request_id: int = 901
) -> PendingHold:
    return PendingHold(
        kind=kind,
        resource_id=resource_id,
        start=start,
        end=end,
        berthing_request_id=request_id,
        recommendation_id=600,
        recommendation_status="PENDING_REVIEW",
        option_id=610,
        option_rank=1,
    )


# Intervals (DEC-32 rule 4)


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        ((T0 - timedelta(hours=2), T0), False),  # ends exactly when the job starts
        ((T1, T2), False),  # starts exactly when the job ends
        ((T0 - timedelta(hours=1), T0 + timedelta(minutes=1)), True),  # reaches in by a minute
        ((T1 - timedelta(minutes=1), T2), True),  # starts a minute before the job ends
        ((T0 - timedelta(hours=1), T2), True),  # contains the job
        ((T0 + timedelta(minutes=30), T0 + timedelta(minutes=45)), True),  # inside the job
    ],
)
def test_intervals_are_half_open(other: tuple[datetime, datetime], expected: bool) -> None:
    assert overlaps(T0, T1, *other) is expected


def test_an_empty_interval_is_refused() -> None:
    with pytest.raises(EmptyIntervalError):
        is_busy(ResourceKind.PILOT, PILOT_ID, T1, T1, (), ())


# Shifts (rule 1(b))


def test_a_shift_covers_a_job_inside_it() -> None:
    assert shift_covers(_state().pilot_shifts, PILOT_ID, T0, T2)


def test_a_job_that_crosses_a_shift_change_is_not_covered_even_by_two_back_to_back_shifts() -> None:
    shifts = (
        Shift(PILOT_ID, 1, T0 - timedelta(hours=8), T1, True),
        Shift(PILOT_ID, 2, T1, T0 + timedelta(hours=8), True),
    )
    assert shift_covers(shifts, PILOT_ID, T0, T1)
    assert not shift_covers(shifts, PILOT_ID, T0, T2)


def test_a_job_that_ends_exactly_at_the_end_of_the_shift_is_covered() -> None:
    assert shift_covers(_state().pilot_shifts, PILOT_ID, T0, SHIFT_END)
    assert not shift_covers(_state().pilot_shifts, PILOT_ID, T0, SHIFT_END + timedelta(minutes=1))


def test_a_retired_shift_or_another_persons_shift_does_not_cover() -> None:
    retired = (Shift(PILOT_ID, 1, SHIFT_START, SHIFT_END, False),)
    other = (Shift(PILOT_ID + 1, 1, SHIFT_START, SHIFT_END, True),)
    assert not shift_covers(retired, PILOT_ID, T0, T1)
    assert not shift_covers(other, PILOT_ID, T0, T1)


# Pilot (rule 1)


def test_a_pilot_on_shift_with_no_hold_is_available() -> None:
    assert is_pilot_available(_state(), PILOT_ID, T0, T2)


def test_an_unknown_pilot_is_not_available() -> None:
    assert not is_pilot_available(_state(), PILOT_ID + 1, T0, T2)


@pytest.mark.parametrize(
    "pilot",
    [
        Pilot(PILOT_ID, "Pilot 1", "FIRST", False, True),  # users.is_active = 0
        Pilot(PILOT_ID, "Pilot 1", "FIRST", True, False),  # role ended (DEC-36)
    ],
    ids=["inactive-user", "role-ended"],
)
def test_an_inactive_pilot_is_not_available(pilot: Pilot) -> None:
    assert not is_pilot_available(_state(pilots=(pilot,)), PILOT_ID, T0, T2)


def test_a_pilot_off_shift_is_not_available() -> None:
    state = _state(pilot_shifts=())
    assert not is_pilot_available(state, PILOT_ID, T0, T2)


@pytest.mark.parametrize(
    "hold",
    [
        _confirmed(ResourceKind.PILOT, PILOT_ID, T1, T3),
        _pending(ResourceKind.PILOT, PILOT_ID, T1, T3),
    ],
    ids=["confirmed", "pending"],
)
def test_a_pilot_with_an_overlapping_hold_is_busy(hold: ConfirmedHold | PendingHold) -> None:
    if isinstance(hold, ConfirmedHold):
        state = _state(confirmed_holds=(hold,))
    else:
        state = _state(pending_holds=(hold,))
    assert not is_pilot_available(state, PILOT_ID, T0, T2)


def test_back_to_back_jobs_do_not_collide() -> None:
    state = _state(confirmed_holds=(_confirmed(ResourceKind.PILOT, PILOT_ID, T2, T3),))
    assert is_pilot_available(state, PILOT_ID, T0, T2)
    assert not is_pilot_available(state, PILOT_ID, T0, T2 + timedelta(minutes=1))


def test_another_resources_hold_does_not_block_the_pilot() -> None:
    state = _state(
        confirmed_holds=(_confirmed(ResourceKind.TUG, PILOT_ID, T0, T2),),  # a tug with that id
        pending_holds=(_pending(ResourceKind.PILOT, PILOT_ID + 1, T0, T2),),
    )
    assert is_pilot_available(state, PILOT_ID, T0, T2)


# Tug (rule 2)


def test_a_tug_with_an_active_master_on_shift_is_available() -> None:
    assert is_tug_available(_state(), TUG_ID, T0, T2)


@pytest.mark.parametrize("status", ["MAINTENANCE", "INACTIVE"])
def test_a_tug_out_of_service_is_not_available(status: str) -> None:
    tug = Tugboat(TUG_ID, "Tug 1", Decimal(60), "BOLLARD_PULL_TONNES", status)
    assert not is_tug_available(_state(tugs=(tug,)), TUG_ID, T0, T2)


def test_the_busy_status_flag_is_not_used() -> None:
    """BUSY is a flag the Tug Master sets; only overlap makes a tug busy (DEC-32)."""
    tug = Tugboat(TUG_ID, "Tug 1", Decimal(60), "BOLLARD_PULL_TONNES", "BUSY")
    assert is_tug_available(_state(tugs=(tug,)), TUG_ID, T0, T2)


@pytest.mark.parametrize(
    "state",
    [
        _state(tug_masters=()),
        _state(tug_masters=(TugMaster(MASTER_ID, "M", None, True, True),)),
        _state(tug_masters=(TugMaster(MASTER_ID, "M", TUG_ID, False, True),)),
        _state(tug_masters=(TugMaster(MASTER_ID, "M", TUG_ID, True, False),)),
        _state(tug_master_shifts=()),
    ],
    ids=["no-master", "master-unassigned", "master-inactive", "role-ended", "master-off-shift"],
)
def test_a_tug_without_an_available_master_is_not_available(state: PortState) -> None:
    assert not is_tug_available(state, TUG_ID, T0, T2)


def test_a_tug_with_an_overlapping_hold_is_busy() -> None:
    confirmed = _state(confirmed_holds=(_confirmed(ResourceKind.TUG, TUG_ID, T1, T3),))
    pending = _state(pending_holds=(_pending(ResourceKind.TUG, TUG_ID, T1, T3),))
    assert not is_tug_available(confirmed, TUG_ID, T0, T2)
    assert not is_tug_available(pending, TUG_ID, T0, T2)


# Berth (AI-050)


def test_a_berth_in_service_for_the_terminal_with_no_hold_is_available() -> None:
    assert is_berth_available(_state(), BERTH_ID, TERMINAL_ID, T0, T2)


@pytest.mark.parametrize("status", ["MAINTENANCE", "INACTIVE"])
def test_a_berth_out_of_service_is_not_available(status: str) -> None:
    berth = replace(_state().berths[0], status=status)
    assert not is_berth_available(_state(berths=(berth,)), BERTH_ID, TERMINAL_ID, T0, T2)


def test_a_berth_not_allowed_for_the_terminal_is_not_available() -> None:
    assert not is_berth_available(_state(), BERTH_ID, TERMINAL_ID + 1, T0, T2)


def test_an_unknown_berth_is_not_available() -> None:
    assert not is_berth_available(_state(), BERTH_ID + 1, TERMINAL_ID, T0, T2)


def test_a_berth_with_an_overlapping_hold_is_busy_and_back_to_back_stays_are_not() -> None:
    state = _state(
        confirmed_holds=(_confirmed(ResourceKind.BERTH, BERTH_ID, T2, T3),),
        pending_holds=(_pending(ResourceKind.BERTH, BERTH_ID, T0 - timedelta(hours=3), T0),),
    )
    assert is_berth_available(state, BERTH_ID, TERMINAL_ID, T0, T2)
    assert not is_berth_available(state, BERTH_ID, TERMINAL_ID, T1, T3)


# Holds carry their request (ruling 2) and the solver can drop its own run's (rule 5, DEC-06)


def test_every_hold_names_its_request_and_a_pending_hold_its_recommendation() -> None:
    confirmed = _confirmed(ResourceKind.PILOT, PILOT_ID, T0, T2, request_id=1550)
    pending = _pending(ResourceKind.PILOT, PILOT_ID, T0, T2, request_id=1553)
    assert confirmed.berthing_request_id == 1550
    assert (pending.berthing_request_id, pending.recommendation_id) == (1553, 600)
    assert (pending.option_id, pending.option_rank) == (610, 1)


def test_dropping_the_holds_of_the_runs_requests_frees_their_resources() -> None:
    """The previous PENDING_REVIEW recommendation of a request in the run holds nothing."""
    previous = _pending(ResourceKind.PILOT, PILOT_ID, T0, T2, request_id=1553)
    other = _pending(ResourceKind.TUG, TUG_ID, T0, T2, request_id=1560)
    state = _state(pending_holds=(previous, other))
    assert not is_pilot_available(state, PILOT_ID, T0, T2)
    left = without_requests(state.pending_holds, [1553])
    assert left == (other,)
    assert is_pilot_available(state, PILOT_ID, T0, T2, pending_holds=left)
    assert not is_tug_available(state, TUG_ID, T0, T2, pending_holds=left)  # request 1560 stays


def test_dropping_applies_to_confirmed_holds_too_and_loses_nothing_else() -> None:
    mine = _confirmed(ResourceKind.BERTH, BERTH_ID, T0, T2, request_id=1540)
    theirs = _confirmed(ResourceKind.PILOT, PILOT_ID, T0, T2, request_id=1541)
    state = _state(confirmed_holds=(mine, theirs))
    assert without_requests(state.confirmed_holds, [1540]) == (theirs,)
    assert without_requests(state.confirmed_holds, []) == (mine, theirs)
    assert state.confirmed_holds == (mine, theirs)  # the snapshot itself is never changed
