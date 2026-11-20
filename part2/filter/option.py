"""B2 on emitted options, AI and FIFO alike (AI-051; Architecture §8.4 "hard filter again on every
emitted option", §8.9 FIFO "passes the same hard filter").

An option passes the pairing rules for its berth, starts inside the confirmed window `[start, end)`
in UTC, and finds its berth, pilot and tugs free: AI-050's availability functions (DEC-32), with
the run's own requests' holds dropped (DEC-32 rule 5). `check_plan` also treats the other options
of the same plan as holds, so a FIFO plan that double-books a resource fails.
"""

from collections.abc import Iterable, Sequence
from typing import Final

from part1.feasibility.scope import require_utc
from part2.filter.model import Code, FilterContext, Kind, Option, OptionCheck, Removal
from part2.filter.pairing import (
    confirmed_window,
    filter_candidates,
    rank_allows,
    tug_count_detail,
    tug_requirement,
)
from part2.state.availability import (
    is_busy,
    is_pilot_available,
    is_tug_available,
    overlaps,
    without_requests,
)
from part2.state.model import ConfirmedHold, PendingHold, PortState, ResourceKind

# Distinct from a pilot who exists but is busy or off shift.
NO_PILOT_ASSIGNED: Final = "no pilot assigned"

_Confirmed = tuple[ConfirmedHold, ...]
_Pending = tuple[PendingHold, ...]


def check_option(
    state: PortState,
    option: Option,
    context: FilterContext,
    *,
    run_request_ids: Iterable[int] = (),
    plan: Sequence[Option] = (),
) -> OptionCheck:
    """B2 for one option. `plan`: the other requests' options in the same plan, as holds.

    The holds of `run_request_ids` and of the option's own request are dropped before the check.
    """
    require_utc(option.start, "option start")
    require_utc(option.end, "option end")
    if option.end <= option.start:
        raise ValueError(f"option must end after it starts: {option.start} to {option.end}")
    if len(set(option.tug_ids)) != len(option.tug_ids):
        raise ValueError(f"option lists a tug twice: {option.tug_ids}")

    candidates = filter_candidates(state, option.request_id, context)
    removals = list(candidates.request_removals)
    berth = next((b for b in candidates.berths if b.berth_id == option.berth_id), None)
    if berth is None:
        detail = f"Berth {option.berth_id} is not in the port snapshot"
        removals.append(Removal(Kind.STRUCTURAL, Code.BERTH_UNAVAILABLE, detail, option.berth_id))
    else:
        removals.extend(berth.removals)

    window = confirmed_window(state, option.request_id)
    if window is not None and not window.start <= option.start < window.end:
        detail = f"Start {option.start.isoformat()} is outside the confirmed window"
        removals.append(Removal(Kind.STRUCTURAL, Code.ENTRY_WINDOW, detail))

    dropped = {option.request_id, *run_request_ids}
    confirmed = without_requests(state.confirmed_holds, dropped)
    pending = without_requests(state.pending_holds, dropped)
    others = [
        o
        for o in plan
        if o.request_id != option.request_id and overlaps(option.start, option.end, o.start, o.end)
    ]
    removals.extend(_berth_busy(option, confirmed, pending, others))
    removals.extend(_pilot(state, option, confirmed, pending, others))
    removals.extend(_tugs(state, option, context, confirmed, pending, others))
    return OptionCheck(option, _one_per_code(removals))


def check_plan(
    state: PortState, options: Sequence[Option], context: FilterContext
) -> tuple[OptionCheck, ...]:
    """B2 for a whole plan (one option per request, for example a FIFO plan), in order.

    The run is the plan's requests: their own holds are dropped, and each option sees the others
    as holds.
    """
    run = {o.request_id for o in options}
    return tuple(
        check_option(state, o, context, run_request_ids=run, plan=options) for o in options
    )


def _berth_busy(
    option: Option, confirmed: _Confirmed, pending: _Pending, others: list[Option]
) -> list[Removal]:
    busy = is_busy(
        ResourceKind.BERTH, option.berth_id, option.start, option.end, confirmed, pending
    ) or any(o.berth_id == option.berth_id for o in others)
    if not busy:
        return []
    return [Removal(Kind.STRUCTURAL, Code.BERTH_OCCUPIED, "The berth is held at this time")]


def _pilot(
    state: PortState, option: Option, confirmed: _Confirmed, pending: _Pending, others: list[Option]
) -> list[Removal]:
    if option.pilot_user_id is None:
        # Pilotage is compulsory for every vessel (confirmed rule, AI-051 task decision).
        return [Removal(Kind.STRUCTURAL, Code.PILOT_UNAVAILABLE, NO_PILOT_ASSIGNED)]
    pilot_id = option.pilot_user_id
    available = is_pilot_available(
        state,
        pilot_id,
        option.start,
        option.end,
        confirmed_holds=confirmed,
        pending_holds=pending,
    ) and not any(o.pilot_user_id == pilot_id for o in others)
    removals = []
    if not available:
        detail = f"Pilot {pilot_id} is not available at this time"
        removals.append(Removal(Kind.STRUCTURAL, Code.PILOT_UNAVAILABLE, detail))
    pilot = next((p for p in state.pilots if p.user_id == pilot_id), None)
    request = next(r for r in state.requests if r.request_id == option.request_id)
    if pilot is not None and not rank_allows(pilot, request.loa, state.pilot_rank_limits):
        detail = f"Pilot {pilot_id} (rank {pilot.rank}) may not pilot LOA {request.loa} m"
        removals.append(Removal(Kind.STRUCTURAL, Code.PILOT_RANK_LIMIT, detail))
    return removals


def _tugs(
    state: PortState,
    option: Option,
    context: FilterContext,
    confirmed: _Confirmed,
    pending: _Pending,
    others: list[Option],
) -> list[Removal]:
    shared = {t for o in others for t in o.tug_ids}
    unavailable = [
        t
        for t in option.tug_ids
        if t in shared
        or not is_tug_available(
            state,
            t,
            option.start,
            option.end,
            confirmed_holds=confirmed,
            pending_holds=pending,
        )
    ]
    removals = []
    if unavailable:
        detail = f"Tugs {', '.join(map(str, unavailable))} are not available at this time"
        removals.append(Removal(Kind.STRUCTURAL, Code.TUG_UNAVAILABLE, detail))
    requirement = tug_requirement(context, option.request_id)
    eligible = sum(1 for t in option.tug_ids if t in requirement.eligible_tugs)
    if eligible < requirement.n_min:
        detail = tug_count_detail(requirement, eligible, "tugs in the option")
        removals.append(Removal(Kind.STRUCTURAL, Code.TUG_COUNT, detail))
    return removals


def _one_per_code(removals: Iterable[Removal]) -> tuple[Removal, ...]:
    """One removal per (kind, code), the first kept, ordered by kind and code."""
    seen: dict[tuple[Kind, str], Removal] = {}
    for removal in removals:
        seen.setdefault((removal.kind, removal.code), removal)
    return tuple(sorted(seen.values(), key=lambda r: (r.kind.value, r.code)))
