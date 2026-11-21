"""OVERRIDE validation (AI-060): a staff change to an option, checked with B2's own code.

CT-13 v1.1 and DEC-03: the changes are applied to the option as one combined plan, the result
is checked by B2's `check_option` (AI-051) against the live port state, and every broken rule
becomes a C-06 `validation_result` violation. Violations are warnings for the officer, not a
refusal (DEC-03). The service reads nothing itself and writes nothing.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from part1.feasibility import ConstraintType
from part2.filter import Code, FilterContext, Kind, Option, Removal, check_option
from part2.filter.pairing import truncate
from part2.state.availability import is_tug_available, without_requests
from part2.state.model import PortState

VALIDATION_TYPE: Final = "OVERRIDE"
OUTCOME_VALID: Final = "VALID"
OUTCOME_VIOLATIONS: Final = "VIOLATIONS"
MAX_VIOLATIONS: Final = 500  # CT-13

BERTH: Final = "BERTH"
PILOT: Final = "PILOT"
TUG: Final = "TUG"
START_TIME: Final = "START_TIME"

# CT-13 example keys first; the rest are Proposed in the AI-060 task decision.
MESSAGE_KEYS: Final[Mapping[str, str]] = {
    Code.MAX_DRAFT: "validation.berth.draft_exceeded",
    "MIN_UKC_M": "validation.ukc.below_minimum",
    Code.MAX_LOA: "validation.berth.loa_exceeded",
    Code.TERMINAL_COMPATIBILITY: "validation.berth.terminal_not_allowed",
    Code.BERTH_UNAVAILABLE: "validation.berth.unavailable",
    Code.BERTH_OCCUPIED: "validation.berth.occupied",
    Code.TUG_UNAVAILABLE: "validation.tug.unavailable",
    Code.TUG_COUNT: "validation.tug.count_below_minimum",
    Code.PILOT_UNAVAILABLE: "validation.pilot.unavailable",
    Code.PILOT_RANK_LIMIT: "validation.pilot.rank_limit",
    Code.ENTRY_WINDOW: "validation.start.outside_entry_window",
}
SAFETY_MESSAGE_KEY_PREFIX: Final = "validation.safety."

# Which change a code is about (`change_index`); other codes come from the combination.
_CODE_COMPONENT: Final[Mapping[str, str]] = {
    Code.MAX_LOA: BERTH,
    Code.MAX_DRAFT: BERTH,
    Code.TERMINAL_COMPATIBILITY: BERTH,
    Code.BERTH_UNAVAILABLE: BERTH,
    Code.BERTH_OCCUPIED: BERTH,
    Code.PILOT_UNAVAILABLE: PILOT,
    Code.PILOT_RANK_LIMIT: PILOT,
    Code.ENTRY_WINDOW: START_TIME,
}


class OverrideMismatchError(ValueError):
    """The changes do not fit the option (C-06 `PRECONDITION_FAILED`): for example a tug to
    replace that the option doesn't have, or a tug added that it already has."""


@dataclass(frozen=True)
class Change:
    """One `proposed_change.changes` item (C-05), as the Backend validated it."""

    component_type: str
    override_berth_id: int | None = None
    override_pilot_user_id: int | None = None
    original_tugboat_id: int | None = None
    override_tugboat_id: int | None = None
    override_start: datetime | None = None


@dataclass(frozen=True)
class Violation:
    kind: Kind
    constraint_type_code: str
    is_hard_safety_limit: bool
    message_key: str
    detail: str
    change_index: int | None

    def as_json(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "constraint_type_code": self.constraint_type_code,
            "is_hard_safety_limit": self.is_hard_safety_limit,
            "message_key": self.message_key,
            "detail": self.detail,
            "change_index": self.change_index,
            "manifest_entry_id": None,
        }


@dataclass(frozen=True)
class OverrideResult:
    subject_id: int
    option: Option  # the option with every change applied
    violations: tuple[Violation, ...]
    truncated: bool

    @property
    def outcome(self) -> str:
        return OUTCOME_VIOLATIONS if self.violations else OUTCOME_VALID

    def validation_result(self) -> dict[str, object]:
        """The C-06 `validation_result` object (`c06-completion.schema.json`)."""
        result: dict[str, object] = {
            "validation_type": VALIDATION_TYPE,
            "subject_id": self.subject_id,
            "valid": not self.violations,
            "violations": [v.as_json() for v in self.violations],
        }
        if self.truncated:
            result["violations_truncated"] = True
        return result


def parse_changes(proposed_change: Mapping[str, Any]) -> tuple[Change, ...]:
    """The C-05 `override_change` items; the envelope schema has already checked their shape."""
    changes = []
    for item in proposed_change["changes"]:
        start = item.get("override_start")
        changes.append(
            Change(
                component_type=item["component_type"],
                override_berth_id=item.get("override_berth_id"),
                override_pilot_user_id=item.get("override_pilot_user_id"),
                original_tugboat_id=item.get("original_tugboat_id"),
                override_tugboat_id=item.get("override_tugboat_id"),
                override_start=_utc(start) if start is not None else None,
            )
        )
    return tuple(changes)


def apply_changes(option: Option, changes: Sequence[Change]) -> Option:
    """The option after every change. A start change keeps the option's duration."""
    berth_id = option.berth_id
    pilot_id = option.pilot_user_id
    tugs = list(option.tug_ids)
    start, end = option.start, option.end
    for index, change in enumerate(changes):
        match change.component_type:
            case "BERTH":
                berth_id = _required(change.override_berth_id, index)
            case "PILOT":
                pilot_id = _required(change.override_pilot_user_id, index)
            case "TUG":
                tugs = _change_tug(tugs, change, index)
            case "START_TIME":
                new_start = _required(change.override_start, index)
                end = new_start + (end - start)
                start = new_start
            case other:
                raise OverrideMismatchError(f"change {index}: unknown component_type {other}")
    return Option(option.request_id, berth_id, start, end, pilot_id, tuple(tugs))


def validate_override(
    state: PortState,
    subject_id: int,
    option: Option,
    changes: Sequence[Change],
    context: FilterContext,
) -> OverrideResult:
    """B2 on the changed option. The request's own holds are dropped (its recommendation is the
    one being changed); every other hold counts."""
    changed = apply_changes(option, changes)
    check = check_option(state, changed, context)
    types = {t.code: t for t in context.constraint_types}
    unavailable = _unavailable_tugs(state, changed)
    violations = [_violation(r, changes, unavailable, types) for r in check.removals]
    return OverrideResult(
        subject_id=subject_id,
        option=changed,
        violations=tuple(violations[:MAX_VIOLATIONS]),
        truncated=len(violations) > MAX_VIOLATIONS,
    )


def _utc(text: str) -> datetime:
    """An RFC 3339 `date-time` (format checked by the schema) as aware UTC; needs an offset."""
    value = datetime.fromisoformat(text)
    if value.utcoffset() is None:
        raise OverrideMismatchError(f"override_start has no UTC offset: {text}")
    return value.astimezone(UTC)


def _required[T](value: T | None, index: int) -> T:
    if value is None:
        raise OverrideMismatchError(f"change {index} has no override value")
    return value


def _change_tug(tugs: list[int], change: Change, index: int) -> list[int]:
    original, override = change.original_tugboat_id, change.override_tugboat_id
    if original is None and override is None:
        raise OverrideMismatchError(f"change {index}: a tug change needs a tug")
    result = list(tugs)
    if original is not None:
        if original not in result:
            raise OverrideMismatchError(f"change {index}: the option has no tug {original}")
        result.remove(original)
    if override is not None:
        if override in result:
            raise OverrideMismatchError(f"change {index}: the option already has tug {override}")
        result.append(override)
    return result


def _unavailable_tugs(state: PortState, option: Option) -> frozenset[int]:
    """The option's tugs that DEC-32 finds unavailable, the request's own holds dropped."""
    confirmed = without_requests(state.confirmed_holds, [option.request_id])
    pending = without_requests(state.pending_holds, [option.request_id])
    return frozenset(
        t
        for t in option.tug_ids
        if not is_tug_available(
            state, t, option.start, option.end, confirmed_holds=confirmed, pending_holds=pending
        )
    )


def _change_index(
    removal: Removal, changes: Sequence[Change], unavailable: frozenset[int]
) -> int | None:
    """The one change a violation is about, or None when it comes from the combination."""
    if removal.kind is Kind.SAFETY:
        component: str | None = BERTH if removal.berth_id is not None else None
    elif removal.code == Code.TUG_UNAVAILABLE:
        added = [
            i
            for i, c in enumerate(changes)
            if c.component_type == TUG and c.override_tugboat_id in unavailable
        ]
        return added[0] if len(added) == 1 else None
    else:
        component = _CODE_COMPONENT.get(removal.code)
    if component is None:
        return None
    indexes = [i for i, c in enumerate(changes) if c.component_type == component]
    return indexes[0] if len(indexes) == 1 else None


def _violation(
    removal: Removal,
    changes: Sequence[Change],
    unavailable: frozenset[int],
    types: Mapping[str, ConstraintType],
) -> Violation:
    if removal.kind is Kind.SAFETY:
        ctype = types.get(removal.code)
        hard = ctype.is_hard_safety_limit if ctype is not None else True
        key = MESSAGE_KEYS.get(removal.code, SAFETY_MESSAGE_KEY_PREFIX + removal.code.lower())
    else:
        hard = False
        key = MESSAGE_KEYS[removal.code]
    return Violation(
        kind=removal.kind,
        constraint_type_code=removal.code,
        is_hard_safety_limit=hard,
        message_key=key,
        detail=truncate(removal.detail),
        change_index=_change_index(removal, changes, unavailable),
    )
