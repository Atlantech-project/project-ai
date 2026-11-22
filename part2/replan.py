"""B7 re-planning inputs (AI-059): the solve scope from the CT-10 triggers, and the pins of a
delay re-plan.

- **Scope (CT-10).** The run's requests are the union of `berthing_request_ids` over the entries;
  `purpose` is `DELAY_REPLAN` for a request in a `REPLAN` entry, `INITIAL` otherwise. A request is
  in at most one entry, and a `REPLAN` entry names exactly one request (the plan's). The envelope
  schema checks the shapes; the two cross-entry rules are checked here.
- **Pins (Architecture §8.13).** A delay re-plan re-solves "with `STARTED` components fixed": every
  begun component of the request's CONFIRMED plan keeps its resource and interval. All of them
  share one interval, the option's (DEC-32 rule 4), so it becomes the pin's start and end. A plan
  whose begun components disagree cannot be written as one option and fails the run.

Nothing here reads or writes the database: the AI-050 snapshot carries the started components.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from common.runtime.errors import ErrorCategory, JobError
from part2.solver import Pin
from part2.state.model import PortState, ResourceKind, StartedComponent

REPLAN: Final = "REPLAN"
TRIGGER_TYPES: Final = frozenset({"NEW_REQUEST", "MANUAL", "RESOURCE_CHANGE", REPLAN})


@dataclass(frozen=True)
class SolveScope:
    """What one PART2_SOLVE message asks for."""

    request_ids: tuple[int, ...]  # the run, sorted
    replan_request_ids: frozenset[int]
    trigger_of: Mapping[int, str]  # request id → the trigger type of its entry


def scope_from_payload(payload: Mapping[str, Any]) -> SolveScope:
    """The run's scope from a C-02 payload (CT-10), checking the cross-entry rules."""
    trigger_of: dict[int, str] = {}
    replan: set[int] = set()
    for entry in payload["triggers"]:
        trigger = str(entry["trigger_type"])
        if trigger not in TRIGGER_TYPES:
            raise JobError(ErrorCategory.INVALID_ENVELOPE, f"unknown trigger_type {trigger}")
        ids = [int(r) for r in entry["berthing_request_ids"]]
        if trigger == REPLAN and len(ids) != 1:
            raise JobError(
                ErrorCategory.INVALID_ENVELOPE,
                f"a REPLAN entry names exactly one request, not {len(ids)} (CT-10)",
            )
        for request_id in ids:
            if request_id in trigger_of:
                raise JobError(
                    ErrorCategory.INVALID_ENVELOPE,
                    f"request {request_id} is in more than one trigger entry (CT-10)",
                )
            trigger_of[request_id] = trigger
            if trigger == REPLAN:
                replan.add(request_id)
    if not trigger_of:
        raise JobError(ErrorCategory.INVALID_ENVELOPE, "the payload names no request")
    return SolveScope(tuple(sorted(trigger_of)), frozenset(replan), trigger_of)


def pins_for(state: PortState, replan_request_ids: Iterable[int]) -> dict[int, Pin]:
    """One pin per REPLAN request with a begun component; requests with none get no pin."""
    replan = frozenset(replan_request_ids)
    by_request: dict[int, list[StartedComponent]] = {}
    for component in state.started_components:
        if component.berthing_request_id in replan:
            by_request.setdefault(component.berthing_request_id, []).append(component)
    return {request_id: _pin(request_id, parts) for request_id, parts in sorted(by_request.items())}


def _pin(request_id: int, parts: Sequence[StartedComponent]) -> Pin:
    intervals = {(c.start, c.end) for c in parts}
    if len(intervals) != 1:
        raise _unrepresentable(request_id, "its begun components have different intervals")
    berths = {c.resource_id for c in parts if c.kind is ResourceKind.BERTH}
    pilots = {c.resource_id for c in parts if c.kind is ResourceKind.PILOT}
    if len(berths) > 1 or len(pilots) > 1:
        raise _unrepresentable(request_id, "it has more than one begun berth or pilot")
    ((start, end),) = intervals
    try:
        return Pin(
            start=start,
            end=end,
            berth_id=next(iter(berths), None),
            pilot_user_id=next(iter(pilots), None),
            tug_ids=frozenset(c.resource_id for c in parts if c.kind is ResourceKind.TUG),
        )
    except ValueError as error:
        raise _unrepresentable(request_id, str(error)) from error


def _unrepresentable(request_id: int, why: str) -> JobError:
    return JobError(
        ErrorCategory.PRECONDITION_FAILED,
        f"request {request_id} can't be re-planned with its started components fixed: {why} "
        "(an option has one interval, DEC-32 rule 4)",
    )
