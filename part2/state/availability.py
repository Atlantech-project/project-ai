"""DEC-32 and the AI-050 berth rule as pure functions over a `PortState` (no database).

One definition of "available" for pilots, tugs and berths. The Backend runs the same statements in
P5-M1; these functions take plain values so the same test vectors can drive both.

The loader exposes the holds of every request, including the requests in the current solve. It does
not drop them. `without_requests` is how a solver does that (DEC-32 rule 5, DEC-06).
"""

from collections.abc import Iterable
from datetime import datetime
from typing import Final

from part2.state.model import (
    Berth,
    ConfirmedHold,
    PendingHold,
    Pilot,
    PortState,
    ResourceKind,
    Shift,
    TugMaster,
)

# Statuses that take a tug or berth out of service (DEC-32 rule 2(a)). A tug's BUSY is a flag the
# Tug Master sets; busyness comes only from overlap (rule 3).
TUG_OUT_OF_SERVICE: Final = frozenset({"MAINTENANCE", "INACTIVE"})
BERTH_OUT_OF_SERVICE: Final = frozenset({"MAINTENANCE", "INACTIVE"})


class EmptyIntervalError(ValueError):
    pass


def overlaps(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    """Half-open intervals: back-to-back jobs do not overlap (DEC-32 rule 4)."""
    return start < other_end and other_start < end


def _check(start: datetime, end: datetime) -> None:
    if end <= start:
        raise EmptyIntervalError(f"interval must end after it starts: {start} to {end}")


def without_requests[H: (ConfirmedHold, PendingHold)](
    holds: Iterable[H], request_ids: Iterable[int]
) -> tuple[H, ...]:
    """The holds left after dropping every hold of the given requests.

    The solver passes the requests of its run: they are variables of the same solve, and their
    previous PENDING_REVIEW recommendation becomes REPLACED (DEC-32 rule 5, DEC-06).
    """
    dropped = frozenset(request_ids)
    return tuple(hold for hold in holds if hold.berthing_request_id not in dropped)


def is_busy(
    kind: ResourceKind,
    resource_id: int,
    start: datetime,
    end: datetime,
    confirmed_holds: Iterable[ConfirmedHold],
    pending_holds: Iterable[PendingHold],
) -> bool:
    """DEC-32 rule 3: the resource has a hold that overlaps `[start, end)`."""
    _check(start, end)
    holds: list[ConfirmedHold | PendingHold] = [*confirmed_holds, *pending_holds]
    return any(
        hold.kind is kind
        and hold.resource_id == resource_id
        and overlaps(start, end, hold.start, hold.end)
        for hold in holds
    )


def shift_covers(shifts: Iterable[Shift], person_id: int, start: datetime, end: datetime) -> bool:
    """One active shift of the person covers the whole interval (DEC-32 rule 1(b)).

    A job that crosses a shift change is not covered, even by two shifts back to back.
    """
    _check(start, end)
    return any(
        shift.person_id == person_id
        and shift.shift_is_active
        and shift.start <= start
        and end <= shift.end
        for shift in shifts
    )


def is_pilot_available(
    state: PortState,
    pilot_user_id: int,
    start: datetime,
    end: datetime,
    *,
    confirmed_holds: Iterable[ConfirmedHold] | None = None,
    pending_holds: Iterable[PendingHold] | None = None,
) -> bool:
    """DEC-32 rule 1. Pass the holds left after `without_requests` to leave a run's own out."""
    pilot = _pilot(state.pilots, pilot_user_id)
    if pilot is None or not (pilot.is_active and pilot.has_active_pilot_role):
        return False
    if not shift_covers(state.pilot_shifts, pilot_user_id, start, end):
        return False
    return not is_busy(
        ResourceKind.PILOT,
        pilot_user_id,
        start,
        end,
        state.confirmed_holds if confirmed_holds is None else confirmed_holds,
        state.pending_holds if pending_holds is None else pending_holds,
    )


def is_tug_available(
    state: PortState,
    tugboat_id: int,
    start: datetime,
    end: datetime,
    *,
    confirmed_holds: Iterable[ConfirmedHold] | None = None,
    pending_holds: Iterable[PendingHold] | None = None,
) -> bool:
    """DEC-32 rule 2: in service, its tug master active and on shift, and not busy.

    A tug with no tug master is not available: rule 2(b) needs "its tug master".
    """
    tug = next((tug for tug in state.tugs if tug.id == tugboat_id), None)
    if tug is None or tug.status in TUG_OUT_OF_SERVICE:
        return False
    master = next((m for m in state.tug_masters if m.tugboat_id == tugboat_id), None)
    if master is None or not _master_on_duty(state, master, start, end):
        return False
    return not is_busy(
        ResourceKind.TUG,
        tugboat_id,
        start,
        end,
        state.confirmed_holds if confirmed_holds is None else confirmed_holds,
        state.pending_holds if pending_holds is None else pending_holds,
    )


def is_berth_available(
    state: PortState,
    berth_id: int,
    terminal_id: int,
    start: datetime,
    end: datetime,
    *,
    confirmed_holds: Iterable[ConfirmedHold] | None = None,
    pending_holds: Iterable[PendingHold] | None = None,
) -> bool:
    """The AI-050 berth rule: in service, allowed for the terminal, and not busy."""
    berth = _berth(state.berths, berth_id)
    if berth is None or berth.status in BERTH_OUT_OF_SERVICE:
        return False
    if terminal_id not in berth.terminal_ids:
        return False
    return not is_busy(
        ResourceKind.BERTH,
        berth_id,
        start,
        end,
        state.confirmed_holds if confirmed_holds is None else confirmed_holds,
        state.pending_holds if pending_holds is None else pending_holds,
    )


def _master_on_duty(state: PortState, master: TugMaster, start: datetime, end: datetime) -> bool:
    if not (master.is_active and master.has_active_tug_master_role):
        return False
    return shift_covers(state.tug_master_shifts, master.user_id, start, end)


def _pilot(pilots: Iterable[Pilot], user_id: int) -> Pilot | None:
    return next((pilot for pilot in pilots if pilot.user_id == user_id), None)


def _berth(berths: Iterable[Berth], berth_id: int) -> Berth | None:
    return next((berth for berth in berths if berth.id == berth_id), None)
